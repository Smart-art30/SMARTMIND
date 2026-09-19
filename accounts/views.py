from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Avg
from django.utils import timezone
from django.utils.text import slugify

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

            if user.is_active:

                login(request, user)

                if user.role == "student":
                    messages.success(
                        request,
                        "Welcome learner. Your classes and assignments are ready."
                    )
                elif user.role == "teacher":
                    messages.success(
                        request,
                        "Welcome teacher. Your teaching dashboard is ready."
                    )
                elif user.role == "school_admin":
                    messages.success(
                        request,
                        "Welcome administrator. School management tools are ready."
                    )
                elif user.role == "parent":
                    messages.success(
                        request,
                        "Welcome parent. You can now monitor learner progress."
                    )

                if user.is_superuser:
                    return redirect("/admin/")

                return redirect("dashboard")

            messages.warning(
                request,
                "Your account is inactive. Contact the school administrator."
            )
        else:
            messages.error(
                request,
                "Invalid username or password. Please enter the correct login details."
            )

    return render(request, "login.html")


# ============================================================
# REGISTRATION
# ============================================================

def register(request):

    if request.method == "POST":

        form = CustomUserCreationForm(request.POST)

        if form.is_valid():

            user = form.save(commit=False)
            user.save()

            # Student self-enrollment → PENDING for admin approval
            if user.role == "student" and user.school_class:

                Enrollment.objects.get_or_create(
                    student=user,
                    school_class=user.school_class,
                    defaults={"status": "PENDING"},
                )

            login(request, user)

            messages.success(
                request,
                "Account created successfully. "
                "Your enrollment is awaiting admin approval."
            )

            return redirect("dashboard")

        print("REGISTER ERRORS:", form.errors)
        return render(request, "register.html", {"form": form})

    form = CustomUserCreationForm()
    return render(request, "register.html", {"form": form})


# ============================================================
# LOAD CLASSES
# ============================================================

def load_classes(request):

    school_id = request.GET.get("school_id")

    classes = SchoolClass.objects.filter(
        school_id=school_id,
        is_active=True,
    )

    return JsonResponse(list(classes.values("id", "name")), safe=False)


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

    # --------------------------------------------------------
    # STUDENT DASHBOARD
    # --------------------------------------------------------

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

        return render(
            request,
            "student.html",
            {
                "assignments": assignments[:5],
                "assignment_count": assignment_count,
                "quiz_count": quiz_count,
                "performance": performance,
                **blog_context,
            }
        )

    if user.role == "parent":

        blog_context = get_blog_context()

        return render(
            request,
            "parent.html",
            {
                **blog_context,
            }
        )

    # --------------------------------------------------------
    # DEFAULT DASHBOARD
    # --------------------------------------------------------

    blog_context = get_blog_context()

    return render(
        request,
        "default.html",
        {
            **blog_context,
        }
    )


# ============================================================
# SCHOOL ADMIN DASHBOARD
# ============================================================

@login_required
def school_admin_dashboard(request):

    user = request.user

    if user.role != "school_admin":
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

    # --------------------------------------------------------
    # PENDING ENROLLMENTS
    # --------------------------------------------------------

    pending_qs = Enrollment.objects.filter(
        school_class__school=school,
        status="PENDING",
    ).select_related("student", "school_class").order_by("created_at")

    # --------------------------------------------------------
    # BLOG DATA
    # --------------------------------------------------------

    blog_context = get_blog_context()

    context = {
        "school": school,
        "students_count": student_qs.count(),
        "teachers_count": teacher_qs.count(),
        "classes_count": SchoolClass.objects.filter(school=school).count(),
        "assignments_count": assignments_qs.count(),
        "quiz_attempts_count": quiz_attempts_qs.count(),
        "performance_rate": performance_rate,

        "recent_assignments": assignments_qs.order_by("-created_at")[:5],
        "recent_attempts": quiz_attempts_qs.order_by("-started_at")[:5],

        # Enrollment validation
        "pending_enrollments_count": pending_qs.count(),
        "pending_enrollments": pending_qs[:10],

        # Blog
        **blog_context,
    }

    return render(request, "school_admin.html", context)


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

    return render(
        request,
        "teacher.html",
        {
            "assignments": assignments[:5],
            "assignment_count": assignment_count,
            "quiz_count": quiz_count,
            "student_count": student_count,
            "pending_submissions": pending_submissions,
            "role": role,
            "role_label": role_label,
            **blog_context,
        }
    )


# ============================================================
# ENROLLMENT VALIDATION
# ============================================================

def _admin_school_or_403(request):
    """
    Helper: return (admin, school) or raise PermissionDenied.
    """
    user = request.user

    if user.role != "school_admin":
        raise PermissionDenied("Only school admins can manage enrollments.")

    if not user.school:
        raise PermissionDenied("No school assigned to this admin.")

    return user, user.school


