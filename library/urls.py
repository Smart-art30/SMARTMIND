from django.urls import path
from . import views


app_name = "library"


urlpatterns = [
    # -------------------------
    # Library navigation
    # -------------------------
    path("", views.library_home, name="home"),

    path("levels/<int:pk>/", views.level_detail, name="level_detail"),
    path("classes/<int:pk>/", views.class_detail, name="class_detail"),
    path("subjects/<int:pk>/", views.subject_detail, name="subject_detail"),
    path("topics/<int:pk>/", views.topic_detail, name="topic_detail"),
    path("subtopics/<int:pk>/", views.subtopic_detail, name="subtopic_detail"),

    # Use one lesson-detail URL format.
    path("lessons/<slug:slug>/", views.lesson_detail, name="lesson_detail"),
    path("lessons/<int:pk>/edit/", views.edit_lesson, name="edit_lesson"),


    # -------------------------
    # Resources
    # -------------------------
    path("resources/", views.resource_list, name="resource_list"),
    path("resources/add/", views.add_resource, name="add_resource"),
    path("resources/<int:pk>/", views.resource_detail, name="resource_detail"),
    path("resources/<int:pk>/edit/", views.edit_resource, name="edit_resource"),
    path("resources/<int:pk>/delete/", views.delete_resource, name="delete_resource"),
    path("resources/<int:pk>/download/",views.download_resource,name="download_resource",),


    # -------------------------
    # AJAX dropdowns
    # -------------------------
    path("ajax/classes/", views.load_classes, name="load_classes"),
    path("ajax/subjects/", views.load_subjects, name="load_subjects"),
    path("ajax/topics/", views.load_topics, name="load_topics"),
    path("ajax/subtopics/", views.load_subtopics, name="load_subtopics"),
    path("ajax/lessons/", views.load_lessons, name="load_lessons"),


    # -------------------------
    # Question bank
    # -------------------------
    path("questions/",views.question_bank_list,name="question_bank_list",),
    path("questions/add/",views.add_question,name="add_question",),
    path("questions/<int:pk>/edit/",views.edit_question,name="edit_question",),
    path("questions/<int:pk>/delete/",views.delete_question,name="delete_question",),


    # -------------------------
    # Question tags
    # -------------------------
    path("question-tags/",views.tag_list,name="tag_list",),
    path("question-tags/add/",views.add_tag,name="add_tag",),
    path("question-tags/<int:pk>/edit/",views.edit_tag,name="edit_tag",),
    path("question-tags/<int:pk>/delete/",views.delete_tag,name="delete_tag",),


    # -------------------------
    # Assessments
    # -------------------------
    path("lessons/<int:lesson_id>/assessments/",views.assessment_list,name="assessment_list",),
    path("lessons/<int:lesson_id>/assessments/add/",views.add_assessment,name="add_assessment",),
    path("assessment/<int:pk>/edit/",views.edit_assessment,name="edit_assessment",),
    path("assessment/<int:pk>/delete/",views.delete_assessment,name="delete_assessment",),
    path("assessment/<int:assessment_id>/start/",views.start_assessment,name="start_assessment",),


    # -------------------------
    # Assessment questions
    # -------------------------
    path("assessments/<int:assessment_id>/questions/",views.assessment_questions,name="assessment_questions",),
    path("assessments/<int:assessment_id>/questions/add/",views.add_assessment_question,name="add_assessment_question",),
    path("assessment-question/<int:pk>/edit/",views.edit_assessment_question,name="edit_assessment_question",),
    path("assessment-question/<int:pk>/delete/",views.delete_assessment_question,name="delete_assessment_question",),


    # -------------------------
    # Assessment attempts
    # -------------------------
    path("attempt/<int:attempt_id>/",views.take_assessment,name="take_assessment",),
    path("attempt/<int:attempt_id>/result/",views.assessment_result,name="assessment_result",),
]