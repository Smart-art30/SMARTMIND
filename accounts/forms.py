from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from academics.models import Subject
from .models import (
    User,
    TeacherRole,
    TeacherPermission,
    TeachingAssignment,
)
from schools.models import School, SchoolClass
from .models import TeacherRole

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    school = forms.ModelChoiceField(
        queryset=School.objects.all(),
        required=False,
    )

    school_class = forms.ModelChoiceField(
        queryset=SchoolClass.objects.none(),
        required=False,
    )

    teacher_role = forms.ModelChoiceField(
        queryset=TeacherRole.objects.none(),
        required=False,
    )

    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
    )

    admission_number = forms.CharField(required=False)
    tsc_number = forms.CharField(required=False)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "role",
            "school",
            "school_class",
            "teacher_role",
            "admission_number",
            "tsc_number",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Bootstrap styling
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

        self.fields["username"].widget.attrs["placeholder"] = "Username"
        self.fields["email"].widget.attrs["placeholder"] = "Email"
        self.fields["school"].widget.attrs["placeholder"] = "School"
        self.fields["school_class"].widget.attrs["placeholder"] = "Class"
        self.fields["teacher_role"].widget.attrs["placeholder"] = "Teacher Role"
        self.fields["admission_number"].widget.attrs["placeholder"] = "Admission Number"
        self.fields["tsc_number"].widget.attrs["placeholder"] = "TSC Number"
        self.fields["password1"].widget.attrs["placeholder"] = "Password"
        self.fields["password2"].widget.attrs["placeholder"] = "Confirm Password"

        # Load classes and teacher roles according to selected school
        if "school" in self.data:
            try:
                school_id = int(self.data.get("school"))

                self.fields["school_class"].queryset = (
                    SchoolClass.objects.filter(
                        school_id=school_id,
                        is_active=True,
                    ).order_by("order")
                )

                self.fields["teacher_role"].queryset = (
                    TeacherRole.objects.filter(
                        school_id=school_id,
                    ).order_by("name")
                )

            except (ValueError, TypeError):
                pass

        elif self.instance.pk and self.instance.school:

            self.fields["school_class"].queryset = (
                SchoolClass.objects.filter(
                    school=self.instance.school,
                    is_active=True,
                ).order_by("order")
            )

            self.fields["teacher_role"].queryset = (
                TeacherRole.objects.filter(
                    school=self.instance.school,
                ).order_by("name")
            )

    def clean(self):
        cleaned_data = super().clean()

        role = cleaned_data.get("role")
        school = cleaned_data.get("school")
        school_class = cleaned_data.get("school_class")
        teacher_role = cleaned_data.get("teacher_role")

        admission_number = (
            cleaned_data.get("admission_number") or ""
        ).strip()

        tsc_number = (
            cleaned_data.get("tsc_number") or ""
        ).strip()

        cleaned_data["admission_number"] = admission_number or None
        cleaned_data["tsc_number"] = tsc_number or None

        # Ensure class belongs to selected school
        if school and school_class:
            if school_class.school != school:
                self.add_error(
                    "school_class",
                    "Selected class does not belong to the selected school.",
                )

        # Ensure teacher role belongs to selected school
        if school and teacher_role:
            if teacher_role.school != school:
                self.add_error(
                    "teacher_role",
                    "Selected teacher role does not belong to the selected school.",
                )

        # -------------------------
        # Teacher
        # -------------------------
        if role == "teacher":

            if not school:
                self.add_error(
                    "school",
                    "Teachers must select a school.",
                )

            if not teacher_role:
                self.add_error(
                    "teacher_role",
                    "Teachers must select a teacher role.",
                )

            if not tsc_number:
                self.add_error(
                    "tsc_number",
                    "Teachers must provide a TSC number.",
                )

            cleaned_data["school_class"] = None
            cleaned_data["admission_number"] = None

        # -------------------------
        # Student
        # -------------------------
        elif role == "student":

            if not school:
                self.add_error(
                    "school",
                    "Students must select a school.",
                )

            if not school_class:
                self.add_error(
                    "school_class",
                    "Students must select a class.",
                )

            if not admission_number:
                self.add_error(
                    "admission_number",
                    "Students must provide an admission number.",
                )

            cleaned_data["teacher_role"] = None
            cleaned_data["tsc_number"] = None

        # -------------------------
        # Parent
        # -------------------------
        elif role == "parent":

            cleaned_data["school"] = None
            cleaned_data["school_class"] = None
            cleaned_data["teacher_role"] = None
            cleaned_data["admission_number"] = None
            cleaned_data["tsc_number"] = None

        # -------------------------
        # School Admin
        # -------------------------
        elif role == "school_admin":

            cleaned_data["school_class"] = None
            cleaned_data["teacher_role"] = None
            cleaned_data["admission_number"] = None
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

        if school:
            self.fields["teacher_role"].queryset = (
                TeacherRole.objects.filter(school=school)
            )
        else:
            self.fields["teacher_role"].queryset = TeacherRole.objects.none()

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


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
            )

            self.fields["school_class"].queryset = SchoolClass.objects.filter(
                school=school,
                is_active=True,
            )

            self.fields["subject"].queryset = Subject.objects.filter(
                school=school,
            )


class TeacherPermissionForm(forms.ModelForm):

    class Meta:
        model = TeacherPermission
        exclude = [
            "teacher",
            "created_at",
            "updated_at",
        ]