from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy

from .forms import LoginForm

from django.contrib.auth import logout
from django.shortcuts import redirect

class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("dashboard")

from django.views.decorators.http import require_POST

@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")

from accounts.oauth import oauth
from django.urls import reverse
from accounts.decorators import public_access
from django.utils.http import url_has_allowed_host_and_scheme
from django.shortcuts import render
from django.contrib.auth import login
from accounts.models import User

@public_access
def google_login(request):
    redirect_uri = request.build_absolute_uri(reverse('google_callback'))
    next_url = request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(url=next_url, allowed_hosts={request.get_host()}):
        request.session['oauth_next_url'] = next_url
    return oauth.google.authorize_redirect(request, redirect_uri)

@public_access
def google_callback(request):
    try:
        token = oauth.google.authorize_access_token(request)
        userinfo = token.get('userinfo')
        if not userinfo:
            userinfo = oauth.google.userinfo(token=token)
    except Exception as e:
        return render(request, "accounts/oauth_error.html", {"error": "Failed to authenticate with Google."})

    if not userinfo.get('email_verified'):
        return render(request, "accounts/oauth_error.html", {"error": "Google email must be verified."})

    email = userinfo.get('email')
    if not email:
        return render(request, "accounts/oauth_error.html", {"error": "Email address not provided by Google."})

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return render(request, "accounts/oauth_error.html", {"error": "Your Google account is not associated with an active ForgeFlow account. Contact your organization administrator."})

    if not user.is_active:
        return render(request, "accounts/oauth_error.html", {"error": "Your ForgeFlow account is inactive."})
        
    if user.user_type == "SYSTEM":
        return render(request, "accounts/oauth_error.html", {"error": "System identities cannot use interactive authentication."})

    employee = getattr(user, "employee_profile", None)
    if not employee:
        return render(request, "accounts/oauth_error.html", {"error": "Your ForgeFlow account lacks an employee profile."})

    if not employee.is_active:
        return render(request, "accounts/oauth_error.html", {"error": "Your employee profile is inactive."})

    login(request, user)
    
    next_url = request.session.pop('oauth_next_url', None)
    if next_url:
        return redirect(next_url)
    return redirect('dashboard')

