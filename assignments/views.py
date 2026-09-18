from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.db.models import Avg, Max, Min
from .forms import SubmissionForm
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .forms import AssignmentForm
from .models import (Assignment,Enrollment,SchoolClass,Subject,
    Question,
    QuizAttempt,
    QuizAnswer,
    Submission
)
from schools.models import School
import random
from django.contrib import messages
from datetime import datetime

def get_student_assignments(user):
    return Assignment.objects.filter(
        school_class__enrollments__student=user
    ).distinct()


@login_required
def quiz_home(request):
    user = request.user

    # ---------- TEACHER ----------
    if user.role == "teacher":
        quizzes = (
            Assignment.objects
            .filter(teacher=user, assignment_type="quiz")
            .select_related("school_class", "subject")
            .order_by("-created_at")
        )
        return render(request, "quiz_home.html", {
            "role": "teacher",
            "role_label": "Teacher",
            "quizzes": quizzes,
        })

    # ---------- SCHOOL ADMIN ----------
    if user.role == "school_admin":
        quizzes = (
            Assignment.objects
            .filter(school_class__school=user.school, assignment_type="quiz")
            .select_related("school_class", "subject", "teacher")
            .order_by("-created_at")
        )
        return render(request, "quiz_home.html", {
            "role": "school_admin",
            "role_label": "School Admin",
            "quizzes": quizzes,
        })

    # ---------- STUDENT ----------
    if user.role == "student":
        enrollments = (
            Enrollment.objects
            .filter(student=user)
            .select_related("school_class")
        )
        return render(request, "quiz_home.html", {
            "role": "student",
            "role_label": "Student",
            "enrollments": enrollments,
        })

    return HttpResponseForbidden("You do not have permission to view quizzes.")


@login_required
def quiz_class_subjects(request, class_id):
    school_class = get_object_or_404(
        SchoolClass,
        id=class_id,
        enrollments__student=request.user
    )

    subjects = Subject.objects.filter(
        assignments__school_class=school_class,
        assignments__assignment_type="quiz"
    ).distinct()

    return render(request, "subjects.html", {
        "school_class": school_class,
        "subjects": subjects
    })


@login_required
def quiz_list(request, class_id, subject_id):
    school_class = get_object_or_404(
        SchoolClass,
        id=class_id,
        enrollments__student=request.user
    )

    subject = get_object_or_404(
        Subject,
        id=subject_id,
        assignments__school_class=school_class,
        assignments__assignment_type="quiz"
    )

    quizzes = Assignment.objects.filter(
        school_class=school_class,
        subject=subject,
        assignment_type="quiz"
    ).select_related("teacher", "subject", "school_class")

    return render(request, "list.html", {
        "school_class": school_class,
        "subject": subject,
        "quizzes": quizzes
    })


@login_required
def assignment_list(request):

    user = request.user

    # =========================
    # STUDENT VIEW
    # =========================
    if user.role == "student":

        enrollment = get_object_or_404(
            Enrollment.objects.select_related("school_class"),
            student=user
        )

        assignments = Assignment.objects.filter(
            school_class=enrollment.school_class
        )


    # =========================
    # TEACHER VIEW
    # =========================
    elif user.role == "teacher":

        assignments = Assignment.objects.filter(
            teacher=user
        )


    # =========================
    # SCHOOL ADMIN VIEW
    # =========================
    elif user.role == "school_admin":

        assignments = Assignment.objects.filter(
            school_class__school=user.school
        )


    else:
        return HttpResponseForbidden(
            "You do not have permission to view assignments."
        )


    assignments = assignments.select_related(
        "teacher",
        "subject",
        "school_class"
    )


    return render(
        request,
        "assignment_list.html",
        {
            "assignments": assignments
        }
    )



@login_required
def assignment_detail(request, pk):
    assignment = get_object_or_404(
        Assignment,
        pk=pk,
        school_class__enrollments__student=request.user
    )

    draft = Submission.objects.filter(
        assignment=assignment,
        student=request.user
    ).first()

    submitted = None

    if draft and draft.is_submitted:
        submitted = draft

    form = SubmissionForm(instance=draft)

    return render(request, "assignment_detail.html", {
        "assignment": assignment,
        "submission": submitted,   # only final submission
        "draft": draft,            # draft for editing
        "form": form,
        "now": timezone.now(),
    })


