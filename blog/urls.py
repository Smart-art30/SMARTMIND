from django.urls import path
from . import views
from .views import add_post


app_name = "blog"


urlpatterns = [

    path(
        "",
        views.home,
        name="home"
    ),

    path(
        "category/<slug:slug>/",
        views.category_post,
        name="category_post"
    ),

    path(
        "posts/<slug:slug>/",
        views.post_detail,
        name="post_detail"
    ),

    path(
        "posts/<slug:slug>/like/",
        views.like_toggle,
        name="like_toggle"
    ),

    path(
        "posts/<slug:slug>/comment/",
        views.add_comment,
        name="add_comment"
    ),

    path(
        "add/",
        add_post,
        name="add_post"
    ),

    path("posts/<int:pk>/edit/", views.edit_post, name="edit_post"),

    path("posts/<int:pk>/delete/", views.delete_post, name="delete_post"),
    path(
    "post/<slug:slug>/comment/<int:comment_id>/reply/",
    views.add_reply,
    name="add_reply",),
    path(
    "comment/<int:comment_id>/like/",
    views.comment_like_toggle,
    name="comment_like_toggle",),
    path(
    "comment/<int:comment_id>/react/",
    views.comment_react,
    name="comment_react",),
    path(
    "post/<slug:slug>/react/",
    views.post_react,
    name="post_react",),
    path(
    "comment/<int:comment_id>/edit/",
    views.comment_edit,
    name="comment_edit",),
    path(    "comment/<int:comment_id>/delete/",
    views.comment_delete,
    name="comment_delete",),

]