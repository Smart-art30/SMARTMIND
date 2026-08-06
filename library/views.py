from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import (AssessmentForm,QuestionForm,ResourceForm,TakeAssessmentForm,)
from django.http import JsonResponse
from django.db.models import F, Q, Max
from .decorators import school_admin_required
from django.core.paginator import Paginator
from urllib.parse import urlparse, parse_qs
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from .models import (
    Level,
    CurriculumClass,
    Subject,
    Topic,
    SubTopic,
    Question,
    Lesson,
    Resource,
    Assessment,
    LessonProgress,
    AssessmentAttempt,
    ResourceView,
    RecentlyViewed,
     StudentAnswer,
)


# ==================================================
# HELPERS
# ==================================================
def resource_search(query):
    return (
        Q(title__icontains=query) |
        Q(description__icontains=query)
    )




def get_embed_url(url):
    if not url:
        return None

    parsed = urlparse(url)

    # YouTube short URL
    if "youtu.be" in parsed.netloc:
        video_id = parsed.path.strip("/")
        return f"https://www.youtube.com/embed/{video_id}"

    # YouTube watch URL
    if "youtube.com" in parsed.netloc:
        video_id = parse_qs(parsed.query).get("v", [""])[0]
        if video_id:
            return f"https://www.youtube.com/embed/{video_id}"

    # Vimeo
    if "vimeo.com" in parsed.netloc:
        video_id = parsed.path.strip("/")
        return f"https://player.vimeo.com/video/{video_id}"

    return None
# ==================================================
# LIBRARY HOME
# ==================================================
def library_home(request):

    levels = (
    Level.objects
    .prefetch_related(
        "classes",
    )
    .order_by("order")
)

    return render(
        request,
        "library/home.html",
        {
            "levels": levels,
        },
    )

def level_detail(request, pk):

    level = get_object_or_404(
        Level.objects.prefetch_related("classes"),
        pk=pk,
    )

    return render(
        request,
        "library/level.html",
        {
            "level": level,
            "classes": level.classes.all(),
        },
    )

def class_detail(request, pk):

    curriculum_class = get_object_or_404(
        CurriculumClass,
        pk=pk,
    )

    subjects = curriculum_class.subjects.all()

    resources = (
        Resource.objects
        .filter(
            lesson__subtopic__topic__subject__curriculum_class=curriculum_class
        )
        .select_related(
            "lesson",
            "lesson__subtopic",
            "lesson__subtopic__topic",
            "lesson__subtopic__topic__subject",
            "resource_type",
        )
        .order_by("lesson__subtopic__topic__subject__name", "order")
    )

    return render(
        request,
        "library/class.html",
        {
            "curriculum_class": curriculum_class,
            "subjects": subjects,
            "resources": resources,
        },
    )

# ==================================================
# SUBJECTS
# ==================================================
def subject_detail(request, pk):

    subject = get_object_or_404(
        Subject.objects.prefetch_related("topics"),
        pk=pk,
    )

    return render(
        request,
        "library/subject.html",
        {
            "subject": subject,
            "topics": subject.topics.all(),
        },
    )


def topic_detail(request, pk):

    topic = get_object_or_404(
        Topic.objects.prefetch_related("subtopics"),
        pk=pk,
    )

    return render(
        request,
        "library/topic.html",
        {
            "topic": topic,
            "subtopics": topic.subtopics.all(),
        },
    )


def subtopic_detail(request, pk):

    subtopic = get_object_or_404(
        SubTopic.objects.prefetch_related("lessons"),
        pk=pk,
    )

    lessons = (
        subtopic.lessons
        .filter(is_published=True)
        .order_by("order")
    )

    return render(
        request,
        "library/subtopic.html",
        {
            "subtopic": subtopic,
            "lessons": lessons,
        },
    )

@login_required
def lesson_detail(request, slug):

    lesson = get_object_or_404(
        Lesson.objects.select_related(
            "subtopic",
            "subtopic__topic",
            "subtopic__topic__subject",
            "subtopic__topic__subject__curriculum_class",
            "subtopic__topic__subject__curriculum_class__level",
        ).prefetch_related(
            "resources__resource_type",
            "resources__access_level",
            "resources__visibility",
            "assessments",
        ),
        slug=slug,
        is_published=True,
    )

    progress, created = LessonProgress.objects.get_or_create(
        learner=request.user,
        lesson=lesson,
    )

    RecentlyViewed.objects.update_or_create(
        learner=request.user,
        lesson=lesson,
    )

    resources = (
        lesson.resources
        .select_related(
            "resource_type",
            "access_level",
            "visibility",
            "uploaded_by",
        )
        .order_by("order")
    )

    assessments = (
        lesson.assessments
        .filter(is_published=True)
        .order_by("created_at")
    )

    return render(
        request,
        "library/lesson.html",
        {
            "lesson": lesson,
            "resources": resources,
            "assessments": assessments,
            "progress": progress,
        },
    )

  


