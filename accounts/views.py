from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib.auth import logout, login as auth_login
from .forms import LoginForm


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        if user and getattr(user, "requires_password_change", False):
            auth_login(self.request, user)
            return redirect("password_change")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("dashboard")


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)
        if getattr(self.request.user, "requires_password_change", False):
            self.request.user.requires_password_change = False
            self.request.user.save(update_fields=["requires_password_change"])
        messages.success(self.request, "Your password has been changed successfully.")
        return response


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
        return render(request, "accounts/oauth_error.html", {"error": "Your Google account is not associated with an active Anukram account. Contact your organization administrator."})

    if not user.is_active:
        return render(request, "accounts/oauth_error.html", {"error": "Your Anukram account is inactive."})
        
    if user.user_type == "SYSTEM":
        return render(request, "accounts/oauth_error.html", {"error": "System identities cannot use interactive authentication."})

    employee = getattr(user, "employee_profile", None)
    if not employee:
        return render(request, "accounts/oauth_error.html", {"error": "Your Anukram account lacks an employee profile."})

    if not employee.is_active:
        return render(request, "accounts/oauth_error.html", {"error": "Your employee profile is inactive."})

    login(request, user)
    
    next_url = request.session.pop('oauth_next_url', None)
    if next_url:
        return redirect(next_url)
    return redirect('dashboard')

