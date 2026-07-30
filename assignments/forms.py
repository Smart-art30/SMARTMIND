from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget
from .models import Submission, Assignment


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ["content", "file"]

        widgets = {
            "content": CKEditor5Widget(config_name="extends"),
        }


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = [
            "title",
            "description",
            "school_class",
            "subject",
            "assignment_type",
            "due_date",
            "attachment",
        ]

        widgets = {
            "description": CKEditor5Widget(config_name="extends"),
            "due_date": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }