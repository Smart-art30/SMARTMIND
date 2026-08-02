from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget

from .models import (
    Resource,
    Lesson,
    ResourceType,
    AccessLevel,
    Visibility,
)


class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = [
            "lesson",
            "resource_type",
            "access_level",
            "visibility",
            "title",
            "description",
            "file",
            "external_url",
            "duration",
            "thumbnail",
            "order",
        ]

        widgets = {
            "lesson": forms.Select(attrs={"class": "form-select"}),
            "resource_type": forms.Select(attrs={"class": "form-select"}),
            "access_level": forms.Select(attrs={"class": "form-select"}),
            "visibility": forms.Select(attrs={"class": "form-select"}),

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter resource title",
                }
            ),

            "description": CKEditor5Widget(
                config_name="extends"
            ),

            "file": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),

            "external_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://example.com",
                }
            ),

            "duration": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                }
            ),

            "thumbnail": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),

            "order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Querysets
        self.fields["lesson"].queryset = (
            Lesson.objects.filter(is_published=True)
            .select_related(
                "subtopic",
                "subtopic__topic",
                "subtopic__topic__subject",
            )
            .order_by(
                "subtopic__topic__subject__name",
                "subtopic__topic__title",
                "title",
            )
        )

        self.fields["resource_type"].queryset = (
            ResourceType.objects.order_by("name")
        )

        self.fields["access_level"].queryset = (
            AccessLevel.objects.order_by("name")
        )

        self.fields["visibility"].queryset = (
            Visibility.objects.order_by("name")
        )

        # Apply Bootstrap styling to all fields except CKEditor
        for name, field in self.fields.items():
            if name != "description":
                existing = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{existing} form-control".strip()

    def clean(self):
        cleaned_data = super().clean()

        uploaded_file = cleaned_data.get("file")
        external_url = cleaned_data.get("external_url")

        if not uploaded_file and not external_url:
            raise forms.ValidationError(
                "Please upload a file or provide an external URL."
            )

        return cleaned_data