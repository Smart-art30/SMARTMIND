# ============================================================
# IMPORTS
# ============================================================

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.forms import (
    ClearableFileInput,
    Select,
    SelectMultiple,
    TextInput,
    Textarea,
    URLInput,
    modelform_factory,
)
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.urls import reverse
from django.views.decorators.http import (
    require_http_methods,
    require_POST,
)
from django.db import transaction
from django.forms import FileInput
from django_ckeditor_5.widgets import CKEditor5Widget
from django.conf import settings
from django.db.models import (
    Count,
    F,
    Prefetch,
)

import os

from .models import (
    Category,
    Comment,
    CommentReaction,
    Post,
    PostImage,
    PostAttachment,
    PostReaction,
)

from .widgets import MultipleFileInput

from django.template.loader import render_to_string
from django.http import JsonResponse
# ============================================================
# DOCUMENT UPLOAD CONSTANTS
# ============================================================

ALLOWED_DOC_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".txt",
    ".csv",
    ".zip",
    ".rar",
}

MAX_DOCUMENT_SIZE = getattr(
    settings,
    "MAX_DOCUMENT_SIZE",
    200 * 1024 * 1024,
)


# ============================================================
# FORMS
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

ReplyForm = modelform_factory(
    Comment,
    fields=["text"],
    widgets={
        "text": Textarea(
            attrs={
                "placeholder": "Write a reply...",
                "rows": 2,
                "class": "form-control reply-textarea",
            }
        )
    },
)


# ============================================================
# MULTIPLE IMAGE WIDGET / FIELD
# ============================================================

class MultipleImageInput(ClearableFileInput):

    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):

    def __init__(self, *args, **kwargs):

        kwargs["widget"] = MultipleImageInput(
            attrs={
                "class": "photo-file-input",
                "accept": "image/*",
            }
        )

        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):

        if not data:
            return []

        if not isinstance(data, (list, tuple)):
            data = [data]

        return [
            super().clean(file, initial)
            for file in data
        ]


# ============================================================
# POST FORM
# ============================================================

class PostForm(forms.ModelForm):

    images = forms.FileField(
        widget=MultipleFileInput(
            attrs={
                "accept": "image/*",
                "id": "id_images",
                "name": "images",
                "class": "form-control",
                "style": "display: none;",
            }
        ),
        required=False,
        label="Photos",
        help_text="Select multiple photos (JPG, PNG, GIF, WebP)",
    )

    class Meta:

        model = Post

        fields = [
            "title",
            "category",
            "excerpt",
            "content",
            "school",
            "target_classes",
            "video",
            "youtube_url",
            "tags",
            "visible_to_all",
            "status",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter post title...",
                }
            ),
            "category": forms.Select(attrs={"class": "form-select"}),
            "excerpt": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Write a brief summary...",
                }
            ),
            "content": CKEditor5Widget(
                attrs={"class": "django_ckeditor_5"},
                config_name="extends",
            ),
            "school": forms.Select(attrs={"class": "form-select"}),
            "target_classes": forms.CheckboxSelectMultiple(),
            "video": ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "video/*",
                    "id": "id_video",
                }
            ),
            "youtube_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://www.youtube.com/watch?v=...",
                }
            ),
            "tags": forms.SelectMultiple(
                attrs={
                    "class": "form-select",
                    "size": 5,
                }
            ),
            "visible_to_all": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if "target_classes" in self.fields:
            self.fields["target_classes"].queryset = (
                self.fields["target_classes"]
                .queryset
                .order_by("name")
            )


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_user_role(request):
    """Safely return the logged-in user's role."""

    return getattr(request.user, "role", None)


def is_staff_user(request):
    """True for superusers, school_admins and teachers."""

    user_role = get_user_role(request)

    return (
        request.user.is_authenticated
        and (
            request.user.is_superuser
            or user_role in ["school_admin", "teacher"]
        )
    )


def can_manage_post(request, post):
    """Can the current user edit / delete this post?"""

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


