from django.urls import path

from . import views

urlpatterns = [
    path('auth/signup/', views.signup, name='signup'),
    path('auth/login/', views.login, name='login'),
    path('auth/logout/', views.logout, name='logout'),
    path('auth/me/', views.me, name='me'),
    path('recipes/', views.recipes, name='recipes'),
    path('suggestions/', views.suggestions, name='suggestions'),
    path('meal-plan/', views.meal_plan, name='meal-plan'),
]
