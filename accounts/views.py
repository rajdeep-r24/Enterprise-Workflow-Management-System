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

def logout_view(request):
    logout(request)
    return redirect("login")
