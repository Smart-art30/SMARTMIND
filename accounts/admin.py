from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "role",
        "school",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "role",
        "school",
        "is_staff",
        "is_superuser",
        "is_active",
    )

    search_fields = (
        "username",
        "email",
    )

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "SmartMind Information",
            {
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
                )
            },
        ),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "SmartMind Information",
            {
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
            },
        ),
    )