@login_required
def resource_list(request):

    resources = (
        Resource.objects
        .select_related(
            "lesson",
            "lesson__subtopic",
            "lesson__subtopic__topic",
            "lesson__subtopic__topic__subject",
            "resource_type",
            "access_level",
            "visibility",
            "uploaded_by",
        )
        .order_by("-created_at")
    )

    query = request.GET.get("q", "").strip()

    if query:
        resources = resources.filter(resource_search(query))
    resource_type = request.GET.get("type")

    if resource_type:
        resources = resources.filter(resource_type__id=resource_type)

    paginator = Paginator(resources, 20)
    page = request.GET.get("page")
    resources = paginator.get_page(page)

    return render(
        request,
        "library/resource_list.html",
        {
            "resources": resources,
            "query": query,
        },
    )
    
@login_required
def resource_detail(request, pk):

    resource = get_object_or_404(
        Resource.objects.select_related(
            "lesson",
            "lesson__subtopic",
            "lesson__subtopic__topic",
            "lesson__subtopic__topic__subject",
            "resource_type",
            "access_level",
            "visibility",
            "uploaded_by",
        ),
        pk=pk,
    )

    Resource.objects.filter(pk=pk).update(
        views=F("views") + 1
    )

    ResourceView.objects.get_or_create(
        learner=request.user,
        resource=resource,
    )

    related_resources = (
        Resource.objects.filter(
            lesson=resource.lesson
        )
        .exclude(pk=resource.pk)
        .select_related("resource_type")
        .order_by("order")
    )

    # Generate embed URL if applicable
    embed_url = get_embed_url(resource.external_url)

    return render(
        request,
        "library/resource_detail.html",
        {
            "resource": resource,
            "related_resources": related_resources,
            "embed_url": embed_url,
        },
    )


@login_required
@school_admin_required
def add_resource(request):

    if request.method == "POST":

        form = ResourceForm(
            request.POST,
            request.FILES,
            user=request.user,
        )

        if form.is_valid():

            resource = form.save(commit=False)
            resource.uploaded_by = request.user
            resource.save()
            form.save_m2m()

            messages.success(
                request,
                "Resource uploaded successfully."
            )

            return redirect(
                "library:resource_detail",
                pk=resource.pk,
            )

    else:

        form = ResourceForm(
            user=request.user
        )

    return render(
        request,
        "library/add_resource.html",
        {
            "form": form,
            "title": "Upload Resource",
        },
    )



@login_required
@school_admin_required
def edit_resource(request, pk):

    resource = get_object_or_404(
        Resource,
        pk=pk,
    )

    if request.method == "POST":

        form = ResourceForm(
            request.POST,
            request.FILES,
            instance=resource,
            user=request.user,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Resource updated successfully."
            )

            return redirect(
            "library:resource_detail",
            pk=resource.pk,
        )

    else:

        form = ResourceForm(
            instance=resource,
            user=request.user,
        )

    return render(
        request,
        "library/add_resource.html",
        {
            "form": form,
            "title": "Edit Resource",
        },
    )



@login_required
@school_admin_required
def delete_resource(request, pk):

    resource = get_object_or_404(
        Resource,
        pk=pk,
    )

    if request.method == "POST":

        resource.delete()

        messages.success(
            request,
            "Resource deleted successfully."
        )

        return redirect(
            "library:resource_list"
        )

    return render(
        request,
        "library/delete_resource.html",
        {
            "resource": resource,
        },
    )


@login_required
def download_resource(request, pk):

    resource = get_object_or_404(
        Resource,
        pk=pk,
    )

    Resource.objects.filter(pk=pk).update(
        downloads=F("downloads") + 1
    )

    view, created = ResourceView.objects.get_or_create(
        learner=request.user,
        resource=resource,
    )

    view.downloads += 1
    view.save()

    return redirect(resource.file.url)


 
# ==================================================
# AJAX DROPDOWNS
# ==================================================

@login_required
def load_classes(request):

    level_id = request.GET.get("level")

    data = list(
        CurriculumClass.objects.filter(
            level_id=level_id
        ).values("id", "name")
    )

    return JsonResponse(data, safe=False)


