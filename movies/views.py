from django.shortcuts import render, redirect
from django_tables2 import RequestConfig
from django.db.models import Avg, Max, Min, Count
from django.conf import settings
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import transaction, IntegrityError, DatabaseError, OperationalError
from .forms import UploadFileForm
from .tables import MovieTable
from .models import Movie
import pandas as pd
import os
import logging
import traceback
import time
from django.http import HttpResponse
from django.db import connection



logger = logging.getLogger(__name__)

def show_results(request):
    """عرض صفحة نتائج تحليل الأفلام مع تحسينات التعامل مع قاعدة البيانات"""
    try:
        # التحقق من وجود الجدول أولاً
        if 'movies_movie' not in connection.introspection.table_names():
            raise DatabaseError("جدول الأفلام غير موجود في قاعدة البيانات")
        
        # استخدام select_related/prefetch_related إذا كانت هناك علاقات
        movies = Movie.objects.all()
        
        # حساب الإحصائيات مع التعامل مع القيم الفارغة
        stats = {
            'avg_rating': movies.aggregate(avg=Avg('rating'))['avg'] or 0,
            'max_rating': movies.aggregate(max=Max('rating'))['max'] or 0,
            'min_rating': movies.aggregate(min=Min('rating'))['min'] or 0,
            'avg_revenue': movies.aggregate(avg=Avg('revenue'))['avg'] or 0,
            'total_movies': movies.count()
        }
        
        # الحصول على أعلى القيم مع التحقق من وجود بيانات
        highest_values = {
            'highest_rating': movies.order_by('-rating').first(),
            'highest_revenue': movies.order_by('-revenue').first(),
            'highest_metascore': movies.order_by('-metascore').first(),
            'most_votes': movies.order_by('-votes').first(),
        }

        # إعداد الجدول مع التعامل مع الأخطاء
        table = MovieTable(movies)
        RequestConfig(request, paginate={'per_page': 25}).configure(table)
        
        context = {
            'table': table,
            'stats': stats,
            'highest_values': highest_values,
            'messages': messages.get_messages(request)
        }
        
        return render(request, 'movies/results.html', context)
        
    except (DatabaseError, OperationalError) as e:
        logger.critical(f"Database error: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, 'خطأ في قاعدة البيانات. الرجاء التأكد من تهيئة الجداول.')
        return render(request, 'movies/error.html', {
            'error_type': 'database',
            'error_details': str(e)
        })
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, 'حدث خطأ غير متوقع في عرض النتائج')
        return render(request, 'movies/error.html', {
            'error_type': 'general',
            'error_details': str(e)
        })
from django.shortcuts import render, redirect
from django_tables2 import RequestConfig
from django.db.models import Avg, Max, Min, Count
from django.conf import settings
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import transaction, IntegrityError, DatabaseError, OperationalError
from .forms import UploadFileForm
from .tables import MovieTable
from .models import Movie
import pandas as pd
import os
import logging
import traceback
import time
from django.http import HttpResponse
from django.db import connection
from django.core.exceptions import ValidationError  # تمت إضافته

