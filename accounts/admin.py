# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import User


# ------------------------------------------------------------------
# Small helper for status pills in the list view
# ------------------------------------------------------------------
def _status_pill(label, bg, fg):
    return format_html(
        '<span style="display:inline-block;padding:2px 8px;border-radius:999px;'
        'font-size:11px;font-weight:700;background:{};color:{};">{}</span>',
        bg, fg, label,
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):

    # ==============================================================
    # LIST VIEW
    # ==============================================================
    list_display = (
        "username",
        "email",
        "role",
        "school",
        "approval_status",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "role",
        "school",
        "is_approved",
        "is_staff",
        "is_superuser",
        "is_active",
    )

    search_fields = (
        "username",
        "email",
        "admission_number",
        "employee_number",
    )

    ordering = ("-approval_requested_at",)

    # ==============================================================
    # BULK ACTIONS
    # ==============================================================
    actions = ("approve_users", "reject_users")

    @admin.action(description=" Approve selected accounts")
    def approve_users(self, request, queryset):
        ok = 0
        failed = []
        for user in queryset.filter(is_superuser=False):
            try:
                user.is_approved = True
                user.approved_by = request.user
                user.save()
                ok += 1
            except ValidationError as exc:
                failed.append(f"{user.username}: {exc.messages[0] if exc.messages else 'invalid'}")

        self.message_user(request, f"{ok} account(s) approved.")
        if failed:
            self.message_user(
                request,
                "Failed: " + "; ".join(failed[:5]) + (" …" if len(failed) > 5 else ""),
                level="warning",
            )

    @admin.action(description=" Reject selected accounts")
    def reject_users(self, request, queryset):
        ok = 0
        failed = []
        for user in queryset.filter(is_superuser=False):
            try:
                user.is_approved = False
                user.is_active = False
                user.approved_by = None
                user.save()
                ok += 1
            except ValidationError as exc:
                failed.append(f"{user.username}: {exc.messages[0] if exc.messages else 'invalid'}")

        self.message_user(request, f"{ok} account(s) rejected.")
        if failed:
            self.message_user(
                request,
                "Failed: " + "; ".join(failed[:5]) + (" …" if len(failed) > 5 else ""),
                level="warning",
            )

    # ==============================================================
    # CUSTOM LIST COLUMNS
    # ==============================================================
    @admin.display(description="Approval")
    def approval_status(self, obj):
        if obj.is_superuser:
            return _status_pill("SUPERUSER", "#e0e7ff", "#3730a3")
        if obj.role == "student":
            return _status_pill("STUDENT · AUTO", "#dcfce7", "#166534")
        if obj.is_approved:
            return _status_pill("APPROVED", "#dcfce7", "#166534")
        return _status_pill("PENDING", "#fef3c7", "#92400e")

    # ==============================================================
    # CHANGE FORM
    # ==============================================================
    fieldsets = (
        (None, {
            "fields": ("username", "password"),
        }),
        ("Personal info", {
            "fields": ("first_name", "last_name", "email"),
        }),
        ("Permissions", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            ),
        }),
        ("Important dates", {
            "fields": ("last_login", "date_joined"),
        }),
        ("SmartMind Information", {
            "fields": (
                "role",
                "school",
                "school_class",
                "admission_number",
                "employee_number",
                "teacher_role",
                "tsc_number",
                "phone_number",
                "profile_picture",
                "date_of_birth",
                "is_verified",
            ),
        }),
        ("Account Approval", {
            "fields": (
                "is_approved",
                "approved_by",
                "approval_requested_at",
            ),
            "description": (
                "Only superusers can set <strong>is_approved</strong>. "
                "Students are auto-approved by <code>User.clean()</code>. "
                "Teachers, parents, and school admins must be approved here "
                "or via the "
                "<a href='/accounts/pending/'>pending approvals queue</a>."
            ),
        }),
    )

    readonly_fields = (
        "approval_requested_at",
    )

    # ==============================================================
    # ADD FORM
    # ==============================================================
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "password1", "password2"),
        }),
        ("Personal info", {
            "classes": ("wide",),
            "fields": ("first_name", "last_name", "email"),
        }),
        ("SmartMind Information", {
            "classes": ("wide",),
            "fields": (
                "role",
                "school",
                "school_class",
                "admission_number",
                "employee_number",
                "teacher_role",
                "tsc_number",
                "phone_number",
                "date_of_birth",
            ),
        }),
        ("Account Approval", {
            "classes": ("wide",),
            "fields": (
                "is_approved",
                "approved_by",
            ),
        }),
    )

    # ==============================================================
    # CHANGELIST BANNER — links to the pending queue
    # ==============================================================
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        if request.user.is_superuser:
            try:
                url = reverse("pending_approvals")
                pending = User.objects.filter(
                    is_approved=False, is_superuser=False
                ).count()

                if pending:
                    extra_context["approval_banner"] = mark_safe(
                        f'<div style="margin: 0 0 12px; padding: 12px 16px;'
                        f'border-radius: 10px; background: #fff7ed; '
                        f'border: 1px solid #fed7aa; color: #9a3412; '
                        f'font-weight: 600; font-size: 13px;">'
                        f'{pending} account(s) are awaiting approval. '
                        f'<a href="{url}" style="color:#ea580c; '
                        f'text-decoration:underline; margin-left:6px;">'
                        f'Open the approval queue →</a>'
                        f'</div>'
                    )
            except Exception:
                # URL not yet wired, or another app error — ignore silently
                pass

        return super().changelist_view(request, extra_context)