@login_required
def enrollment_review_list(request):
    
    admin, school = _admin_school_or_403(request)

    status_filter = request.GET.get("status", "PENDING").upper()

    valid_statuses = {"PENDING", "ACTIVE", "REJECTED", "TRANSFERRED", "WITHDRAWN"}
    if status_filter not in valid_statuses:
        status_filter = "PENDING"

    enrollments = Enrollment.objects.filter(
        school_class__school=school,
        status=status_filter,
    ).select_related("student", "school_class").order_by("-created_at")

    counts = {
        s: Enrollment.objects.filter(
            school_class__school=school, status=s
        ).count()
        for s in valid_statuses
    }

    return render(
        request,
        "enrollment_review_list.html",
        {
            "school": school,
            "enrollments": enrollments,
            "status_filter": status_filter,
            "counts": counts,
        }
    )


@login_required
def enrollment_approve(request, pk):
    """
    Activate a pending enrollment.
    """
    admin, school = _admin_school_or_403(request)

    if request.method != "POST":
        return redirect("enrollment_review_list")

    enrollment = get_object_or_404(
        Enrollment,
        pk=pk,
        school_class__school=school,
    )

    if enrollment.status == "ACTIVE":
        messages.info(request, "Enrollment is already active.")
        return redirect(request.META.get("HTTP_REFERER", "enrollment_review_list"))

    enrollment.status = "ACTIVE"
    enrollment.decided_by = admin
    enrollment.decided_at = timezone.now()
    enrollment.save(update_fields=["status", "decided_by", "decided_at"])

    messages.success(
        request,
        f"{enrollment.student.get_full_name() or enrollment.student.username} "
        f"approved for {enrollment.school_class.name}."
    )

    return redirect(request.META.get("HTTP_REFERER", "enrollment_review_list"))


@login_required
def enrollment_reject(request, pk):
    """
    Reject a pending enrollment. Learner remains registered but not enrolled.
    """
    admin, school = _admin_school_or_403(request)

    if request.method != "POST":
        return redirect("enrollment_review_list")

    enrollment = get_object_or_404(
        Enrollment,
        pk=pk,
        school_class__school=school,
    )

    enrollment.status = "REJECTED"
    enrollment.decided_by = admin
    enrollment.decided_at = timezone.now()
    enrollment.notes = request.POST.get("notes", "").strip()
    enrollment.save(update_fields=["status", "decided_by", "decided_at", "notes"])

    messages.warning(
        request,
        f"Enrollment rejected for "
        f"{enrollment.student.get_full_name() or enrollment.student.username}."
    )

    return redirect(request.META.get("HTTP_REFERER", "enrollment_review_list"))


@login_required
def enrollment_transfer(request, pk):
    """
    Move a learner from one class to another.
    GET  → show the class picker form.
    POST → perform the move.
    """
    admin, school = _admin_school_or_403(request)

    enrollment = get_object_or_404(
        Enrollment,
        pk=pk,
        school_class__school=school,
    )

    available_classes = SchoolClass.objects.filter(
        school=school,
        is_active=True,
    ).exclude(pk=enrollment.school_class_id).order_by("order", "name")

    if request.method == "POST":

        new_class_id = request.POST.get("school_class")

        new_class = get_object_or_404(
            SchoolClass,
            pk=new_class_id,
            school=school,
            is_active=True,
        )

        # Prevent duplicates: same student in the target class
        if Enrollment.objects.filter(
            student=enrollment.student,
            school_class=new_class,
        ).exclude(pk=enrollment.pk).exists():

            messages.error(
                request,
                "This learner is already enrolled in the selected class."
            )
            return redirect("enrollment_transfer", pk=enrollment.pk)

        old_class_name = enrollment.school_class.name

        enrollment.school_class = new_class
        enrollment.status = "ACTIVE"
        enrollment.decided_by = admin
        enrollment.decided_at = timezone.now()
        enrollment.notes = (
            f"Transferred from {old_class_name} to {new_class.name} "
            f"by {admin.get_full_name() or admin.username}."
        )
        enrollment.save()

        messages.success(
            request,
            f"{enrollment.student.get_full_name() or enrollment.student.username} "
            f"transferred to {new_class.name}."
        )

        return redirect("enrollment_review_list")

    return render(
        request,
        "enrollment_transfer.html",
        {
            "enrollment": enrollment,
            "available_classes": available_classes,
        }
    )


# ============================================================
# TEACHER CREATE
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


# ============================================================
# TEACHER UPDATE
# ============================================================

