from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import MealPlanEntry, Recipe, RecipeIngredient, RecipeInstructionStep


def serialize_recipe(recipe):
    return {
        "id": recipe.id,
        "name": recipe.name,
        "description": recipe.description,
        "prepTime": recipe.prep_time,
        "cookTime": recipe.cook_time,
        "servings": recipe.servings,
        "macrosPerServing": {
            "calories": recipe.calories,
            "protein": float(recipe.protein),
            "carbs": float(recipe.carbs),
            "totalFat": float(recipe.total_fat),
            "saturatedFat": float(recipe.saturated_fat),
        },
        "ingredients": [serialize_ingredient(ingredient) for ingredient in recipe.ingredients.all()],
        "instructions": [serialize_instruction_step(step) for step in recipe.instruction_steps.all()],
    }


def serialize_ingredient(ingredient):
    return {
        "id": ingredient.id,
        "position": ingredient.position,
        "name": ingredient.name,
        "amount": float(ingredient.amount) if ingredient.amount is not None else None,
        "unit": ingredient.unit,
    }


def serialize_instruction_step(step):
    return {
        "id": step.id,
        "position": step.position,
        "text": step.text,
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


def serialize_auth_response(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": serialize_user(user),
    }


def get_required_value(data, field):
    value = data.get(field)
    if value in (None, ""):
        raise ValidationError(f"{field} is required")
    return value


def create_recipe_from_request(user, data):
    macros = get_required_value(data, "macrosPerServing")
    if not isinstance(macros, dict):
        raise ValidationError("macrosPerServing must be an object")

    with transaction.atomic():
        recipe = Recipe(
            user=user,
            name=get_required_value(data, "name"),
            description=get_required_value(data, "description"),
            prep_time=get_required_value(data, "prepTime"),
            cook_time=get_required_value(data, "cookTime"),
            servings=get_required_value(data, "servings"),
            calories=get_required_value(macros, "calories"),
            protein=get_required_value(macros, "protein"),
            carbs=get_required_value(macros, "carbs"),
            total_fat=get_required_value(macros, "totalFat"),
            saturated_fat=get_required_value(macros, "saturatedFat"),
            is_suggestion=False,
        )
        recipe.full_clean()
        recipe.save()
        ingredients = get_required_list(data, "ingredients")
        instructions = get_required_list(data, "instructions")
        create_ingredients_from_request(recipe, ingredients)
        create_instruction_steps_from_request(recipe, instructions)
    return recipe


def get_required_list(data, field):
    value = get_required_value(data, field)
    if not isinstance(value, list):
        raise ValidationError(f"{field} must be an array")
    if not value:
        raise ValidationError(f"{field} must include at least one item")
    return value


def get_optional_position(item, fallback):
    position = item.get("position", fallback)
    if position in (None, ""):
        return fallback
    return position


def create_ingredients_from_request(recipe, ingredients):
    for index, ingredient_data in enumerate(ingredients, start=1):
        if not isinstance(ingredient_data, dict):
            raise ValidationError("ingredients must contain objects")

        ingredient = RecipeIngredient(
            recipe=recipe,
            position=get_optional_position(ingredient_data, index),
            name=get_required_value(ingredient_data, "name"),
            amount=get_optional_amount(ingredient_data),
            unit=ingredient_data.get("unit") or "",
        )
        ingredient.full_clean()
        ingredient.save()


def create_instruction_steps_from_request(recipe, instructions):
    for index, instruction_data in enumerate(instructions, start=1):
        if not isinstance(instruction_data, dict):
            raise ValidationError("instructions must contain objects")

        step = RecipeInstructionStep(
            recipe=recipe,
            position=get_optional_position(instruction_data, index),
            text=get_required_value(instruction_data, "text"),
        )
        step.full_clean()
        step.save()


def get_optional_amount(data):
    amount = data.get("amount")
    if amount in (None, ""):
        return None
    return amount


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
    return Response(
        serialize_auth_response(user),
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

    return Response(serialize_auth_response(user))


@api_view(["POST"])
def logout(request):
    refresh_token = request.data.get("refresh")
    if not refresh_token:
        return Response(
            {"error": "Refresh token is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        RefreshToken(refresh_token).blacklist()
    except TokenError:
        return Response(
            {"error": "Invalid refresh token"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
def me(request):
    return Response({"user": serialize_user(request.user)})


@api_view(["GET", "POST"])
def recipes(request):
    if request.method == "POST":
        try:
            recipe = create_recipe_from_request(request.user, request.data)
        except ValidationError as error:
            return Response(
                {"error": "; ".join(error.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"recipe": serialize_recipe(recipe)}, status=status.HTTP_201_CREATED)

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
