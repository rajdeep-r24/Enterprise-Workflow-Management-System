from django import forms
from .models import Designation
from django.core.exceptions import ValidationError

class DesignationForm(forms.ModelForm):
    class Meta:
        model = Designation
        fields = ["name", "code", "level", "description", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop("tenant", None)
        super().__init__(*args, **kwargs)

    def clean_code(self):
        code = self.cleaned_data["code"]
        
        qs = Designation.objects.filter(organization=self.tenant, code=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
            
        if qs.exists():
            raise ValidationError("A designation with this code already exists.")
            
        return code
