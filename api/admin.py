from django.contrib import admin

from .models import MealPlanEntry, Recipe


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'prep_time', 'is_suggestion')
    list_filter = ('is_suggestion',)
    search_fields = ('name', 'description')


@admin.register(MealPlanEntry)
class MealPlanEntryAdmin(admin.ModelAdmin):
    list_display = ('day', 'date_label', 'meal_type', 'recipe')
    search_fields = ('day', 'meal_type', 'recipe__name')
