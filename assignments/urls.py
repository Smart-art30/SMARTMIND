from django.urls import path
from . import views

urlpatterns = [
    path('', views.assignment_list, name='assignment_list'),
    
    path('<int:pk>/', views.assignment_detail, name='assignment_detail'),

    path('<int:pk>/submit/', views.submit_assignment, name='submit_assignment'),

    path('<int:pk>/quiz/start/', views.start_quiz, name='start_quiz'),
    path('<int:pk>/quiz/submit/', views.submit_quiz, name='submit_quiz'),

    path('result/<int:attempt_id>/', views.quiz_result, name='quiz_result'),

    path("quizzes/", views.quiz_home, name="quiz_home"),

    path("quizzes/class/<int:class_id>/", views.quiz_class_subjects, name="quiz_class_subjects"),

    path("quizzes/class/<int:class_id>/subject/<int:subject_id>/", views.quiz_list, name="quiz_list"),

    path("quizzes/start/<int:pk>/", views.start_quiz, name="start_quiz"),

    path("quizzes/submit/<int:pk>/", views.submit_quiz, name="submit_quiz"),

    path("quizzes/result/<int:attempt_id>/", views.quiz_result, name="quiz_result"),

    path("schools/<int:school_id>/subjects/", views.school_subjects, name="school_subjects"),

    path("schools/<int:school_id>/subjects/create/", views.create_subject, name="create_subject"),
    path("dashboard/assignments/", views.manage_assignments, name="manage_assignments"),
    path("dashboard/quizzes/", views.manage_quizzes, name="manage_quizzes"),
    path("dashboard/submissions/", views.submission_list, name="submission_list"),
    path("dashboard/gradebook/", views.gradebook, name="gradebook"),
    path("dashboard/assignment/create/", views.create_assignment, name="create_assignment"),
    path("dashboard/quiz/create/", views.create_quiz, name="create_quiz"),
    path("submissions/",views.submission_list,name="submission_list",),
    path("submissions/<int:pk>/",views.submission_detail,name="submission_detail",),
    path("submissions/<int:pk>/grade/",views.grade_submission,name="grade_submission",),
    path("<int:pk>/autosave/",views.autosave_submission,name="autosave_submission",),
]