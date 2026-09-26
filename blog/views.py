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

import os

from .models import (
    Category,
    Comment,
    Post,
    PostImage,
    PostAttachment,
)

from .widgets import MultipleFileInput
from django.db.models import (
    F,
    Prefetch,
)


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

# 20MB — override via settings.MAX_DOCUMENT_SIZE if defined
MAX_DOCUMENT_SIZE = getattr(
    settings,
    "MAX_DOCUMENT_SIZE",
    20 * 1024 * 1024,
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


class PostForm(forms.ModelForm):
    # Use the custom multiple file input
    images = forms.FileField(
        widget=MultipleFileInput(attrs={
            'accept': 'image/*',
            'id': 'id_images',
            'name': 'images',
            'class': 'form-control',
            'style': 'display: none;',
        }),
        required=False,
        label='Photos',
        help_text='Select multiple photos (JPG, PNG, GIF, WebP)'
    )

    class Meta:
        model = Post
        fields = [
            'title', 'category', 'excerpt', 'content',
            'school', 'target_classes', 'video', 'youtube_url',
            'tags', 'visible_to_all', 'status'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter post title...'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'excerpt': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Write a brief summary...'
            }),
            'content': CKEditor5Widget(
                attrs={
                    'class': 'django_ckeditor_5',
                },
                config_name='extends',
            ),
            'school': forms.Select(attrs={
                'class': 'form-select'
            }),
            'target_classes': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': 5
            }),
            'video': ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'video/*',
                'id': 'id_video'
            }),
            'youtube_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.youtube.com/watch?v=...'
            }),
            'tags': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': 5
            }),
            'visible_to_all': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
        }


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_user_role(request):
    """
    Safely return the logged-in user's role.
    """

    return getattr(
        request.user,
        "role",
        None
    )


def is_staff_user(request):
    """
    Return True for superusers, school administrators,
    and teachers.
    """

    user_role = get_user_role(request)

    return (
        request.user.is_authenticated
        and (
            request.user.is_superuser
            or user_role in [
                "school_admin",
                "teacher",
            ]
        )
    )


