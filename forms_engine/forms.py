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
