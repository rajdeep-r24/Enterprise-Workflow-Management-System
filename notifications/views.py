from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Notification
from .services import NotificationService


@login_required
def notification_list(request):
    notifications = (
        Notification.objects.filter(recipient=request.user)
        .select_related("workflow_instance")
        .order_by("-created_at", "-pk")
    )
    return render(
        request,
        "notifications/list.html",
        {
            "notifications": notifications,
            "unread_count": NotificationService.unread_count(request.user),
        },
    )


@login_required
@require_POST
def mark_notification_read(request, pk):
    notification = get_object_or_404(
        Notification,
        pk=pk,
        recipient=request.user,
    )
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return redirect("notifications:list")


@login_required
@require_POST
def mark_all_notifications_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect("notifications:list")
