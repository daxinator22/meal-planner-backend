from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import MealPlanEntry, Recipe


def serialize_recipe(recipe):
    return {
        "id": recipe.id,
        "name": recipe.name,
        "description": recipe.description,
        "prepTime": recipe.prep_time,
        "tags": recipe.tags,
        "ingredients": recipe.ingredients,
        "instructions": recipe.instructions,
    }


def serialize_meal_plan_entry(entry):
    return {
        "id": entry.id,
        "date": entry.date.isoformat(),
        "mealType": entry.meal_type,
        "recipe": serialize_recipe(entry.recipe) if entry.recipe else None,
    }


def serialize_user(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
    }


@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    username = request.data.get("username")
    email = request.data.get("email")
    password = request.data.get("password")

    if not username or not email or not password:
        return Response(
            {"error": "Username, email, and password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(username=username).exists():
        return Response(
            {"error": "Username is already in use"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(email=email).exists():
        return Response(
            {"error": "Email is already in use"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.create_user(username=username, email=email, password=password)
    token = Token.objects.create(user=user)
    return Response(
        {"token": token.key, "user": serialize_user(user)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return Response(
            {"error": "Username and password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response(
            {"error": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": serialize_user(user)})


@api_view(["POST"])
def logout(request):
    request.user.auth_token.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
def me(request):
    return Response({"user": serialize_user(request.user)})


@api_view(["GET"])
def recipes(request):
    recipe_list = Recipe.objects.filter(user=request.user, is_suggestion=False)
    return Response({"recipes": [serialize_recipe(recipe) for recipe in recipe_list]})


@api_view(["GET"])
def suggestions(request):
    suggestion_list = Recipe.objects.filter(is_suggestion=True)
    return Response({"suggestions": [serialize_recipe(recipe) for recipe in suggestion_list]})


@api_view(["GET"])
def meal_plan(request):
    entries = MealPlanEntry.objects.filter(user=request.user).select_related("recipe")
    return Response({"mealPlan": [serialize_meal_plan_entry(entry) for entry in entries]})
