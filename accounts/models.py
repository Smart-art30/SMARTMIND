from django.contrib.auth.models import AbstractUser
from django.db import models
from schools.models import SchoolClass
from academics.models import Subject
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.utils import timezone


class User(AbstractUser):
    ROLE_CHOICES = [
        ("school_admin", "School Admin"),
        ("teacher", "Teacher"),
        ("student", "Student"),
        ("parent", "Parent"),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="student",
        db_index=True,
    )

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
    )

    school_class = models.ForeignKey(
        "schools.SchoolClass",
        on_delete=models.SET_NULL,
        related_name="students",
        null=True,
        blank=True,
    )

    teacher_role = models.ForeignKey(
        "TeacherRole",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teachers",
    )

    admission_number = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        null=True,
        db_index=True,
    )

    employee_number = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        null=True,
        db_index=True,
    )

    tsc_number = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )

    phone_number = models.CharField(max_length=20, blank=True)
    profile_picture = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True,
    )
    date_of_birth = models.DateField(blank=True, null=True)

    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Convenience permission helpers
    def can_create_assignments(self):
        return (
            self.is_teacher
            and self.teacher_permissions
            and self.teacher_permissions.can_create_assignments
        )

    def can_add_resources(self):
        return (
            self.is_teacher
            and self.teacher_permissions
            and self.teacher_permissions.can_add_resources
        )

    def can_enter_marks(self):
        return (
            self.is_teacher
            and self.teacher_permissions
            and self.teacher_permissions.can_enter_marks
        )

    def save(self, *args, **kwargs):
        if kwargs.get("update_fields"):
            return super().save(*args, **kwargs)

        self.full_clean()
        return super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        if self.role == "teacher":
            if not self.employee_number:
                raise ValidationError({
                    "employee_number": "Teachers must have an employee number."
                })

            if not self.teacher_role:
                raise ValidationError({
                    "teacher_role": "Teachers must have a teacher role."
                })

        if self.role == "student":
            if not self.admission_number:
                raise ValidationError({
                    "admission_number": "Students must have an admission number."
                })

        if self.role != "teacher":
            self.teacher_role = None

    @property
    def full_name(self):
        return self.get_full_name() or self.username

    @property
    def is_school_admin(self):
        return self.role == "school_admin"

    @property
    def is_teacher(self):
        return self.role == "teacher"

    @property
    def is_student(self):
        return self.role == "student"

    @property
    def is_parent(self):
        return self.role == "parent"

    @property
    def teacher_permissions(self):
        return getattr(self, "permissions", None)

    def __str__(self):
        return f"{self.full_name} ({self.role})"


class TeachingAssignment(models.Model):
    school = models.ForeignKey(
    "schools.School",
    on_delete=models.CASCADE,
    related_name="teaching_assignments",
    null=True,
    blank=True,
)

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
        limit_choices_to={"role": "teacher"},
    )

    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
    )

    is_class_teacher = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.full_clean()  # [web:14]
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()  # [web:12]

        if self.teacher.school != self.school:
            raise ValidationError("Teacher does not belong to this school.")

        if self.school_class.school != self.school:
            raise ValidationError("Class does not belong to this school.")

    class Meta:
        ordering = [
            "school_class",
            "subject",
            "teacher",
        ]  # default ordering for queries [web:11]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "school",
                    "teacher",
                    "school_class",
                    "subject",
                ],
                name="unique_teacher_assignment",
            )
        ]  # [web:13]

    def __str__(self):
        return f"{self.teacher.full_name} • {self.school_class} • {self.subject}"


class TeacherPermission(models.Model):
    teacher = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="permissions",
        limit_choices_to={"role": "teacher"},
    )

    can_add_resources = models.BooleanField(default=True)
    can_edit_resources = models.BooleanField(default=True)
    can_delete_resources = models.BooleanField(default=False)
    can_create_assignments = models.BooleanField(default=True)
    can_mark_assignments = models.BooleanField(default=True)
    can_create_quizzes = models.BooleanField(default=True)
    can_mark_quizzes = models.BooleanField(default=True)
    can_enter_marks = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=False)
    can_manage_attendance = models.BooleanField(default=False)
    can_manage_blog = models.BooleanField(default=False)
    can_send_announcements = models.BooleanField(default=False)
    can_manage_library = models.BooleanField(default=False)
    can_manage_students = models.BooleanField(default=False)
    can_manage_exams = models.BooleanField(default=False)
    can_manage_timetable = models.BooleanField(default=False)
    can_manage_fee_records = models.BooleanField(default=False)
    can_manage_discipline = models.BooleanField(default=False)
    can_manage_events = models.BooleanField(default=False)
    can_download_reports = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.teacher.get_full_name()


class TeacherRole(models.Model):
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="teacher_roles",
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]  # [web:11]

        constraints = [
            models.UniqueConstraint(
                fields=["school", "name"],
                name="unique_teacher_role_per_school",
            )
        ]  # [web:13]

    def __str__(self):
        return self.name


class ParentStudent(models.Model):
    parent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="children",
        limit_choices_to={"role": "parent"},
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="parents",
        limit_choices_to={"role": "student"},
    )

    relationship = models.CharField(
        max_length=20,
        choices=[
            ("father", "Father"),
            ("mother", "Mother"),
            ("guardian", "Guardian"),
        ],
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["parent", "student"],
                name="unique_parent_student",
            )
        ]  # [web:13]

    def __str__(self):
        return f"{self.parent} → {self.student}"


@receiver(post_save, sender=User)
def create_teacher_permissions(sender, instance, created, **kwargs):
    if instance.role == "teacher":
        TeacherPermission.objects.get_or_create(teacher=instance)  # [web:14]