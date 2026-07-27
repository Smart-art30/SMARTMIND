from django.urls import path
from . import views

app_name = "library"

urlpatterns = [
    # 📚 Library Home
    path('', views.library_home, name='home'),

    # 🎓 Levels → Subjects
    path('levels/<int:level_id>/',
         views.subjects,
         name='subjects'),

    # 📘 Subjects → Topics
    path('subjects/<int:subject_id>/',
         views.topics,
         name='topics'),

    # 📖 Topic Detail
    path('topics/<int:topic_id>/',
         views.topic_detail,
         name='topic_detail'),

    # 🚀 Learning Mode
    path(
        'topics/<int:topic_id>/learn/',
        views.learning_mode,
        name='learning_mode'
    ),

    # ==========================
    # RESOURCES
    # ==========================
    path(
        'resources/',
        views.resource_list,
        name='resource_list'
    ),

    path(
        'resources/add/',
        views.add_resource,
        name='add_resource'
    ),

    path(
        'resources/<int:pk>/',
        views.resource_detail,
        name='resource_detail'
    ),

    path(
        'resources/<int:pk>/edit/',
        views.edit_resource,
        name='edit_resource'
    ),

    path(
        'resources/<int:pk>/delete/',
        views.delete_resource,
        name='delete_resource'
    ),

    # ==========================
    # FILTERS
    # ==========================
    path(
        'subject/<int:subject_id>/resources/',
        views.resources_by_subject,
        name='resources_by_subject'
    ),

    path(
        'topic/<int:topic_id>/resources/',
        views.resources_by_topic,
        name='resources_by_topic'
    ),

    path(
        'subtopic/<int:subtopic_id>/resources/',
        views.resources_by_subtopic,
        name='resources_by_subtopic'
    ),

    # ==========================
    # AJAX
    # ==========================
    path(
        'ajax/topics/',
        views.load_topics,
        name='load_topics'
    ),

    path(
        'ajax/subtopics/',
        views.load_subtopics,
        name='load_subtopics'
    ),

    # 🔍 Search
    path(
        'search/',
        views.search_library,
        name='search'
    ),
    path(
    "subtopics/<int:subtopic_id>/",
    views.subtopic_detail,
    name="subtopic_detail",
)
]