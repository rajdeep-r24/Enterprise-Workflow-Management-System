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

    location_type = forms.ChoiceField(choices=[])
    custom_location_type = forms.CharField(max_length=100, required=False, label="Custom Location Type")

    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop("tenant", None)
        super().__init__(*args, **kwargs)
        
        # Build choices
        choices = list(Location.LOCATION_TYPES) + [("OTHER", "Other")]
        self.fields["location_type"].choices = choices
        
        # If instance has a custom location type, select "OTHER" and set custom value
        if self.instance and self.instance.pk:
            current_type = self.instance.location_type
            if current_type not in dict(Location.LOCATION_TYPES):
                self.initial["location_type"] = "OTHER"
                self.initial["custom_location_type"] = current_type

    def clean_code(self):
        code = self.cleaned_data["code"]
        
        qs = Location.objects.filter(organization=self.tenant, code=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
            
        if qs.exists():
            raise ValidationError("A location with this code already exists.")
            
        return code

    def clean(self):
        cleaned_data = super().clean()
        loc_type = cleaned_data.get("location_type")
        custom_loc_type = cleaned_data.get("custom_location_type")
        
        if loc_type == "OTHER":
            if not custom_loc_type:
                self.add_error("custom_location_type", "Custom Location Type is required when 'Other' is selected.")
            else:
                cleaned_data["location_type"] = custom_loc_type
        return cleaned_data
