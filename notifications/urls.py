from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_list, name="list"),
    path("<int:pk>/read/", views.mark_notification_read, name="mark-read"),
    path("mark-all-read/", views.mark_all_notifications_read, name="mark-all-read"),
]
