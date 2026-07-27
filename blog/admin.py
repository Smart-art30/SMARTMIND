from django.contrib import admin
from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget

from .models import Post, Category, Tag


class PostAdminForm(forms.ModelForm):
    content = forms.CharField(
        widget=CKEditor5Widget(config_name="default")
    )

    class Meta:
        model = Post
        fields = "__all__"


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    form = PostAdminForm

    list_display = (
        "title",
        "category",
        "author",
        "school",
        "status",
        "approved",
        "created_at",
    )

    list_filter = (
        "status",
        "approved",
        "category",
        "school",
    )

    search_fields = (
        "title",
        "content",
    )

    filter_horizontal = (
        "tags",
        "target_classes",
        "likes",
    )

    prepopulated_fields = {
        "slug": ("title",)
    }


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ("name",)