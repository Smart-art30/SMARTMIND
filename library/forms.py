from django import forms

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

            "title": forms.TextInput(attrs={"class": "form-control"}),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                }
            ),

            "file": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),

            "external_url": forms.URLInput(
                attrs={"class": "form-control"}
            ),

            "duration": forms.NumberInput(
                attrs={"class": "form-control"}
            ),

            "thumbnail": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),

            "order": forms.NumberInput(
                attrs={"class": "form-control"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
            ResourceType.objects.order_by("order")
        )

        self.fields["access_level"].queryset = (
            AccessLevel.objects.all()
        )

        self.fields["visibility"].queryset = (
            Visibility.objects.all()
        )

    def clean(self):
        cleaned_data = super().clean()

        file = cleaned_data.get("file")
        external_url = cleaned_data.get("external_url")

        if not file and not external_url:
            raise forms.ValidationError(
                "Please upload a file or provide an external URL."
            )

        return cleaned_data