def _attach_comment_meta(comment, user_id):
    """
    Attach like + reaction metadata to a Comment instance.

    Adds:
        likes_count
        liked_by_current_user
        reaction_counts   -> {reaction_code: count}
        user_reaction     -> reaction_code or None
        total_reactions   -> int
        replies_list      -> [] (populated later by _build_comment_tree)
    """

    comment.likes_count = comment.liked_by.count()

    if user_id:
        comment.liked_by_current_user = any(
            u.pk == user_id for u in comment.liked_by.all()
        )
    else:
        comment.liked_by_current_user = False

    counts = {}
    user_reaction = None

    for rxn in comment.reactions.all():
        counts[rxn.reaction] = counts.get(rxn.reaction, 0) + 1
        if user_id and rxn.user_id == user_id:
            user_reaction = rxn.reaction

    comment.reaction_counts = counts
    comment.user_reaction = user_reaction
    comment.total_reactions = sum(counts.values())

    # Ensure every comment has a replies_list for the template
    if not hasattr(comment, "replies_list"):
        comment.replies_list = []


def _build_comment_tree(comments):
    """
    Take a flat list of Comment objects (all for the same post)
    and return only the top-level ones, with `.replies_list`
    populated recursively to arbitrary depth.
    """

    by_id = {c.pk: c for c in comments}

    # Ensure each comment starts with an empty replies_list
    for c in comments:
        c.replies_list = []

    roots = []

    for c in comments:
        if c.parent_id and c.parent_id in by_id:
            by_id[c.parent_id].replies_list.append(c)
        else:
            roots.append(c)

    # Sort replies chronologically at every level
    def sort_tree(nodes):
        nodes.sort(key=lambda x: x.created_at)
        for n in nodes:
            sort_tree(n.replies_list)

    # Top-level comments ordered newest-first
    roots.sort(key=lambda x: x.created_at, reverse=True)
    for r in roots:
        sort_tree(r.replies_list)

    return roots


def get_post_comments(request, post):
    """
    Fetch ALL comments for a post (every depth), build the nested
    tree, and attach like/reaction metadata to each comment.
    Returns only the top-level comments; replies live under
    `.replies_list` on each comment.
    """

    all_comments = list(
        Comment.objects
        .filter(post=post)
        .select_related("author")
        .prefetch_related("liked_by", "reactions")
        .order_by("created_at")
    )

    user_id = (
        request.user.pk
        if request.user.is_authenticated
        else None
    )

    for c in all_comments:
        _attach_comment_meta(c, user_id)

    return _build_comment_tree(all_comments)


def _attach_post_reactions(request, post):
    """Add reaction aggregates to a Post instance."""

    counts = dict(
        PostReaction.objects
        .filter(post=post)
        .values_list("reaction")
        .annotate(c=Count("id"))
    )

    if request.user.is_authenticated:
        user_reaction = (
            PostReaction.objects
            .filter(post=post, user=request.user)
            .values_list("reaction", flat=True)
            .first()
        )
    else:
        user_reaction = None

    post.reaction_counts = counts
    post.user_reaction = user_reaction
    post.total_reactions = sum(counts.values())


# ============================================================
# HOME
# ============================================================

