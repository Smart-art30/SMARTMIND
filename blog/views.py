from django.http import JsonResponse
from django.shortcuts import (
    render,
    get_object_or_404,
    redirect,
)
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import (
    require_http_methods,
    require_POST,
)
from django.db.models import Prefetch, F, Value
from django.db.models.functions import Coalesce
from django.core.exceptions import PermissionDenied

from django.forms import (
    modelform_factory,
    Textarea,
    TextInput,
    Select,
    ClearableFileInput,
    URLInput,
    SelectMultiple,
)

from django_ckeditor_5.widgets import CKEditor5Widget

from .models import (
    Post,
    Comment,
    Category,
)


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
            config_name="default"
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
# HOME
# ============================================================

def home(request):

    posts = (
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
        .order_by("-created_at")
        .first()
    )

    return render(
        request,
        "home.html",
        {
            "posts": posts,
            "categories": categories,
            "featured_post": featured_post,
        },
    )


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

    return render(
        request,
        "category_post.html",
        {
            "category": category,
            "posts": posts,
        },
    )

# ============================================================
# POST DETAIL
# ============================================================
def post_detail(request, slug):

    post = get_object_or_404(
        Post,
        slug=slug,
        status="published",
    )

    return render(
        request,
        "post_detail.html",
        {
            "post": post,
        },
    )

# ============================================================
# LIKE / UNLIKE POST
# ============================================================

@login_required
@require_POST
def like_toggle(request, slug):

    post = get_object_or_404(
        Post,
        slug=slug,
        status="published",
    )

    if post.likes.filter(
        id=request.user.id
    ).exists():

        post.likes.remove(
            request.user
        )

        is_liked = False

    else:

        post.likes.add(
            request.user
        )

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

    form = CommentForm(
        request.POST
    )

    if form.is_valid():

        comment = form.save(
            commit=False
        )

        comment.post = post

        comment.author = request.user

        comment.save()

        return redirect(
            f"{post.get_absolute_url()}"
            f"?commented=1"
            f"#comment-{comment.id}"
        )

    return redirect(
        post.get_absolute_url()
    )


# ============================================================
# ADD POST
# ============================================================

@login_required
@require_http_methods(["GET", "POST"])
def add_post(request):

    # --------------------------------------------------------
    # ALLOWED ROLES
    # --------------------------------------------------------

    allowed_roles = [
        "school_admin",
        "teacher",
    ]

    user_role = getattr(
        request.user,
        "role",
        None,
    )

    if not (
        request.user.is_superuser
        or user_role in allowed_roles
    ):

        raise PermissionDenied(
            "You do not have permission to add posts."
        )

    # --------------------------------------------------------
    # POST REQUEST
    # --------------------------------------------------------

    if request.method == "POST":

        form = PostForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            post = form.save(
                commit=False
            )

            # Automatically assign author
            post.author = request.user

            post.save()

            form.save_m2m()

            return redirect(
                post.get_absolute_url()
            )

    # --------------------------------------------------------
    # GET REQUEST
    # --------------------------------------------------------

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

    user_role = getattr(
        request.user,
        "role",
        None,
    )

    # --------------------------------------------------------
    # PERMISSION
    # --------------------------------------------------------

    can_edit = (

        request.user.is_superuser

        or user_role == "school_admin"

        or (
            user_role == "teacher"
            and post.author_id == request.user.id
        )
    )

    if not can_edit:

        raise PermissionDenied(
            "You do not have permission to edit this post."
        )

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

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

            # Never allow editing the author
            updated_post.author = post.author

            updated_post.save()

            form.save_m2m()

            return redirect(
                updated_post.get_absolute_url()
            )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

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

    user_role = getattr(
        request.user,
        "role",
        None,
    )

    # --------------------------------------------------------
    # PERMISSION
    # --------------------------------------------------------

    can_delete = (

        request.user.is_superuser

        or user_role == "school_admin"

        or (
            user_role == "teacher"
            and post.author_id == request.user.id
        )
    )

    if not can_delete:

        raise PermissionDenied(
            "You do not have permission to delete this post."
        )

    # --------------------------------------------------------
    # CONFIRM DELETE
    # --------------------------------------------------------

    if request.method == "POST":

        post.delete()

        return redirect(
            "blog:home"
        )

    # --------------------------------------------------------
    # SHOW CONFIRMATION
    # --------------------------------------------------------

    return render(
        request,
        "delete_post.html",
        {
            "post": post,
        },
    )