@login_required
def submit_assignment(request, pk):
    assignment = get_object_or_404(
        Assignment,
        pk=pk,
        school_class__enrollments__student=request.user
    )

    submission = Submission.objects.filter(
        assignment=assignment,
        student=request.user
    ).first()

    if request.method == "POST":

        form = SubmissionForm(
            request.POST,
            request.FILES,
            instance=submission
        )

        if form.is_valid():

            submission = form.save(commit=False)

            submission.assignment = assignment
            submission.student = request.user

            # Final submission
            submission.is_submitted = True
            submission.submitted_at = timezone.now()

            # Reset grading
            submission.graded = False
            submission.marks = None
            submission.feedback = None

            submission.save()

            return redirect("assignment_detail", pk=pk)

    else:

        form = SubmissionForm(instance=submission)

    return render(request, "assignment_detail.html", {
        "assignment": assignment,
        "submission": submission,
        "form": form,
        "now": timezone.now(),
    })

@login_required
def start_quiz(request, pk):
    assignment = get_object_or_404(
        Assignment,
        pk=pk,
        assignment_type="quiz",
        school_class__enrollments__student=request.user,
    )

   
    passed_attempt = (
        QuizAttempt.objects
        .filter(
            assignment=assignment,
            student=request.user,
            passed=True,
        )
        .order_by("-id")
        .first()
    )

    if passed_attempt:
        messages.info(
            request,
            "You've already passed this quiz. Retakes are locked."
        )
        return redirect("quiz_result", attempt_id=passed_attempt.id)

    in_progress = (
        QuizAttempt.objects
        .filter(
            assignment=assignment,
            student=request.user,
            submitted_at__isnull=True,
        )
        .order_by("-id")
        .first()
    )

    if in_progress:
        attempt = in_progress
    else:
        
        attempt = QuizAttempt.objects.create(
            assignment=assignment,
            student=request.user,
        )

    
    if not attempt.question_order:
        question_ids = list(
            assignment.questions.values_list("id", flat=True)[:20]
        )
        random.shuffle(question_ids)
        attempt.question_order = question_ids
        attempt.save(update_fields=["question_order"])

    questions = Question.objects.filter(
        id__in=attempt.question_order
    ).only(
        "id", "text", "option_a", "option_b", "option_c", "option_d", "marks"
    )

    ordered_questions = sorted(
        questions,
        key=lambda q: attempt.question_order.index(q.id)
    )

    return render(request, "quizzes/take.html", {
        "assignment": assignment,
        "attempt": attempt,
        "questions": ordered_questions,
        "duration": assignment.duration_minutes,
    })

@login_required
def submit_quiz(request, pk):
    assignment = get_object_or_404(
        Assignment,
        pk=pk,
        assignment_type="quiz",
        school_class__enrollments__student=request.user
    )

    attempt = get_object_or_404(
        QuizAttempt,
        assignment=assignment,
        student=request.user
    )

    if attempt.submitted_at:
        return redirect("quiz_result", attempt_id=attempt.id)

    question_ids = attempt.question_order
    questions = list(Question.objects.filter(id__in=question_ids))
    questions.sort(key=lambda q: question_ids.index(q.id))

    with transaction.atomic():
        for q in questions:
            selected = request.POST.get(str(q.id))
            QuizAnswer.objects.update_or_create(
                attempt=attempt,
                question=q,
                defaults={"selected_option": selected}
            )

        attempt.grade()

    return redirect("quiz_result", attempt_id=attempt.id)


@login_required
def quiz_result(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt,
        id=attempt_id,
        student=request.user
    )

    return render(request, "result.html", {
        "attempt": attempt
    })


@login_required
def create_subject(request, school_id):
    school = get_object_or_404(School, id=school_id)

    if not hasattr(request.user, "school") or request.user.school != school:
        return HttpResponseForbidden()

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        code = request.POST.get("code", "").strip()

        if not name:
            return render(request, "subjects/create.html", {
                "school": school,
                "error": "Subject name is required"
            })

        subject, created = Subject.objects.get_or_create(
            school=school,
            name=name,
            defaults={"code": code}
        )

        if not created:
            return render(request, "subjects/create.html", {
                "school": school,
                "error": "Learning area already exists"
            })

        return redirect("school_subjects", school_id=school.id)

    return render(request, "subjects/create.html", {
        "school": school
    })


@login_required
def school_subjects(request, school_id):
    school = get_object_or_404(School, id=school_id)
    subjects = school.subjects.all().order_by("name")

    return render(request, "subjects/list.html", {
        "school": school,
        "subjects": subjects
    })


