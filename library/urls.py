from django.urls import path
from . import views

app_name = "library"

urlpatterns = [
    path("", views.library_home, name="home"),

    # Library
    path("levels/<int:pk>/", views.level_detail, name="level_detail"),
    path("classes/<int:pk>/", views.class_detail, name="class_detail"),
    path("subjects/<int:pk>/", views.subject_detail, name="subject_detail"),
    path("topics/<int:pk>/", views.topic_detail, name="topic_detail"),
    path("subtopics/<int:pk>/", views.subtopic_detail, name="subtopic_detail"),
    path("lessons/<slug:slug>/", views.lesson_detail, name="lesson_detail"),

    # Resources
    path("resources/", views.resource_list, name="resource_list"),
    path("resources/add/", views.add_resource, name="add_resource"),
    path("resources/<int:pk>/", views.resource_detail, name="resource_detail"),
    path("resources/<int:pk>/edit/", views.edit_resource, name="edit_resource"),
    path("resources/<int:pk>/delete/", views.delete_resource, name="delete_resource"),
    path("resources/<int:pk>/download/", views.download_resource, name="download_resource"),

    # AJAX dropdowns
    path("ajax/classes/", views.load_classes, name="load_classes"),
    path("ajax/subjects/", views.load_subjects, name="load_subjects"),
    path("ajax/topics/", views.load_topics, name="load_topics"),
    path("ajax/subtopics/", views.load_subtopics, name="load_subtopics"),
    path("ajax/lessons/", views.load_lessons, name="load_lessons"),


    path("assessment/<int:assessment_id>/questions/",views.question_list,name="question_list",),
    path("assessment/<int:assessment_id>/questions/add/",views.add_question,name="add_question",),
    path("question/<int:pk>/edit/",views.edit_question,name="edit_question",),
    path("question/<int:pk>/delete/",views.delete_question,name="delete_question",),
    path("assessment/<int:assessment_id>/start/",views.start_assessment,name="start_assessment",),
    path("attempt/<int:attempt_id>/result/",views.assessment_result,name="assessment_result",),
    path("lesson/<int:lesson_id>/assessments/",views.assessment_list,name="assessment_list",),
    path("lesson/<int:lesson_id>/assessments/add/",views.add_assessment,name="add_assessment",),
    path("assessment/<int:pk>/edit/",views.edit_assessment,name="edit_assessment",),
    path("assessment/<int:pk>/delete/",views.delete_assessment,name="delete_assessment",),
    path("attempt/<int:attempt_id>/",views.take_assessment,name="take_assessment",),
    
]