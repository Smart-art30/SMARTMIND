from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Avg
from django.db.models import Q
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import slugify
from django.core.paginator import Paginator
from collections import OrderedDict

from .models import (
    TeacherPermission,
    TeachingAssignment,
    TeacherRole,
)

from blog.models import Post, Category

from assignments.models import (
    Assignment,
    Enrollment,
    QuizAttempt,
    Submission,
)

from schools.models import SchoolClass

from .forms import (
    CustomUserCreationForm,
    TeacherPermissionForm,
    TeachingAssignmentForm,
    TeacherForm,
)

User = get_user_model()

# Default backend used when a freshly-created user (never authenticated)
# needs to be logged in. Required when AUTHENTICATION_BACKENDS has >1 entry.
DEFAULT_AUTH_BACKEND = "django.contrib.auth.backends.ModelBackend"


# ============================================================
# SHARED HELPERS
# ============================================================

def _safe_next(request, default_name):
    """
    Redirect to the POSTed/GETed `next` URL if it is on this host,
    otherwise redirect to the named route `default_name`.

    Never trust HTTP_REFERER — it is user-controlled and may be
    cross-origin, which drops SameSite cookies and logs the user out.
    """
    nxt = request.POST.get("next") or request.GET.get("next")
    if nxt and url_has_allowed_host_and_scheme(
        url=nxt,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(nxt)
    return redirect(default_name)


def _is_school_admin(user):
    return getattr(user, "role", None) == "school_admin"


def _admin_school_or_403(request):
    """
    Return (admin, school) or raise PermissionDenied.
    School admins must have a school; superusers are allowed but
    have no implicit school (callers must derive it from the object).
    """
    user = request.user

    if user.is_superuser:
        return user, getattr(user, "school", None)

    if not _is_school_admin(user):
        raise PermissionDenied("Only school admins can perform this action.")

    if not user.school:
        raise PermissionDenied("No school is assigned to this admin.")

    return user, user.school


def _resolve_enrollment_for_user(request, pk):
    """
    Fetch an Enrollment and derive its school.
    Enforces permission:
      - superuser    → any enrollment
      - school_admin → only enrollments in their own school
    Returns (enrollment, school).
    """
    enrollment = get_object_or_404(
        Enrollment.objects.select_related(
            "school_class__school", "student"
        ),
        pk=pk,
    )
    school = enrollment.school_class.school

    user = request.user
    if not user.is_superuser:
        if not _is_school_admin(user) or user.school_id != school.id:
            raise PermissionDenied("You cannot manage this enrollment.")

    return enrollment, school


# ============================================================
# BLOG DATA FOR ALL DASHBOARDS
# ============================================================

def get_blog_categories():
    categories = list(Category.objects.all().order_by("name"))

    published_posts = Post.objects.filter(
        status="published"
    ).select_related("author", "category").order_by("-created_at")

    posts_by_category = {}
    for post in published_posts:
        if post.category_id:
            posts_by_category.setdefault(post.category_id, []).append(post)

    for category in categories:
        category.dashboard_posts = posts_by_category.get(category.id, [])

    return categories


def get_blog_posts():
    return Post.objects.filter(
        status="published"
    ).select_related("author", "category").order_by("-created_at")[:5]


def get_blog_context():
    return {
        "posts": get_blog_posts(),
        "categories": get_blog_categories(),
    }


# ============================================================
# LOGIN
# ============================================================

def user_login(request):
    if request.method == "POST":
        username_or_email = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = None
        try:
            user_obj = User.objects.get(email=username_or_email)
            user = authenticate(
                request,
                username=user_obj.username,
                password=password,
            )
        except User.DoesNotExist:
            user = authenticate(
                request,
                username=username_or_email,
                password=password,
            )

        if user is not None:
            if not user.is_active:
                messages.warning(
                    request,
                    "Your account is inactive. Contact the school administrator.",
                )
                return render(request, "login.html", {
                    "login_failed": True,
                    "form": {"username": username_or_email},
                })

            # Pending accounts cannot log in (superusers bypass).
            if not user.is_superuser and not user.is_approved:
                messages.warning(
                    request,
                    "Your account is awaiting superadmin approval. "
                    "You will be able to sign in once it is approved.",
                )
                return render(request, "login.html", {
                    "login_failed": True,
                    "form": {"username": username_or_email},
                })

            # authenticate() sets user.backend; pass it explicitly so we
            # stay safe if multiple backends are configured.
            backend = getattr(user, "backend", DEFAULT_AUTH_BACKEND)
            login(request, user, backend=backend)

            if user.role == "student":
                messages.success(request, "Welcome learner. Your classes and assignments are ready.")
            elif user.role == "teacher":
                messages.success(request, "Welcome teacher. Your teaching dashboard is ready.")
            elif user.role == "school_admin":
                messages.success(request, "Welcome administrator. School management tools are ready.")
            elif user.role == "parent":
                messages.success(request, "Welcome parent. You can now monitor learner progress.")

            if user.is_superuser:
                return redirect("/admin/")

            return redirect("dashboard")

        messages.error(
            request,
            "Invalid username or password. Please enter the correct login details.",
        )
        return render(request, "login.html", {
            "login_failed": True,
            "form": {"username": username_or_email},
        })

    return render(request, "login.html")


# ============================================================
# REGISTRATION
# ============================================================

def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)

            # User.clean() requires employee_number & teacher_role for
            # teachers. Provide a default placeholder role.
            if user.role == "teacher" and not user.teacher_role and user.school:
                pending_role, _ = TeacherRole.objects.get_or_create(
                    school=user.school,
                    name="Pending Approval",
                    defaults={
                        "description": (
                            "Auto-created for teacher signup; "
                            "superadmin must reassign."
                        )
                    },
                )
                user.teacher_role = pending_role

            user.save()

            # Student → create a PENDING enrollment record for admin approval.
            if user.role == "student" and user.school_class:
                Enrollment.objects.get_or_create(
                    student=user,
                    school_class=user.school_class,
                    defaults={"status": "PENDING"},
                )
                # Freshly-created users have no .backend attribute,
                # and multiple auth backends are configured → must be explicit.
                login(request, user, backend=DEFAULT_AUTH_BACKEND)
                messages.success(
                    request,
                    "Account created successfully. "
                    "Your enrollment is awaiting admin approval.",
                )
                return redirect("dashboard")

            # Teacher / Parent / School Admin → wait for superadmin approval.
            messages.info(
                request,
                "Your account request has been submitted. "
                "A superadmin must approve it before you can sign in.",
            )
            return redirect("login")

        print("REGISTER ERRORS:", form.errors)
        return render(request, "register.html", {"form": form})

    form = CustomUserCreationForm()
    return render(request, "register.html", {"form": form})


