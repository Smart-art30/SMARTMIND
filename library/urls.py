from django.urls import path
from . import views

app_name = "library"

urlpatterns = [
    path("", views.library_home, name="home"),

    path("levels/<int:pk>/", views.level_detail, name="level_detail"),
    path("classes/<int:pk>/", views.class_detail, name="class_detail"),
    path("subjects/<int:pk>/", views.subject_detail, name="subject_detail"),
    path("topics/<int:pk>/", views.topic_detail, name="topic_detail"),
    path("subtopics/<int:pk>/", views.subtopic_detail, name="subtopic_detail"),
    path("lessons/<slug:slug>/", views.lesson_detail, name="lesson_detail"),

    path("resources/", views.resource_list, name="resource_list"),
    path("resources/add/", views.add_resource, name="add_resource"),
    path("resources/<int:pk>/", views.resource_detail, name="resource_detail"),
    path("resources/<int:pk>/edit/", views.edit_resource, name="edit_resource"),
    path("resources/<int:pk>/delete/", views.delete_resource, name="delete_resource"),
    path("resources/<int:pk>/download/", views.download_resource, name="download_resource"),
    path("resources/<int:pk>/",views.resource_detail,name="resource_detail",),
    path("resources/<int:pk>/", views.resource_detail, name="resource_detail"),
    path("resources/<int:pk>/edit/", views.edit_resource, name="edit_resource"),
    path("resources/<int:pk>/delete/", views.delete_resource, name="delete_resource"),
    path("resources/<int:pk>/download/", views.download_resource, name="download_resource"),
]