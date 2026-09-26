from django.db import models
from django.contrib.auth import get_user_model
from django_ckeditor_5.fields import CKEditor5Field
from django.urls import reverse
from django.template.defaultfilters import slugify
import uuid
import os


User = get_user_model()


# ==========================================================
# CATEGORY
# ==========================================================

class Category(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    slug = models.SlugField(
        max_length=110,
        unique=True,
        blank=True
    )


    class Meta:

        verbose_name_plural = "Categories"

        ordering = ["name"]


    def __str__(self):

        return self.name


    def save(self, *args, **kwargs):

        if not self.slug:

            self.slug = slugify(
                self.name
            )

        super().save(
            *args,
            **kwargs
        )


# ==========================================================
# TAG
# ==========================================================

class Tag(models.Model):

    name = models.CharField(
        max_length=50,
        unique=True
    )


    def __str__(self):

        return self.name



class Post(models.Model):

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
    ]

    title = models.CharField(
        max_length=200
    )

    slug = models.SlugField(
        max_length=200,
        unique=True,
        blank=True
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE
    )

    tags = models.ManyToManyField(
        Tag,
        blank=True
    )

    excerpt = models.TextField(
        max_length=500
    )

    content = CKEditor5Field(
        "Content",
        config_name="default"
    )

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="posts",
        null=True,
        blank=True
    )

    target_classes = models.ManyToManyField(
        "schools.SchoolClass",
        blank=True,
        related_name="posts"
    )

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="posts"
    )

    approved = models.BooleanField(
        default=False
    )

    is_featured = models.BooleanField(
        default=False
    )

    

    video = models.FileField(
        upload_to="videos/",
        blank=True,
        null=True
    )

    youtube_url = models.URLField(
        blank=True,
        null=True
    )

    view_count = models.PositiveIntegerField(
        default=0
    )

    likes = models.ManyToManyField(
        User,
        related_name="liked_posts",
        blank=True
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="draft"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    visible_to_all = models.BooleanField(
        default=False
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["school"]
            ),
            models.Index(
                fields=["status", "approved"]
            ),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse(
            "blog:post_detail",
            kwargs={"slug": self.slug}
        )

    def save(self, *args, **kwargs):

        if not self.slug:

            base_slug = slugify(self.title)

            self.slug = (
                f"{base_slug}-"
                f"{uuid.uuid4().hex[:6]}"
            )

        super().save(*args, **kwargs)



class PostImage(models.Model):

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = models.ImageField(
        upload_to="posts/gallery/"
    )

    position = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = [
            "position",
            "created_at",
        ]

    def __str__(self):

        return (
            f"{self.post.title} - "
            f"{self.image.name}"
        )


# ==========================================================
# POST ATTACHMENT (PDF / DOCUMENTS)
# ==========================================================

import os


class PostAttachment(models.Model):

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="attachments"
    )

    file = models.FileField(
        upload_to="posts/attachments/"
    )

    original_name = models.CharField(
        max_length=255,
        blank=True
    )

    position = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = [
            "position",
            "created_at",
        ]

    def __str__(self):

        return (
            f"{self.post.title} - "
            f"{self.original_name or self.file.name}"
        )

    def save(self, *args, **kwargs):

        if not self.original_name and self.file:

            self.original_name = os.path.basename(
                self.file.name
            )

        super().save(*args, **kwargs)

    @property
    def extension(self):

        name = self.original_name or self.file.name

        ext = os.path.splitext(name)[1].lower()

        return ext.lstrip(".")

    @property
    def is_pdf(self):

        return self.extension == "pdf"

    @property
    def is_image(self):

        return self.extension in {
            "jpg", "jpeg", "png", "gif", "webp", "bmp", "svg"
        }

    @property
    def icon_class(self):

        mapping = {
            "pdf":  "bi-file-earmark-pdf",
            "doc":  "bi-file-earmark-word",
            "docx": "bi-file-earmark-word",
            "xls":  "bi-file-earmark-excel",
            "xlsx": "bi-file-earmark-excel",
            "ppt":  "bi-file-earmark-ppt",
            "pptx": "bi-file-earmark-ppt",
            "txt":  "bi-file-earmark-text",
            "csv":  "bi-file-earmark-spreadsheet",
            "zip":  "bi-file-earmark-zip",
            "rar":  "bi-file-earmark-zip",
        }

        return mapping.get(
            self.extension,
            "bi-file-earmark"
        )

    @property
    def size_display(self):

        try:

            size = self.file.size

        except (OSError, ValueError):

            return "—"

        if size < 1024:

            return f"{size} B"

        if size < 1024 * 1024:

            return f"{size / 1024:.1f} KB"

        return f"{size / (1024 * 1024):.2f} MB"


class Comment(models.Model):

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="comments"
    )


    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="comments"
    )


    text = CKEditor5Field(
        "Text",
        config_name="default"
    )


    liked_by = models.ManyToManyField(
        User,
        related_name="liked_comments",
        blank=True
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    updated_at = models.DateTimeField(
        auto_now=True
    )


    class Meta:

        ordering = [
            "created_at"
        ]


    def __str__(self):

        return (
            f"{self.author} on "
            f"{self.post}"
        )