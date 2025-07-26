import logging
import os
from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator
from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)

class UploadFileForm(forms.Form):
    """
    نموذج لتحميل ملفات الأفلام مع تحسينات للتعامل مع ملفات Excel التي يتم التعرف عليها كـ zip
    """
    
    file = forms.FileField(
        label=_('اختر ملف بيانات الأفلام'),
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.xls,.csv',
            'id': 'fileInput',
            'required': 'required',
            'aria-label': _('رفع ملف بيانات الأفلام')
        }),
        help_text=_('''
            <div class="file-requirements mt-2">
                <ul class="list-unstyled small text-muted">
                    <li><i class="fas fa-check-circle text-success me-2"></i> %(extensions)s</li>
                    <li><i class="fas fa-check-circle text-success me-2"></i> %(size_limit)s</li>
                </ul>
            </div>
        ''') % {
            'extensions': _('الامتدادات المسموحة: .xlsx, .xls, .csv'),
            'size_limit': _('الحد الأقصى للحجم: 15MB')
        },
        validators=[
            FileExtensionValidator(
                allowed_extensions=['xlsx', 'xls', 'csv'],
                message=_('نوع الملف غير مدعوم. يرجى استخدام ملف Excel أو CSV')
            )
        ]
    )

    def clean_file(self):
        """
        التحقق المتقدم من صحة الملف المرفوع مع تحسينات لملفات Excel
        """
        file = self.cleaned_data.get('file')
        
        if not file:
            raise forms.ValidationError(
                _('الرجاء اختيار ملف للرفع'),
                code='missing_file'
            )

        # التحقق من حجم الملف (15MB كحد أقصى)
        max_size = 15 * 1024 * 1024
        if file.size > max_size:
            raise forms.ValidationError(
                _('حجم الملف كبير جداً (%(size)sMB). الحد الأقصى المسموح به هو %(max_size)sMB'),
                params={
                    'size': round(file.size / (1024 * 1024), 2),
                    'max_size': 15
                },
                code='file_too_large'
            )

        # التحقق من أن الملف ليس فارغاً
        if file.size == 0:
            raise forms.ValidationError(
                _('الملف فارغ'),
                code='empty_file'
            )

        # التحقق من الامتداد
        file_name = file.name
        ext = os.path.splitext(file_name)[1].lower()
        
        if ext not in ['.xlsx', '.xls', '.csv']:
            raise forms.ValidationError(
                _('امتداد الملف "%(ext)s" غير مسموح به'),
                params={'ext': ext},
                code='invalid_extension'
            )

        # التحقق من نوع الملف بناءً على المحتوى (MIME Type)
        try:
            import magic
            mime = magic.Magic(mime=True)
            file.seek(0)
            mime_type = mime.from_buffer(file.read(1024))
            file.seek(0)

            # قائمة بأنواع MIME المسموحة بما فيها zip لملفات Excel الحديثة
            allowed_mime_types = [
                'application/vnd.ms-excel',  # للـ XLS القديم
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # للـ XLSX
                'application/zip',  # لأن بعض ملفات XLSX يتم التعرف عليها كـ zip
                'text/csv',
                'text/plain',
                'application/octet-stream'
            ]

            if mime_type not in allowed_mime_types:
                logger.warning(f"نوع MIME غير متطابق: {mime_type} لملف {file_name}")
                
                # إذا كان الامتداد xlsx/xls والـ mime_type هو zip، نعتبره صالحاً
                if ext in ['.xlsx', '.xls'] and mime_type == 'application/zip':
                    return file
                
                raise forms.ValidationError(
                    _('نوع الملف الحقيقي (%(mime_type)s) لا يتطابق مع الامتداد'),
                    params={'mime_type': mime_type},
                    code='invalid_mime_type'
                )

        except ImportError:
            logger.warning("لم يتم العثور على مكتبة python-magic، سيتم التحقق من الامتداد فقط")
        except Exception as e:
            logger.error(f"خطأ في التحقق من نوع الملف: {str(e)}", exc_info=True)
            # في حالة الخطأ، نستمر مع التحقق الأساسي بدلاً من رفض الملف
            pass

        # التحقق من محتوى الملف فعلياً عن طريق محاولة قراءته
        try:
            file.seek(0)
            
            if ext == '.csv':
                # قراءة أول سطر للتحقق من أنه CSV صالح
                first_line = file.read(1024).decode('utf-8-sig').split('\n')[0]
                file.seek(0)
                if not first_line.strip():
                    raise forms.ValidationError(
                        _('ملف CSV فارغ أو غير صالح'),
                        code='invalid_csv'
                    )
            else:
                # محاولة قراءة ملف Excel
                import pandas as pd
                try:
                    if ext == '.xlsx':
                        engine = 'openpyxl'
                    else:  # .xls
                        engine = 'xlrd'
                    
                    # قراءة أول صف فقط للتحقق
                    df = pd.read_excel(file, engine=engine, nrows=1)
                    file.seek(0)
                    
                    if df.empty:
                        raise forms.ValidationError(
                            _('ملف Excel فارغ أو غير صالح'),
                            code='invalid_excel'
                        )
                except ImportError as e:
                    logger.error(f"مكتبة Pandas أو محرك Excel غير مثبت: {str(e)}")
                    # إذا لم تكن المكتبات مثبتة، نتخطى التحقق الدقيق
                    pass
                except Exception as e:
                    raise forms.ValidationError(
                        _('لا يمكن قراءة ملف Excel: %(error)s'),
                        params={'error': str(e)},
                        code='unreadable_excel'
                    )
        except UnicodeDecodeError:
            raise forms.ValidationError(
                _('تنسيق الملف غير صالح (غير قادر على فك الترميز)'),
                code='encoding_error'
            )
        except Exception as e:
            raise forms.ValidationError(
                _('تعذر قراءة الملف: %(error)s'),
                params={'error': str(e)},
                code='unreadable_file'
            )

        return file