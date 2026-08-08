from django.contrib import messages
from django.shortcuts import redirect
from functools import wraps

def school_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        # Allow superusers, school admins, and teachers
        if request.user.is_superuser or request.user.role in ("school_admin", "teacher"):
            return view_func(request, *args, **kwargs)

        messages.error(
            request,
            "You do not have permission to manage resources."
        )

        return redirect("library:resource_list")

    return wrapper