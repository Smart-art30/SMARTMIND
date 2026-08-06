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
    Question,
    Assessment,
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
            "description": CKEditor5Widget(config_name="extends"),
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

        self.fields["resource_type"].queryset = ResourceType.objects.order_by("name")
        self.fields["access_level"].queryset = AccessLevel.objects.order_by("name")
        self.fields["visibility"].queryset = Visibility.objects.order_by("name")
        self.fields["lesson"].queryset = Lesson.objects.none()

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
            self.fields[field].widget.attrs.update({"class": "form-select"})

        text_fields = ["title", "external_url", "duration", "order"]

        for field in text_fields:
            self.fields[field].widget.attrs.update({"class": "form-control"})

        self.fields["file"].widget.attrs.update({"class": "form-control"})
        self.fields["thumbnail"].widget.attrs.update({"class": "form-control"})

        if self.data:
            level_id = self.data.get("level")
            class_id = self.data.get("curriculum_class")
            subject_id = self.data.get("subject")
            topic_id = self.data.get("topic")
            subtopic_id = self.data.get("subtopic")

            if level_id:
                self.fields["curriculum_class"].queryset = (
                    CurriculumClass.objects.filter(level_id=level_id).order_by("order")
                )

            if class_id:
                self.fields["subject"].queryset = (
                    Subject.objects.filter(curriculum_class_id=class_id).order_by("order")
                )

            if subject_id:
                self.fields["topic"].queryset = (
                    Topic.objects.filter(subject_id=subject_id).order_by("order")
                )

            if topic_id:
                self.fields["subtopic"].queryset = (
                    SubTopic.objects.filter(topic_id=topic_id).order_by("order")
                )

            if subtopic_id:
                self.fields["lesson"].queryset = (
                    Lesson.objects.filter(
                        subtopic_id=subtopic_id,
                        is_published=True,
                    ).order_by("order")
                )

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
                CurriculumClass.objects.filter(level=level).order_by("order")
            )

            self.fields["subject"].queryset = (
                Subject.objects.filter(curriculum_class=curriculum_class).order_by("order")
            )

            self.fields["topic"].queryset = (
                Topic.objects.filter(subject=subject).order_by("order")
            )

            self.fields["subtopic"].queryset = (
                SubTopic.objects.filter(topic=topic).order_by("order")
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


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = [
            "assessment",
            "question_type",
            "question",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "answer",
            "marks",
            "order",
            "explanation",
        ]

        widgets = {
            "question": CKEditor5Widget(config_name="default"),
            "explanation": CKEditor5Widget(config_name="default"),
            "assessment": forms.Select(attrs={"class": "form-select"}),
            "question_type": forms.Select(attrs={"class": "form-select"}),
            "option_a": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Option A"}
            ),
            "option_b": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Option B"}
            ),
            "option_c": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Option C"}
            ),
            "option_d": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Option D"}
            ),
            "answer": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Correct Answer"}
            ),
            "marks": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        }

    def clean(self):
        cleaned_data = super().clean()
        question_type = cleaned_data.get("question_type")
        option_a = cleaned_data.get("option_a")
        option_b = cleaned_data.get("option_b")
        option_c = cleaned_data.get("option_c")
        option_d = cleaned_data.get("option_d")
        answer = cleaned_data.get("answer")

        if question_type == "mcq":
            options = [option_a, option_b, option_c, option_d]
            if not all(options):
                raise forms.ValidationError(
                    "All four options are required for Multiple Choice questions."
                )

            if answer not in ["A", "B", "C", "D"]:
                raise forms.ValidationError(
                    "Correct answer must be A, B, C or D."
                )

        elif question_type == "true_false":
            if answer not in ["True", "False"]:
                raise forms.ValidationError("Answer must be True or False.")

        return cleaned_data



class TakeAssessmentForm(forms.Form):

    def __init__(self, *args, questions=None, **kwargs):
        super().__init__(*args, **kwargs)

        if not questions:
            return

        for question in questions:

            field_name = f"question_{question.id}"

            if question.question_type == "mcq":

                self.fields[field_name] = forms.ChoiceField(
                    label="",
                    choices=[
                        ("A", question.option_a),
                        ("B", question.option_b),
                        ("C", question.option_c),
                        ("D", question.option_d),
                    ],
                    widget=forms.RadioSelect,
                    required=True,
                )

            elif question.question_type == "true_false":

                self.fields[field_name] = forms.ChoiceField(
                    label="",
                    choices=[
                        ("True", "True"),
                        ("False", "False"),
                    ],
                    widget=forms.RadioSelect,
                    required=True,
                )

            elif question.question_type == "short":

                self.fields[field_name] = forms.CharField(
                    label="",
                    widget=forms.TextInput(
                        attrs={
                            "class": "form-control",
                            "placeholder": "Type your answer...",
                        }
                    ),
                    required=True,
                )

            elif question.question_type == "essay":

                self.fields[field_name] = forms.CharField(
                    label="",
                    widget=CKEditor5Widget(
                        config_name="extends"
                    ),
                    required=True,
                )



class AssessmentForm(forms.ModelForm):

    class Meta:
        model = Assessment

        fields = [
            "title",
            "instructions",
            "time_limit",
            "passing_score",
            "is_published",
        ]

        widgets = {

            "title": forms.TextInput(
                attrs={
                    "class":"form-control",
                    "placeholder":"Assessment title"
                }
            ),

            "instructions": CKEditor5Widget(
                config_name="default"
            ),

            "time_limit": forms.NumberInput(
                attrs={
                    "class":"form-control",
                    "min":1
                }
            ),

            "passing_score": forms.NumberInput(
                attrs={
                    "class":"form-control",
                    "min":0,
                    "max":100
                }
            ),

            "is_published": forms.CheckboxInput(
                attrs={
                    "class":"form-check-input"
                }
            ),

        }