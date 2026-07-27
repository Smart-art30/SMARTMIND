from django.urls import path
from . import views
from .views import add_post

app_name = 'blog'

urlpatterns = [
    path('', views.home, name='home'),
    path('posts/<slug:slug>/', views.post_detail, name='post_detail'),
    path('posts/<slug:slug>/like/', views.like_toggle, name='like_toggle'),
    path('posts/<slug:slug>/comment/', views.add_comment, name='add_comment'),
    path('category/<slug:slug>/', views.category_post, name='category_post'),
    path('add/', add_post, name= 'add_post'),
    


  
]