@login_required
def load_subjects(request):

    class_id = request.GET.get("curriculum_class")

    data = list(
        Subject.objects.filter(
            curriculum_class_id=class_id
        ).values("id", "name")
    )

    return JsonResponse(data, safe=False)


@login_required
def load_topics(request):

    subject_id = request.GET.get("subject")

    data = list(
        Topic.objects.filter(
            subject_id=subject_id
        ).values("id", "title")
    )

    return JsonResponse(data, safe=False)


@login_required
def load_subtopics(request):

    topic_id = request.GET.get("topic")

    data = list(
        SubTopic.objects.filter(
            topic_id=topic_id
        ).values("id", "title")
    )

    return JsonResponse(data, safe=False)


@login_required
def load_lessons(request):

    subtopic_id = request.GET.get("subtopic")

    data = list(
        Lesson.objects.filter(
            subtopic_id=subtopic_id,
            is_published=True,
        ).values("id", "title")
    )

    return JsonResponse(data, safe=False)


@login_required
@school_admin_required
def question_list(request, assessment_id):

    assessment = get_object_or_404(Assessment,pk=assessment_id,)
    questions = (assessment.questions.all().order_by("order"))

    return render(
        request,
        "library/question_list.html",
        {
            "assessment": assessment,
            "questions": questions,
        },
    )


@login_required
@school_admin_required
def add_question(request, assessment_id):

    assessment = get_object_or_404(Assessment,pk=assessment_id,)

    if request.method == "POST":

        form = QuestionForm(request.POST)

        if form.is_valid():

            question = form.save(commit=False)
            question.assessment = assessment
            question.save()

            messages.success(
                request,
                "Question added successfully."
            )

            return redirect(
                "library:question_list",
                assessment_id=assessment.id,
            )

    else:

        form = QuestionForm(
            initial={
                "assessment": assessment,
            }
        )

    return render(
        request,
        "library/question_form.html",
        {
            "form": form,
            "assessment": assessment,
            "title": "Add Question",
        },
    )


@login_required
@school_admin_required
def edit_question(request, pk):

    question = get_object_or_404(Question,pk=pk,)

    if request.method == "POST":

        form = QuestionForm(
            request.POST,
            instance=question,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Question updated successfully."
            )

            return redirect(
                "library:question_list",
                assessment_id=question.assessment.id,
            )

    else:

        form = QuestionForm(instance=question)

    return render(
        request,
        "library/question_form.html",
        {
            "form": form,
            "assessment": question.assessment,
            "title": "Edit Question",
        },
    )



@login_required
@school_admin_required
def delete_question(request, pk):

    question = get_object_or_404(
        Question,
        pk=pk,
    )

    assessment = question.assessment

    if request.method == "POST":

        question.delete()

        messages.success(
            request,
            "Question deleted successfully."
        )

        return redirect(
            "library:question_list",
            assessment_id=assessment.id,
        )

    return render(
        request,
        "library/question_confirm_delete.html",
        {
            "question": question,
        },
    )


@login_required
def start_assessment(request, assessment_id):
    assessment = get_object_or_404(
        Assessment,
        pk=assessment_id,
        is_published=True,
    )

    # Ensure the assessment has questions
    if assessment.questions.count() == 0:
        messages.warning(
            request,
            "This assessment has no questions yet."
        )
        return redirect(
            "library:lesson_detail",
            slug=assessment.lesson.slug,
        )

    # Resume an unfinished attempt if one exists
    attempt = AssessmentAttempt.objects.filter(
        learner=request.user,
        assessment=assessment,
        status="started",
    ).first()

    if attempt:
        return redirect(
            "library:take_assessment",
            attempt_id=attempt.pk,
        )

    # Determine next attempt number
    last_attempt = (
        AssessmentAttempt.objects.filter(
            learner=request.user,
            assessment=assessment,
        ).aggregate(
            Max("attempt_number")
        )
    )

    next_attempt = (
        last_attempt["attempt_number__max"] or 0
    ) + 1

    # Create new attempt
    attempt = AssessmentAttempt.objects.create(
        learner=request.user,
        assessment=assessment,
        attempt_number=next_attempt,
        status="started",
    )

    # Verify it was actually saved
    if not AssessmentAttempt.objects.filter(pk=attempt.pk).exists():
        messages.error(
            request,
            "Unable to start the assessment. Please try again."
        )
        return redirect(
            "library:lesson_detail",
            slug=assessment.lesson.slug,
        )

    return redirect(
        "library:take_assessment",
        attempt_id=attempt.pk,
    )

