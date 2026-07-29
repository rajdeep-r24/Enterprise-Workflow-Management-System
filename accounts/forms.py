from django import forms
from django.contrib.auth.forms import AuthenticationForm


class LoginForm(AuthenticationForm):

    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "class": "ff-input",
                "placeholder": "you@company.com",
            }
        ),
    )

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "ff-input",
                "placeholder": "Enter your password",
            }
        ),
    )

from .models import User


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User

        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "date_of_birth",
        ]

        widgets = {
            "date_of_birth": forms.DateInput(
                attrs={"type": "date"}
            ),
        }

    def clean_email(self):
        email = self.cleaned_data["email"]

        if User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError("Email already exists.")

        return email