def home(request):

    user_id = (
        request.user.pk
        if request.user.is_authenticated
        else None
    )

    posts_qs = (
        Post.objects
        .select_related("author", "category")
        .prefetch_related(
            "tags",
            "images",
            "attachments",
            "likes",
        )
        .order_by("-created_at")
    )

    posts = []

    for post in posts_qs:

        comments = get_post_comments(request, post)

        comments_count = (
            Comment.objects
            .filter(post=post)
            .count()
        )

        is_liked = (
            bool(user_id)
            and post.likes.filter(pk=user_id).exists()
        )

        likes_count = post.likes.count()
        views_count = post.view_count

        _attach_post_reactions(request, post)

        can_edit = can_manage_post(request, post)
        can_delete = can_edit

        posts.append({
            "post": post,
            "comments": comments,
            "comments_count": comments_count,
            "likes_count": likes_count,
            "views_count": views_count,
            "is_liked": is_liked,
            "can_edit": can_edit,
            "can_delete": can_delete,
        })

    categories = (
        Category.objects
        .all()
        .order_by("name")
    )

    featured_post = (
        Post.objects
        .filter(is_featured=True)
        .select_related("author", "category")
        .prefetch_related(
            "tags",
            "images",
            "attachments",
        )
        .order_by("-created_at")
        .first()
    )

    if featured_post:
        _attach_post_reactions(request, featured_post)

    context = {
        "posts": posts,
        "categories": categories,
        "featured_post": featured_post,
        "reaction_choices": CommentReaction.REACTION_CHOICES,
    }

    return render(request, "home.html", context)


# ============================================================
# POST DETAIL
# ============================================================

def post_detail(request, slug):

    post = get_object_or_404(
        Post.objects
        .select_related("author", "category", "school")
        .prefetch_related(
            "tags",
            "images",
            "attachments",
            "likes",
        ),
        slug=slug,
    )

    # ---- View count (once per session) ----
    viewed_posts = request.session.get("viewed_posts", [])

    if post.pk not in viewed_posts:

        Post.objects.filter(pk=post.pk).update(
            view_count=F("view_count") + 1
        )
        post.refresh_from_db(fields=["view_count"])

        viewed_posts.append(post.pk)
        request.session["viewed_posts"] = viewed_posts

    # ---- Comments (infinite-depth tree) ----
    comments = get_post_comments(request, post)

    comments_count = (
        Comment.objects
        .filter(post=post)
        .count()
    )

    # ---- Post likes ----
    is_liked = (
        request.user.is_authenticated
        and post.likes.filter(pk=request.user.pk).exists()
    )

    likes_count = post.likes.count()
    views_count = post.view_count

    # ---- Post reactions ----
    _attach_post_reactions(request, post)

    # ---- Permissions ----
    can_edit = can_manage_post(request, post)
    can_delete = can_edit

    context = {
        "post": post,
        "comments": comments,
        "comments_count": comments_count,
        "likes_count": likes_count,
        "views_count": views_count,
        "is_liked": is_liked,
        "can_edit": can_edit,
        "can_delete": can_delete,
        "comment_form": CommentForm(),
        "reaction_choices": CommentReaction.REACTION_CHOICES,
    }

    return render(request, "post_detail.html", context)


# ============================================================
# CATEGORY POSTS
# ============================================================

def category_post(request, slug):

    category = get_object_or_404(Category, slug=slug)

    posts_qs = (
        Post.objects
        .filter(category=category)
        .select_related("author", "category", "school")
        .prefetch_related(
            "tags",
            "images",
            "attachments",
            "likes",
        )
        .order_by("-created_at")
    )

    posts = []

    for post in posts_qs:

        comments = get_post_comments(request, post)

        comments_count = (
            Comment.objects
            .filter(post=post)
            .count()
        )

        is_liked = (
            request.user.is_authenticated
            and post.likes.filter(pk=request.user.pk).exists()
        )

        likes_count = post.likes.count()
        views_count = post.view_count

        _attach_post_reactions(request, post)

        can_edit = can_manage_post(request, post)
        can_delete = can_edit

        post.category_name = (
            post.category.name
            if post.category
            else ""
        )

        post.comments_list = comments
        post.comments_count = comments_count
        post.likes_count = likes_count
        post.views_count = views_count
        post.is_liked = is_liked
        post.can_edit = can_edit
        post.can_delete = can_delete

        posts.append(post)

    categories = (
        Category.objects
        .all()
        .order_by("name")
    )

    context = {
        "category": category,
        "posts": posts,
        "categories": categories,
        "reaction_choices": CommentReaction.REACTION_CHOICES,
    }

    return render(request, "category_post.html", context)


