import os
import io
import json
import hmac
import hashlib
import logging
import time
import requests
from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Q, Prefetch, Sum
from django.forms import (
    ClearableFileInput,
    Select,
    SelectMultiple,
    TextInput,
    Textarea,
    URLInput,
    FileInput,
    modelform_factory,
)
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import (
    require_http_methods,
    require_POST,
)
from django_ckeditor_5.widgets import CKEditor5Widget

from .access import user_can_download, user_has_paid_for_post
from .models import (
    Category,
    Comment,
    CommentReaction,
    Post,
    PostImage,
    PostAttachment,
    PostReaction,
    AttachmentPurchase,
    MpesaTransaction,
    CreatorWallet,
    CreatorSale,
    WalletLedgerEntry,
    CreatorPayout,
)
from .payments import initiate_stk_push
from .watermark import watermark_pdf
from .widgets import MultipleFileInput
logger = logging.getLogger(__name__)

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
        return [super().clean(file, initial) for file in data]


class MultipleFileField(forms.FileField):
    """
    FileField that returns a LIST of uploaded files.
    Pairs with MultipleFileInput (<input multiple>).
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "widget",
            MultipleFileInput(
                attrs={
                    "class": "form-control",
                    "style": "display: none;",
                }
            ),
        )
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        cleaned = []
        for f in data:
            cleaned.append(super(MultipleFileField, self).clean(f, initial))
        return cleaned


# ============================================================
# POST FORM
# ============================================================
class PostForm(forms.ModelForm):

    # ── Currency choices ──
    CURRENCY_CHOICES = [
        ("USD", "USD — US Dollar"),
        ("KES", "KES — Kenyan Shilling"),
        ("NGN", "NGN — Nigerian Naira"),
        ("EUR", "EUR — Euro"),
        ("GBP", "GBP — British Pound"),
        ("ZAR", "ZAR — South African Rand"),
    ]

    # ── Override currency as a dropdown ──
    attachment_currency = forms.ChoiceField(
        choices=CURRENCY_CHOICES,
        initial="USD",
        required=False,
        widget=forms.Select(
            attrs={"class": "form-select", "id": "id_attachment_currency"}
        ),
    )

    images = MultipleFileField(
        widget=MultipleFileInput(
            attrs={
                "accept": "image/*",
                "id": "id_images",
                "name": "images",
                "class": "form-control",
                "style": "display: none;",
                "multiple": "multiple",
            }
        ),
        required=False,
        label="Photos",
        help_text="Select multiple photos (JPG, PNG, GIF, WebP)",
    )

    attachments = MultipleFileField(
        widget=MultipleFileInput(
            attrs={
                "accept": (
                    ".pdf,.doc,.docx,.xls,.xlsx,"
                    ".ppt,.pptx,.txt,.csv,.zip,.rar"
                ),
                "id": "id_attachments",
                "name": "attachments",
                "class": "form-control",
                "style": "display: none;",
                "multiple": "multiple",
            }
        ),
        required=False,
        label="Attachments",
        help_text=(
            "PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, "
            "TXT, CSV, ZIP, RAR"
        ),
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
            # ── NEW: monetization ──
            "is_monetized",
            "attachment_price",
            "attachment_currency",
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
            # ── NEW: monetization widgets ──
            "is_monetized": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                    "id": "id_is_monetized",
                }
            ),
            "attachment_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "placeholder": "0.00",
                    "id": "id_attachment_price",
                }
            ),
            # attachment_currency is defined as a ChoiceField above,
            # so it doesn't need an entry in Meta.widgets.
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "target_classes" in self.fields:
            self.fields["target_classes"].queryset = (
                self.fields["target_classes"].queryset.order_by("name")
            )

        # Ensure `multiple` is always present on the
        # multi-file widgets, even if a subclass replaces them.
        for name in ("images", "attachments"):
            if name in self.fields:
                self.fields[name].widget.attrs["multiple"] = "multiple"

        # ── NEW: make price optional on the form level.
        # The clean() method enforces "> 0 when monetized".
        if "attachment_price" in self.fields:
            self.fields["attachment_price"].required = False

        # ── NEW: preserve saved currency when editing ──
        if self.instance and self.instance.pk and self.instance.attachment_currency:
            self.fields["attachment_currency"].initial = (
                self.instance.attachment_currency
            )

    def clean(self):
        cleaned = super().clean()

        is_monetized = cleaned.get("is_monetized")
        price = cleaned.get("attachment_price")
        currency = cleaned.get("attachment_currency")

        if is_monetized:
            # Price must be > 0 for monetization to make sense
            if price is None or price <= 0:
                self.add_error(
                    "attachment_price",
                    "Set a price greater than 0 when monetization is enabled.",
                )

            # Currency must be chosen
            if not currency:
                self.add_error(
                    "attachment_currency",
                    "Choose a currency when monetization is enabled.",
                )
        else:
            # When monetization is off, force sensible defaults
            cleaned["attachment_price"] = 0
            cleaned["attachment_currency"] = currency or "USD"

        return cleaned


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


def _increment_view_count(request, post):
    """
    Increment a post's view_count once per session per post.

    Works from any view (home, category, trending, detail).
    Returns the current view_count.

    NOTE: `Post.view_count` must have `default=0` (not nullable).
    `F("view_count") + 1` on NULL stays NULL.
    """
    if post is None:
        return 0

    viewed_posts = request.session.get("viewed_posts", [])

    if post.pk not in viewed_posts:
        Post.objects.filter(pk=post.pk).update(
            view_count=F("view_count") + 1
        )
        viewed_posts.append(post.pk)
        request.session["viewed_posts"] = viewed_posts
        request.session.modified = True

    post.refresh_from_db(fields=["view_count"])
    return post.view_count


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

        # ---- View count (once per session per post) ----
        _increment_view_count(request, post)

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
        _increment_view_count(request, featured_post)

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

    # ---- View count (once per session per post) ----
    _increment_view_count(request, post)

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
    attachments = [
        {"doc": doc, "locked": not user_can_download(request.user, doc)}
        for doc in post.attachments.all()
    ]
    attachments_locked = (
        post.is_monetized
        and post.attachment_price > 0
        and not user_has_paid_for_post(request.user, post)
    )

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
        "attachments": attachments,
        "attachments_locked": attachments_locked,
    }

    return render(request, "post_detail.html", context)


# ============================================================
# ATTACHMENT DOWNLOAD
# ============================================================

def _read_file_bytes(file_field, extension=""):
    # 1) Try the normal Django way first (local FS storage)
    try:
        with file_field.open("rb") as fh:
            return fh.read()
    except (OSError, IOError, NotImplementedError):
        pass

    # 2) HTTP fallback (Cloudinary, S3, etc.)
    url = file_field.url

    # --- Cloudinary quirk: raw uploads often drop the extension.
    # If the URL has no file extension and we know what it should be,
    # append it before fetching.
    if extension:
        ext_lower = extension.lower().lstrip(".")
        if not url.lower().endswith("." + ext_lower):
            # Only append if the URL doesn't already end with ANY extension
            # (avoid doubling like .pdf.pdf)
            if not url.lower().rsplit("/", 1)[-1].count("."):
                url = url + "." + ext_lower

    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.content



@login_required
def download_attachment(request, attachment_id):
    # --- Fetch attachment ---
    doc = get_object_or_404(
        PostAttachment.objects.select_related("post"),
        pk=attachment_id,
    )
    post = doc.post

    # --- Permission check ---
    if not post.visible_to_all:
        if not request.user.is_superuser:
            role = getattr(request.user, "role", None)
            is_staff_viewer = role in ("school_admin", "teacher")

            allowed = (
                is_staff_viewer
                or post.target_classes.filter(students=request.user).exists()
            )
            if not allowed:
                raise Http404

    # --- Paywall check ---
    if not user_can_download(request.user, doc):
        return redirect(
            reverse("blog:paywall", kwargs={"slug": post.slug})
        )

    ext = (doc.extension or "").lower()
    original = doc.original_name or f"document.{ext}"

    # ---------- PDF: watermark ----------
    if ext == "pdf":
        pdf_bytes = _read_file_bytes(doc.file, extension=ext)
        label = f"SmartMind · {request.user.username}"
        marked = watermark_pdf(pdf_bytes, label=label)

        # watermark_pdf already returns a BytesIO — don't wrap it again
        if isinstance(marked, (bytes, bytearray)):
            marked = io.BytesIO(marked)

        response = FileResponse(
            marked,
            as_attachment=True,
            filename=original,
            content_type="application/pdf",
        )
        response["Cache-Control"] = "private, no-store"
        return response

    # ---------- TXT: header injection ----------
    if ext == "txt":
        body_bytes = _read_file_bytes(doc.file, extension=ext)
        body = body_bytes.decode("utf-8", errors="ignore")

        header = (
            f"----- SmartMind -----\n"
            f"Downloaded by: {request.user.username}\n"
            f"Source: {post.title}\n"
            f"---------------------\n\n"
        )
        data = (header + body).encode("utf-8")

        response = FileResponse(
            io.BytesIO(data),
            as_attachment=True,
            filename=original,
            content_type="text/plain",
        )
        response["Cache-Control"] = "private, no-store"
        return response

    # ---------- Fallback: stream through Django (never expose storage URL) ----------
    try:
        file_handle = doc.file.open("rb")
    except (FileNotFoundError, OSError):
        raise Http404("File not available.")

    response = FileResponse(
        file_handle,
        as_attachment=True,
        filename=original,
        content_type="application/octet-stream",
    )
    response["Cache-Control"] = "private, no-store"
    return response


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

        # ---- View count (once per session per post) ----
        _increment_view_count(request, post)

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
                        f"{settings.MAX_IMAGE_SIZE // (1024 * 1024)}MB limit."
                    )
                    return render(
                        request,
                        "add_post.html",
                        {"form": form},
                    )

            # -----------------------------------------
            # VALIDATE DOCUMENTS
            # -----------------------------------------

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
                        f"{MAX_DOCUMENT_SIZE // (1024 * 1024)}MB limit."
                    )
                    return render(
                        request,
                        "add_post.html",
                        {"form": form},
                    )

            # -----------------------------------------
            # VALIDATE VIDEO
            # -----------------------------------------

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
                        f"{settings.MAX_VIDEO_SIZE // (1024 * 1024)}MB limit."
                    )
                    return render(
                        request,
                        "add_post.html",
                        {"form": form},
                    )

            # -----------------------------------------
            # SAVE POST AND MEASURE PERFORMANCE
            # -----------------------------------------

            try:

                total_start = time.perf_counter()

                with transaction.atomic():

                    # Save the main post
                    step_start = time.perf_counter()

                    post = form.save(commit=False)
                    post.author = request.user
                    post.save()

                    logger.info(
                        "POST TIMING: post.save() took %.2f seconds",
                        time.perf_counter() - step_start,
                    )

                    # Save tags and other many-to-many fields
                    step_start = time.perf_counter()

                    form.save_m2m()

                    logger.info(
                        "POST TIMING: form.save_m2m() took %.2f seconds",
                        time.perf_counter() - step_start,
                    )

                    # Save gallery images
                    for position, image in enumerate(uploaded_images):

                        step_start = time.perf_counter()

                        PostImage.objects.create(
                            post=post,
                            image=image,
                            position=position,
                        )

                        logger.info(
                            "POST TIMING: image '%s' took %.2f seconds",
                            image.name,
                            time.perf_counter() - step_start,
                        )

                    # Save document attachments
                    for position, doc in enumerate(uploaded_docs):

                        step_start = time.perf_counter()

                        PostAttachment.objects.create(
                            post=post,
                            file=doc,
                            original_name=doc.name,
                            position=position,
                        )

                        logger.info(
                            "POST TIMING: document '%s' took %.2f seconds",
                            doc.name,
                            time.perf_counter() - step_start,
                        )

                logger.info(
                    "POST TIMING: all saves and transaction took %.2f seconds",
                    time.perf_counter() - total_start,
                )

                messages.success(
                    request,
                    f'Post "{post.title}" created successfully!'
                )

                return redirect("blog:home")

            except Exception:

                logger.exception(
                    "Error creating post"
                )

                messages.error(
                    request,
                    "An error occurred while creating the post. "
                    "Please check the server logs."
                )

                return render(
                    request,
                    "add_post.html",
                    {"form": form},
                )

        else:

            # -----------------------------------------
            # DISPLAY FORM VALIDATION ERRORS
            # -----------------------------------------

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

    # Helper so every render() gets the same context.
    def _render(form):
        return render(
            request,
            "edit_post.html",
            {
                "form": form,
                "post": post,
                "existing_images": post.images.all().order_by(
                    "position", "id"
                ),
                "existing_attachments": post.attachments.all().order_by(
                    "position", "id"
                ),
            },
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
                    return _render(form)

                if image.size > settings.MAX_IMAGE_SIZE:
                    messages.error(
                        request,
                        f'Image "{image.name}" exceeds '
                        f"{settings.MAX_IMAGE_SIZE // (1024 * 1024)}MB limit."
                    )
                    return _render(form)

            for doc in uploaded_docs:

                if not is_valid_document(doc):
                    messages.error(
                        request,
                        f"Invalid document: {doc.name}. "
                        "Allowed: PDF, DOC, DOCX, XLS, XLSX, "
                        "PPT, PPTX, TXT, CSV, ZIP, RAR."
                    )
                    return _render(form)

                if doc.size > MAX_DOCUMENT_SIZE:
                    messages.error(
                        request,
                        f'Document "{doc.name}" exceeds '
                        f"{MAX_DOCUMENT_SIZE // (1024 * 1024)}MB limit."
                    )
                    return _render(form)

            if "video" in request.FILES:

                video = request.FILES["video"]

                if not is_valid_video(video):
                    messages.error(
                        request,
                        "Invalid video format. "
                        "Please use MP4, WebM, or OGG."
                    )
                    return _render(form)

                if video.size > settings.MAX_VIDEO_SIZE:
                    messages.error(
                        request,
                        f"Video exceeds "
                        f"{settings.MAX_VIDEO_SIZE // (1024 * 1024)}MB limit."
                    )
                    return _render(form)

            try:

                with transaction.atomic():

                    updated_post = form.save(commit=False)
                    updated_post.author = post.author
                    updated_post.save()
                    form.save_m2m()

                    # Continue positions after whatever already exists.
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

            except Exception:
                # Don't leak exception text to the user.
                logger.exception("Error updating post pk=%s", pk)

                messages.error(
                    request,
                    "An error occurred while updating the post. "
                    "Please check the server logs."
                )
                return _render(form)

        else:

            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(
                        request,
                        f"{field}: {error}"
                    )

    else:

        form = PostForm(instance=post)

    return _render(form)


# ============================================================
# VALIDATORS
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
# REMOVE IMAGE / DOCUMENT
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


# ============================================================
# COMMENT EDIT / DELETE
# ============================================================

def can_manage_comment(request, comment):
    if not request.user.is_authenticated:
        return False
    if request.user.is_superuser:
        return True
    role = getattr(request.user, "role", None)
    if role == "school_admin":
        return True
    return comment.author_id == request.user.pk


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

    total = Comment.objects.filter(post_id=post_id).count()

    return JsonResponse({
        "success": True,
        "parent_id": parent_id,
        "comments_count": total,
    })


# ============================================================
# TRENDING
# ============================================================

def trending(request):
    """Most-read posts, ranked by views then recency.

    Visibility rules:
      - Everyone sees approved posts.
      - Logged-in users also see their own unapproved posts.
      - Superusers and school admins see everything.
    """
    base = (
        Post.objects
        .select_related("author", "category", "school")
    )

    # Visibility
    if request.user.is_authenticated:
        role = getattr(request.user, "role", None)
        if request.user.is_superuser or role == "school_admin":
            pass  # see everything
        else:
            base = base.filter(
                Q(approved=True) | Q(author=request.user)
            )
    else:
        base = base.filter(approved=True)

    qs = base.order_by("-view_count", "-created_at")

    paginator = Paginator(qs, 12)
    page = paginator.get_page(request.GET.get("page"))

    # ---- View count for every post shown on this page ----
    for post in page:
        _increment_view_count(request, post)

    return render(request, "trending.html", {"page": page})

@login_required
def paywall(request, slug):
    post = get_object_or_404(Post, slug=slug)

    if user_has_paid_for_post(request.user, post):
        return redirect("blog:post_detail", slug=post.slug)

    return render(request, "paywall.html", {
        "post": post,
        "price": post.attachment_price,
        "currency": post.attachment_currency,
    })


@login_required
@require_POST
def initialize_mpesa_payment(request, slug):
    post = get_object_or_404(Post, slug=slug)

    if user_has_paid_for_post(request.user, post):
        return JsonResponse({"already_paid": True})

    if not post.is_monetized or post.attachment_price <= 0:
        return JsonResponse(
            {"error": "This post is not for sale."},
            status=400,
        )

    # M-Pesa Daraja accepts payments in Kenyan shillings.
    if post.attachment_currency.upper() != "KES":
        return JsonResponse(
            {"error": "This attachment must be priced in KES to accept M-Pesa."},
            status=400,
        )

    amount = Decimal(str(post.attachment_price))

    if amount != amount.to_integral_value():
        return JsonResponse(
            {"error": "M-Pesa payments must be whole amounts in KES."},
            status=400,
        )

    phone = request.POST.get("phone_number", "").strip()

    callback_url = settings.MPESA_CALLBACK_URL

    if not callback_url:
        callback_url = request.build_absolute_uri(
            reverse("blog:mpesa_callback")
        )

    result = initiate_stk_push(
        phone=phone,
        amount=amount,
        account_reference=post.slug,
        transaction_description="SmartMind attachment",
        callback_url=callback_url,
    )

    if not result.get("success"):
        return JsonResponse(
            {"error": result.get("error", "Could not initiate payment.")},
            status=400,
        )

    data = result["data"]

    checkout_id = data.get("CheckoutRequestID")
    merchant_id = data.get("MerchantRequestID")

    if not checkout_id:
        logger.error("M-Pesa response missing CheckoutRequestID: %s", data)
        return JsonResponse(
            {"error": "M-Pesa returned an invalid response."},
            status=502,
        )

    from .payments import normalize_mpesa_phone

    normalized_phone = normalize_mpesa_phone(phone)

    MpesaTransaction.objects.create(
        user=request.user,
        post=post,
        phone_number=normalized_phone,
        amount=amount,
        currency="KES",
        merchant_request_id=merchant_id or "",
        checkout_request_id=checkout_id,
        status="pending",
    )

    return JsonResponse({
        "success": True,
        "message": "STK Push sent. Enter your M-Pesa PIN on your phone.",
        "checkout_request_id": checkout_id,
    })


@csrf_exempt
def mpesa_callback(request):
    """
    Receive Daraja STK Push callback.

    A verified successful payment:
    1. Unlocks the attachment.
    2. Records the sale.
    3. Credits 70% to the creator wallet.
    4. Records 30% platform commission.
    5. Creates a wallet ledger entry.

    Duplicate callbacks cannot credit the wallet twice.
    """

    try:
        callback_data = json.loads(request.body)

    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.warning("Invalid M-Pesa callback JSON.")
        return HttpResponse(status=200)

    stk_callback = (
        callback_data.get("Body", {})
        .get("stkCallback", {})
    )

    checkout_id = stk_callback.get("CheckoutRequestID")
    result_code = str(stk_callback.get("ResultCode", ""))
    result_description = stk_callback.get("ResultDesc", "")

    if not checkout_id:
        logger.warning("M-Pesa callback missing CheckoutRequestID.")
        return HttpResponse(status=200)

    mpesa_transaction = MpesaTransaction.objects.filter(
        checkout_request_id=checkout_id
    ).first()

    if not mpesa_transaction:
        logger.warning(
            "Unknown M-Pesa CheckoutRequestID: %s",
            checkout_id,
        )
        return HttpResponse(status=200)

    # Ignore callbacks for transactions already processed.
    if mpesa_transaction.status != "pending":
        return HttpResponse(status=200)

    # Record unsuccessful payment.
    if result_code != "0":

        mpesa_transaction.result_code = result_code
        mpesa_transaction.result_description = result_description
        mpesa_transaction.status = "failed"
        mpesa_transaction.save(
            update_fields=[
                "result_code",
                "result_description",
                "status",
            ]
        )

        logger.info(
            "M-Pesa payment failed. CheckoutRequestID=%s ResultCode=%s",
            checkout_id,
            result_code,
        )

        return HttpResponse(status=200)

    # Extract callback metadata.
    metadata_items = (
        stk_callback.get("CallbackMetadata", {})
        .get("Item", [])
    )

    metadata = {}

    for item in metadata_items:
        name = item.get("Name")
        value = item.get("Value")

        if name:
            metadata[name] = value

    receipt = str(metadata.get("MpesaReceiptNumber", ""))
    callback_amount = metadata.get("Amount")
    callback_phone = metadata.get("PhoneNumber")

    from .payments import normalize_mpesa_phone

    normalized_callback_phone = normalize_mpesa_phone(
        str(callback_phone or "")
    )

    try:
        received_amount = Decimal(str(callback_amount))

    except (TypeError, ValueError):
        received_amount = Decimal("0")

    amount_matches = (
        received_amount == mpesa_transaction.amount
    )

    phone_matches = (
        normalized_callback_phone
        == mpesa_transaction.phone_number
    )

    # Verify the payment before crediting anyone.
    if not amount_matches or not phone_matches or not receipt:

        mpesa_transaction.status = "failed"

        mpesa_transaction.result_description = (
            "Payment verification failed: "
            "amount, phone or receipt mismatch."
        )

        mpesa_transaction.save()

        logger.error(
            "M-Pesa verification mismatch. CheckoutRequestID=%s",
            checkout_id,
        )

        return HttpResponse(status=200)

    # Process everything together.
    # If any operation fails, all changes are rolled back.
    try:

        with transaction.atomic():

            # Lock the transaction against duplicate callbacks.
            mpesa_transaction = (
                MpesaTransaction.objects
                .select_for_update()
                .get(checkout_request_id=checkout_id)
            )

            # Check again inside the lock.
            if mpesa_transaction.status != "pending":
                return HttpResponse(status=200)

            # Prevent using the same receipt on another transaction.
            duplicate_receipt = (
                MpesaTransaction.objects
                .filter(mpesa_receipt_number=receipt)
                .exclude(pk=mpesa_transaction.pk)
                .exists()
            )

            if duplicate_receipt:

                mpesa_transaction.status = "failed"
                mpesa_transaction.result_code = result_code
                mpesa_transaction.result_description = (
                    "Duplicate M-Pesa receipt detected."
                )

                mpesa_transaction.save()

                logger.error(
                    "Duplicate M-Pesa receipt detected: %s",
                    receipt,
                )

                return HttpResponse(status=200)

            # Mark payment successful.
            mpesa_transaction.status = "success"
            mpesa_transaction.result_code = result_code
            mpesa_transaction.result_description = result_description
            mpesa_transaction.mpesa_receipt_number = receipt

            mpesa_transaction.save()

            # Unlock the attachment for the learner.
            AttachmentPurchase.objects.update_or_create(
                user=mpesa_transaction.user,
                post=mpesa_transaction.post,
                defaults={
                    "paid": True,
                    "amount_paid": mpesa_transaction.amount,
                    "currency": "KES",
                    "payment_reference": receipt,
                },
            )

            # Identify the creator of the purchased post.
            creator = mpesa_transaction.post.author

            gross_amount = mpesa_transaction.amount

            # Prevent creators earning commission from
            # purchasing their own content.
            if creator.pk == mpesa_transaction.user_id:

                creator_earning = Decimal("0.00")
                platform_commission = Decimal("0.00")

            else:

                creator_earning = (
                    gross_amount * Decimal("0.70")
                ).quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                )

                # The remainder guarantees that the total
                # always equals the original payment.
                platform_commission = (
                    gross_amount - creator_earning
                ).quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                )

            # Record the sale.
            creator_sale = CreatorSale.objects.create(
                mpesa_transaction=mpesa_transaction,
                creator=creator,
                post=mpesa_transaction.post,
                gross_amount=gross_amount,
                platform_commission=platform_commission,
                creator_earning=creator_earning,
                commission_rate=Decimal("30.00"),
            )

            # Credit the creator only if there is an earning.
            if creator_earning > 0:

                wallet, created = CreatorWallet.objects.get_or_create(
                    creator=creator
                )

                # Lock the wallet while updating its balances.
                wallet = (
                    CreatorWallet.objects
                    .select_for_update()
                    .get(pk=wallet.pk)
                )

                wallet.available_balance += creator_earning
                wallet.total_earned += creator_earning

                wallet.save(
                    update_fields=[
                        "available_balance",
                        "total_earned",
                        "updated_at",
                    ]
                )

                # Record the credit in the wallet ledger.
                WalletLedgerEntry.objects.create(
                    wallet=wallet,
                    sale=creator_sale,
                    entry_type="sale",
                    amount=creator_earning,
                    description=(
                        f"70% earnings from sale of "
                        f"{mpesa_transaction.post.title}"
                    ),
                )

    except Exception:

        logger.exception(
            "Error processing successful M-Pesa payment. "
            "CheckoutRequestID=%s",
            checkout_id,
        )

        # Report failure so the payment can be investigated
        # and processing can be retried if necessary.
        return HttpResponse(status=500)

    logger.info(
        "M-Pesa payment verified and attachment unlocked. "
        "Receipt=%s Post=%s User=%s",
        receipt,
        mpesa_transaction.post_id,
        mpesa_transaction.user_id,
    )

    return HttpResponse(status=200)


@login_required
def creator_wallet_management(request):
    """
    Administrator dashboard for managing creator wallets.

    Superadmin:
        Views all teacher wallets.

    School admin:
        Views wallets belonging to teachers in their school only.
    """

    role = getattr(request.user, "role", None)

    # Restrict access to superadmins and school administrators.
    if not (
        request.user.is_superuser
        or role == "superadmin"
        or role == "school_admin"
    ):
        raise PermissionDenied(
            "You do not have permission to manage creator wallets."
        )

    # Base querysets: teachers only.
    wallets = CreatorWallet.objects.filter(
        creator__role="teacher"
    ).select_related(
        "creator",
        "creator__school",
    ).order_by(
        "-total_earned"
    )

    sales = CreatorSale.objects.filter(
        creator__role="teacher"
    ).select_related(
        "creator",
        "post",
        "mpesa_transaction",
    ).order_by(
        "-created_at"
    )

    payouts = CreatorPayout.objects.filter(
        creator__role="teacher"
    ).select_related(
        "creator",
        "wallet",
    ).order_by(
        "-requested_at"
    )

    # School administrators are restricted to their own school.
    if role == "school_admin" and not request.user.is_superuser:

        if not request.user.school_id:
            raise PermissionDenied(
                "Your administrator account is not assigned to a school."
            )

        wallets = wallets.filter(
            creator__school_id=request.user.school_id
        )

        sales = sales.filter(
            creator__school_id=request.user.school_id
        )

        payouts = payouts.filter(
            creator__school_id=request.user.school_id
        )

    # Financial totals.
    wallet_totals = wallets.aggregate(
        total_available=Sum("available_balance"),
        total_earned=Sum("total_earned"),
        total_paid=Sum("total_paid"),
    )

    sales_totals = sales.aggregate(
        total_gross=Sum("gross_amount"),
        total_commission=Sum("platform_commission"),
        total_creator_earnings=Sum("creator_earning"),
    )

    # Payout request counts.
    payout_counts = {
        "pending": payouts.filter(status="pending").count(),
        "approved": payouts.filter(status="approved").count(),
        "paid": payouts.filter(status="paid").count(),
        "rejected": payouts.filter(status="rejected").count(),
    }

    context = {
        "wallets": wallets,
        "sales": sales[:50],
        "payouts": payouts[:50],

        "total_available": wallet_totals["total_available"] or Decimal("0.00"),
        "total_earned": wallet_totals["total_earned"] or Decimal("0.00"),
        "total_paid": wallet_totals["total_paid"] or Decimal("0.00"),

        "total_gross": sales_totals["total_gross"] or Decimal("0.00"),
        "total_commission": sales_totals["total_commission"] or Decimal("0.00"),
        "total_creator_earnings": sales_totals["total_creator_earnings"] or Decimal("0.00"),

        "payout_counts": payout_counts,
        "wallet_count": wallets.count(),
    }

    return render(
        request,
        "creator_wallet_management.html",
        context,
    )


@login_required
def creator_wallet(request):
    """Display the logged-in creator's wallet and earnings."""

    # Only teachers can access the creator wallet.
    if request.user.role != "teacher":
        raise PermissionDenied(
            "Only teachers can access the creator wallet."
        )

    wallet, created = CreatorWallet.objects.get_or_create(
        creator=request.user
    )

    sales = (
        CreatorSale.objects
        .filter(creator=request.user)
        .select_related("post", "mpesa_transaction")
        .order_by("-created_at")
    )

    ledger_entries = (
        WalletLedgerEntry.objects
        .filter(wallet=wallet)
        .select_related("sale", "payout")
        .order_by("-created_at")
    )

    payouts = CreatorPayout.objects.filter(
        creator=request.user
    ).order_by("-requested_at")

    context = {
        "wallet": wallet,
        "sales": sales[:10],
        "ledger_entries": ledger_entries[:10],
        "payouts": payouts[:10],
    }

    return render(
        request,
        "wallet.html",
        context
    )
