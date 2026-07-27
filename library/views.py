from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, F
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from .decorators import school_admin_required
from .forms import ResourceForm
from .models import (
    Level,
    Subject,
    Topic,
    SubTopic,
    Resource,
    Question,
    Progress,
    ResourceView,
)


# ==================================================
# HELPERS
# ==================================================
def resource_search(query):
    return (
        Q(title__icontains=query) |
        Q(description__icontains=query)
    )


# ==================================================
# LIBRARY HOME
# ==================================================
def library_home(request):
    levels = Level.objects.prefetch_related('subjects')
    total_resources = Resource.objects.count()
    completed_resources = 0
    progress_percentage = 0
    recent_resources = []

    if request.user.is_authenticated:
        recent_resources = (
            ResourceView.objects
            .filter(learner=request.user)
            .select_related(
                'resource',
                'resource__subject',
                'resource__topic'
            )[:6]
        )
        completed_resources = (
            ResourceView.objects
            .filter(learner=request.user)
            .count()
        )
        if total_resources:
            progress_percentage = int(completed_resources / total_resources * 100)

    return render(
        request,
        'library/home.html',
        {
            'levels': levels,
            'total_resources': total_resources,
            'completed_resources': completed_resources,
            'progress_percentage': progress_percentage,
            'recent_resources': recent_resources,
        }
    )


# ==================================================
# SUBJECTS
# ==================================================
def subjects(request, level_id):
    level = get_object_or_404(
        Level.objects.prefetch_related(
            'subjects',
            'subjects__topics'
        ),
        pk=level_id
    )
    return render(
        request,
        'library/subjects.html',
        {
            'level': level,
            'subjects': level.subjects.all()
        }
    )


# ==================================================
# TOPICS
# ==================================================
def topics(request, subject_id):
    subject = get_object_or_404(
        Subject.objects
        .select_related('level')
        .prefetch_related('topics', 'topics__subtopics'),
        pk=subject_id
    )
    topics = subject.topics.all()
    search = request.GET.get('q', '').strip()

    if search:
        topics = topics.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )

    return render(
        request,
        'library/topics.html',
        {
            'subject': subject,
            'topics': topics,
            'search': search
        }
    )


# ==================================================
# SUBTOPICS
# ==================================================
def subtopics(request, topic_id):
    topic = get_object_or_404(
        Topic.objects
        .select_related('subject', 'level')
        .prefetch_related('subtopics'),
        pk=topic_id
    )
    return render(
        request,
        'library/subtopics.html',
        {
            'topic': topic,
            'subtopics': topic.subtopics.all()
        }
    )


# ==================================================
# TOPIC DETAIL
# ==================================================
def topic_detail(request, topic_id):
    topic = get_object_or_404(
        Topic.objects
        .select_related('subject', 'level')
        .prefetch_related('subtopics'),
        pk=topic_id
    )
    return render(
        request,
        'library/topic_detail.html',
        {
            'topic': topic,
            'subtopics': topic.subtopics.all()
        }
    )


# ==================================================
# SUBTOPIC DETAIL
# ==================================================
def subtopic_detail(request, subtopic_id):
    subtopic = get_object_or_404(
        SubTopic.objects.select_related(
            'topic',
            'topic__subject',
            'topic__level'
        ),
        pk=subtopic_id
    )
    resources = subtopic.resources.select_related(
        'level',
        'subject',
        'topic',
        'subtopic'
    )

    if request.user.role == "student":
        resources = resources.filter(
            target_classes=request.user.school_class
        )

    resources = resources.order_by("-created_at").distinct()
    search = request.GET.get('q', '').strip()

    if search:
        resources = resources.filter(resource_search(search))

    paginator = Paginator(resources, 10)
    page = request.GET.get('page')
    resources = paginator.get_page(page)
    questions_count = subtopic.questions.count()

    return render(
        request,
        'library/subtopic_detail.html',
        {
            'subtopic': subtopic,
            'resources': resources,
            'questions_count': questions_count,
            'search': search
        }
    )


# ==================================================
# LEARNING MODE
# ==================================================
def learning_mode(request, subtopic_id):
    subtopic = get_object_or_404(
        SubTopic.objects.prefetch_related('resources', 'questions'),
        pk=subtopic_id
    )
    resources = subtopic.resources.all()

    if request.user.role == "student":
        resources = resources.filter(
            target_classes=request.user.school_class
        ).distinct()
    
    return render(
        request,
        'library/learning_mode.html',
        {
            'subtopic': subtopic,
            'notes': resources.filter(resource_type='note'),
            'videos': resources.filter(resource_type='video'),
            'assignments': resources.filter(resource_type='assignment'),
            'pastpapers': resources.filter(resource_type='pastpaper'),
            'questions_count': subtopic.questions.count()
        }
    )


# ==================================================
# RESOURCE DETAIL
# ==================================================
def resource_detail(request, pk):
    resource = get_object_or_404(
        Resource.objects.select_related(
            'level',
            'subject',
            'topic',
            'subtopic'
        ),
        pk=pk
    )
    
    if request.user.role == "student":
        if not resource.target_classes.filter(
            id=request.user.school_class_id
        ).exists():
            raise PermissionDenied(
                "You do not have permission to access this resource."
            )

    Resource.objects.filter(pk=resource.pk).update(views=F('views') + 1)
    resource.refresh_from_db(fields=['views'])

    return render(
        request,
        'library/resource_detail.html',
        {
            'resource': resource
        }
    )


