"""
URL configuration for smartmind project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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

from accounts.views import user_login, dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path("smartmind_ai/", include("smartmind_ai.urls")),

    # apps
    path('', include('blog.urls')),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("accounts/", include("accounts.urls")),

    # auth (ONLY ONCE)
    path('login/', user_login, name='login'),
    path('dashboard/', dashboard, name='dashboard'),
    path('assignments/', include('assignments.urls')),
    path('library/',include('library.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)