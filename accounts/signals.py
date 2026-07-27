from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User, TeacherPermission


@receiver(post_save, sender=User)
def create_teacher_permissions(sender, instance, **kwargs):
    if instance.role == "teacher":
        TeacherPermission.objects.get_or_create(
            teacher=instance
        )