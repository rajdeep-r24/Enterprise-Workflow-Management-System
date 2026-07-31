from django import forms
from .models import Location
from django.core.exceptions import ValidationError

class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = [
            "name", "code", "location_type", "address", 
            "city", "state", "country", "is_active"
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop("tenant", None)
        super().__init__(*args, **kwargs)

    def clean_code(self):
        code = self.cleaned_data["code"]
        
        qs = Location.objects.filter(organization=self.tenant, code=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
            
        if qs.exists():
            raise ValidationError("A location with this code already exists.")
            
        return code
