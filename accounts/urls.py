from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import user_login, dashboard

urlpatterns = [
    # auth
    path('login/', user_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),

    # dashboards
    path('dashboard/', dashboard, name='dashboard'),
    path('dashboard/school-admin/', views.school_admin_dashboard, name='school_admin_dashboard'),
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),

    # ajax
    path('ajax/load-classes/', views.load_classes, name='load_classes'),

    # teachers
    path('teachers/', views.teacher_list, name='teacher_list'),
    path('teachers/add/', views.teacher_create, name='teacher_create'),
    path('teachers/<int:pk>/edit/', views.teacher_update, name='teacher_update'),
    path('teachers/<int:pk>/delete/', views.teacher_delete, name='teacher_delete'),

    # teacher assignments / roles / permissions
    path('teacher-assignments/', views.teacher_assignment_list, name='teacher_assignment_list'),
    path('teacher-assignments/add/', views.teacher_assignment_create, name='teacher_assignment_create'),
    path('teacher-roles/', views.teacher_role_list, name='teacher_role_list'),
    path("teacher-permissions/",views.teacher_permissions,name="teacher_permission_list",),
    path("students/",views.student_list,name="student_list",),
    path("classes/",views.class_list,name="class_list",),
    path("",views.attendance_dashboard,name="attendance_dashboard",),
    path("parents/",views.parent_list,name="parent_list",),
    path("ajax/load-teacher-roles/",views.load_teacher_roles,name="ajax_load_teacher_roles",),
  
]