@login_required
def manage_assignments(request):
    user = request.user

    if not (user.is_teacher or user.is_school_admin):
        return HttpResponseForbidden("Permission denied.")

    if user.is_school_admin:
        assignments = Assignment.objects.filter(
            school_class__school=user.school
        ).select_related("school_class", "subject", "teacher")
    else:
        assignments = Assignment.objects.filter(
            teacher=user
        ).select_related("school_class", "subject", "teacher")

    return render(request, "manage_assignments.html", {
        "assignments": assignments,
    })


@login_required
def manage_quizzes(request):
    if request.user.role != "teacher":
        return HttpResponseForbidden()

    quizzes = Assignment.objects.filter(
        teacher=request.user,
        assignment_type="quiz"
    ).select_related("school_class", "subject")

    return render(request, "manage_quizzes.html", {
        "quizzes": quizzes
    })


@login_required
def submission_list(request):
    if request.user.role != "teacher":
        return HttpResponseForbidden()

    submissions = Submission.objects.filter(
        assignment__teacher=request.user
    ).select_related(
        "student",
        "assignment"
    )

    return render(request, "submission_list.html", {
        "submissions": submissions
    })


@login_required
def gradebook(request):
    user = request.user

    if not (user.is_teacher or user.is_school_admin):
        return HttpResponseForbidden()

    if user.is_school_admin:
        attempts = QuizAttempt.objects.filter(
            assignment__school_class__school=user.school
        )
    else:
        attempts = QuizAttempt.objects.filter(
            assignment__teacher=user
        )

    attempts = attempts.select_related("student", "assignment")

    stats = attempts.aggregate(
        average=Avg("score"),
        highest=Max("score"),
        lowest=Min("score"),
    )

    return render(request, "gradebook.html", {
        "attempts": attempts,
        "average": round(stats["average"] or 0, 1),
        "highest": stats["highest"] or 0,
        "lowest": stats["lowest"] or 0,
    })


@login_required
def create_assignment(request):
    if request.method == "POST":
        form = AssignmentForm(request.POST, request.FILES)

        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.teacher = request.user
            assignment.save()
            return redirect("manage_assignments")
    else:
        form = AssignmentForm()

    return render(request, "create_assignment.html", {
        "form": form,
    })
@login_required
def create_quiz(request):
    # ---------- Permission ----------
    if request.user.role != "teacher":
        return HttpResponseForbidden("Only teachers can create quizzes.")

    school = getattr(request.user, "school", None)

    if school is None:
        messages.error(
            request,
            "Your account is not linked to a school."
        )
        return redirect("manage_quizzes")

    # ---------- Dropdown data ----------
    teacher_classes = (
        SchoolClass.objects
        .filter(
            school=school,
            is_active=True
        )
        .order_by("name")
    )

    teacher_subjects = (
        Subject.objects
        .filter(school=school)
        .order_by("name")
    )

    # ---------- Empty-state guard ----------
    if not teacher_classes.exists():
        messages.warning(
            request,
            "No classes exist for your school yet. "
            "Ask your school admin to create at least one class "
            "before adding a quiz."
        )

    if not teacher_subjects.exists():
        messages.warning(
            request,
            "No subjects exist for your school yet. "
            "Ask your school admin to create at least one subject "
            "before adding a quiz."
        )

    # ---------- POST ----------
    if request.method == "POST":

        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()

        subject_id = request.POST.get("subject")
        class_id = request.POST.get("school_class")

        due_date_input = request.POST.get("due_date", "").strip()

        duration_input = request.POST.get(
            "duration_minutes",
            "30"
        ).strip()

        errors = []

        # ---------- Basic validation ----------
        if not title:
            errors.append("Title is required.")

        if not subject_id:
            errors.append("Subject is required.")

        if not class_id:
            errors.append("Class is required.")

        if not due_date_input:
            errors.append("Due date and time are required.")

        # ---------- Class validation ----------
        school_class = None

        if class_id:
            school_class = teacher_classes.filter(
                id=class_id
            ).first()

            if not school_class:
                errors.append(
                    "You can only create quizzes for classes "
                    "in your school."
                )

        # ---------- Subject validation ----------
        subject = None

        if subject_id:
            subject = teacher_subjects.filter(
                id=subject_id
            ).first()

            if not subject:
                errors.append(
                    "You can only use subjects from your school."
                )

        # ---------- Duration validation ----------
        try:
            duration = int(duration_input or 30)

            if duration <= 0:
                errors.append(
                    "Duration must be greater than zero."
                )

        except (TypeError, ValueError):
            duration = 30
            errors.append(
                "Duration must be a valid number."
            )

        # ---------- Due date validation ----------
        due_date = None

        if due_date_input:
            try:
                # HTML <input type="datetime-local">
                # sends: 2026-09-24T18:18
                naive_due_date = datetime.strptime(
                    due_date_input,
                    "%Y-%m-%dT%H:%M"
                )

                # Interpret the teacher's entered time
                # as Kenyan local time.
                due_date = timezone.make_aware(
                    naive_due_date,
                    timezone.get_current_timezone()
                )

                # Check against current timezone-aware time.
                if due_date <= timezone.now():
                    errors.append(
                        "Due date and time must be in the future."
                    )

            except ValueError:
                errors.append(
                    "Please enter a valid due date and time."
                )

        # ---------- Return form with errors ----------
        if errors:
            return render(
                request,
                "create_quiz.html",
                {
                    "errors": errors,
                    "subjects": teacher_subjects,
                    "classes": teacher_classes,
                    "form_data": request.POST,
                }
            )

        # ---------- Create quiz ----------
        with transaction.atomic():

            quiz = Assignment.objects.create(
                title=title,
                description=description,
                subject=subject,
                school_class=school_class,
                teacher=request.user,
                assignment_type="quiz",
                due_date=due_date,
                duration_minutes=duration,
                is_timed=True,
            )

        messages.success(
            request,
            "Quiz created successfully. You can now add questions."
        )

        return redirect(
            "edit_quiz",
            pk=quiz.id
        )

    # ---------- GET ----------
    return render(
        request,
        "create_quiz.html",
        {
            "subjects": teacher_subjects,
            "classes": teacher_classes,
        }
    )

