from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.decorators import login_required
from blog.models import Post
from assignments.models import Assignment, QuizAttempt
from schools.models import School, SchoolClass
from django.http import HttpResponseForbidden
from .forms import CustomUserCreationForm
from django.db.models import Avg, Count, Sum, Max, Min
User = get_user_model()
from django.http import JsonResponse
from assignments.models import Assignment, Submission, Enrollment
from .models import TeacherPermission
from .forms import TeacherPermissionForm
from .forms import TeachingAssignmentForm

User = get_user_model()

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        print("Username:", username)
        print("Password:", password)

        user = authenticate(
            request,
            username=username,
            password=password
        )

        print("Authenticated user:", user)

        if user is not None:
            login(request, user)
            print("LOGIN SUCCESS")

            if user.is_superuser:
                return redirect('/admin/')

            return redirect('dashboard')

        print("LOGIN FAILED")
        return render(request, 'login.html', {
            'error': 'Invalid credentials'
        })

    return render(request, 'login.html')

def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')

        print("REGISTER ERRORS:", form.errors) 

        return render(request, "register.html", {"form": form})

    else:
        form = CustomUserCreationForm()

    return render(request, "register.html", {"form": form})

def load_classes(request):
    school_id = request.GET.get("school_id")

    classes = SchoolClass.objects.filter(
        school_id=school_id,
        is_active=True
    )

    print("School ID:", school_id)
    print("Classes:", list(classes.values("id", "name")))

    return JsonResponse(
        list(classes.values("id", "name")),
        safe=False
    )


@login_required
def dashboard(request):
    user = request.user

    if user.is_superuser:
        return redirect('/admin/')

    elif user.role == 'school_admin':
        return redirect('school_admin_dashboard')

    elif user.role == "teacher":
        return redirect("teacher_dashboard")

    elif user.role == 'student':
        assignments = Assignment.objects.filter(
            school_class__enrollments__student=user
        ).select_related('subject').order_by('-created_at')

        assignment_count = assignments.count()
        quiz_count = assignments.filter(assignment_type='quiz').count()

        attempts = QuizAttempt.objects.filter(student=user)
        posts = (
            Post.objects.filter(status="published")
            .select_related("author", "category")
            .order_by("-created_at")[:5]
        )

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

    elif user.role == 'parent':
        return render(request, 'parent.html')

    return render(request, 'default.html')




@login_required
def school_admin_dashboard(request):
    user = request.user

    # 🔐 strict role enforcement
    if user.role != "school_admin":
        return HttpResponseForbidden("Access denied")

    # 🏫 safety check (important for data integrity)
    if not user.school:
        return HttpResponseForbidden("No school assigned to this admin")

    school = user.school

    # =========================
    # USERS (optimized counts)
    # =========================
    student_qs = User.objects.filter(role="student", school=school)
    teacher_qs = User.objects.filter(role="teacher", school=school)

    students_count = student_qs.count()
    teachers_count = teacher_qs.count()

    # =========================
    # ACADEMIC STRUCTURE
    # =========================
    classes_count = SchoolClass.objects.filter(school=school).count()

    assignments_qs = Assignment.objects.filter(
        school_class__school=school
    ).select_related("subject", "school_class")

    assignments_count = assignments_qs.count()

    # =========================
    # QUIZ ANALYTICS
    # =========================
    quiz_attempts_qs = QuizAttempt.objects.filter(
        assignment__school_class__school=school
    ).select_related("assignment")

    quiz_attempts_count = quiz_attempts_qs.count()

    # 📊 performance insight (average score %)
    avg_score = quiz_attempts_qs.aggregate(
        avg=Avg("score")
    )["avg"] or 0

    avg_total = quiz_attempts_qs.aggregate(
        avg=Avg("total")
    )["avg"] or 0

    performance_rate = 0
    if avg_total > 0:
        performance_rate = round((avg_score / avg_total) * 100, 1)

    # =========================
    # RECENT ACTIVITY (dashboard value-add)
    # =========================
    recent_assignments = assignments_qs.order_by("-created_at")[:5]
    recent_attempts = quiz_attempts_qs.order_by("-started_at")[:5]

    # =========================
    # CONTEXT
    # =========================
    posts = (
    Post.objects.filter(status="published")
    .select_related("author", "category")
    .order_by("-created_at")[:5]
)
    context = {
        "school": school,

        # counts
        "students_count": students_count,
        "teachers_count": teachers_count,
        "classes_count": classes_count,
        "assignments_count": assignments_count,
        "quiz_attempts_count": quiz_attempts_count,

        # analytics
        "performance_rate": performance_rate,

        # activity
        "recent_assignments": recent_assignments,
        "recent_attempts": recent_attempts,
        "posts": posts,
    }

    return render(request, "school_admin.html", context)

