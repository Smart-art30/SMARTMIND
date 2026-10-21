from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect


class ApprovalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if not request.user.is_superuser and not getattr(request.user, "is_approved", False):
                logout(request)
                messages.warning(
                    request,
                    "Your account is awaiting administrator approval.",
                )
                return redirect("login")
        return self.get_response(request)