from django.urls import path
from django.contrib.auth import views as auth_views

from .views import CustomLoginView, logout_view, google_login, google_callback
from . import views

from accounts.decorators import public_access

urlpatterns = [
    path(
        "login/",
        public_access(CustomLoginView.as_view()),
        name="login",
    ),

    path(
        "login/google/",
        views.google_login,
        name="google_login",
    ),

    path(
        "login/google/callback/",
        views.google_callback,
        name="google_callback",
    ),

    path(
        "logout/",
        logout_view,
        name="logout",
    ),

    path(
        "accounts/password-change/",
        views.CustomPasswordChangeView.as_view(),
        name="password_change",
    ),
    path(
        "password-change/",
        views.CustomPasswordChangeView.as_view(),
    ),
    path(
        "password-reset/",
        public_access(auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset.html",
            email_template_name="accounts/password_reset_email.txt",
            html_email_template_name="accounts/password_reset_email.html",
            subject_template_name="accounts/password_reset_subject.txt",
        )),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        public_access(auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html",
        )),
        name="password_reset_done",
    ),
    path(
        "password-reset/confirm/<uidb64>/<token>/",
        public_access(auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
        )),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        public_access(auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html",
        )),
        name="password_reset_complete",
    ),
]
