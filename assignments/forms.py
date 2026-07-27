from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget
from .models import Submission


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ["content", "file"]

        widgets = {
            "content": CKEditor5Widget(config_name="extends"),
        }