# ==================================================
# GLOBAL SEARCH
# ==================================================
def search_library(request):
    query = request.GET.get('q', '').strip()
    topics = Topic.objects.none()
    subtopics = SubTopic.objects.none()
    resources = Resource.objects.none()

    if query:
        topics = (
            Topic.objects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query)
            )
            .select_related('subject', 'level')
        )
        subtopics = (
            SubTopic.objects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query)
            )
            .select_related('topic', 'topic__subject')
        )
        resources = (
            Resource.objects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query)
            )
            .select_related(
                'level',
                'subject',
                'topic',
                'subtopic'
            )
        )

    if request.user.role == "student":
        resources = resources.filter(
            target_classes=request.user.school_class
        )

    resources = resources.distinct()

    return render(
        request,
        'library/search.html',
        {
            'query': query,
            'topics': topics,
            'subtopics': subtopics,
            'resources': resources,
        }
    )


# ==================================================
# RESOURCE MANAGEMENT
# ==================================================
@login_required
def resource_list(request):
    resources = (
        Resource.objects
        .select_related(
            "level",
            "subject",
            "topic",
            "subtopic",
        )
    )

    # Superadmin
    if request.user.is_superuser:
        pass

    # School Admin
    elif request.user.role == "school_admin":
        resources = resources.filter(
            target_classes__school=request.user.school
        )

    # Student
    elif request.user.role == "student":
        if request.user.school_class:
            resources = resources.filter(
                target_classes=request.user.school_class
            )
        else:
            resources = resources.none()

    # Other users (teachers/parents)
    else:
        resources = resources.none()

    resources = (
        resources
        .distinct()
        .order_by("-created_at")
    )

    paginator = Paginator(resources, 20)
    page = request.GET.get("page")
    resources = paginator.get_page(page)

    return render(
        request,
        "library/resource_list.html",
        {
            "resources": resources,
        },
    )


@login_required
@school_admin_required
def add_resource(request):
    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Resource added successfully.')
            return redirect('resource_list')
    else:
        form = ResourceForm(user=request.user)

    return render(
        request,
        'library/add_resource.html',
        {
            'form': form,
            'title': 'Add Resource'
        }
    )


@login_required
@school_admin_required
def edit_resource(request, pk):
    resource = get_object_or_404(Resource, pk=pk)

    if request.method == 'POST':
        form = ResourceForm(
            request.POST,
            request.FILES,
            instance=resource,
            user=request.user
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Resource updated successfully.')
            return redirect('resource_list')
    else:
        form = ResourceForm(instance=resource, user=request.user)

    return render(
        request,
        'library/add_resource.html',
        {
            'form': form,
            'title': 'Edit Resource'
        }
    )


@login_required
@school_admin_required
def delete_resource(request, pk):
    resource = get_object_or_404(Resource, pk=pk)

    if request.method == 'POST':
        resource.delete()
        messages.success(request, 'Resource deleted successfully.')
        return redirect('resource_list')

    return render(
        request,
        'library/delete_resource.html',
        {
            'resource': resource
        }
    )


# ==================================================
# AJAX
# ==================================================
@login_required
def load_topics(request):
    subject_id = request.GET.get('subject')
    topics = (
        Topic.objects
        .filter(subject_id=subject_id)
        .order_by('title')
        .values('id', 'title')
    )
    return JsonResponse(list(topics), safe=False)


@login_required
def load_subtopics(request):
    topic_id = request.GET.get('topic')
    subtopics = (
        SubTopic.objects
        .filter(topic_id=topic_id)
        .order_by('title')
        .values('id', 'title')
    )
    return JsonResponse(list(subtopics), safe=False)


# ==================================================
# FILTER RESOURCES
# ==================================================
@login_required
def resources_by_subject(request, subject_id):
    subject = get_object_or_404(Subject, pk=subject_id)
    resources = (
        Resource.objects
        .filter(subject=subject)
        .select_related(
            'level',
            'subject',
            'topic',
            'subtopic'
        )
    )
    if request.user.role == "student":
        resources = resources.filter(
            target_classes=request.user.school_class
        )

    return render(
        request,
        'library/resource_list.html',
        {
            'resources': resources,
            'selected_subject': subject
        }
    )


@login_required
def resources_by_topic(request, topic_id):
    topic = get_object_or_404(Topic, pk=topic_id)
    resources = (
        Resource.objects
        .filter(topic=topic)
        .select_related(
            'level',
            'subject',
            'topic',
            'subtopic'
        )
    )
    if request.user.role == "student":
        resources = resources.filter(
            target_classes=request.user.school_class
        )

    return render(
        request,
        'library/resource_list.html',
        {
            'resources': resources,
            'selected_topic': topic
        }
    )


@login_required
def resources_by_subtopic(request, subtopic_id):
    subtopic = get_object_or_404(SubTopic, pk=subtopic_id)
    resources = (
        Resource.objects
        .filter(subtopic=subtopic)
        .select_related(
            'level',
            'subject',
            'topic',
            'subtopic'
        )
    )
    if request.user.role == "student":
        resources = resources.filter(
            target_classes=request.user.school_class
        )

    return render(
        request,
        'library/resource_list.html',
        {
            'resources': resources,
            'selected_subtopic': subtopic
        }
    )