# ============================================================
# LOADERS
# ============================================================

def load_classes(request):
    school_id = request.GET.get("school_id")
    classes = SchoolClass.objects.filter(
        school_id=school_id,
        is_active=True,
    )
    return JsonResponse(list(classes.values("id", "name")), safe=False)


def load_teacher_roles(request):
    school_id = request.GET.get("school_id")
    roles = TeacherRole.objects.filter(
        school_id=school_id
    ).values("id", "name")
    return JsonResponse(list(roles), safe=False)


# ============================================================
# MAIN DASHBOARD ROUTER
# ============================================================

@login_required
def dashboard(request):
    user = request.user

    if user.is_superuser:
        return redirect("/admin/")

    if user.role == "school_admin":
        return redirect("school_admin_dashboard")

    if user.role == "teacher":
        return redirect("teacher_dashboard")

    # ---------- STUDENT ----------
    if user.role == "student":
        assignments = Assignment.objects.filter(
            school_class__enrollments__student=user
        ).select_related("subject").order_by("-created_at")

        assignment_count = assignments.count()
        quiz_count = assignments.filter(assignment_type="quiz").count()

        attempts = QuizAttempt.objects.filter(student=user)
        performance = 0
        if attempts.exists():
            total_score = sum(a.score for a in attempts)
            total_possible = sum(a.total for a in attempts if a.total)
            if total_possible > 0:
                performance = round((total_score / total_possible) * 100, 1)

        blog_context = get_blog_context()
        return render(request, "student.html", {
            "assignments": assignments[:5],
            "assignment_count": assignment_count,
            "quiz_count": quiz_count,
            "performance": performance,
            **blog_context,
        })

    # ---------- PARENT ----------
    if user.role == "parent":
        blog_context = get_blog_context()
        return render(request, "parent.html", {**blog_context})

    # ---------- FALLBACK ----------
    blog_context = get_blog_context()
    return render(request, "default.html", {**blog_context})


# ============================================================
# SCHOOL ADMIN DASHBOARD
# ============================================================

