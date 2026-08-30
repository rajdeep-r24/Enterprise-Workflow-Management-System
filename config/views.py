import os
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from accounts.decorators import public_access


@public_access
def error_400(request, exception=None):
    return render(request, "400.html", status=400)


@public_access
def error_403(request, exception=None):
    return render(request, "403.html", status=403)


@public_access
def error_404(request, exception=None):
    return render(request, "404.html", status=404)


@public_access
def error_500(request):
    return render(request, "500.html", status=500)


@public_access
def robots_txt(request):
    robots_path = os.path.join(settings.BASE_DIR, "static", "robots.txt")
    if os.path.exists(robots_path):
        with open(robots_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "User-agent: *\nAllow: /\nSitemap: https://anukram.onrender.com/sitemap.xml\n"
    return HttpResponse(content, content_type="text/plain")


@public_access
def sitemap_xml(request):
    sitemap_path = os.path.join(settings.BASE_DIR, "static", "sitemap.xml")
    if os.path.exists(sitemap_path):
        with open(sitemap_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://anukram.onrender.com/</loc></url></urlset>'
    return HttpResponse(content, content_type="application/xml")


