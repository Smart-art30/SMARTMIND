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
        "category/<slug:slug>/",
        views.category_post,
        name="category_post"
    ),


    # =========================================================
    # ADD POST
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
    # Uses numeric primary key.
    #
    # Example:
    # /posts/10/edit/
    # =========================================================

    path("posts/<slug:slug>/edit/", views.edit_post, name="edit_post"),


    # =========================================================
    # DELETE POST
    #
    # Uses numeric primary key.
    #
    # Example:
    # /posts/10/delete/
    # =========================================================

    path(
    "posts/<slug:slug>/delete/",
    views.delete_post,
    name="delete_post",
),

]
