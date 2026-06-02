from django.contrib import admin

from .models import MealPlanEntry, Recipe, RecipeIngredient, RecipeInstructionStep


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1


class RecipeInstructionStepInline(admin.TabularInline):
    model = RecipeInstructionStep
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'prep_time', 'cook_time', 'servings', 'calories', 'is_suggestion')
    list_filter = ('is_suggestion',)
    search_fields = ('name', 'description')
    inlines = (RecipeIngredientInline, RecipeInstructionStepInline)


@admin.register(MealPlanEntry)
class MealPlanEntryAdmin(admin.ModelAdmin):
    list_display = ('date', 'meal_type', 'recipe')
    search_fields = ('meal_type', 'recipe__name')
