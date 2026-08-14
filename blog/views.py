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

from .models import (
    Category,
    Comment,
    Post,
    PostImage,
)

from .widgets import MultipleFileInput
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
            'style': 'display: none;',  # Hide the default input
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
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Write your post content...'
            }),
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
    """
    Fetch the latest comments and mark whether
    the current user liked each comment.
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
        .prefetch_related(
            "tags",
            "images",
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

        # ----------------------------------------------------
        # POST LIKE STATUS
        # ----------------------------------------------------

        is_liked = (
            request.user.is_authenticated
            and post.likes.filter(
                pk=request.user.pk
            ).exists()
        )

        # ----------------------------------------------------
        # PERMISSIONS
        # ----------------------------------------------------

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
            "is_liked": is_liked,
            "can_edit": can_edit,
            "can_delete": can_delete,
        })

    # --------------------------------------------------------
    # CATEGORIES
    # --------------------------------------------------------

    categories = Category.objects.all()

    # --------------------------------------------------------
    # FEATURED POST
    # --------------------------------------------------------

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
        .prefetch_related(
            "tags",
            "images",
        )
        .order_by(
            "-created_at"
        )
        .first()
    )

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

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


# ============================================================
# CATEGORY POSTS
# ============================================================

def category_post(
    request,
    slug
):

    category = get_object_or_404(
        Category,
        slug=slug,
    )

    posts = (
        Post.objects
        .filter(
            category=category
        )
        .select_related(
            "author",
            "category",
        )
        .prefetch_related(
            "tags",
            "images",
        )
        .order_by(
            "-created_at"
        )
    )

    context = {
        "category": category,
        "posts": posts,
    }

    return render(
        request,
        "category_post.html",
        context
    )


# ============================================================
# LIKE OR UNLIKE POST
# ============================================================

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
            f"{reverse('blog:home')}"
            f"#post-{post.pk}"
        )

    return redirect(
        "blog:home"
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
            
            # Validate images before saving
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
                
                messages.success(
                    request, 
                    f'Post "{post.title}" created successfully!'
                )
                return redirect("blog:home")
                
            except Exception as e:
                messages.error(request, f'Error creating post: {str(e)}')
                return render(request, "add_post.html", {"form": form})
        else:
            # Form errors
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
                    updated_post.author = post.author  # Keep original author
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
                
                messages.success(
                    request, 
                    f'Post "{updated_post.title}" updated successfully!'
                )
                return redirect(updated_post.get_absolute_url())
                
            except Exception as e:
                messages.error(request, f'Error updating post: {str(e)}')
                return render(request, "edit_post.html", {"form": form, "post": post})
        else:
            # Form errors
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


# ============================================================
# CATEGORY POSTS
# ============================================================

def category_posts(
    request,
    slug
):

    category = get_object_or_404(
        Category,
        slug=slug
    )

    posts = (
        Post.objects
        .filter(
            category=category,
            status="published"
        )
        .select_related(
            "author",
            "category"
        )
        .prefetch_related(
            "tags",
            "images"
        )
        .order_by(
            "-created_at"
        )
    )

    categories = (
        Category.objects
        .all()
        .order_by("name")
    )

    return render(
        request,
        "blog/category_posts.html",
        {
            "category": category,
            "posts": posts,
            "categories": categories,
        }
    )