@login_required
def teacher_dashboard(request):
    teacher = request.user

    # Base queryset (NO slicing)
    assignments = (
        Assignment.objects.filter(
            teacher=teacher
        )
        .select_related("subject", "school_class")
        .order_by("-created_at")
    )

    posts = (
        Post.objects.filter(status="published")
        .select_related("author", "category")
        .order_by("-created_at")[:5]
    )

    assignment_count = assignments.exclude(
        assignment_type="quiz"
    ).count()

    quiz_count = assignments.filter(
        assignment_type="quiz"
    ).count()

    student_count = Enrollment.objects.filter(
        school_class__assignments__teacher=teacher
    ).values("student").distinct().count()

    pending_submissions = Submission.objects.filter(
        assignment__teacher=teacher,
        graded=False
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

    form.fields["teacher_role"].queryset = (
        request.user.school.teacher_roles.all()
    )

    if form.is_valid():

        teacher = form.save(commit=False)

        teacher.role = "teacher"

        teacher.school = request.user.school

        teacher.set_password("Teacher123")

        teacher.save()

        messages.success(
            request,
            "Teacher added successfully."
        )

        return redirect("teacher_list")

    return render(
        request,
        "accounts/teacher_form.html",
        {
            "form": form,
        },
    )

@login_required
def teacher_update(request, pk):
    teacher = get_object_or_404(
        User,
        pk=pk,
        role="teacher",
        school=request.user.school,
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
        form = TeacherForm(
            instance=teacher,
            school=request.user.school,
        )

    return render(
        request,
        "accounts/teacher_form.html",
        {
            "form": form,
            "teacher": teacher,
        },
    )
@login_required
def teacher_delete(request, pk):
    teacher = get_object_or_404(
        User,
        pk=pk,
        role="teacher",
        school=request.user.school,
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

    return render(

        request,

        "accounts/teacher_list.html",

        {

            "teachers": teachers,

        },

    )


@login_required
def assign_teacher(request):

    school = request.user.school

    if request.method == "POST":
        form = TeachingAssignmentForm(
            request.POST,
            school=school,
        )

        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.school = school
            assignment.save()

            messages.success(
                request,
                "Teacher assigned successfully."
            )

            return redirect("teacher_assignment_list")

    else:
        form = TeachingAssignmentForm(
            school=school,
        )

    return render(
        request,
        "accounts/assignment_form.html",
        {
            "form": form,
        },
    )

@login_required
def teacher_permissions(request, pk):

    teacher = get_object_or_404(
        User,
        pk=pk,
        role="teacher",
        school=request.user.school,
    )

    permissions, created = TeacherPermission.objects.get_or_create(
        teacher=teacher
    )

    if request.method == "POST":

        form = TeacherPermissionForm(
            request.POST,
            instance=permissions,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Permissions updated."
            )

            return redirect("teacher_list")

    else:

        form = TeacherPermissionForm(
            instance=permissions,
        )

    return render(
        request,
        "accounts/teacher_permissions.html",
        {
            "teacher": teacher,
            "form": form,
        },
    )



@login_required
def teacher_assignment_list(request):

    assignments = TeachingAssignment.objects.filter(
        school=request.user.school
    ).select_related(
        "teacher",
        "school_class",
        "subject",
    )

    return render(
        request,
        "accounts/teacher_assignment_list.html",
        {
            "assignments": assignments,
        },
    )


@login_required
def teacher_assignment_create(request):

    if request.method == "POST":

        form = TeachingAssignmentForm(
            request.POST,
            school=request.user.school,
        )

        if form.is_valid():

            assignment = form.save(commit=False)

            assignment.school = request.user.school

            assignment.save()

            messages.success(
                request,
                "Assignment saved."
            )

            return redirect(
                "teacher_assignment_list"
            )

    else:

        form = TeachingAssignmentForm(
            school=request.user.school,
        )

    return render(
        request,
        "accounts/teacher_assignment_form.html",
        {
            "form": form,
        },
    )


@login_required
def teacher_assignment_update(request, pk):

    assignment = get_object_or_404(
        TeachingAssignment,
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":

        form = TeachingAssignmentForm(
            request.POST,
            instance=assignment,
            school=request.user.school,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Assignment updated."
            )

            return redirect(
                "teacher_assignment_list"
            )

    else:

        form = TeachingAssignmentForm(
            instance=assignment,
            school=request.user.school,
        )

    return render(
        request,
        "accounts/teacher_assignment_form.html",
        {
            "form": form,
        },
    )


@login_required
def teacher_assignment_delete(request, pk):

    assignment = get_object_or_404(
        TeachingAssignment,
        pk=pk,
        school=request.user.school,
    )

    assignment.delete()

    messages.success(
        request,
        "Assignment removed."
    )

    return redirect(
        "teacher_assignment_list"
    )


def teacher_role_list(request):
    # TODO: replace with your real queryset / logic
    roles = []  # e.g. TeacherRole.objects.all()
    context = {
        "roles": roles,
    }
    return render(request, "accounts/teacher_role_list.html", context)

@login_required
def teacher_permission_list(request):
    permissions = (
        TeacherPermission.objects
        .filter(teacher__school=request.user.school)
        .select_related("teacher")
    )

    return render(
        request,
        "accounts/teacher_permission_list.html",
        {
            "permissions": permissions,
        },
    )

@login_required
def student_list(request):
    students = User.objects.filter(
        role="student",
        school=request.user.school,
    ).select_related("school_class")

    return render(
        request,
        "accounts/student_list.html",
        {
            "students": students,
        },
    )

@login_required
def class_list(request):
    classes = SchoolClass.objects.filter(
        school=request.user.school
    ).order_by("order", "name")

    return render(
        request,
        "schools/class_list.html",
        {
            "classes": classes,
        },
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
        {
            "parents": parents,
        },
    )