from django.contrib import messages
from django.shortcuts import redirect
from functools import wraps


def school_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated:
            return redirect("login")

        if request.user.is_superuser or request.user.role == "school_admin":
            return view_func(request, *args, **kwargs)

        messages.error(
            request,
            "You do not have permission to manage resources."
        )

        return redirect("library:resource_list")   # ✅ Fixed

    return wrapper