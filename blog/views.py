from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import F
from django.forms import (
    ClearableFileInput,
    Select,
    SelectMultiple,
    TextInput,
    Textarea,
    URLInput,
    modelform_factory,
)
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import (
    require_http_methods,
    require_POST,
)

from django_ckeditor_5.widgets import CKEditor5Widget

from .models import Category, Comment, Post


# ============================================================
# COMMENT FORM
# ============================================================

CommentForm = modelform_factory(
    Comment,
    fields=["text"],
    widgets={
        "text": Textarea(
            attrs={
                "placeholder": "Share your view",
                "rows": 4,
                "class": "form-control",
            }
        )
    },
)


# ============================================================
# POST FORM
# ============================================================

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
        "title": TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter post title...",
            }
        ),
        "category": Select(
            attrs={
                "class": "form-select",
            }
        ),
        "excerpt": Textarea(
            attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Short description of the post...",
            }
        ),
        "content": CKEditor5Widget(
            config_name="default",
        ),
        "school": Select(
            attrs={
                "class": "form-select",
            }
        ),
        "target_classes": SelectMultiple(
            attrs={
                "class": "form-select",
            }
        ),
        "image": ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": "image/*",
            }
        ),
        "video": ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": "video/*",
            }
        ),
        "youtube_url": URLInput(
            attrs={
                "class": "form-control",
                "placeholder": "https://www.youtube.com/watch?v=...",
            }
        ),
        "tags": SelectMultiple(
            attrs={
                "class": "form-select",
            }
        ),
        "visible_to_all": Select(
            attrs={
                "class": "form-select",
            }
        ),
        "status": Select(
            attrs={
                "class": "form-select",
            }
        ),
    },
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_user_role(request):
    """
    Safely return the logged-in user's role.
    """
    return getattr(request.user, "role", None)


def is_staff_user(request):
    """
    Return True for superusers, school administrators, and teachers.
    """
    user_role = get_user_role(request)

    return (
        request.user.is_authenticated
        and (
            request.user.is_superuser
            or user_role in ["school_admin", "teacher"]
        )
    )


def can_manage_post(request, post):
    """
    Determine whether the current user can edit or delete a post.
    """
    user_role = get_user_role(request)

    return (
        request.user.is_authenticated
        and (
            request.user.is_superuser
            or user_role == "school_admin"
            or (
                user_role == "teacher"
                and post.author_id == request.user.pk
            )
        )
    )


def get_post_comments(request, post):
    """
    Fetch the latest comments and mark whether the current user
    liked each comment.
    """
    comments = list(
        Comment.objects
        .filter(post=post)
        .select_related("author")
        .prefetch_related("liked_by")
        .order_by("created_at")[:20]
    )

    if request.user.is_authenticated:
        user_id = request.user.pk

        for comment in comments:
            # Uses the prefetched liked_by objects without another
            # database query for every comment.
            comment.liked_by_current_user = any(
                user.pk == user_id
                for user in comment.liked_by.all()
            )
    else:
        for comment in comments:
            comment.liked_by_current_user = False

    return comments


# ============================================================
# HOME
# ============================================================

def home(request):
    posts_qs = (
        Post.objects
        .filter(
            status="published",
            approved=True,
        )
        .select_related(
            "author",
            "category",
        )
        .prefetch_related("tags")
        .order_by("-created_at")
    )

    posts = []
    for post in posts_qs:
        # Comments
        comments = list(
            Comment.objects
            .filter(post=post)
            .select_related("author")
            .prefetch_related("liked_by")
            .order_by("created_at")[:20]
        )

        if request.user.is_authenticated:
            user_id = request.user.pk
            for comment in comments:
                comment.liked_by_current_user = any(
                    user.pk == user_id
                    for user in comment.liked_by.all()
                )
        else:
            for comment in comments:
                comment.liked_by_current_user = False

        # Like status for post
        is_liked = (
            request.user.is_authenticated
            and post.likes.filter(pk=request.user.pk).exists()
        )

        # Permissions
        can_edit = can_manage_post(request, post)
        can_delete = can_edit

        posts.append({
            "post": post,
            "comments": comments,
            "is_liked": is_liked,
            "can_edit": can_edit,
            "can_delete": can_delete,
        })

    categories = Category.objects.all()

    featured_post = (
        Post.objects
        .filter(
            status="published",
            approved=True,
            is_featured=True,
        )
        .select_related(
            "author",
            "category",
        )
        .prefetch_related("tags")
        .order_by("-created_at")
        .first()
    )

    context = {
        "posts": posts,  # now a list of dicts
        "categories": categories,
        "featured_post": featured_post,
    }

    return render(request, "home.html", context)
# ============================================================
# CATEGORY POSTS
# ============================================================

def category_post(request, slug):
    category = get_object_or_404(
        Category,
        slug=slug,
    )

    posts = (
        Post.objects
        .filter(category=category)
        .select_related(
            "author",
            "category",
        )
        .prefetch_related("tags")
        .order_by("-created_at")
    )

    context = {
        "category": category,
        "posts": posts,
    }

    return render(request, "category_post.html", context)


# ============================================================
# POST DETAIL
# ============================================================

def post_detail(request, slug):
    post = get_object_or_404(
        Post.objects
        .select_related(
            "author",
            "category",
        )
        .prefetch_related(
            "tags",
        ),
        slug=slug,
    )

    # Only non-staff users are restricted to published posts.
    if not is_staff_user(request) and post.status != "published":
        raise PermissionDenied("This post is not available.")

    # ---------------------------------------------------------
    # INCREMENT VIEW COUNT ONCE PER SESSION
    # ---------------------------------------------------------
    session_key = f"viewed_post_{post.pk}"

    if not request.session.get(session_key):
        Post.objects.filter(pk=post.pk).update(
            view_count=F("view_count") + 1
        )

        request.session[session_key] = True
        request.session.modified = True

        post.refresh_from_db(
            fields=["view_count"]
        )

    # ---------------------------------------------------------
    # COMMENTS
    # ---------------------------------------------------------
    comments = get_post_comments(
        request,
        post,
    )

    # ---------------------------------------------------------
    # PERMISSIONS
    # ---------------------------------------------------------
    can_edit = can_manage_post(
        request,
        post,
    )

    can_delete = can_edit

    # ---------------------------------------------------------
    # LIKE STATUS
    # ---------------------------------------------------------
    is_liked = False

    if request.user.is_authenticated:
        is_liked = post.likes.filter(
            pk=request.user.pk
        ).exists()

    # ---------------------------------------------------------
    # COMMENT FORM
    # ---------------------------------------------------------
    comment_form = CommentForm()

    # ---------------------------------------------------------
    # CONTEXT
    # ---------------------------------------------------------
    context = {
        "post": post,
        "comments": comments,
        "total_comments": len(comments),
        "is_liked": is_liked,
        "form": comment_form,
        "can_edit": can_edit,
        "can_delete": can_delete,
    }

    return render(
        request,
        "post_detail.html",
        context,
    )


# ============================================================
# LIKE OR UNLIKE POST
# ============================================================

@login_required
@require_POST
def like_toggle(request, slug):
    post = get_object_or_404(
        Post,
        slug=slug,
        status="published",
    )

    if post.likes.filter(pk=request.user.pk).exists():
        post.likes.remove(request.user)
        is_liked = False
    else:
        post.likes.add(request.user)
        is_liked = True

    return JsonResponse(
        {
            "is_liked": is_liked,
            "like_count": post.likes.count(),
        }
    )


# ============================================================
# ADD COMMENT
# ============================================================
@login_required
@require_POST
def add_comment(request, slug):
    post = get_object_or_404(
        Post,
        slug=slug,
        status="published",
    )

    form = CommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()

        # Redirect to home with anchor to this post
        return redirect(
            f"{reverse('blog:home')}#post-{post.pk}"
        )

    return redirect("blog:home")
# ============================================================
# ADD POST
# ============================================================

@login_required
@require_http_methods(["GET", "POST"])
def add_post(request):
    allowed_roles = [
        "school_admin",
        "teacher",
    ]

    user_role = get_user_role(request)

    has_permission = (
        request.user.is_superuser
        or user_role in allowed_roles
    )

    if not has_permission:
        raise PermissionDenied(
            "You do not have permission to add posts."
        )

    if request.method == "POST":
        form = PostForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()

            # Required for ManyToMany fields such as tags.
            form.save_m2m()

            return redirect(post.get_absolute_url())
    else:
        form = PostForm()

    return render(
        request,
        "add_post.html",
        {
            "form": form,
        },
    )


# ============================================================
# EDIT POST
# ============================================================

@login_required
@require_http_methods(["GET", "POST"])
def edit_post(request, pk):
    post = get_object_or_404(
        Post,
        pk=pk,
    )

    if not can_manage_post(request, post):
        raise PermissionDenied(
            "You do not have permission to edit this post."
        )

    if request.method == "POST":
        form = PostForm(
            request.POST,
            request.FILES,
            instance=post,
        )

        if form.is_valid():
            updated_post = form.save(
                commit=False
            )

            # Preserve the original author.
            updated_post.author = post.author
            updated_post.save()

            # Required for ManyToMany fields such as tags.
            form.save_m2m()

            return redirect(
                updated_post.get_absolute_url()
            )
    else:
        form = PostForm(
            instance=post
        )

    return render(
        request,
        "edit_post.html",
        {
            "form": form,
            "post": post,
        },
    )


# ============================================================
# DELETE POST
# ============================================================

@login_required
@require_http_methods(["GET", "POST"])
def delete_post(request, pk):
    post = get_object_or_404(
        Post,
        pk=pk,
    )

    if not can_manage_post(request, post):
        raise PermissionDenied(
            "You do not have permission to delete this post."
        )

    if request.method == "POST":
        post.delete()
        return redirect("blog:home")

    return render(
        request,
        "delete_post.html",
        {
            "post": post,
        },
    )