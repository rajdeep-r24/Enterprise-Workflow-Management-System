from .services import NotificationService


def unread_notifications(request):
    if not request.user.is_authenticated:
        return {"unread_notifications": []}
    return {
        "unread_notifications": NotificationService.unread_count(request.user),
    }
