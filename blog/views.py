from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db.models import Prefetch
from django.core.exceptions import PermissionDenied
from django.forms import modelform_factory, Textarea, TextInput, Select, ClearableFileInput, URLInput, SelectMultiple
from django_ckeditor_5.widgets import CKEditor5Widget

from .models import Post, Comment, Category


CommentForm = modelform_factory(
    Comment,
    fields=["text"],
    widgets={
        "text": Textarea(attrs={
            "placeholder": "Share your view",
            "rows": 4,
            "class": "form-control",
        })
    }
)

PostForm = modelform_factory(
    Post,
    fields=[
        "title",
        "category",
        "excerpt",
        "content",
        "school",
        "target_classes",
        "image",
        "video",
        "youtube_url",
        "tags",
        "visible_to_all",
        "status",
    ],
    widgets={
        "title": TextInput(attrs={"class": "form-control"}),
        "category": Select(attrs={"class": "form-select"}),
        "excerpt": Textarea(attrs={"class": "form-control", "rows": 2}),
        "content": CKEditor5Widget(config_name="default"),
        "school": Select(attrs={"class": "form-select"}),
        "target_classes": SelectMultiple(attrs={"class": "form-select"}),
        "image": ClearableFileInput(attrs={"class": "form-control"}),
        "video": ClearableFileInput(attrs={"class": "form-control"}),
        "youtube_url": URLInput(attrs={"class": "form-control"}),
        "tags": SelectMultiple(attrs={"class": "form-select"}),
        "visible_to_all": Select(attrs={"class": "form-select"}),
        "status": Select(attrs={"class": "form-select"}),
    },
)


def home(request):
    posts = Post.objects.filter(status="published", approved=True).order_by("-created_at")
    categories = Category.objects.all()
    featured_post = Post.objects.filter(
        status="published",
        approved=True,
        is_featured=True
    ).order_by("-created_at").first()

    return render(request, "home.html", {
        "posts": posts,
        "categories": categories,
        "featured_post": featured_post,
    })

def category_post(request, slug):
    category = get_object_or_404(Category, slug=slug)
    posts = Post.objects.filter(category=category).order_by("-created_at")
    return render(request, "category_post.html", {"category": category, "posts": posts})


def post_detail(request, slug):
    comments_qs = Comment.objects.order_by("created_at").prefetch_related("liked_by")

    post = get_object_or_404(
        Post.objects.select_related("category", "author")
        .prefetch_related("tags", "likes", Prefetch("comments", queryset=comments_qs))
        .filter(status="published"),
        slug=slug,
    )

    session_key = f"viewed_post_{post.id}"
    if not request.session.get(session_key):
        Post.objects.filter(id=post.id).update(view_count=post.view_count + 1)
        request.session[session_key] = True
        post.view_count += 1

    comments = list(post.comments.all()[:20])

    if request.user.is_authenticated:
        user_id = request.user.id
        for comment in comments:
            comment.liked_by_current_user = comment.liked_by.filter(id=user_id).exists()
    else:
        for comment in comments:
            comment.liked_by_current_user = False

    context = {
        "post": post,
        "comments": comments,
        "total_comments": post.comments.count(),
        "is_liked": request.user.is_authenticated and post.likes.filter(id=request.user.id).exists(),
        "form": CommentForm(),
    }
    return render(request, "post_detail.html", context)


@login_required
@require_http_methods(["POST"])
def like_toggle(request, slug):
    post = get_object_or_404(Post, slug=slug, status="published")

    if post.likes.filter(id=request.user.id).exists():
        post.likes.remove(request.user)
        is_liked = False
    else:
        post.likes.add(request.user)
        is_liked = True

    return JsonResponse({
        "is_liked": is_liked,
        "like_count": post.likes.count(),
    })


@login_required
@require_http_methods(["POST"])
def add_comment(request, slug):
    post = get_object_or_404(Post, slug=slug, status="published")
    form = CommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
        return redirect(f"{post.get_absolute_url()}?commented=1#comment-{comment.id}")

    return redirect(post.get_absolute_url())


@login_required
@require_http_methods(["GET", "POST"])
def add_post(request):
    # Allow superusers, school admins, and teachers
    allowed_roles = ["school_admin", "teacher"]

    if not (
        request.user.is_superuser
        or getattr(request.user, "role", None) in allowed_roles
    ):
        raise PermissionDenied("You do not have permission to add posts.")

    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)

        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            form.save_m2m()

            return redirect(post.get_absolute_url())

    else:
        form = PostForm()

    return render(request, "add_post.html", {"form": form})