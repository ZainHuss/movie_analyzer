from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.csrf import csrf_exempt  # لإستثناء CSRF عند الحاجة

urlpatterns = [
    # صفحة رفع الملف
    path('upload/', views.upload_file, name='upload'),
    
    # صفحة عرض النتائج
    path('results/', views.show_results, name='results'),
    
    # صفحة تفاصيل الفيلم (إضافة اختيارية)
 
    
    # حذف الفيلم (إضافة اختيارية)

]

# فقط في وضع التطوير نخدم الملفات الوسائط
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)