@login_required
@transaction.atomic
def take_assessment(request, attempt_id):
    attempt = get_object_or_404(
        AssessmentAttempt,
        pk=attempt_id,
        learner=request.user,
    )

    assessment = attempt.assessment
    questions = assessment.questions.all().order_by("order")
    end_time = attempt.started_at + timedelta(minutes=assessment.time_limit)
    remaining_seconds = int((end_time - timezone.now()).total_seconds())
    if remaining_seconds < 0:
        remaining_seconds = 0

    if request.method == "POST":
        form = TakeAssessmentForm(
            request.POST,
            questions=questions,
        )

        if form.is_valid():
            attempt.answers.all().delete()

            total_score = 0
            total_marks = 0

            for question in questions:
                field_name = f"question_{question.id}"
                student_answer = form.cleaned_data[field_name]

                total_marks += question.marks
                is_correct = False
                marks_awarded = 0

                if question.question_type in ["mcq", "true_false", "short"]:
                    if student_answer.strip().lower() == question.answer.strip().lower():
                        is_correct = True
                        marks_awarded = question.marks

                StudentAnswer.objects.create(
                    attempt=attempt,
                    question=question,
                    selected_answer=student_answer,
                    is_correct=is_correct,
                    marks_awarded=marks_awarded,
                )

                total_score += marks_awarded

            percentage = (total_score / total_marks) * 100 if total_marks else 0

            attempt.score = total_score
            attempt.percentage = percentage
            attempt.passed = percentage >= assessment.passing_score
            attempt.completed_at = timezone.now()
            attempt.status = "submitted"
            attempt.save()

            return redirect("library:assessment_result", attempt.id)
    else:
        form = TakeAssessmentForm(questions=questions)

    if timezone.now() > end_time and attempt.status == "started":
        messages.warning(request, "The assessment time has expired.")

    question_forms = [
        (question, form[f"question_{question.id}"])
        for question in questions
    ]

    return render(
        request,
        "library/take_assessment.html",
        {
            "attempt": attempt,
            "assessment": assessment,
            "question_forms": question_forms,
            "form": form,
            "remaining_seconds": remaining_seconds,
        },
    )



@login_required
def assessment_result(request, attempt_id):

    attempt = get_object_or_404(
        AssessmentAttempt.objects.select_related(
            "assessment",
        ),
        pk=attempt_id,
        learner=request.user,
    )

    answers = (
        attempt.answers
        .select_related("question")
        .order_by("question__order")
    )

    return render(
        request,
        "library/assessment_result.html",
        {
            "attempt": attempt,
            "answers": answers,
        },
    )


@login_required
@school_admin_required
def assessment_list(request, lesson_id):

    lesson = get_object_or_404(
        Lesson,
        pk=lesson_id,
    )

    assessments = (
        lesson.assessments
        .all()
        .order_by("-created_at")
    )

    return render(
        request,
        "library/assessment_list.html",
        {
            "lesson": lesson,
            "assessments": assessments,
        },
    )


@login_required
@school_admin_required
def add_assessment(request, lesson_id):

    lesson = get_object_or_404(
        Lesson,
        pk=lesson_id,
    )

    if request.method == "POST":

        form = AssessmentForm(request.POST)

        if form.is_valid():

            assessment = form.save(commit=False)

            assessment.lesson = lesson

            assessment.save()

            messages.success(
                request,
                "Assessment created successfully."
            )

            return redirect(
                "library:assessment_list",
                lesson.id,
            )

    else:

        form = AssessmentForm()

    return render(
        request,
        "library/assessment_form.html",
        {
            "form":form,
            "lesson":lesson,
            "title":"Create Assessment",
        }
    )


@login_required
@school_admin_required
def edit_assessment(request, pk):

    assessment = get_object_or_404(
        Assessment,
        pk=pk,
    )

    if request.method == "POST":

        form = AssessmentForm(
            request.POST,
            instance=assessment,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Assessment updated."
            )

            return redirect(
                "library:assessment_list",
                assessment.lesson.id,
            )

    else:

        form = AssessmentForm(
            instance=assessment
        )

    return render(
        request,
        "library/assessment_form.html",
        {
            "form":form,
            "lesson":assessment.lesson,
            "title":"Edit Assessment",
        }
    )


@login_required
@school_admin_required
def delete_assessment(request, pk):

    assessment = get_object_or_404(
        Assessment,
        pk=pk,
    )

    lesson = assessment.lesson

    if request.method == "POST":

        assessment.delete()

        messages.success(
            request,
            "Assessment deleted."
        )

        return redirect(
            "library:assessment_list",
            lesson.id,
        )

    return render(
        request,
        "library/delete_assessment.html",
        {
            "assessment":assessment,
        }
    )