# ============================================================
# POST LIKE TOGGLE
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

    return JsonResponse({
        "is_liked": is_liked,
        "like_count": post.likes.count(),
    })


# ============================================================
# ADD COMMENT
# ============================================================
@login_required
@require_POST
def add_comment(request, slug):

    post = get_object_or_404(Post, slug=slug)
    form = CommentForm(request.POST)

    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if not form.is_valid():
        if is_ajax:
            return JsonResponse(
                {"success": False, "errors": form.errors},
                status=400,
            )
        return redirect(f"{post.get_absolute_url()}#comments-section")

    comment = form.save(commit=False)
    comment.post = post
    comment.author = request.user
    comment.save()

    # Attach like/reaction metadata so the partial renders correctly
    _attach_comment_meta(comment, request.user.pk)

    if is_ajax:
        html = render_to_string(
            "blog/partials/_comment.html",
            {
                "comment": comment,
                "user": request.user,
                "reaction_choices": CommentReaction.REACTION_CHOICES,
            },
            request=request,
        )
        return JsonResponse({
            "success": True,
            "comment_id": comment.pk,
            "html": html,
            "comments_count": Comment.objects.filter(post=post).count(),
        })

    return redirect(f"{post.get_absolute_url()}#comments-section")


@login_required
@require_POST
def add_reply(request, slug, comment_id):

    post = get_object_or_404(Post, slug=slug)
    parent = get_object_or_404(Comment, pk=comment_id, post=post)
    form = ReplyForm(request.POST)

    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if not form.is_valid():
        if is_ajax:
            return JsonResponse(
                {"success": False, "errors": form.errors},
                status=400,
            )
        return redirect(f"{post.get_absolute_url()}#comment-{parent.pk}")

    reply = form.save(commit=False)
    reply.post = post
    reply.author = request.user
    reply.parent = parent
    reply.save()

    # Attach metadata so the partial renders correctly
    _attach_comment_meta(reply, request.user.pk)

    if is_ajax:
        html = render_to_string(
            "blog/partials/_comment.html",
            {
                "comment": reply,
                "user": request.user,
                "reaction_choices": CommentReaction.REACTION_CHOICES,
            },
            request=request,
        )
        return JsonResponse({
            "success": True,
            "reply_id": reply.pk,
            "parent_id": parent.pk,
            "html": html,
        })

    return redirect(f"{post.get_absolute_url()}#comment-{parent.pk}")
# ============================================================
# COMMENT LIKE TOGGLE
# ============================================================

@login_required
@require_POST
def comment_like_toggle(request, comment_id):

    comment = get_object_or_404(Comment, pk=comment_id)

    if comment.liked_by.filter(pk=request.user.pk).exists():
        comment.liked_by.remove(request.user)
        is_liked = False
    else:
        comment.liked_by.add(request.user)
        is_liked = True

    return JsonResponse({
        "success": True,
        "is_liked": is_liked,
        "likes_count": comment.liked_by.count(),
    })


# ============================================================
# COMMENT REACTION TOGGLE
# ============================================================

@login_required
@require_POST
def comment_react(request, comment_id):

    comment = get_object_or_404(Comment, pk=comment_id)
    reaction = request.POST.get("reaction")

    valid = dict(CommentReaction.REACTION_CHOICES)

    if reaction not in valid:
        return JsonResponse(
            {"success": False, "message": "Invalid reaction"},
            status=400,
        )

    existing = CommentReaction.objects.filter(
        comment=comment, user=request.user
    ).first()

    if existing and existing.reaction == reaction:
        existing.delete()
        user_reaction = None
    elif existing:
        existing.reaction = reaction
        existing.save(update_fields=["reaction"])
        user_reaction = reaction
    else:
        CommentReaction.objects.create(
            comment=comment,
            user=request.user,
            reaction=reaction,
        )
        user_reaction = reaction

    counts = dict(
        CommentReaction.objects
        .filter(comment=comment)
        .values_list("reaction")
        .annotate(c=Count("id"))
    )

    return JsonResponse({
        "success": True,
        "user_reaction": user_reaction,
        "reaction_counts": counts,
        "total_reactions": sum(counts.values()),
    })


