from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import User
from .models import Employee


class EmployeeRegistrationForm(forms.Form):

    # ---------- User ----------

    first_name = forms.CharField(max_length=150)

    last_name = forms.CharField(max_length=150)

    email = forms.EmailField()

    phone = forms.CharField(max_length=15, required=False)

    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"})
    )

    # ---------- Employee ----------

    organization = forms.ModelChoiceField(
        queryset=None
    )

    department = forms.ModelChoiceField(
        queryset=None
    )

    location = forms.ModelChoiceField(
        queryset=None
    )

    designation = forms.ModelChoiceField(
        queryset=None
    )

    role = forms.ModelChoiceField(
        queryset=None
    )

    manager = forms.ModelChoiceField(
        queryset=None,
        required=False
    )

    joining_date = forms.DateField(
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    is_active = forms.BooleanField(
        required=False,
        initial=True
    )

    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)

        from organizations.models import Organization
        from departments.models import Department
        from locations.models import Location
        from designations.models import Designation
        from rbac.models import Role

        if self.tenant:
            self.fields["organization"].queryset = Organization.objects.filter(pk=self.tenant.pk)
            self.fields["organization"].initial = self.tenant
            self.fields["organization"].widget = forms.HiddenInput()
            
            self.fields["department"].queryset = Department.objects.for_tenant(self.tenant)
            self.fields["location"].queryset = Location.objects.for_tenant(self.tenant)
            self.fields["designation"].queryset = Designation.objects.for_tenant(self.tenant)
            self.fields["manager"].queryset = Employee.objects.for_tenant(self.tenant)
        else:
            self.fields["organization"].queryset = Organization.objects.none()
            self.fields["department"].queryset = Department.objects.none()
            self.fields["location"].queryset = Location.objects.none()
            self.fields["designation"].queryset = Designation.objects.none()
            self.fields["manager"].queryset = Employee.objects.none()

        self.fields["role"].queryset = Role.objects.all()

    def clean_email(self):

        email = self.cleaned_data["email"]

        if User.objects.filter(email=email).exists():
            raise ValidationError(
                "Email already exists."
            )

        return email


    @transaction.atomic
    def save(self):

        user = User.objects.create_user(

            username=self.cleaned_data["email"],

            email=self.cleaned_data["email"],

            first_name=self.cleaned_data["first_name"],

            last_name=self.cleaned_data["last_name"],

            phone=self.cleaned_data["phone"],

            date_of_birth=self.cleaned_data["date_of_birth"],

            is_active=False,
        )

        org = self.cleaned_data["organization"]

        # Generate employee code
        latest_employee = Employee.objects.filter(
            organization=org,
            employee_code__regex=r'^EMP\d{4}$'
        ).order_by('-employee_code').first()

        if latest_employee:
            last_num = int(latest_employee.employee_code[3:])
            new_code = f"EMP{last_num + 1:04d}"
        else:
            new_code = "EMP0001"

        employee = Employee.objects.create(

            user=user,

            employee_code=new_code,

            organization=org,

            department=self.cleaned_data["department"],

            location=self.cleaned_data["location"],

            designation=self.cleaned_data["designation"],

            role=self.cleaned_data["role"],

            manager=self.cleaned_data["manager"],

            joining_date=self.cleaned_data["joining_date"],

            is_active=self.cleaned_data["is_active"],
        )

        return employee
    
from django.forms import ModelForm


class EmployeeForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        
        if self.tenant:
            from departments.models import Department
            from locations.models import Location
            from designations.models import Designation
            from rbac.models import Role
            
            self.fields["organization"].queryset = self.tenant.__class__.objects.filter(pk=self.tenant.pk)
            self.fields["organization"].widget = forms.HiddenInput()
            
            self.fields["department"].queryset = Department.objects.for_tenant(self.tenant)
            self.fields["location"].queryset = Location.objects.for_tenant(self.tenant)
            self.fields["designation"].queryset = Designation.objects.for_tenant(self.tenant)
            self.fields["manager"].queryset = Employee.objects.for_tenant(self.tenant)
            self.fields["role"].queryset = Role.objects.all()
        else:
            self.fields["organization"].queryset = self.fields["organization"].queryset.none()
            self.fields["department"].queryset = self.fields["department"].queryset.none()
            self.fields["location"].queryset = self.fields["location"].queryset.none()
            self.fields["designation"].queryset = self.fields["designation"].queryset.none()
            self.fields["manager"].queryset = self.fields["manager"].queryset.none()

    class Meta:
        model = Employee

        fields = [
            "organization",
            "department",
            "location",
            "designation",
            "role",
            "employee_code",
            "manager",
            "joining_date",
            "is_active",
        ]

        widgets = {
            "joining_date": forms.DateInput(
                attrs={"type": "date"}
            )
        }

class EmployeeOnboardingForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "New Password"})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm Password"})
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")

        if password and confirm:
            if password != confirm:
                raise ValidationError("Passwords do not match.")
            validate_password(password)

        return cleaned_data
