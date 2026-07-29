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

    password = forms.CharField(
        widget=forms.PasswordInput()
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput()
    )

    # ---------- Employee ----------

    employee_code = forms.CharField(max_length=20)

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

        super().__init__(*args, **kwargs)

        from organizations.models import Organization
        from departments.models import Department
        from locations.models import Location
        from designations.models import Designation
        from rbac.models import Role

        self.fields["organization"].queryset = Organization.objects.all()

        self.fields["department"].queryset = Department.objects.all()

        self.fields["location"].queryset = Location.objects.all()

        self.fields["designation"].queryset = Designation.objects.all()

        self.fields["role"].queryset = Role.objects.all()

        self.fields["manager"].queryset = Employee.objects.all()

    def clean_email(self):

        email = self.cleaned_data["email"]

        if User.objects.filter(email=email).exists():
            raise ValidationError(
                "Email already exists."
            )

        return email

    def clean_employee_code(self):

        code = self.cleaned_data["employee_code"]

        if Employee.objects.filter(
            employee_code=code
        ).exists():
            raise ValidationError(
                "Employee code already exists."
            )

        return code

    def clean(self):

        cleaned_data = super().clean()

        password = cleaned_data.get("password")

        confirm = cleaned_data.get("confirm_password")

        if password != confirm:

            raise ValidationError(
                "Passwords do not match."
            )

        validate_password(password)

        return cleaned_data

    @transaction.atomic
    def save(self):

        user = User.objects.create_user(

            username=self.cleaned_data["email"],

            email=self.cleaned_data["email"],

            first_name=self.cleaned_data["first_name"],

            last_name=self.cleaned_data["last_name"],

            phone=self.cleaned_data["phone"],

            date_of_birth=self.cleaned_data["date_of_birth"],

            password=self.cleaned_data["password"],
        )

        employee = Employee.objects.create(

            user=user,

            employee_code=self.cleaned_data["employee_code"],

            organization=self.cleaned_data["organization"],

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
