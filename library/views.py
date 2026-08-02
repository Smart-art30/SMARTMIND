from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import ResourceForm
from django.db.models import F, Q
from .decorators import school_admin_required
from django.core.paginator import Paginator
from urllib.parse import urlparse, parse_qs
from .models import (
    Level,
    CurriculumClass,
    Subject,
    Topic,
    SubTopic,
    Lesson,
    Resource,
    Assessment,
    LessonProgress,
    ResourceView,
    RecentlyViewed,
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
        CurriculumClass.objects.prefetch_related("subjects"),
        pk=pk,
    )

    return render(
        request,
        "library/class.html",
        {
            "curriculum_class": curriculum_class,
            "subjects": curriculum_class.subjects.all(),
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


 



