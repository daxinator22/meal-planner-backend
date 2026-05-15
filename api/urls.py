from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path('auth/signup/', views.signup, name='signup'),
    path('auth/login/', views.login, name='login'),
    path('auth/logout/', views.logout, name='logout'),
    path('auth/me/', views.me, name='me'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('recipes/', views.recipes, name='recipes'),
    path('suggestions/', views.suggestions, name='suggestions'),
    path('meal-plan/', views.meal_plan, name='meal-plan'),
]