# ============================================================
# POST REACTION TOGGLE
# ============================================================

@login_required
@require_POST
def post_react(request, slug):

    post = get_object_or_404(Post, slug=slug)
    reaction = request.POST.get("reaction")

    valid = dict(PostReaction.REACTION_CHOICES)

    if reaction not in valid:
        return JsonResponse(
            {"success": False, "message": "Invalid reaction"},
            status=400,
        )

    existing = PostReaction.objects.filter(
        post=post, user=request.user
    ).first()

    if existing and existing.reaction == reaction:
        existing.delete()
        user_reaction = None
    elif existing:
        existing.reaction = reaction
        existing.save(update_fields=["reaction"])
        user_reaction = reaction
    else:
        PostReaction.objects.create(
            post=post,
            user=request.user,
            reaction=reaction,
        )
        user_reaction = reaction

    counts = dict(
        PostReaction.objects
        .filter(post=post)
        .values_list("reaction")
        .annotate(c=Count("id"))
    )

    return JsonResponse({
        "success": True,
        "user_reaction": user_reaction,
        "reaction_counts": counts,
        "total_reactions": sum(counts.values()),
    })


# ============================================================
# ADD POST
# ============================================================

@login_required
@require_http_methods(["GET", "POST"])
def add_post(request):

    allowed_roles = ["school_admin", "teacher"]
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

        form = PostForm(request.POST, request.FILES)

        if form.is_valid():

            uploaded_images = request.FILES.getlist("images")
            uploaded_docs = request.FILES.getlist("attachments")

            for image in uploaded_images:

                if not is_valid_image(image):
                    messages.error(
                        request,
                        f"Invalid image: {image.name}. "
                        "Please use JPG, PNG, GIF, or WebP."
                    )
                    return render(
                        request,
                        "add_post.html",
                        {"form": form},
                    )

                if image.size > settings.MAX_IMAGE_SIZE:
                    messages.error(
                        request,
                        f'Image "{image.name}" exceeds '
                        f"{settings.MAX_IMAGE_SIZE // (1024*1024)}MB limit."
                    )
                    return render(
                        request,
                        "add_post.html",
                        {"form": form},
                    )

            for doc in uploaded_docs:

                if not is_valid_document(doc):
                    messages.error(
                        request,
                        f"Invalid document: {doc.name}. "
                        "Allowed: PDF, DOC, DOCX, XLS, XLSX, "
                        "PPT, PPTX, TXT, CSV, ZIP, RAR."
                    )
                    return render(
                        request,
                        "add_post.html",
                        {"form": form},
                    )

                if doc.size > MAX_DOCUMENT_SIZE:
                    messages.error(
                        request,
                        f'Document "{doc.name}" exceeds '
                        f"{MAX_DOCUMENT_SIZE // (1024*1024)}MB limit."
                    )
                    return render(
                        request,
                        "add_post.html",
                        {"form": form},
                    )

            if "video" in request.FILES:

                video = request.FILES["video"]

                if not is_valid_video(video):
                    messages.error(
                        request,
                        "Invalid video format. "
                        "Please use MP4, WebM, or OGG."
                    )
                    return render(
                        request,
                        "add_post.html",
                        {"form": form},
                    )

                if video.size > settings.MAX_VIDEO_SIZE:
                    messages.error(
                        request,
                        f"Video exceeds "
                        f"{settings.MAX_VIDEO_SIZE // (1024*1024)}MB limit."
                    )
                    return render(
                        request,
                        "add_post.html",
                        {"form": form},
                    )

            try:

                with transaction.atomic():

                    post = form.save(commit=False)
                    post.author = request.user
                    post.save()
                    form.save_m2m()

                    for position, image in enumerate(uploaded_images):
                        PostImage.objects.create(
                            post=post,
                            image=image,
                            position=position,
                        )

                    for position, doc in enumerate(uploaded_docs):
                        PostAttachment.objects.create(
                            post=post,
                            file=doc,
                            original_name=doc.name,
                            position=position,
                        )

                messages.success(
                    request,
                    f'Post "{post.title}" created successfully!'
                )
                return redirect("blog:home")

            except Exception as e:
                messages.error(
                    request,
                    f"Error creating post: {str(e)}"
                )
                return render(
                    request,
                    "add_post.html",
                    {"form": form},
                )

        else:

            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(
                        request,
                        f"{field}: {error}"
                    )

    else:

        form = PostForm()

    return render(
        request,
        "add_post.html",
        {"form": form}
    )


