"""
URL configuration for movie_analyzer project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve  # للتعامل مع الملفات في production
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from movies.views import upload_file
  # للملفات الثابتة

urlpatterns = [
    path('admin/', admin.site.urls),
     path('', upload_file, name='upload'),
    
    # تضمين روابط التطبيق movies
    path('', include('movies.urls')),
]

# إعدادات التطوير (الملفات الثابتة والوسائط)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    # إعدادات الإنتاج (لخدمة الملفات الثابتة والوسائط)
    urlpatterns += [
        path(f'{settings.MEDIA_URL.lstrip("/")}<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
        path(f'{settings.STATIC_URL.lstrip("/")}<path:path>', serve, {'document_root': settings.STATIC_ROOT}),
    ]

# تضمين أنماط الملفات الثابتة
urlpatterns += staticfiles_urlpatterns()