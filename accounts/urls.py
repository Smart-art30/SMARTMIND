
from django.urls import path
from django.contrib.auth import views as auth_views

from . import views, admin_views
from .views import user_login, dashboard


urlpatterns = [
    # Authentication
    path("login/", user_login, name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),

    # User approvals
    path(
        "pending/",
        admin_views.pending_approvals,
        name="pending_approvals",
    ),
    path(
        "<int:user_id>/approve/",
        admin_views.approve_user,
        name="approve_user",
    ),
    path(
        "<int:user_id>/reject/",
        admin_views.reject_user,
        name="reject_user",
    ),
    path(
        "<int:user_id>/promote/",
        admin_views.promote_to_superuser,
        name="promote_to_superuser",
    ),

    # School-specific user approvals
    path(
        "school/pending/",
        admin_views.school_pending_approvals,
        name="school_pending_approvals",
    ),
    path(
        "school/<int:user_id>/approve/",
        admin_views.school_approve_user,
        name="school_approve_user",
    ),
    path(
        "school/<int:user_id>/reject/",
        admin_views.school_reject_user,
        name="school_reject_user",
    ),

    # Dashboards
    path("dashboard/", dashboard, name="dashboard"),
    path(
        "dashboard/school-admin/",
        views.school_admin_dashboard,
        name="school_admin_dashboard",
    ),
    path(
        "teacher/dashboard/",
        views.teacher_dashboard,
        name="teacher_dashboard",
    ),

    # AJAX
    path(
        "ajax/load-classes/",
        views.load_classes,
        name="load_classes",
    ),
    path(
        "ajax/load-teacher-roles/",
        views.load_teacher_roles,
        name="ajax_load_teacher_roles",
    ),

    # Teachers
    path("teachers/", views.teacher_list, name="teacher_list"),
    path("teachers/add/", views.teacher_create, name="teacher_create"),
    path(
        "teachers/<int:pk>/edit/",
        views.teacher_update,
        name="teacher_update",
    ),
    path(
        "teachers/<int:pk>/delete/",
        views.teacher_delete,
        name="teacher_delete",
    ),

    # Teacher assignments, roles and permissions
    path(
        "teacher-assignments/",
        views.teacher_assignment_list,
        name="teacher_assignment_list",
    ),
    path(
        "teacher-assignments/add/",
        views.teacher_assignment_create,
        name="teacher_assignment_create",
    ),
    path("teacher-roles/", views.teacher_role_list, name="teacher_role_list"),
    path(
        "teacher-permissions/",
        views.teacher_permissions,
        name="teacher_permission_list",
    ),

    # Students
    path("students/", views.student_list, name="student_list"),
    path(
        "students/<int:pk>/",
        views.student_detail,
        name="student_detail",
    ),

    # Classes
    path("classes/", views.class_list, name="class_list"),
    path("classes/new/", views.class_create, name="class_create"),
    path("classes/<int:pk>/edit/", views.class_edit, name="class_edit"),
    path("classes/<int:pk>/delete/", views.class_delete, name="class_delete"),

    # Parents
    path("parents/", views.parent_list, name="parent_list"),

    # Attendance
    path("", views.attendance_dashboard, name="attendance_dashboard"),

    # Enrollment review and decisions
    path(
        "enrollments/",
        views.enrollment_review_list,
        name="enrollment_review_list",
    ),
    path(
        "enrollments/<int:pk>/approve/",
        views.enrollment_approve,
        name="enrollment_approve",
    ),
    path(
        "enrollments/<int:pk>/reject/",
        views.enrollment_reject,
        name="enrollment_reject",
    ),
    path(
        "enrollments/<int:pk>/transfer/",
        views.enrollment_transfer,
        name="enrollment_transfer",
    ),
]