# ============================================================
# EDIT POST
# ============================================================

@login_required
@require_http_methods(["GET", "POST"])
def edit_post(request, pk):

    post = get_object_or_404(Post, pk=pk)

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

            uploaded_images = request.FILES.getlist("images")
            uploaded_docs = request.FILES.getlist("attachments")

            for image in uploaded_images:

                if not is_valid_image(image):
                    messages.error(
                        request,
                        f"Invalid image: {image.name}. "
                        "Please use JPG, PNG, GIF, or WebP."
                    )
                    return render(
                        request,
                        "edit_post.html",
                        {"form": form, "post": post},
                    )

                if image.size > settings.MAX_IMAGE_SIZE:
                    messages.error(
                        request,
                        f'Image "{image.name}" exceeds '
                        f"{settings.MAX_IMAGE_SIZE // (1024*1024)}MB limit."
                    )
                    return render(
                        request,
                        "edit_post.html",
                        {"form": form, "post": post},
                    )

            for doc in uploaded_docs:

                if not is_valid_document(doc):
                    messages.error(
                        request,
                        f"Invalid document: {doc.name}. "
                        "Allowed: PDF, DOC, DOCX, XLS, XLSX, "
                        "PPT, PPTX, TXT, CSV, ZIP, RAR."
                    )
                    return render(
                        request,
                        "edit_post.html",
                        {"form": form, "post": post},
                    )

                if doc.size > MAX_DOCUMENT_SIZE:
                    messages.error(
                        request,
                        f'Document "{doc.name}" exceeds '
                        f"{MAX_DOCUMENT_SIZE // (1024*1024)}MB limit."
                    )
                    return render(
                        request,
                        "edit_post.html",
                        {"form": form, "post": post},
                    )

            if "video" in request.FILES:

                video = request.FILES["video"]

                if not is_valid_video(video):
                    messages.error(
                        request,
                        "Invalid video format. "
                        "Please use MP4, WebM, or OGG."
                    )
                    return render(
                        request,
                        "edit_post.html",
                        {"form": form, "post": post},
                    )

                if video.size > settings.MAX_VIDEO_SIZE:
                    messages.error(
                        request,
                        f"Video exceeds "
                        f"{settings.MAX_VIDEO_SIZE // (1024*1024)}MB limit."
                    )
                    return render(
                        request,
                        "edit_post.html",
                        {"form": form, "post": post},
                    )

            try:

                with transaction.atomic():

                    updated_post = form.save(commit=False)
                    updated_post.author = post.author
                    updated_post.save()
                    form.save_m2m()

                    current_count = post.images.count()

                    for index, image in enumerate(
                        uploaded_images,
                        start=current_count,
                    ):
                        PostImage.objects.create(
                            post=updated_post,
                            image=image,
                            position=index,
                        )

                    current_doc_count = post.attachments.count()

                    for index, doc in enumerate(
                        uploaded_docs,
                        start=current_doc_count,
                    ):
                        PostAttachment.objects.create(
                            post=updated_post,
                            file=doc,
                            original_name=doc.name,
                            position=index,
                        )

                messages.success(
                    request,
                    f'Post "{updated_post.title}" updated successfully!'
                )
                return redirect(updated_post.get_absolute_url())

            except Exception as e:
                messages.error(
                    request,
                    f"Error updating post: {str(e)}"
                )
                return render(
                    request,
                    "edit_post.html",
                    {"form": form, "post": post},
                )

        else:

            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(
                        request,
                        f"{field}: {error}"
                    )

    else:

        form = PostForm(instance=post)

    return render(
        request,
        "edit_post.html",
        {"form": form, "post": post},
    )