@login_required
def submission_detail(request, pk):
    submission = get_object_or_404(
        Submission.objects.select_related("student", "assignment"),
        pk=pk,
        assignment__teacher=request.user
    )

    return render(request, "submission_detail.html", {
        "submission": submission,
        "now": timezone.now(),
    })


@login_required
def grade_submission(request, pk):
    submission = get_object_or_404(
        Submission,
        pk=pk,
        assignment__teacher=request.user
    )

    if request.method == "POST":
        submission.marks = float(request.POST.get("marks") or 0)
        submission.feedback = request.POST.get("feedback", "")
        submission.graded = True
        submission.save()

        return redirect("submission_list")

    return render(request, "grade_submission.html", {
        "submission": submission
    })



@require_POST
@login_required
def autosave_submission(request, pk):
    assignment = get_object_or_404(
        Assignment,
        pk=pk,
        school_class__enrollments__student=request.user
    )

    submission, created = Submission.objects.get_or_create(
        assignment=assignment,
        student=request.user,
        defaults={
            "is_submitted": False
        }
    )

    if submission.is_submitted:
        return JsonResponse({
            "success": False,
            "message": "Assignment already submitted."
        })

    submission.content = request.POST.get("content", "")
    submission.save(update_fields=["content"])

    return JsonResponse({
        "success": True,
        "saved_at": timezone.localtime().strftime("%H:%M:%S")
    })


# views.py
@login_required
def edit_quiz(request, pk):
    if request.user.role != "teacher":
        return HttpResponseForbidden()

    quiz = get_object_or_404(
        Assignment, pk=pk, teacher=request.user, assignment_type="quiz"
    )

    if request.method == "POST":
        action = request.POST.get("action", "add_question")

        if action == "delete_question":
            Question.objects.filter(
                id=request.POST.get("question_id"), assignment=quiz
            ).delete()

        elif action == "add_question":
            text = request.POST.get("text", "").strip()
            a = request.POST.get("option_a", "").strip()
            b = request.POST.get("option_b", "").strip()
            c = request.POST.get("option_c", "").strip()
            d = request.POST.get("option_d", "").strip()
            correct = request.POST.get("correct_option")
            marks = request.POST.get("marks") or 1

            if text and a and b and c and d and correct:
                Question.objects.create(
                    assignment=quiz,
                    text=text,
                    option_a=a, option_b=b, option_c=c, option_d=d,
                    correct_option=correct,
                    marks=marks,
                )

        return redirect("edit_quiz", pk=pk)

    return render(request, "edit_quiz.html", {
        "quiz": quiz,
        "questions": quiz.questions.all(),
    })


@login_required
def delete_quiz(request, pk):
    if request.user.role != "teacher":
        return HttpResponseForbidden("Only teachers can delete quizzes.")

    quiz = get_object_or_404(
        Assignment,
        pk=pk,
        teacher=request.user,
        assignment_type="quiz",
    )

    if request.method == "POST":
        title = quiz.title
        quiz.delete()
        messages.success(request, f'Quiz "{title}" deleted.')
        return redirect("manage_quizzes")

    return render(request, "delete_quiz.html", {"quiz": quiz})