logger = logging.getLogger(__name__)
def upload_file(request):
    """دالة محسنة لرفع الملفات مع معالجة متقدمة للأخطاء"""
    if request.method != 'POST':
        form = UploadFileForm()
        return render(request, 'movies/upload.html', {'form': form})

    form = UploadFileForm(request.POST, request.FILES)
    if not form.is_valid():
        # تسجيل تفاصيل الأخطاء للتصحيح
        for field, errors in form.errors.items():
            for error in errors:
                logger.error(f"Form error in {field}: {error}")
        return render(request, 'movies/upload.html', {'form': form})

    file = request.FILES['file']
    temp_path = None
    
    try:
        # === التحقق من وجود الجدول أولاً ===
        if 'movies_movie' not in connection.introspection.table_names():
            raise DatabaseError("جدول الأفلام غير موجود في قاعدة البيانات")

        # === معالجة الملف ===
        file_name = file.name
        file_ext = os.path.splitext(file_name)[1].lower()
        
        # حفظ الملف مؤقتاً
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads')
        os.makedirs(temp_dir, exist_ok=True)
        temp_filename = f"upload_{int(time.time())}{file_ext}"
        temp_path = default_storage.save(f'temp_uploads/{temp_filename}', ContentFile(file.read()))
        file_path = default_storage.path(temp_path)

        # قراءة الملف بناءً على نوعه
        try:
            if file_ext == '.csv':
                df = pd.read_csv(file_path, encoding='utf-8-sig')
            else:
                # محاولة قراءة الملف بكل المحركات المتاحة
                try:
                    engine = 'openpyxl' if file_ext == '.xlsx' else 'xlrd'
                    df = pd.read_excel(file_path, engine=engine)
                except Exception as e:
                    logger.warning(f"Failed to read with {engine}, trying other engines")
                    try:
                        df = pd.read_excel(file_path, engine=None)  # حاول مع جميع المحركات المتاحة
                    except Exception as e:
                        raise ValueError(f'لا يمكن قراءة ملف Excel: {str(e)}')
            
            if df.empty:
                raise ValueError('لا توجد بيانات في الملف')
                
            # توحيد أسماء الأعمدة
            df.columns = df.columns.str.strip().str.lower()
            
        except Exception as e:
            raise ValueError(f'خطأ في قراءة الملف: {str(e)}')

        # === التحقق من البيانات ===
        required_columns = {'title', 'year', 'rating'}
        missing_cols = required_columns - set(df.columns.str.lower())
        if missing_cols:
            raise ValueError(f'الأعمدة المطلوبة مفقودة: {", ".join(missing_cols)}')

        # === تحضير البيانات ===
        movies_to_create = []
        error_rows = []
        
        for idx, row in df.iterrows():
            try:
                movie_data = {
                    'title': str(row['title']).strip()[:255] if pd.notna(row.get('title')) else None,
                    'year': int(row['year']) if pd.notna(row.get('year')) else None,
                    'rating': float(row['rating']) if pd.notna(row.get('rating')) else 0.0,
                    'genre': str(row.get('genre', '')).strip()[:255] if pd.notna(row.get('genre')) else '',
                    'director': str(row.get('director', '')).strip()[:255] if pd.notna(row.get('director')) else '',
                    'runtime': int(row.get('runtime', 0)) if pd.notna(row.get('runtime')) else 0,
                    'votes': int(row.get('votes', 0)) if pd.notna(row.get('votes')) else 0,
                    'revenue': float(row.get('revenue', 0.0)) if pd.notna(row.get('revenue')) else 0.0,
                    'metascore': int(row.get('metascore', 0)) if pd.notna(row.get('metascore')) else 0,
                }
                
                # التحقق من صحة البيانات
                if not movie_data['title']:
                    raise ValidationError('عنوان الفيلم مطلوب')
                    
                if movie_data['year'] is None:
                    raise ValidationError('سنة الإنتاج مطلوبة')
                    
                if not (1888 <= movie_data['year'] <= 2100):
                    raise ValidationError('سنة الإنتاج يجب أن تكون بين 1888 و 2100')
                    
                if not (0 <= movie_data['rating'] <= 10):
                    raise ValidationError('التقييم يجب أن يكون بين 0 و 10')
                    
                movies_to_create.append(Movie(**movie_data))
                
            except Exception as e:
                error_rows.append((idx + 2, str(e)))
                continue

        if not movies_to_create:
            raise ValueError('لا توجد بيانات صالحة للحفظ')

        # === حفظ البيانات ===
        with transaction.atomic():
            created_movies = Movie.objects.bulk_create(
                movies_to_create,
                batch_size=50,
                ignore_conflicts=True
            )
            created_count = len(created_movies)
            
            result_msg = f'تم حفظ {created_count} أفلام بنجاح'
            if error_rows:
                result_msg += f' (تم تجاهل {len(error_rows)} صفاً)'
                logger.warning(f"Rows with errors: {error_rows}")
            
            messages.success(request, result_msg)
            return redirect('results')
            
    except ValueError as e:
        messages.error(request, str(e))
        logger.error(f"Validation error: {str(e)}")
    except (DatabaseError, OperationalError) as e:
        logger.critical(f"Database error: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, 'خطأ في قاعدة البيانات. الرجاء التأكد من تهيئة الجداول.')
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, 'حدث خطأ غير متوقع أثناء معالجة الملف')
    finally:
        if temp_path and default_storage.exists(temp_path):
            try:
                default_storage.delete(temp_path)
            except Exception as e:
                logger.error(f"Error deleting temp file: {str(e)}")

    return render(request, 'movies/upload.html', {'form': form})