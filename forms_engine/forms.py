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
    code = forms.CharField(required=False)

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
            from api.services.code_generation import CodeGenerationService
            name = self.cleaned_data.get("name", "")
            code = CodeGenerationService.generate("requesttype", name, self.tenant)
            
        from .models import FormDefinition
        qs = FormDefinition.objects.filter(organization=self.tenant, code=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
            
        if qs.exists():
            from django.core.exceptions import ValidationError
            raise ValidationError("A request type with this code already exists.")
            
        return code

class FormFieldForm(forms.ModelForm):
    field_name = forms.SlugField(required=False)
    order = forms.IntegerField(required=False)
    options = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

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
        }
        help_texts = {
            "options": "Enter options separated by commas (e.g., Dell, HP, Lenovo). Leave blank for non-select fields.",
        }

    def __init__(self, *args, **kwargs):
        self.form_definition = kwargs.pop("form_definition", None)
        super().__init__(*args, **kwargs)
        
        if not self.instance.pk:
            self.initial['is_required'] = True
            
        if self.instance.pk and self.instance.options:
            if isinstance(self.instance.options, list):
                self.initial['options'] = ", ".join(self.instance.options)
                
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'

    def clean_field_name(self):
        field_name = self.cleaned_data.get("field_name")
        if not field_name:
            from django.utils.text import slugify
            label = self.cleaned_data.get("label", "")
            field_name = slugify(label).replace("-", "_")
            
        from .models import FormField
        qs = FormField.objects.filter(form=self.form_definition, field_name=field_name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
            
        if qs.exists():
            from django.core.exceptions import ValidationError
            raise ValidationError("A field with this name already exists in this form.")
            
        return field_name

    def clean_options(self):
        options_text = self.cleaned_data.get("options")
        if options_text:
            import re
            parts = re.split(r'[,\n]', options_text)
            return [p.strip() for p in parts if p.strip()]
        return []

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.order:
            from django.db import models
            from .models import FormField
            max_order = FormField.objects.filter(form=self.form_definition).aggregate(models.Max('order'))['order__max']
            instance.order = (max_order or 0) + 1
        if commit:
            instance.save()
        return instance

class WorkflowStepForm(forms.ModelForm):
    step_order = forms.IntegerField(required=False)

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
        
        if not self.instance.pk:
            self.initial['approver_type'] = 'MANAGER'
        
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
        instance.step_type = "APPROVAL"
        if not instance.step_order:
            from django.db import models
            from workflow.models import WorkflowStepDefinition
            max_order = WorkflowStepDefinition.objects.filter(workflow_version=self.workflow_version).aggregate(models.Max('step_order'))['step_order__max']
            instance.step_order = (max_order or 0) + 1
        if commit:
            instance.save()
        return instance
