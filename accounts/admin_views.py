# accounts/admin_views.py
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404

from .models import User, TeacherRole, TeacherPermission

# Adjust path if Enrollment lives elsewhere
from assignments.models import Enrollment


# ==================================================================
# ACCESS HELPERS
# ==================================================================
def superuser_required(view):
    """Allow only authenticated superusers."""
    return user_passes_test(
        lambda u: u.is_authenticated and u.is_superuser,
        login_url="login",
    )(view)


def school_admin_required(view):
    """
    Allow superusers OR school admins who have a school assigned.
    School admins without a school are rejected to avoid accidental
    wide-open access.
    """
    return user_passes_test(
        lambda u: (
            u.is_authenticated
            and (u.is_superuser or (u.is_school_admin and u.school_id))
        ),
        login_url="login",
    )(view)


def _school_admin_can_manage(school_admin, target_user):
    """
    Business rule:
      - Superusers bypass everything.
      - A school admin can only touch non-superuser, non-student users
        who belong to the SAME school.
      - Students are auto-approved and must not appear here.
    """
    if school_admin.is_superuser:
        return True
    if target_user.is_superuser:
        return False
    if target_user.role == "student":
        return False
    if target_user.school_id != school_admin.school_id:
        return False
    return True


# ==================================================================
# SUPERADMIN (GLOBAL) APPROVALS
# ==================================================================
@superuser_required
def pending_approvals(request):
    pending_users = (
        User.objects
        .filter(is_approved=False, is_superuser=False)
        .select_related("school", "teacher_role")
        .order_by("approval_requested_at")
    )

    pending_enrollments = (
        Enrollment.objects
        .filter(status="PENDING")
        .select_related("student", "school_class")
    )

    teacher_roles = TeacherRole.objects.all().order_by("school__name", "name")

    return render(request, "admin/pending_approvals.html", {
        "pending_users": pending_users,
        "pending_enrollments": pending_enrollments,
        "teacher_roles": teacher_roles,
    })


@superuser_required
def approve_user(request, user_id):
    user = get_object_or_404(User, pk=user_id, is_superuser=False)

    if request.method == "POST":
        # Teachers must be assigned a real teacher_role from their own school
        if user.role == "teacher":
            teacher_role_id = request.POST.get("teacher_role")
            if not teacher_role_id:
                messages.error(
                    request,
                    f"Cannot approve {user.username}: choose a teacher role first.",
                )
                return redirect("pending_approvals")

            user.teacher_role = get_object_or_404(
                TeacherRole, pk=teacher_role_id, school=user.school
            )

        user.is_approved = True
        user.approved_by = request.user
        user.save()

        if user.role == "teacher":
            TeacherPermission.objects.get_or_create(teacher=user)

        messages.success(request, f"{user.username} approved.")

    return redirect("pending_approvals")


@superuser_required
def reject_user(request, user_id):
    user = get_object_or_404(User, pk=user_id, is_superuser=False)

    if request.method == "POST":
        user.is_approved = False
        user.is_active = False
        user.approved_by = None
        user.save()
        messages.warning(request, f"{user.username} rejected.")

    return redirect("pending_approvals")


@superuser_required
def approve_enrollment(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, pk=enrollment_id, status="PENDING")

    if request.method == "POST":
        enrollment.status = "APPROVED"
        enrollment.save(update_fields=["status"])
        messages.success(
            request,
            f"Enrollment for {enrollment.student.username} approved.",
        )

    return redirect("pending_approvals")


@superuser_required
def promote_to_superuser(request, user_id):
    """
    Dedicated, superuser-only promotion. There is NO other self-service path.
    """
    if not request.user.is_superuser:
        return redirect("login")

    user = get_object_or_404(User, pk=user_id)

    if request.method == "POST":
        user.is_superuser = True
        user.is_staff = True
        user.is_approved = True
        user.save()
        messages.success(request, f"{user.username} promoted to superuser.")

    return redirect("pending_approvals")


# ==================================================================
# SCHOOL-ADMIN (SCHOOL-SCOPED) APPROVALS
# ==================================================================
@school_admin_required
def school_pending_approvals(request):
    """
    Pending accounts and enrollments scoped to the school admin's own school.
    """
    school = request.user.school

    pending_users = (
        User.objects
        .filter(
            school=school,
            is_approved=False,
            is_superuser=False,
            role__in=["teacher", "parent", "school_admin"],
        )
        .exclude(pk=request.user.pk)
        .select_related("school", "teacher_role")
        .order_by("-approval_requested_at")
    )

    pending_enrollments = (
        Enrollment.objects
        .filter(school_class__school=school, status="PENDING")
        .select_related("student", "school_class")
    )

    teacher_roles = TeacherRole.objects.filter(school=school).order_by("name")

    return render(request, "admin/school_pending_approvals.html", {
        "school": school,
        "pending_users": pending_users,
        "pending_enrollments": pending_enrollments,
        "teacher_roles": teacher_roles,
    })


@school_admin_required
def school_approve_user(request, user_id):
    target = get_object_or_404(User, pk=user_id)

    if not _school_admin_can_manage(request.user, target):
        messages.error(request, "You cannot approve that account.")
        return redirect("school_pending_approvals")

    if request.method == "POST":
        if target.role == "teacher":
            role_id = request.POST.get("teacher_role")
            if not role_id:
                messages.error(
                    request,
                    f"Choose a teacher role before approving {target.username}.",
                )
                return redirect("school_pending_approvals")
            target.teacher_role = get_object_or_404(
                TeacherRole, pk=role_id, school=target.school
            )

        target.is_approved = True
        target.approved_by = request.user
        target.save()

        if target.role == "teacher":
            TeacherPermission.objects.get_or_create(teacher=target)

        messages.success(request, f"{target.username} approved.")

    return redirect("school_pending_approvals")


@school_admin_required
def school_reject_user(request, user_id):
    target = get_object_or_404(User, pk=user_id)

    if not _school_admin_can_manage(request.user, target):
        messages.error(request, "You cannot reject that account.")
        return redirect("school_pending_approvals")

    if request.method == "POST":
        target.is_approved = False
        target.is_active = False
        target.approved_by = None
        target.save()
        messages.warning(request, f"{target.username} rejected.")

    return redirect("school_pending_approvals")