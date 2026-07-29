from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.dispatch import receiver
from schools.models import School
from accounts.models import TeacherRole
from .models import User, TeacherPermission


@receiver(post_save, sender=User)
def create_teacher_permissions(sender, instance, **kwargs):
    if instance.role == "teacher":
        TeacherPermission.objects.get_or_create(
            teacher=instance
        )


DEFAULT_TEACHER_ROLES = [
    "Head Teacher",
    "Deputy Head Teacher",
    "Director of Studies",
    "Senior Teacher",
    "Class Teacher",
    "Mathematics Teacher",
    "English Teacher",
    "Kiswahili Teacher",
    "Science Teacher",
    "Social Studies Teacher",
    "CRE Teacher",
    "Agriculture Teacher",
    "Pre-Technical Teacher",
    "Computer Teacher",
    "Games Teacher",
    "Librarian",
]

@receiver(post_save, sender=School)
def create_default_teacher_roles(sender, instance, created, **kwargs):
    if created:
        for role in DEFAULT_TEACHER_ROLES:
            TeacherRole.objects.get_or_create(
                school=instance,
                name=role,
            )