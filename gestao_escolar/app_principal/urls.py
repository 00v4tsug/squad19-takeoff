from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),

    path('', views.painel, name='painel'),
    path('admin/', views.painel_admin, name='painel_admin'),
    path('professor/', views.painel_professor, name='painel_professor'),
    path('aluno/', views.painel_aluno, name='painel_aluno'),
]