def can_manage_post(
    request,
    post
):
    """
    Determine whether the current user can
    edit or delete a post.
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


def get_post_comments(
    request,
    post
):

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

    return comments


def home(request):

    # ========================================================
    # USER INFORMATION
    # ========================================================

    user_id = (
        request.user.pk
        if request.user.is_authenticated
        else None
    )

    comments_queryset = (
        Comment.objects
        .select_related("author")
        .prefetch_related("liked_by")
        .order_by("created_at")
    )

    posts_qs = (
        Post.objects
        .select_related(
            "author",
            "category",
        )
        .prefetch_related(
            "tags",
            "images",
            "attachments",          # <-- NEW
            "likes",
            Prefetch(
                "comments",
                queryset=comments_queryset[:20],
                to_attr="home_comments",
            ),
        )
        .order_by(
            "-created_at"
        )
    )

    posts = []

    for post in posts_qs:

        # ----------------------------------------------------
        # COMMENTS
        # ----------------------------------------------------

        comments = getattr(
            post,
            "home_comments",
            []
        )

        for comment in comments:

            if user_id:

                comment.liked_by_current_user = any(
                    user.pk == user_id
                    for user in comment.liked_by.all()
                )

            else:

                comment.liked_by_current_user = False

            comment.likes_count = (
                comment.liked_by.count()
            )

        comments_count = (
            Comment.objects
            .filter(post=post)
            .count()
        )

        is_liked = (
            bool(user_id)
            and post.likes.filter(
                pk=user_id
            ).exists()
        )

        likes_count = post.likes.count()

        views_count = post.view_count

        can_edit = can_manage_post(
            request,
            post
        )

        can_delete = can_edit

        # ----------------------------------------------------
        # ADD POST DATA
        # ----------------------------------------------------

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

    # ========================================================
    # CATEGORIES
    # ========================================================

    categories = (
        Category.objects
        .all()
        .order_by("name")
    )

    # ========================================================
    # FEATURED POST
    # ========================================================

    featured_post = (
        Post.objects
        .filter(
            is_featured=True
        )
        .select_related(
            "author",
            "category",
        )
        .prefetch_related(
            "tags",
            "images",
            "attachments",          # <-- NEW
        )
        .order_by(
            "-created_at"
        )
        .first()
    )

    # ========================================================
    # CONTEXT
    # ========================================================

    context = {

        "posts": posts,

        "categories": categories,

        "featured_post": featured_post,

    }

    return render(
        request,
        "home.html",
        context
    )


def post_detail(request, slug):
    """
    Display a single post with:
    - post information
    - images
    - attachments (documents)
    - likes
    - comments
    - view count
    - edit/delete permissions
    """

    # ---------------------------------------------------------
    # GET THE POST
    # ---------------------------------------------------------

    post = get_object_or_404(
        Post.objects
        .select_related(
            "author",
            "category",
            "school",
        )
        .prefetch_related(
            "tags",
            "images",
            "attachments",          # <-- NEW
            "likes",
        ),
        slug=slug,
    )

    # ---------------------------------------------------------
    # INCREASE VIEW COUNT
    # ---------------------------------------------------------

    Post.objects.filter(
        pk=post.pk
    ).update(
        view_count=F("view_count") + 1
    )

    post.refresh_from_db()

    # ---------------------------------------------------------
    # GET COMMENTS
    # ---------------------------------------------------------

    comments = list(
        Comment.objects
        .filter(post=post)
        .select_related("author")
        .prefetch_related("liked_by")
        .order_by("created_at")
    )

    # ---------------------------------------------------------
    # COMMENT LIKE INFORMATION
    # ---------------------------------------------------------

    if request.user.is_authenticated:

        user_id = request.user.pk

        for comment in comments:

            comment.likes_count = (
                comment.liked_by.count()
            )

            comment.liked_by_current_user = (
                comment.liked_by
                .filter(pk=user_id)
                .exists()
            )

    else:

        for comment in comments:

            comment.likes_count = (
                comment.liked_by.count()
            )

            comment.liked_by_current_user = False

    # ---------------------------------------------------------
    # POST LIKE INFORMATION
    # ---------------------------------------------------------

    is_liked = (
        request.user.is_authenticated
        and post.likes.filter(
            pk=request.user.pk
        ).exists()
    )

    likes_count = post.likes.count()

    comments_count = len(comments)

    views_count = post.view_count

    # ---------------------------------------------------------
    # EDIT / DELETE PERMISSION
    # ---------------------------------------------------------

    can_edit = can_manage_post(
        request,
        post
    )

    can_delete = can_edit

    # ---------------------------------------------------------
    # CONTEXT
    # ---------------------------------------------------------

    context = {
        "post": post,
        "comments": comments,
        "comments_count": comments_count,
        "likes_count": likes_count,
        "views_count": views_count,
        "is_liked": is_liked,
        "can_edit": can_edit,
        "can_delete": can_delete,
    }

    return render(request, "post_detail.html", context)


def category_post(request, slug):
    """
    Display all posts belonging to a specific category.

    Posts are displayed immediately after creation.
    There is intentionally no status='published'
    or approved=True visibility filter.
    """

    # --------------------------------------------------------
    # GET THE SELECTED CATEGORY
    # --------------------------------------------------------

    category = get_object_or_404(
        Category,
        slug=slug
    )

    # --------------------------------------------------------
    # GET ALL POSTS BELONGING TO THIS CATEGORY
    # --------------------------------------------------------

    posts_qs = (
        Post.objects
        .filter(
            category=category
        )
        .select_related(
            "author",
            "category",
            "school",
        )
        .prefetch_related(
            "tags",
            "images",
            "attachments",          # <-- NEW
            "likes",
        )
        .order_by(
            "-created_at"
        )
    )

    # --------------------------------------------------------
    # PREPARE POSTS
    # --------------------------------------------------------

    posts = []

    for post in posts_qs:

        # ----------------------------------------------------
        # COMMENTS
        # ----------------------------------------------------

        comments = list(
            Comment.objects
            .filter(
                post=post
            )
            .select_related(
                "author"
            )
            .prefetch_related(
                "liked_by"
            )
            .order_by(
                "created_at"
            )
        )

        # ----------------------------------------------------
        # COMMENT LIKE STATUS
        # ----------------------------------------------------

        if request.user.is_authenticated:

            user_id = request.user.pk

            for comment in comments:

                comment.likes_count = (
                    comment.liked_by.count()
                )

                comment.liked_by_current_user = (
                    comment.liked_by
                    .filter(pk=user_id)
                    .exists()
                )

        else:

            for comment in comments:

                comment.likes_count = (
                    comment.liked_by.count()
                )

                comment.liked_by_current_user = False

        # ----------------------------------------------------
        # POST LIKE STATUS
        # ----------------------------------------------------

        if request.user.is_authenticated:

            is_liked = (
                post.likes
                .filter(pk=request.user.pk)
                .exists()
            )

        else:

            is_liked = False

        # ----------------------------------------------------
        # POST LIKE COUNT
        # ----------------------------------------------------

        likes_count = post.likes.count()

        # ----------------------------------------------------
        # COMMENT COUNT
        # ----------------------------------------------------

        comments_count = Comment.objects.filter(
            post=post
        ).count()

        # ----------------------------------------------------
        # VIEW COUNT
        # ----------------------------------------------------

        views_count = post.view_count

        # ----------------------------------------------------
        # EDIT / DELETE PERMISSIONS
        # ----------------------------------------------------

        can_edit = can_manage_post(
            request,
            post
        )

        can_delete = can_edit

        # ----------------------------------------------------
        # ATTACH EXTRA DATA TO THE POST OBJECT
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # ADD ACTUAL POST OBJECT
        # ----------------------------------------------------

        posts.append(post)

    # --------------------------------------------------------
    # GET ALL CATEGORIES FOR NAVIGATION
    # --------------------------------------------------------

    categories = (
        Category.objects
        .all()
        .order_by("name")
    )

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = {
        "category": category,
        "posts": posts,
        "categories": categories,
    }

    # --------------------------------------------------------
    # RENDER CATEGORY PAGE
    # --------------------------------------------------------

    return render(
        request,
        "category_post.html",
        context
    )


@login_required
@require_POST
def like_toggle(
    request,
    slug
):

    post = get_object_or_404(
        Post,
        slug=slug,
        status="published",
    )

    if post.likes.filter(
        pk=request.user.pk
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

    return JsonResponse({
        "is_liked": is_liked,
        "like_count": post.likes.count(),
    })


# ============================================================
# ADD COMMENT
# ============================================================

@login_required
@require_POST
def add_comment(
    request,
    slug
):

    post = get_object_or_404(
        Post,
        slug=slug,
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
            f"{post.get_absolute_url()}#comments-section"
        )

    return redirect(
        f"{post.get_absolute_url()}#comments-section"
    )


# ============================================================
# ADD POST
# ============================================================

@login_required
@require_http_methods(["GET", "POST"])
def add_post(request):
    allowed_roles = ["school_admin", "teacher"]
    user_role = get_user_role(request)

    has_permission = (
        request.user.is_superuser or
        user_role in allowed_roles
    )

    if not has_permission:
        raise PermissionDenied("You do not have permission to add posts.")

    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded_images = request.FILES.getlist('images')
            uploaded_docs = request.FILES.getlist('attachments')

            # Validate images
            for image in uploaded_images:
                if not is_valid_image(image):
                    messages.error(
                        request,
                        f'Invalid image: {image.name}. Please use JPG, PNG, GIF, or WebP.'
                    )
                    return render(request, "add_post.html", {"form": form})

                if image.size > settings.MAX_IMAGE_SIZE:
                    messages.error(
                        request,
                        f'Image "{image.name}" exceeds {settings.MAX_IMAGE_SIZE // (1024*1024)}MB limit.'
                    )
                    return render(request, "add_post.html", {"form": form})

            # Validate documents
            for doc in uploaded_docs:
                if not is_valid_document(doc):
                    messages.error(
                        request,
                        f'Invalid document: {doc.name}. Allowed: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT, CSV, ZIP, RAR.'
                    )
                    return render(request, "add_post.html", {"form": form})

                if doc.size > MAX_DOCUMENT_SIZE:
                    messages.error(
                        request,
                        f'Document "{doc.name}" exceeds {MAX_DOCUMENT_SIZE // (1024*1024)}MB limit.'
                    )
                    return render(request, "add_post.html", {"form": form})

            # Validate video
            if 'video' in request.FILES:
                video = request.FILES['video']
                if not is_valid_video(video):
                    messages.error(
                        request,
                        'Invalid video format. Please use MP4, WebM, or OGG.'
                    )
                    return render(request, "add_post.html", {"form": form})

                if video.size > settings.MAX_VIDEO_SIZE:
                    messages.error(
                        request,
                        f'Video exceeds {settings.MAX_VIDEO_SIZE // (1024*1024)}MB limit.'
                    )
                    return render(request, "add_post.html", {"form": form})

            try:
                with transaction.atomic():
                    post = form.save(commit=False)
                    post.author = request.user
                    post.save()
                    form.save_m2m()

                    # Save all photos
                    for position, image in enumerate(uploaded_images):
                        PostImage.objects.create(
                            post=post,
                            image=image,
                            position=position,
                        )

                    # Save all documents                          # <-- NEW
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
                messages.error(request, f'Error creating post: {str(e)}')
                return render(request, "add_post.html", {"form": form})
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = PostForm()

    return render(request, "add_post.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def edit_post(request, pk):
    post = get_object_or_404(Post, pk=pk)

    if not can_manage_post(request, post):
        raise PermissionDenied("You do not have permission to edit this post.")

    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post)

        if form.is_valid():
            uploaded_images = request.FILES.getlist('images')
            uploaded_docs = request.FILES.getlist('attachments')

            # Validate new images
            for image in uploaded_images:
                if not is_valid_image(image):
                    messages.error(
                        request,
                        f'Invalid image: {image.name}. Please use JPG, PNG, GIF, or WebP.'
                    )
                    return render(request, "edit_post.html", {"form": form, "post": post})

                if image.size > settings.MAX_IMAGE_SIZE:
                    messages.error(
                        request,
                        f'Image "{image.name}" exceeds {settings.MAX_IMAGE_SIZE // (1024*1024)}MB limit.'
                    )
                    return render(request, "edit_post.html", {"form": form, "post": post})

            # Validate new documents
            for doc in uploaded_docs:
                if not is_valid_document(doc):
                    messages.error(
                        request,
                        f'Invalid document: {doc.name}. Allowed: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT, CSV, ZIP, RAR.'
                    )
                    return render(request, "edit_post.html", {"form": form, "post": post})

                if doc.size > MAX_DOCUMENT_SIZE:
                    messages.error(
                        request,
                        f'Document "{doc.name}" exceeds {MAX_DOCUMENT_SIZE // (1024*1024)}MB limit.'
                    )
                    return render(request, "edit_post.html", {"form": form, "post": post})

            # Validate video
            if 'video' in request.FILES:
                video = request.FILES['video']
                if not is_valid_video(video):
                    messages.error(
                        request,
                        'Invalid video format. Please use MP4, WebM, or OGG.'
                    )
                    return render(request, "edit_post.html", {"form": form, "post": post})

                if video.size > settings.MAX_VIDEO_SIZE:
                    messages.error(
                        request,
                        f'Video exceeds {settings.MAX_VIDEO_SIZE // (1024*1024)}MB limit.'
                    )
                    return render(request, "edit_post.html", {"form": form, "post": post})

            try:
                with transaction.atomic():
                    updated_post = form.save(commit=False)
                    updated_post.author = post.author
                    updated_post.save()
                    form.save_m2m()

                    # Add new photos
                    current_count = post.images.count()
                    for index, image in enumerate(uploaded_images, start=current_count):
                        PostImage.objects.create(
                            post=updated_post,
                            image=image,
                            position=index,
                        )

                    # Add new documents                           # <-- NEW
                    current_doc_count = post.attachments.count()
                    for index, doc in enumerate(uploaded_docs, start=current_doc_count):
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
                messages.error(request, f'Error updating post: {str(e)}')
                return render(request, "edit_post.html", {"form": form, "post": post})
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = PostForm(instance=post)

    return render(request, "edit_post.html", {
        "form": form,
        "post": post,
    })


def is_valid_image(file):
    """Check if uploaded file is a valid image."""
    valid_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    return file.content_type in valid_types


def is_valid_video(file):
    """Check if uploaded file is a valid video."""
    valid_types = ['video/mp4', 'video/webm', 'video/ogg']
    return file.content_type in valid_types


def is_valid_document(file):
    """
    Check if uploaded file is a valid document
    based on its extension.
    """
    ext = os.path.splitext(file.name)[1].lower()
    return ext in ALLOWED_DOC_EXTENSIONS


@login_required
@require_http_methods(["POST"])
def remove_image(request, image_id):
    """Remove an image from a post."""
    try:
        image = PostImage.objects.get(id=image_id)
        if can_manage_post(request, image.post):
            image.delete()
            return JsonResponse({'success': True, 'message': 'Image removed successfully'})
        else:
            return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    except PostImage.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Image not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


# ============================================================
# REMOVE DOCUMENT (AJAX)
# ============================================================

@login_required
@require_POST
def remove_document(request, pk):
    """
    Remove a single PostAttachment via AJAX.
    Called by the template's 'Remove Document' buttons.
    """
    try:
        document = PostAttachment.objects.get(pk=pk)
    except PostAttachment.DoesNotExist:
        return JsonResponse(
            {'success': False, 'message': 'Document not found'},
            status=404,
        )

    if not can_manage_post(request, document.post):
        return JsonResponse(
            {'success': False, 'message': 'Permission denied'},
            status=403,
        )

    try:
        # Delete the physical file first
        document.file.delete(save=False)
        document.delete()
        return JsonResponse({
            'success': True,
            'message': 'Document removed successfully',
        })
    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': str(e)},
            status=500,
        )


# ============================================================
# DELETE POST
# ============================================================

@login_required
@require_http_methods(
    ["GET", "POST"]
)
def delete_post(
    request,
    pk
):

    post = get_object_or_404(
        Post,
        pk=pk,
    )

    if not can_manage_post(
        request,
        post
    ):

        raise PermissionDenied(
            "You do not have permission "
            "to delete this post."
        )

    if request.method == "POST":

        post.delete()

        return redirect(
            "blog:home"
        )

    return render(
        request,
        "delete_post.html",
        {
            "post": post,
        },
    )