# ============================================================
# FILE VALIDATORS
# ============================================================

def is_valid_image(file):
    valid_types = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
    ]
    return file.content_type in valid_types


def is_valid_video(file):
    valid_types = [
        "video/mp4",
        "video/webm",
        "video/ogg",
    ]
    return file.content_type in valid_types


def is_valid_document(file):
    ext = os.path.splitext(file.name)[1].lower()
    return ext in ALLOWED_DOC_EXTENSIONS


# ============================================================
# REMOVE IMAGE (AJAX)
# ============================================================

@login_required
@require_POST
def remove_image(request, image_id):

    try:
        image = PostImage.objects.get(id=image_id)
    except PostImage.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Image not found"},
            status=404,
        )

    if not can_manage_post(request, image.post):
        return JsonResponse(
            {"success": False, "message": "Permission denied"},
            status=403,
        )

    try:
        image.delete()
        return JsonResponse({
            "success": True,
            "message": "Image removed successfully",
        })
    except Exception as e:
        return JsonResponse(
            {"success": False, "message": str(e)},
            status=500,
        )


# ============================================================
# REMOVE DOCUMENT (AJAX)
# ============================================================

@login_required
@require_POST
def remove_document(request, pk):

    try:
        document = PostAttachment.objects.get(pk=pk)
    except PostAttachment.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Document not found"},
            status=404,
        )

    if not can_manage_post(request, document.post):
        return JsonResponse(
            {"success": False, "message": "Permission denied"},
            status=403,
        )

    try:
        document.file.delete(save=False)
        document.delete()
        return JsonResponse({
            "success": True,
            "message": "Document removed successfully",
        })
    except Exception as e:
        return JsonResponse(
            {"success": False, "message": str(e)},
            status=500,
        )


# ============================================================
# DELETE POST
# ============================================================

@login_required
@require_http_methods(["GET", "POST"])
def delete_post(request, pk):

    post = get_object_or_404(Post, pk=pk)

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
        {"post": post},
    )


def can_manage_comment(request, comment):
   
    if not request.user.is_authenticated:
        return False

    if request.user.is_superuser:
        return True

    role = getattr(request.user, "role", None)

    if role == "school_admin":
        return True

    return comment.author_id == request.user.pk


# ============================================================
# EDIT COMMENT (AJAX)
# ============================================================

@login_required
@require_POST
def comment_edit(request, comment_id):

    comment = get_object_or_404(Comment, pk=comment_id)

    if not can_manage_comment(request, comment):
        return JsonResponse(
            {"success": False, "message": "Permission denied"},
            status=403,
        )

    new_text = (request.POST.get("text") or "").strip()

    if not new_text:
        return JsonResponse(
            {"success": False, "message": "Comment cannot be empty"},
            status=400,
        )

    comment.text = new_text
    comment.save(update_fields=["text", "updated_at"])

    return JsonResponse({
        "success": True,
        "comment_id": comment.pk,
        "text": comment.text,
    })


# ============================================================
# DELETE COMMENT (AJAX)
# ============================================================

@login_required
@require_POST
def comment_delete(request, comment_id):

    comment = get_object_or_404(Comment, pk=comment_id)

    if not can_manage_comment(request, comment):
        return JsonResponse(
            {"success": False, "message": "Permission denied"},
            status=403,
        )

    parent_id = comment.parent_id
    post_id = comment.post_id
    comment.delete()

    # Return the new total comment count for the post
    total = Comment.objects.filter(post_id=post_id).count()

    return JsonResponse({
        "success": True,
        "parent_id": parent_id,
        "comments_count": total,
    })