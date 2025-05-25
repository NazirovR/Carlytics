from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('visit/', views.visit_create, name='visit_create'),
    path('visit/<int:pk>/', views.visit_detail, name='visit_detail'),
    path('profile/', views.profile_view, name='profile'),
]
