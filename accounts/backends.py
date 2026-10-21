# accounts/backends.py
from django.contrib.auth.backends import ModelBackend


class ApprovalBackend(ModelBackend):
    """
    Rejects login for non-superusers who have not been approved by a superadmin.
    Superusers bypass the check.
    """
    def user_can_authenticate(self, user):
        if user.is_superuser:
            return True
        if not getattr(user, "is_approved", False):
            return False
        return super().user_can_authenticate(user)