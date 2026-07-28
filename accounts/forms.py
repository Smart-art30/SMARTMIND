from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from schools.models import School, SchoolClass
from django import forms
from django.forms import ModelForm

from academics.models import Subject
from schools.models import SchoolClass

from .models import User, TeachingAssignment, TeacherPermission


User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
  
    school = forms.ModelChoiceField(
        queryset=School.objects.all(),
        required=False
    )

    school_class = forms.ModelChoiceField(
        queryset=SchoolClass.objects.none(),
        required=False
    )

    role = forms.ChoiceField(
        choices=[
            ("student", "Student"),
            ("teacher", "Teacher"),
            ("parent", "Parent"),
            ("school_admin", "School Admin"),
        ]
    )

    tsc_number = forms.CharField(required=False)
    admission_number = forms.CharField(
        required=False
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "role",
            "school",
            "school_class",
            "admission_number",
            "tsc_number",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        placeholders = {
            "admission_number": "Enter admission number",
            "username": "Enter username",
            "email": "Enter email address",
            "role": "Select role",
            "school": "Select school",
            "school_class": "Select class",
            "tsc_number": "TSC number (teachers only)",
            "password1": "Create password",
            "password2": "Confirm password",
        }

        for name, field in self.fields.items():
            field.widget.attrs.update({
                "class": "form-control"
            })

            if name in placeholders:
                field.widget.attrs.update({
                    "placeholder": placeholders[name]
                })
        
        # 🔥 FIX: Load classes for selected school (MOVED INSIDE __init__)
        if "school" in self.data:
            try:
                school_id = int(self.data.get("school"))
                self.fields["school_class"].queryset = SchoolClass.objects.filter(
                    school_id=school_id,
                    is_active=True
                ).order_by("order")
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.school:
            self.fields["school_class"].queryset = SchoolClass.objects.filter(
                school=self.instance.school,
                is_active=True
            ).order_by("order")

    def clean(self):
        cleaned_data = super().clean()

        role = cleaned_data.get("role")
        school = cleaned_data.get("school")
        school_class = cleaned_data.get("school_class")
        tsc = (cleaned_data.get("tsc_number") or "").strip()

        cleaned_data["tsc_number"] = tsc or None

        # Ensure selected class belongs to selected school
        if school and school_class:
            if school_class.school != school:
                self.add_error(
                    "school_class",
                    "Selected class does not belong to the selected school."
                )

        # ======================
        # TEACHER RULES
        # ======================
        if role == "teacher":
            if not tsc:
                self.add_error("tsc_number", "TSC number is required for teachers.")

            if not school:
                self.add_error("school", "Teachers must select a school.")

            # teachers do NOT need class
            cleaned_data["school_class"] = None

        # ======================
        # STUDENT RULES
        # ======================
        elif role == "student":



            admission = cleaned_data.get("admission_number")

            if not admission:
                self.add_error(
                    "admission_number",
                    "Students must provide an admission number."
                )

            if not school:
                self.add_error(
                    "school",
                    "Students must select a school."
                )

            if not school_class:
                self.add_error(
                    "school_class",
                    "Students must select a class."
                )

            cleaned_data["tsc_number"] = None

        # ======================
        # PARENT RULES
        # ======================
        elif role == "parent":
            cleaned_data["school"] = None
            cleaned_data["school_class"] = None
            cleaned_data["tsc_number"] = None

        # ======================
        # ADMIN RULES
        # ======================
        elif role == "school_admin":
            cleaned_data["school"] = None
            cleaned_data["school_class"] = None
            cleaned_data["tsc_number"] = None

        return cleaned_data
class TeacherForm(forms.ModelForm):

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "username",
            "email",
            "employee_number",
            "tsc_number",
            "phone_number",
            "teacher_role",
            "is_active",
        ]

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["teacher_role"].queryset = TeacherRole.objects.none()

        if school:
            self.fields["teacher_role"].queryset = (
                TeacherRole.objects.filter(school=school)
            )

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

from .models import TeachingAssignment

class TeachingAssignmentForm(forms.ModelForm):

    class Meta:
        model = TeachingAssignment
        fields = [
            "teacher",
            "school_class",
            "subject",
            "is_class_teacher",
        ]

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)

        if school:

            self.fields["teacher"].queryset = User.objects.filter(
                school=school,
                role="teacher",
            ).order_by("first_name", "last_name")

            self.fields["school_class"].queryset = SchoolClass.objects.filter(
                school=school,
                is_active=True,
            ).order_by("order")

            self.fields["subject"].queryset = Subject.objects.filter(
                school=school,
            ).order_by("name")

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class TeacherPermissionForm(forms.ModelForm):

    class Meta:

        model = TeacherPermission

        exclude = [
            "teacher",
            "created_at",
            "updated_at",
        ]