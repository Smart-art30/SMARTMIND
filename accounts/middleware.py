
from django.contrib import messages
from django.shortcuts import redirect


class ApprovalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user

        if not user.is_authenticated:
            return self.get_response(request)

        # Superadmins and school admins can manage their permitted tasks.
        if user.is_superuser or getattr(user, "role", None) == "school_admin":
            return self.get_response(request)

        # Allow access to login and logout pages.
        if request.resolver_match and request.resolver_match.url_name in {
            "login",
            "logout",
        }:
            return self.get_response(request)

        # Check approval for other users only when the field exists.
        if hasattr(user, "is_approved") and not user.is_approved:
            messages.warning(
                request,
                "Your account is awaiting administrator approval.",
            )
            return redirect("login")

        return self.get_response(request)
