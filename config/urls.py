"""
URL configuration for config project.

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
from django.urls import include, path

from django.conf import settings
from django.conf.urls.static import static
from config import views as config_views

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("accounts.urls")),
    path("", include("dashboards.urls")),
    path("", include("departments.urls")),
    path("", include("designations.urls")),
    path("", include("locations.urls")),
    path("", include("employees.urls")),
    path("", include("organizations.urls")),
    path("", include("forms_engine.urls")),
    path("notifications/", include("notifications.urls", namespace="notifications")),
    path("api/", include("api.urls")),
    path("robots.txt", config_views.robots_txt, name="robots_txt"),
    path("sitemap.xml", config_views.sitemap_xml, name="sitemap_xml"),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )

handler400 = "config.views.error_400"
handler403 = "config.views.error_403"
handler404 = "config.views.error_404"
handler500 = "config.views.error_500"

