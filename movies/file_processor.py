import pandas as pd
import logging
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from .models import Movie

logger = logging.getLogger(__name__)

class FileProcessor:
    """فئة لمعالجة ملفات الأفلام وتحويلها إلى بيانات يمكن تخزينها"""

    @staticmethod
    def validate_file(file):
        """
        التحقق من صحة الملف قبل معالجته
        """
        if not file.name.endswith(('.csv', '.xls', '.xlsx')):
            raise ValueError(_('نوع الملف غير مدعوم. يرجى استخدام ملف CSV أو Excel'))
        
        if file.size > 10 * 1024 * 1024:  # 10MB كحد أقصى
            raise ValueError(_('حجم الملف يتجاوز الحد المسموح (10MB)'))

    @staticmethod
    def process_file(file_path):
        """
        معالجة الملف وتحويله إلى DataFrame
        """
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file_path)
            else:
                raise ValueError(_('نوع الملف غير مدعوم'))
            
            # تنظيف البيانات: إزالة مسافات زائدة من أسماء الأعمدة
            df.columns = df.columns.str.strip()
            
            return df
            
        except pd.errors.EmptyDataError:
            raise ValueError(_('الملف فارغ أو لا يحتوي على بيانات'))
        except pd.errors.ParserError:
            raise ValueError(_('تنسيق الملف غير صحيح أو تالف'))
        except Exception as e:
            logger.error(f"خطأ في معالجة الملف: {str(e)}")
            raise ValueError(_('حدث خطأ أثناء قراءة الملف'))

    @staticmethod
    def validate_dataframe(df):
        """
        التحقق من وجود الأعمدة الأساسية في DataFrame
        """
        required_columns = {
            'title': ['title', 'film', 'movie', 'اسم الفيلم'],
            'year': ['year', 'release_year', 'سنة', 'سنة الإصدار'],
            'rating': ['rating', 'score', 'تقييم']
        }
        
        column_mapping = {}
        
        for field, possible_names in required_columns.items():
            for name in possible_names:
                if name in df.columns:
                    column_mapping[field] = name
                    break
            else:
                raise ValueError(_(f'عمود {field} مفقود في الملف'))
        
        return column_mapping

    @staticmethod
    def convert_to_movies_data(df, column_mapping=None):
        """
        تحويل DataFrame إلى قواميس جاهزة لحفظها في قاعدة البيانات
        """
        if column_mapping is None:
            column_mapping = FileProcessor.validate_dataframe(df)
        
        movies_data = []
        
        for _, row in df.iterrows():
            try:
                movie_data = {
                    'title': str(row[column_mapping['title']]).strip(),
                    'year': int(row[column_mapping['year']]),
                    'rating': float(row[column_mapping['rating']]),
                    # يمكن إضافة المزيد من الحقول هنا حسب الحاجة
                }
                
                # معالجة حقول اختيارية
                if 'revenue' in df.columns:
                    movie_data['revenue'] = float(row['revenue']) if pd.notna(row['revenue']) else None
                
                if 'runtime' in df.columns:
                    movie_data['runtime'] = int(row['runtime']) if pd.notna(row['runtime']) else None
                
                movies_data.append(movie_data)
                
            except (ValueError, TypeError) as e:
                logger.warning(f"خطأ في تحويل بيانات الفيلم: {str(e)}")
                continue
                
        return movies_data

    @staticmethod
    def create_movie_objects(movies_data):
        """
        إنشاء كائنات Movie من البيانات المعالجة
        """
        movies_to_create = []
        error_rows = []
        
        for idx, data in enumerate(movies_data, start=2):  # الصفوف تبدأ من 2 في Excel
            try:
                # التحقق من صحة البيانات قبل الإنشاء
                if not data['title'] or len(str(data['title']).strip()) == 0:
                    raise ValueError(_('اسم الفيلم لا يمكن أن يكون فارغًا'))
                
                if data['year'] < 1900 or data['year'] > 2100:
                    raise ValueError(_('سنة الإصدار غير صالحة'))
                
                if data['rating'] < 0 or data['rating'] > 10:
                    raise ValueError(_('التقييم يجب أن يكون بين 0 و 10'))
                
                movies_to_create.append(Movie(**data))
                
            except Exception as e:
                error_rows.append((idx, str(e)))
                continue
                
        return movies_to_create, error_rows