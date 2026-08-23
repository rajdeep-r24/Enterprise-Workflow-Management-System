from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class OrganizationSignupForm(forms.Form):
    organization_name = forms.CharField(
        max_length=255, 
        label="Organization Name",
        widget=forms.TextInput(attrs={
            "class": "ff-input",
            "placeholder": "Acme Corp",
        })
    )
    
    first_name = forms.CharField(
        max_length=150, 
        label="First Name",
        widget=forms.TextInput(attrs={
            "class": "ff-input",
            "placeholder": "Rajvee",
        })
    )
    last_name = forms.CharField(
        max_length=150, 
        label="Last Name",
        widget=forms.TextInput(attrs={
            "class": "ff-input",
            "placeholder": "Rathod",
        })
    )
    
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={
            "class": "ff-input",
            "placeholder": "you@company.com",
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "ff-input",
            "placeholder": "Create a password",
        }), 
        label="Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "ff-input",
            "placeholder": "Confirm password",
        }), 
        label="Confirm Password"
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        
        return cleaned_data
