from django.conf import settings
from django.db import models


class Recipe(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recipes",
    )
    name = models.CharField(max_length=120)
    description = models.TextField()
    prep_time = models.PositiveIntegerField()
    cook_time = models.PositiveIntegerField()
    servings = models.PositiveIntegerField()
    calories = models.PositiveIntegerField()
    protein = models.DecimalField(max_digits=6, decimal_places=1)
    carbs = models.DecimalField(max_digits=6, decimal_places=1)
    total_fat = models.DecimalField(max_digits=6, decimal_places=1)
    saturated_fat = models.DecimalField(max_digits=6, decimal_places=1)
    tags = models.JSONField(default=list, blank=True)
    ingredients = models.JSONField(default=list, blank=True)
    instructions = models.JSONField(default=list, blank=True)
    is_suggestion = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class MealPlanEntry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="meal_plan_entries",
    )
    date = models.DateField()
    meal_type = models.CharField(max_length=40)
    recipe = models.ForeignKey(
        Recipe,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="meal_plan_entries",
    )

    class Meta:
        ordering = ["id"]
        verbose_name_plural = "meal plan entries"

    def __str__(self):
        return f"{self.date} {self.meal_type}"
