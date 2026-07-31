class TenantMiddleware:
    """
    Middleware that resolves the current tenant (Organization) 
    based on the authenticated user's Employee profile.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None

        if request.user.is_authenticated:
            # Check if user has an employee profile
            if hasattr(request.user, 'employee_profile'):
                request.tenant = request.user.employee_profile.organization

        response = self.get_response(request)
        return response