@login_required
def school_admin_dashboard(request):
    user = request.user

    if not user.is_superuser and not _is_school_admin(user):
        return HttpResponseForbidden("Access denied")

    if not user.school:
        return HttpResponseForbidden("No school assigned to this admin")

    school = user.school

    student_qs = User.objects.filter(role="student", school=school)
    teacher_qs = User.objects.filter(role="teacher", school=school)

    assignments_qs = Assignment.objects.filter(
        school_class__school=school
    ).select_related("subject", "school_class")

    quiz_attempts_qs = QuizAttempt.objects.filter(
        assignment__school_class__school=school
    ).select_related("assignment")

    avg_score = quiz_attempts_qs.aggregate(avg=Avg("score"))["avg"] or 0
    avg_total = quiz_attempts_qs.aggregate(avg=Avg("total"))["avg"] or 0
    performance_rate = (
        round((avg_score / avg_total) * 100, 1) if avg_total > 0 else 0
    )

    pending_qs = Enrollment.objects.filter(
        school_class__school=school,
        status="PENDING",
    ).select_related("student", "school_class").order_by("created_at")

    blog_context = get_blog_context()

    return render(request, "school_admin.html", {
        "school": school,
        "students_count": student_qs.count(),
        "teachers_count": teacher_qs.count(),
        "classes_count": SchoolClass.objects.filter(school=school).count(),
        "assignments_count": assignments_qs.count(),
        "quiz_attempts_count": quiz_attempts_qs.count(),
        "performance_rate": performance_rate,

        "recent_assignments": assignments_qs.order_by("-created_at")[:5],
        "recent_attempts": quiz_attempts_qs.order_by("-started_at")[:5],

        "pending_enrollments_count": pending_qs.count(),
        "pending_enrollments": pending_qs[:10],

        **blog_context,
    })


# ============================================================
# TEACHER DASHBOARD
# ============================================================

@login_required
def teacher_dashboard(request):
    teacher = request.user

    if getattr(teacher, "role", None) not in ("teacher", "school_admin"):
        return HttpResponseForbidden(
            "Only teachers and school admins can access this dashboard."
        )

    assignments = Assignment.objects.filter(
        teacher=teacher
    ).select_related("subject", "school_class").order_by("-created_at")

    assignment_count = assignments.exclude(assignment_type="quiz").count()
    quiz_count = assignments.filter(assignment_type="quiz").count()

    student_count = Enrollment.objects.filter(
        school_class__assignments__teacher=teacher,
        status="ACTIVE",
    ).values("student").distinct().count()

    pending_submissions = Submission.objects.filter(
        assignment__teacher=teacher,
        graded=False,
    ).count()

    blog_context = get_blog_context()

    role = getattr(teacher, "role", "") or "unknown"
    role_labels = {
        "teacher": "Teacher",
        "school_admin": "School Admin",
        "student": "Student",
        "parent": "Parent",
    }
    role_label = role_labels.get(role, role.replace("_", " ").title())

    return render(request, "teacher.html", {
        "assignments": assignments[:5],
        "assignment_count": assignment_count,
        "quiz_count": quiz_count,
        "student_count": student_count,
        "pending_submissions": pending_submissions,
        "role": role,
        "role_label": role_label,
        **blog_context,
    })


# ============================================================
# ENROLLMENT REVIEW — LIST
# ============================================================

@login_required
def enrollment_review_list(request):
    user = request.user

    if user.is_superuser:
        base_qs = Enrollment.objects.all()
        school = None
    else:
        admin, school = _admin_school_or_403(request)
        base_qs = Enrollment.objects.filter(school_class__school=school)

    status_filter = (request.GET.get("status") or "PENDING").upper()
    valid_statuses = {"PENDING", "ACTIVE", "REJECTED", "TRANSFERRED", "WITHDRAWN"}
    if status_filter not in valid_statuses:
        status_filter = "PENDING"

    enrollments = (
        base_qs.filter(status=status_filter)
        .select_related("student", "school_class")
        .order_by("-created_at")
    )

    counts = {s: base_qs.filter(status=s).count() for s in valid_statuses}

    return render(request, "enrollment_review_list.html", {
        "school": school,
        "enrollments": enrollments,
        "status_filter": status_filter,
        "counts": counts,
    })


# ============================================================
# ENROLLMENT REVIEW — APPROVE
# ============================================================


