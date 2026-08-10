from django.conf import settings
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field


class ChatMessage(models.Model):
    ROLE_CHOICES = (
        ("user", "User"),
        ("assistant", "Assistant"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    message = CKEditor5Field(
    config_name="default",
    blank=True,
)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.role}"