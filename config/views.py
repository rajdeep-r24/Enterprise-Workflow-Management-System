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


@public_access
def health_check(request):
    """
    Public health check endpoint for uptime monitors and load balancers.
    Verifies application and PostgreSQL database connectivity.
    Returns HTTP 200 on healthy, HTTP 503 if database check fails.
    Never leaks credentials, hostnames, SQL queries, or stack traces.
    """
    from django.db import connection
    from django.http import JsonResponse
    from django.utils import timezone

    db_ok = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            row = cursor.fetchone()
            if row and row[0] == 1:
                db_ok = True
    except Exception:
        db_ok = False

    if db_ok:
        return JsonResponse(
            {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": timezone.now().isoformat(),
            },
            status=200,
        )
    else:
        return JsonResponse(
            {
                "status": "unhealthy",
                "version": "1.0.0",
                "timestamp": timezone.now().isoformat(),
            },
            status=503,
        )


@public_access
def security_architecture(request):
    """
    Public Security & Architecture documentation page.
    Explains Anukram's tenant isolation, RBAC, QR token verification,
    and audit trail logging.
    """
    return render(request, "security_architecture.html")