@login_required
def enrollment_approve(request, pk):
    print(
        "APPROVE DEBUG:",
        "user_id =", request.user.pk,
        "authenticated =", request.user.is_authenticated,
        "role =", getattr(request.user, "role", None),
        "method =", request.method,
        "path =", request.path,
    )

    if request.method != "POST":
        return _safe_next(request, "enrollment_review_list")

    enrollment, school = _resolve_enrollment_for_user(request, pk)

    if enrollment.status == "ACTIVE":
        messages.info(request, "Enrollment is already active.")
        return _safe_next(request, "school_admin_dashboard")

    enrollment.status = "ACTIVE"
    enrollment.decided_by = request.user
    enrollment.decided_at = timezone.now()
    enrollment.save(
        update_fields=["status", "decided_by", "decided_at"]
    )

    messages.success(
        request,
        f"{enrollment.student.get_full_name() or enrollment.student.username} "
        f"approved for {enrollment.school_class.name}.",
    )

    return _safe_next(request, "school_admin_dashboard")

# ============================================================
# ENROLLMENT REVIEW — REJECT
# ============================================================

@login_required
def enrollment_reject(request, pk):
    if request.method != "POST":
        return _safe_next(request, "enrollment_review_list")

    enrollment, school = _resolve_enrollment_for_user(request, pk)

    enrollment.status = "REJECTED"
    enrollment.decided_by = request.user
    enrollment.decided_at = timezone.now()
    enrollment.notes = request.POST.get("notes", "").strip()
    enrollment.save(update_fields=["status", "decided_by", "decided_at", "notes"])

    messages.warning(
        request,
        f"Enrollment rejected for "
        f"{enrollment.student.get_full_name() or enrollment.student.username}.",
    )
    return _safe_next(request, "school_admin_dashboard")


# ============================================================
# ENROLLMENT REVIEW — TRANSFER
# ============================================================

@login_required
def enrollment_transfer(request, pk):
    enrollment, school = _resolve_enrollment_for_user(request, pk)

    available_classes = (
        SchoolClass.objects
        .filter(school=school, is_active=True)
        .exclude(pk=enrollment.school_class_id)
        .order_by("order", "name")
    )

    if request.method == "POST":
        new_class_id = request.POST.get("school_class")
        new_class = get_object_or_404(
            SchoolClass, pk=new_class_id, school=school, is_active=True
        )

        if Enrollment.objects.filter(
            student=enrollment.student,
            school_class=new_class,
        ).exclude(pk=enrollment.pk).exists():
            messages.error(
                request,
                "This learner is already enrolled in the selected class.",
            )
            return redirect("enrollment_transfer", pk=enrollment.pk)

        old_class_name = enrollment.school_class.name

        enrollment.school_class = new_class
        enrollment.status = "ACTIVE"
        enrollment.decided_by = request.user
        enrollment.decided_at = timezone.now()
        enrollment.notes = (
            f"Transferred from {old_class_name} to {new_class.name} "
            f"by {request.user.get_full_name() or request.user.username}."
        )
        enrollment.save()

        messages.success(
            request,
            f"{enrollment.student.get_full_name() or enrollment.student.username} "
            f"transferred to {new_class.name}.",
        )
        return _safe_next(request, "enrollment_review_list")

    return render(request, "enrollment_transfer.html", {
        "enrollment": enrollment,
        "available_classes": available_classes,
    })


# ============================================================
# TEACHERS — CREATE / UPDATE / DELETE / LIST
# ============================================================

@login_required
def teacher_create(request):
    if not request.user.is_school_admin:
        return redirect("/")

    form = TeacherForm(request.POST or None)
    form.fields["teacher_role"].queryset = request.user.school.teacher_roles.all()

    if form.is_valid():
        teacher = form.save(commit=False)
        teacher.role = "teacher"
        teacher.school = request.user.school
        teacher.set_password("Teacher123")
        teacher.save()

        messages.success(request, "Teacher added successfully.")
        return redirect("teacher_list")

    return render(request, "teacher_form.html", {"form": form})