@login_required
def teacher_update(request, pk):

    teacher = get_object_or_404(
        User, pk=pk, role="teacher", school=request.user.school
    )

    if request.method == "POST":

        form = TeacherForm(
            request.POST,
            instance=teacher,
            school=request.user.school,
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Teacher updated successfully.")
            return redirect("teacher_list")

    else:
        form = TeacherForm(instance=teacher, school=request.user.school)

    return render(request, "teacher_form.html", {"form": form, "teacher": teacher})


# ============================================================
# TEACHER DELETE
# ============================================================

@login_required
def teacher_delete(request, pk):

    teacher = get_object_or_404(
        User, pk=pk, role="teacher", school=request.user.school
    )

    teacher.is_active = False
    teacher.save(update_fields=["is_active"])

    messages.success(request, "Teacher account has been deactivated.")
    return redirect("teacher_list")


# ============================================================
# TEACHER LIST
# ============================================================

@login_required
def teacher_list(request):

    teachers = User.objects.filter(
        role="teacher",
        school=request.user.school,
    ).select_related("teacher_role")

    return render(request, "teacher_list.html", {"teachers": teachers})


# ============================================================
# ASSIGN TEACHER
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

    return render(
        request,
        "accounts/teacher_permissions.html",
        {"teacher": teacher, "form": form},
    )


# ============================================================
# TEACHER ASSIGNMENT LIST
# ============================================================

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


# ============================================================
# TEACHER ASSIGNMENT CREATE
# ============================================================

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


# ============================================================
# TEACHER ASSIGNMENT UPDATE
# ============================================================

@login_required
def teacher_assignment_update(request, pk):

    assignment = get_object_or_404(
        TeachingAssignment, pk=pk, school=request.user.school
    )

    if request.method == "POST":

        form = TeachingAssignmentForm(
            request.POST,
            instance=assignment,
            school=request.user.school,
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


# ============================================================
# TEACHER ASSIGNMENT DELETE
# ============================================================

@login_required
def teacher_assignment_delete(request, pk):

    assignment = get_object_or_404(
        TeachingAssignment, pk=pk, school=request.user.school
    )

    assignment.delete()
    messages.success(request, "Assignment removed.")
    return redirect("teacher_assignment_list")


# ============================================================
# TEACHER ROLES
# ============================================================

def teacher_role_list(request):
    roles = []
    return render(
        request,
        "accounts/teacher_role_list.html",
        {"roles": roles},
    )


# ============================================================
# TEACHER PERMISSION LIST
# ============================================================

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


# ============================================================
# STUDENT LIST
# ============================================================

@login_required
def student_list(request):

    students = User.objects.filter(
        role="student",
        school=request.user.school,
    ).select_related("school_class")

    return render(
        request,
        "student_list.html",
        {"students": students},
    )




@login_required
def class_list(request):

    classes = SchoolClass.objects.filter(
        school=request.user.school
    ).order_by("order", "name")

    return render(
        request,
        "class_list.html",
        {"classes": classes},
    )




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
        request,
        "accounts/parent_list.html",
        {"parents": parents},
    )


# ============================================================
# LOAD TEACHER ROLES
# ============================================================

def load_teacher_roles(request):

    school_id = request.GET.get("school_id")

    roles = TeacherRole.objects.filter(
        school_id=school_id
    ).values("id", "name")

    return JsonResponse(list(roles), safe=False)





@login_required
def class_list(request):

    classes = SchoolClass.objects.filter(
        school=request.user.school
    ).order_by("order", "name")

    return render(
        request,
        "class_list.html",
        {"classes": classes},
    )


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
            school=school,
            name=name,
            order=order,
            is_active=is_active,
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

        # Prevent duplicate name collision (excluding self)
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

    return render(
        request,
        "class_edit.html",
        {"class": klass},
    )


@login_required
def class_delete(request, pk):

    if request.user.role != "school_admin":
        return HttpResponseForbidden("Access denied")

    klass = get_object_or_404(
        SchoolClass, pk=pk, school=request.user.school
    )

    # Soft-delete: deactivate instead of dropping rows (keeps enrollments intact)
    klass.is_active = False
    klass.save(update_fields=["is_active"])

    messages.success(request, f"Class '{klass.name}' deactivated.")
    return redirect("class_list")

@login_required
def student_detail(request, pk):

    if request.user.role != "school_admin":
        return HttpResponseForbidden("Access denied")

    student = get_object_or_404(
        User,
        pk=pk,
        role="student",
        school=request.user.school,
    )

    enrollments = student.enrollments.select_related(
        "school_class"
    ).order_by("-created_at")

    return render(
        request,
        "student_detail.html",
        {
            "student": student,
            "enrollments": enrollments,
        },
    )