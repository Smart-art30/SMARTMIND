from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Avg

from blog.models import Post
from assignments.models import Assignment, Enrollment, QuizAttempt, Submission
from schools.models import SchoolClass

from .forms import (
    CustomUserCreationForm,
    TeacherPermissionForm,
    TeachingAssignmentForm,
    TeacherForm,
)
from .models import TeacherPermission, TeachingAssignment

User = get_user_model()


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

            messages.warning(request, "Your account is inactive. Contact the school administrator.")
        else:
            messages.error(request, "Invalid username or password. Please enter the correct login details.")

    return render(request, "login.html")


def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.save()

            if user.role == "student" and user.school_class:
                Enrollment.objects.get_or_create(
                    student=user,
                    school_class=user.school_class,
                )

            login(request, user)
            messages.success(request, "Account created successfully. Welcome to SmartCoach.")
            return redirect("dashboard")

        print("REGISTER ERRORS:", form.errors)
        return render(request, "register.html", {"form": form})

    form = CustomUserCreationForm()
    return render(request, "register.html", {"form": form})


def load_classes(request):
    school_id = request.GET.get("school_id")

    classes = SchoolClass.objects.filter(
        school_id=school_id,
        is_active=True,
    )

    return JsonResponse(list(classes.values("id", "name")), safe=False)


@login_required
def dashboard(request):
    user = request.user

    if user.is_superuser:
        return redirect("/admin/")
    if user.role == "school_admin":
        return redirect("school_admin_dashboard")
    if user.role == "teacher":
        return redirect("teacher_dashboard")
    if user.role == "student":
        assignments = Assignment.objects.filter(
            school_class__enrollments__student=user
        ).select_related("subject").order_by("-created_at")

        assignment_count = assignments.count()
        quiz_count = assignments.filter(assignment_type="quiz").count()

        attempts = QuizAttempt.objects.filter(student=user)
        posts = Post.objects.filter(status="published").select_related("author", "category").order_by("-created_at")[:5]

        performance = 0
        if attempts.exists():
            total_score = sum(a.score for a in attempts)
            total_possible = sum(a.total for a in attempts if a.total)
            if total_possible > 0:
                performance = round((total_score / total_possible) * 100, 1)

        return render(request, "student.html", {
            "assignments": assignments[:5],
            "assignment_count": assignment_count,
            "quiz_count": quiz_count,
            "performance": performance,
            "posts": posts,
        })

    if user.role == "parent":
        return render(request, "parent.html")

    return render(request, "default.html")


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
    performance_rate = round((avg_score / avg_total) * 100, 1) if avg_total > 0 else 0

    posts = Post.objects.filter(status="published").select_related("author", "category").order_by("-created_at")[:5]

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
        "posts": posts,
    }

    return render(request, "school_admin.html", context)


@login_required
def teacher_dashboard(request):
    teacher = request.user

    assignments = Assignment.objects.filter(
        teacher=teacher
    ).select_related("subject", "school_class").order_by("-created_at")

    posts = Post.objects.filter(status="published").select_related("author", "category").order_by("-created_at")[:5]

    assignment_count = assignments.exclude(assignment_type="quiz").count()
    quiz_count = assignments.filter(assignment_type="quiz").count()

    student_count = Enrollment.objects.filter(
        school_class__assignments__teacher=teacher
    ).values("student").distinct().count()

    pending_submissions = Submission.objects.filter(
        assignment__teacher=teacher,
        graded=False,
    ).count()

    return render(request, "teacher.html", {
        "assignments": assignments[:5],
        "assignment_count": assignment_count,
        "quiz_count": quiz_count,
        "student_count": student_count,
        "pending_submissions": pending_submissions,
        "posts": posts,
    })


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

    return render(request, "accounts/teacher_form.html", {"form": form})


@login_required
def teacher_update(request, pk):
    teacher = get_object_or_404(User, pk=pk, role="teacher", school=request.user.school)

    if request.method == "POST":
        form = TeacherForm(request.POST, instance=teacher, school=request.user.school)
        if form.is_valid():
            form.save()
            messages.success(request, "Teacher updated successfully.")
            return redirect("teacher_list")
    else:
        form = TeacherForm(instance=teacher, school=request.user.school)

    return render(request, "accounts/teacher_form.html", {"form": form, "teacher": teacher})


@login_required
def teacher_delete(request, pk):
    teacher = get_object_or_404(User, pk=pk, role="teacher", school=request.user.school)
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

    return render(request, "accounts/teacher_list.html", {"teachers": teachers})


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
def teacher_permissions(request, pk):
    teacher = get_object_or_404(User, pk=pk, role="teacher", school=request.user.school)

    permissions, _ = TeacherPermission.objects.get_or_create(teacher=teacher)

    if request.method == "POST":
        form = TeacherPermissionForm(request.POST, instance=permissions)
        if form.is_valid():
            form.save()
            messages.success(request, "Permissions updated.")
            return redirect("teacher_list")
    else:
        form = TeacherPermissionForm(instance=permissions)

    return render(request, "accounts/teacher_permissions.html", {"teacher": teacher, "form": form})


@login_required
def teacher_assignment_list(request):
    assignments = TeachingAssignment.objects.filter(
        school=request.user.school
    ).select_related("teacher", "school_class", "subject")

    return render(request, "accounts/teacher_assignment_list.html", {"assignments": assignments})


@login_required
def teacher_assignment_create(request):
    if request.method == "POST":
        form = TeachingAssignmentForm(request.POST, school=request.user.school)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.school = request.user.school
            assignment.save()
            messages.success(request, "Assignment saved.")
            return redirect("teacher_assignment_list")
    else:
        form = TeachingAssignmentForm(school=request.user.school)

    return render(request, "accounts/teacher_assignment_form.html", {"form": form})


@login_required
def teacher_assignment_update(request, pk):
    assignment = get_object_or_404(TeachingAssignment, pk=pk, school=request.user.school)

    if request.method == "POST":
        form = TeachingAssignmentForm(request.POST, instance=assignment, school=request.user.school)
        if form.is_valid():
            form.save()
            messages.success(request, "Assignment updated.")
            return redirect("teacher_assignment_list")
    else:
        form = TeachingAssignmentForm(instance=assignment, school=request.user.school)

    return render(request, "accounts/teacher_assignment_form.html", {"form": form})


@login_required
def teacher_assignment_delete(request, pk):
    assignment = get_object_or_404(TeachingAssignment, pk=pk, school=request.user.school)
    assignment.delete()
    messages.success(request, "Assignment removed.")
    return redirect("teacher_assignment_list")


def teacher_role_list(request):
    roles = []
    return render(request, "accounts/teacher_role_list.html", {"roles": roles})


@login_required
def teacher_permission_list(request):
    permissions = TeacherPermission.objects.filter(
        teacher__school=request.user.school
    ).select_related("teacher")

    return render(request, "accounts/teacher_permission_list.html", {"permissions": permissions})


@login_required
def student_list(request):
    students = User.objects.filter(
        role="student",
        school=request.user.school,
    ).select_related("school_class")

    return render(request, "accounts/student_list.html", {"students": students})


@login_required
def class_list(request):
    classes = SchoolClass.objects.filter(
        school=request.user.school
    ).order_by("order", "name")

    return render(request, "schools/class_list.html", {"classes": classes})


@login_required
def attendance_dashboard(request):
    return render(request, "attendance/dashboard.html")


@login_required
def parent_list(request):
    parents = User.objects.filter(
        role="parent",
        school=request.user.school,
    ).order_by("first_name", "last_name")

    return render(request, "accounts/parent_list.html", {"parents": parents})