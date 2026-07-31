from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseForbidden

class LoginRequiredMiddleware:
    """
    Middleware that enforces a default-deny policy.
    Requires authentication for all views unless they are explicitly marked as public.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        
        # Ensure LOGIN_URL is defined, fallback if not
        self.login_url = getattr(settings, 'LOGIN_URL', '/login/')

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        # 1. Exempt admin paths, as Django admin handles its own authentication
        if request.path.startswith('/admin/'):
            return None

        # 2. Check if view is explicitly marked as public
        is_public = getattr(view_func, 'is_public', False)
        
        # Some class-based views might have the attribute on the view_class
        if not is_public and hasattr(view_func, 'view_class'):
            is_public = getattr(view_func.view_class, 'is_public', False)

        # 3. Block unauthenticated access to non-public views
        if not request.user.is_authenticated and not is_public:
            return redirect(self.login_url)
            
        # 4. System accounts cannot log in interactively / use web views
        if request.user.is_authenticated and request.user.user_type == "SYSTEM":
            return HttpResponseForbidden("System identities cannot be used for interactive access.")

        return None