@login_required
def teacher_update(request, pk):
    teacher = get_object_or_404(
        User, pk=pk, role="teacher", school=request.user.school
    )

    if request.method == "POST":
        form = TeacherForm(
            request.POST, instance=teacher, school=request.user.school,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Teacher updated successfully.")
            return redirect("teacher_list")
    else:
        form = TeacherForm(instance=teacher, school=request.user.school)

    return render(request, "teacher_form.html", {
        "form": form, "teacher": teacher,
    })


@login_required
def teacher_delete(request, pk):
    teacher = get_object_or_404(
        User, pk=pk, role="teacher", school=request.user.school
    )
    teacher.is_active = False
    teacher.save(update_fields=["is_active"])
    messages.success(request, "Teacher account has been deactivated.")
    return redirect("teacher_list")


@login_required
def teacher_list(request):
    teachers = User.objects.filter(
        role="teacher",
        school=request.user.school,
    ).select_related("teacher_role")
    return render(request, "teacher_list.html", {"teachers": teachers})


# ============================================================
# TEACHING ASSIGNMENTS
# ============================================================

@login_required
def assign_teacher(request):
    school = request.user.school

    if request.method == "POST":
        form = TeachingAssignmentForm(request.POST, school=school)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.school = school
            assignment.save()
            messages.success(request, "Teacher assigned successfully.")
            return redirect("teacher_assignment_list")
    else:
        form = TeachingAssignmentForm(school=school)

    return render(request, "accounts/assignment_form.html", {"form": form})


@login_required
def teacher_assignment_list(request):
    assignments = TeachingAssignment.objects.filter(
        school=request.user.school
    ).select_related("teacher", "school_class", "subject")
    return render(
        request,
        "accounts/teacher_assignment_list.html",
        {"assignments": assignments},
    )


@login_required
def teacher_assignment_create(request):
    if request.method == "POST":
        form = TeachingAssignmentForm(
            request.POST, school=request.user.school
        )
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.school = request.user.school
            assignment.save()
            messages.success(request, "Assignment saved.")
            return redirect("teacher_assignment_list")
    else:
        form = TeachingAssignmentForm(school=request.user.school)

    return render(
        request,
        "accounts/teacher_assignment_form.html",
        {"form": form},
    )


@login_required
def teacher_assignment_update(request, pk):
    assignment = get_object_or_404(
        TeachingAssignment, pk=pk, school=request.user.school
    )

    if request.method == "POST":
        form = TeachingAssignmentForm(
            request.POST, instance=assignment, school=request.user.school,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Assignment updated.")
            return redirect("teacher_assignment_list")
    else:
        form = TeachingAssignmentForm(
            instance=assignment, school=request.user.school
        )

    return render(
        request,
        "accounts/teacher_assignment_form.html",
        {"form": form},
    )


@login_required
def teacher_assignment_delete(request, pk):
    assignment = get_object_or_404(
        TeachingAssignment, pk=pk, school=request.user.school
    )
    assignment.delete()
    messages.success(request, "Assignment removed.")
    return redirect("teacher_assignment_list")


# ============================================================
# TEACHER PERMISSIONS
# ============================================================

@login_required
def teacher_permissions(request, pk):
    teacher = get_object_or_404(
        User, pk=pk, role="teacher", school=request.user.school
    )

    permissions, _ = TeacherPermission.objects.get_or_create(teacher=teacher)

    if request.method == "POST":
        form = TeacherPermissionForm(request.POST, instance=permissions)
        if form.is_valid():
            form.save()
            messages.success(request, "Permissions updated.")
            return redirect("teacher_list")
    else:
        form = TeacherPermissionForm(instance=permissions)

    return render(request, "accounts/teacher_permissions.html", {
        "teacher": teacher, "form": form,
    })


@login_required
def teacher_permission_list(request):
    permissions = TeacherPermission.objects.filter(
        teacher__school=request.user.school
    ).select_related("teacher")
    return render(
        request,
        "accounts/teacher_permission_list.html",
        {"permissions": permissions},
    )


def teacher_role_list(request):
    return render(
        request,
        "accounts/teacher_role_list.html",
        {"roles": []},
    )


# ============================================================
# STUDENTS
# ============================================================

@login_required
def student_list(request):
    school = request.user.school

    qs = (
        User.objects
        .filter(role="student", school=school)
        .select_related("school_class")
        .prefetch_related("enrollments")
        .order_by(
            "school_class__order",
            "school_class__name",
            "first_name",
            "last_name",
            "username",
        )
    )

    q = request.GET.get("q", "").strip()
    class_filter = request.GET.get("class", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if q:
        qs = qs.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(username__icontains=q)
            | Q(admission_number__icontains=q)
            | Q(email__icontains=q)
        )

    if class_filter:
        if class_filter == "unassigned":
            qs = qs.filter(school_class__isnull=True)
        else:
            qs = qs.filter(school_class_id=class_filter)

    if status_filter == "active":
        qs = qs.filter(is_active=True)
    elif status_filter == "inactive":
        qs = qs.filter(is_active=False)
    elif status_filter == "pending":
        qs = qs.filter(enrollments__status="PENDING").distinct()
    elif status_filter == "unassigned":
        qs = qs.filter(school_class__isnull=True)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    grouped = OrderedDict()
    for student in page_obj.object_list:
        grouped.setdefault(student.school_class, []).append(student)

    class_groups = sorted(
        grouped.items(),
        key=lambda kv: (
            kv[0] is None,
            kv[0].order if kv[0] else 0,
            kv[0].name if kv[0] else "",
        ),
    )

    total_students = User.objects.filter(school=school, role="student").count()
    active_students = User.objects.filter(
        school=school, role="student", is_active=True
    ).count()
    pending_students = User.objects.filter(
        school=school, role="student", enrollments__status="PENDING"
    ).distinct().count()
    unassigned_students = User.objects.filter(
        school=school, role="student", school_class__isnull=True
    ).count()

    all_classes = (
        SchoolClass.objects
        .filter(school=school, is_active=True)
        .order_by("order", "name")
    )

    return render(request, "student_list.html", {
        "students": page_obj.object_list,
        "class_groups": class_groups,
        "page_obj": page_obj,
        "paginator": paginator,
        "q": q,
        "class_filter": class_filter,
        "status_filter": status_filter,
        "all_classes": all_classes,
        "total_students": total_students,
        "active_students": active_students,
        "pending_students": pending_students,
        "unassigned_students": unassigned_students,
        "pending_count": pending_students,
    })


@login_required
def student_detail(request, pk):
    if request.user.role != "school_admin":
        return HttpResponseForbidden("Access denied")

    student = get_object_or_404(
        User, pk=pk, role="student", school=request.user.school,
    )

    enrollments = student.enrollments.select_related(
        "school_class"
    ).order_by("-created_at")

    return render(request, "student_detail.html", {
        "student": student,
        "enrollments": enrollments,
    })


# ============================================================
# CLASSES
# ============================================================

@login_required
def class_list(request):
    classes = SchoolClass.objects.filter(
        school=request.user.school
    ).order_by("order", "name")
    return render(request, "class_list.html", {"classes": classes})


@login_required
def class_create(request):
    if request.user.role != "school_admin":
        return HttpResponseForbidden("Access denied")

    school = request.user.school

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        order = request.POST.get("order") or 0
        is_active = request.POST.get("is_active") == "on"

        if not name:
            messages.error(request, "Class name is required.")
            return redirect("class_list")

        if SchoolClass.objects.filter(school=school, name__iexact=name).exists():
            messages.warning(request, f"A class named '{name}' already exists.")
            return redirect("class_list")

        try:
            order = int(order)
        except (TypeError, ValueError):
            order = 0

        SchoolClass.objects.create(
            school=school, name=name, order=order, is_active=is_active,
        )
        messages.success(request, f"Class '{name}' created.")
        return redirect("class_list")

    return redirect("class_list")


@login_required
def class_edit(request, pk):
    if request.user.role != "school_admin":
        return HttpResponseForbidden("Access denied")

    klass = get_object_or_404(
        SchoolClass, pk=pk, school=request.user.school
    )

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        order = request.POST.get("order") or 0
        is_active = request.POST.get("is_active") == "on"

        if not name:
            messages.error(request, "Class name is required.")
            return redirect("class_list")

        if SchoolClass.objects.filter(
            school=request.user.school, name__iexact=name
        ).exclude(pk=klass.pk).exists():
            messages.warning(request, f"Another class already uses '{name}'.")
            return redirect("class_list")

        try:
            order = int(order)
        except (TypeError, ValueError):
            order = 0

        klass.name = name
        klass.order = order
        klass.is_active = is_active
        klass.save()

        messages.success(request, f"Class '{name}' updated.")
        return redirect("class_list")

    return render(request, "class_edit.html", {"class": klass})


@login_required
def class_delete(request, pk):
    if request.user.role != "school_admin":
        return HttpResponseForbidden("Access denied")

    klass = get_object_or_404(
        SchoolClass, pk=pk, school=request.user.school
    )
    klass.is_active = False
    klass.save(update_fields=["is_active"])
    messages.success(request, f"Class '{klass.name}' deactivated.")
    return redirect("class_list")


# ============================================================
# ATTENDANCE / PARENTS
# ============================================================

@login_required
def attendance_dashboard(request):
    return render(request, "attendance/dashboard.html")


@login_required
def parent_list(request):
    parents = User.objects.filter(
        role="parent",
        school=request.user.school,
    ).order_by("first_name", "last_name")
    return render(
        request, "accounts/parent_list.html", {"parents": parents},
    )