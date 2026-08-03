from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget

from .models import (
    Resource,
    Lesson,
    ResourceType,
    AccessLevel,
    Visibility,
    Level,
    CurriculumClass,
    Subject,
    Topic,
    SubTopic,
)


class ResourceForm(forms.ModelForm):

    level = forms.ModelChoiceField(
        queryset=Level.objects.order_by("order"),
        required=False,
        empty_label="Select Level",
    )

    curriculum_class = forms.ModelChoiceField(
        queryset=CurriculumClass.objects.none(),
        required=False,
        empty_label="Select Curriculum Class",
    )

    subject = forms.ModelChoiceField(
        queryset=Subject.objects.none(),
        required=False,
        empty_label="Select Subject",
    )

    topic = forms.ModelChoiceField(
        queryset=Topic.objects.none(),
        required=False,
        empty_label="Select Topic",
    )

    subtopic = forms.ModelChoiceField(
        queryset=SubTopic.objects.none(),
        required=False,
        empty_label="Select Sub Topic",
    )

    class Meta:
        model = Resource

        fields = [
            "access_level",
            "level",
            "curriculum_class",
            "subject",
            "topic",
            "subtopic",
            "lesson",
            "resource_type",
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
            "description": CKEditor5Widget(
                config_name="extends"
            ),

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter resource title",
                }
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
                    "min": 0,
                }
            ),

            "file": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "thumbnail": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        kwargs.pop("user", None)

        super().__init__(*args, **kwargs)

        # ---------------------------------------
        # Querysets
        # ---------------------------------------

        self.fields["resource_type"].queryset = (
            ResourceType.objects.order_by("name")
        )

        self.fields["access_level"].queryset = (
            AccessLevel.objects.order_by("name")
        )

        self.fields["visibility"].queryset = (
            Visibility.objects.order_by("name")
        )

        self.fields["lesson"].queryset = Lesson.objects.none()

        # ---------------------------------------
        # Bootstrap styling
        # ---------------------------------------

        select_fields = [
            "access_level",
            "level",
            "curriculum_class",
            "subject",
            "topic",
            "subtopic",
            "lesson",
            "resource_type",
            "visibility",
        ]

        for field in select_fields:
            self.fields[field].widget.attrs.update({
                "class": "form-select"
            })

        text_fields = [
            "title",
            "external_url",
            "duration",
            "order",
        ]

        for field in text_fields:
            self.fields[field].widget.attrs.update({
                "class": "form-control"
            })

        self.fields["file"].widget.attrs.update({
            "class": "form-control"
        })

        self.fields["thumbnail"].widget.attrs.update({
            "class": "form-control"
        })

        # ---------------------------------------
        # POST (Create)
        # ---------------------------------------

        if self.data:

            level_id = self.data.get("level")
            class_id = self.data.get("curriculum_class")
            subject_id = self.data.get("subject")
            topic_id = self.data.get("topic")
            subtopic_id = self.data.get("subtopic")

            if level_id:

                self.fields["curriculum_class"].queryset = (
                    CurriculumClass.objects.filter(
                        level_id=level_id
                    ).order_by("order")
                )

            if class_id:

                self.fields["subject"].queryset = (
                    Subject.objects.filter(
                        curriculum_class_id=class_id
                    ).order_by("order")
                )

            if subject_id:

                self.fields["topic"].queryset = (
                    Topic.objects.filter(
                        subject_id=subject_id
                    ).order_by("order")
                )

            if topic_id:

                self.fields["subtopic"].queryset = (
                    SubTopic.objects.filter(
                        topic_id=topic_id
                    ).order_by("order")
                )

            if subtopic_id:

                self.fields["lesson"].queryset = (
                    Lesson.objects.filter(
                        subtopic_id=subtopic_id,
                        is_published=True,
                    ).order_by("order")
                )

        # ---------------------------------------
        # EDIT
        # ---------------------------------------

        elif self.instance.pk:

            lesson = self.instance.lesson
            subtopic = lesson.subtopic
            topic = subtopic.topic
            subject = topic.subject
            curriculum_class = subject.curriculum_class
            level = curriculum_class.level

            self.initial["level"] = level
            self.initial["curriculum_class"] = curriculum_class
            self.initial["subject"] = subject
            self.initial["topic"] = topic
            self.initial["subtopic"] = subtopic

            self.fields["curriculum_class"].queryset = (
                CurriculumClass.objects.filter(
                    level=level
                ).order_by("order")
            )

            self.fields["subject"].queryset = (
                Subject.objects.filter(
                    curriculum_class=curriculum_class
                ).order_by("order")
            )

            self.fields["topic"].queryset = (
                Topic.objects.filter(
                    subject=subject
                ).order_by("order")
            )

            self.fields["subtopic"].queryset = (
                SubTopic.objects.filter(
                    topic=topic
                ).order_by("order")
            )

            self.fields["lesson"].queryset = (
                Lesson.objects.filter(
                    subtopic=subtopic,
                    is_published=True,
                ).order_by("order")
            )

    def clean(self):

        cleaned_data = super().clean()

        uploaded_file = cleaned_data.get("file")
        external_url = cleaned_data.get("external_url")

        if not uploaded_file and not external_url:
            raise forms.ValidationError(
                "Please upload a file or provide an external URL."
            )

        return cleaned_data