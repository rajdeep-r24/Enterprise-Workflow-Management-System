from django import forms


class DynamicForm(forms.Form):

    def __init__(self, form_definition, *args, **kwargs):

        super().__init__(*args, **kwargs)

        for field in form_definition.fields.all():

            common_attrs = {
                "class": "form-control",
            }

            if field.placeholder:
                common_attrs["placeholder"] = field.placeholder

            # TEXT
            if field.field_type == "text":

                self.fields[field.field_name] = forms.CharField(
                    label=field.label,
                    required=field.is_required,
                    help_text=field.help_text,
                    widget=forms.TextInput(
                        attrs=common_attrs
                    ),
                )

            # TEXTAREA
            elif field.field_type == "textarea":

                self.fields[field.field_name] = forms.CharField(
                    label=field.label,
                    required=field.is_required,
                    help_text=field.help_text,
                    widget=forms.Textarea(
                        attrs={
                            **common_attrs,
                            "rows": 3,
                        }
                    ),
                )

            # NUMBER
            elif field.field_type == "number":

                self.fields[field.field_name] = forms.IntegerField(
                    label=field.label,
                    required=field.is_required,
                    widget=forms.NumberInput(
                        attrs=common_attrs
                    ),
                )

            # DATE
            elif field.field_type == "date":

                self.fields[field.field_name] = forms.DateField(
                    label=field.label,
                    required=field.is_required,
                    widget=forms.DateInput(
                        attrs={
                            **common_attrs,
                            "type": "date",
                        }
                    ),
                )

            # TIME
            elif field.field_type == "time":

                self.fields[field.field_name] = forms.TimeField(
                    label=field.label,
                    required=field.is_required,
                    widget=forms.TimeInput(
                        attrs={
                            **common_attrs,
                            "type": "time",
                        }
                    ),
                )

            # EMAIL
            elif field.field_type == "email":

                self.fields[field.field_name] = forms.EmailField(
                    label=field.label,
                    required=field.is_required,
                    widget=forms.EmailInput(
                        attrs=common_attrs
                    ),
                )

            # CHECKBOX
            elif field.field_type == "checkbox":

                self.fields[field.field_name] = forms.BooleanField(
                    required=False,
                    label=field.label,
                    help_text=field.help_text,
                    widget=forms.CheckboxInput(
                        attrs={
                            "class": "form-check-input",
                        }
                    ),
                )

            # SELECT
            elif field.field_type == "select":

                choices = []

                if field.options:
                    choices = [
                        (item, item)
                        for item in field.options
                    ]

                self.fields[field.field_name] = forms.ChoiceField(
                    choices=choices,
                    label=field.label,
                    required=field.is_required,
                    help_text=field.help_text,
                    widget=forms.Select(
                        attrs=common_attrs
                    ),
                )

class RequestTypeForm(forms.ModelForm):
    class Meta:
        from .models import FormDefinition
        model = FormDefinition
        fields = ["name", "code", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop("tenant", None)
        super().__init__(*args, **kwargs)

    def clean_code(self):
        code = self.cleaned_data.get("code")
        if not code:
            return code
            
        from .models import FormDefinition
        qs = FormDefinition.objects.filter(organization=self.tenant, code=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
            
        if qs.exists():
            from django.core.exceptions import ValidationError
            raise ValidationError("A request type with this code already exists.")
            
        return code

class FormFieldForm(forms.ModelForm):
    class Meta:
        from .models import FormField
        model = FormField
        fields = [
            "label",
            "field_name",
            "field_type",
            "is_required",
            "order",
            "placeholder",
            "help_text",
            "options",
        ]
        widgets = {
            "help_text": forms.Textarea(attrs={"rows": 2}),
            "options": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "options": "For select fields, enter options as a JSON array of strings (e.g., [\"Option 1\", \"Option 2\"]). Leave blank for other field types.",
            "field_name": "A unique identifier for this field (e.g., 'first_name'). Only lowercase letters, numbers, and underscores.",
        }

    def __init__(self, *args, **kwargs):
        self.form_definition = kwargs.pop("form_definition", None)
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'

    def clean_field_name(self):
        field_name = self.cleaned_data.get("field_name")
        if not field_name:
            return field_name
            
        from .models import FormField
        qs = FormField.objects.filter(form=self.form_definition, field_name=field_name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
            
        if qs.exists():
            from django.core.exceptions import ValidationError
            raise ValidationError("A field with this name already exists in this form.")
            
        return field_name

class WorkflowStepForm(forms.ModelForm):
    class Meta:
        from workflow.models import WorkflowStepDefinition
        model = WorkflowStepDefinition
        fields = [
            "name",
            "step_order",
            "approver_type",
            "role_code",
            "specific_approver",
            "is_required",
        ]

    def __init__(self, *args, **kwargs):
        self.workflow_version = kwargs.pop("workflow_version", None)
        self.tenant = kwargs.pop("tenant", None)
        super().__init__(*args, **kwargs)
        
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'
                
        # Limit specific_approver to users in the current tenant
        if self.tenant:
            from accounts.models import User
            from employees.models import Employee
            user_ids = Employee.objects.filter(organization=self.tenant).values_list('user_id', flat=True)
            self.fields['specific_approver'].queryset = User.objects.filter(id__in=user_ids)
            
        # Make role_code a choice field using existing roles
        from rbac.models import Role
        roles = Role.objects.filter(is_active=True).values_list('code', 'name')
        choices = [('', '---------')] + list(roles)
        self.fields['role_code'] = forms.ChoiceField(
            choices=choices,
            required=False,
            widget=forms.Select(attrs={'class': 'form-control'})
        )
        self.fields['role_code'].label = "Role"
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Always set step_type to APPROVAL
        instance.step_type = "APPROVAL"
        if commit:
            instance.save()
        return instance
