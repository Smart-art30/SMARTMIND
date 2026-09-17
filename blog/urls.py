
from django.urls import path
from . import views
from .views import add_post


app_name = "blog"


urlpatterns = [

    # =========================================================
    # HOME
    # =========================================================

    path(
        "",
        views.home,
        name="home"
    ),


    # =========================================================
    # CATEGORY POSTS
    #
    # Example:
    # /category/pre-technical-studies/
    # =========================================================

    path(
        "category/<slug:slug>/",
        views.category_post,
        name="category_post"
    ),


    # =========================================================
    # SINGLE POST DETAIL
    #
    # Example:
    # /posts/my-first-post/
    # =========================================================

    path(
        "posts/<slug:slug>/",
        views.post_detail,
        name="post_detail"
    ),


    # =========================================================
    # LIKE / UNLIKE POST
    #
    # Example:
    # /posts/my-first-post/like/
    # =========================================================

    path(
        "posts/<slug:slug>/like/",
        views.like_toggle,
        name="like_toggle"
    ),


    # =========================================================
    # ADD COMMENT
    #
    # Example:
    # /posts/my-first-post/comment/
    # =========================================================

    path(
        "posts/<slug:slug>/comment/",
        views.add_comment,
        name="add_comment"
    ),


    # =========================================================
    # ADD POST
    #
    # Example:
    # /add/
    # =========================================================

    path(
        "add/",
        add_post,
        name="add_post"
    ),


    # =========================================================
    # EDIT POST
    #
    # Example:
    # /posts/my-first-post/edit/
    # =========================================================

    path(
        "posts/<slug:slug>/edit/",
        views.edit_post,
        name="edit_post"
    ),


    # =========================================================
    # DELETE POST
    #
    # Example:
    # /posts/my-first-post/delete/
    # =========================================================

    path(
        "posts/<slug:slug>/delete/",
        views.delete_post,
        name="delete_post"
    ),

]
