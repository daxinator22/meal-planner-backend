from django.db import models


class Recipe(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField()
    prep_time = models.PositiveIntegerField()
    tags = models.JSONField(default=list, blank=True)
    ingredients = models.JSONField(default=list, blank=True)
    instructions = models.JSONField(default=list, blank=True)
    is_suggestion = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class MealPlanEntry(models.Model):
    day = models.CharField(max_length=20)
    date_label = models.CharField(max_length=10)
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
        return f"{self.day} {self.meal_type}"
