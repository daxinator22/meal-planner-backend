from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from .models import MealPlanEntry, Recipe, RecipeIngredient, RecipeInstructionStep


class ApiEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="password123",
        )
        self.refresh_token = RefreshToken.for_user(self.user)
        self.access_token = self.refresh_token.access_token
        self.auth_header = {"HTTP_AUTHORIZATION": f"Bearer {self.access_token}"}
        self.other_user = User.objects.create_user(
            username="otheruser",
            email="otheruser@example.com",
            password="password123",
        )
        self.recipe = Recipe.objects.create(
            user=self.user,
            name="Lemon Herb Chicken Bowls",
            description="Grilled chicken with rice and vegetables.",
            prep_time=35,
            cook_time=20,
            servings=4,
            calories=520,
            protein="38.5",
            carbs="48.0",
            total_fat="18.0",
            saturated_fat="4.5",
        )
        RecipeIngredient.objects.create(recipe=self.recipe, position=1, name="Chicken", amount="1.50", unit="lb")
        RecipeIngredient.objects.create(recipe=self.recipe, position=2, name="Rice", amount="1.00", unit="cup")
        RecipeInstructionStep.objects.create(recipe=self.recipe, position=1, text="Cook rice")
        RecipeInstructionStep.objects.create(recipe=self.recipe, position=2, text="Grill chicken")
        self.other_recipe = Recipe.objects.create(
            user=self.other_user,
            name="Other User Pasta",
            description="A recipe owned by another user.",
            prep_time=20,
            cook_time=15,
            servings=2,
            calories=610,
            protein="22.0",
            carbs="84.0",
            total_fat="19.5",
            saturated_fat="6.0",
        )
        RecipeIngredient.objects.create(recipe=self.other_recipe, position=1, name="Pasta", amount="12.00", unit="oz")
        RecipeInstructionStep.objects.create(recipe=self.other_recipe, position=1, text="Cook pasta")
        self.suggestion = Recipe.objects.create(
            user=self.other_user,
            name="Sheet Pan Fajita Bowls",
            description="Peppers, onions, and chicken roasted together.",
            prep_time=35,
            cook_time=25,
            servings=4,
            calories=480,
            protein="36.0",
            carbs="42.0",
            total_fat="16.5",
            saturated_fat="3.5",
            is_suggestion=True,
        )
        RecipeIngredient.objects.create(recipe=self.suggestion, position=1, name="Chicken", amount="1.50", unit="lb")
        RecipeIngredient.objects.create(recipe=self.suggestion, position=2, name="Peppers", amount="3.00", unit="")
        RecipeInstructionStep.objects.create(recipe=self.suggestion, position=1, text="Slice ingredients")
        RecipeInstructionStep.objects.create(recipe=self.suggestion, position=2, text="Roast on sheet pan")
        MealPlanEntry.objects.create(
            user=self.user,
            date="2026-05-11",
            meal_type="Dinner",
            recipe=self.recipe,
        )
        MealPlanEntry.objects.create(
            user=self.user,
            date="2026-05-12",
            meal_type="Dinner",
        )
        MealPlanEntry.objects.create(
            user=self.other_user,
            date="2026-05-13",
            meal_type="Dinner",
            recipe=self.other_recipe,
        )

    def test_recipes_endpoint_returns_saved_recipes(self):
        response = self.client.get("/api/recipes/", **self.auth_header)

        self.assertEqual(response.status_code, 200)
        recipe_response = response.json()["recipes"][0]
        self.assertEqual(recipe_response["name"], "Lemon Herb Chicken Bowls")
        self.assertEqual(recipe_response["ingredients"], [
            {
                "id": self.recipe.ingredients.get(position=1).id,
                "position": 1,
                "name": "Chicken",
                "amount": 1.5,
                "unit": "lb",
            },
            {
                "id": self.recipe.ingredients.get(position=2).id,
                "position": 2,
                "name": "Rice",
                "amount": 1.0,
                "unit": "cup",
            },
        ])
        self.assertEqual(recipe_response["instructions"], [
            {
                "id": self.recipe.instruction_steps.get(position=1).id,
                "position": 1,
                "text": "Cook rice",
            },
            {
                "id": self.recipe.instruction_steps.get(position=2).id,
                "position": 2,
                "text": "Grill chicken",
            },
        ])

    def test_recipes_endpoint_excludes_other_users_recipes(self):
        response = self.client.get("/api/recipes/", **self.auth_header)

        recipe_names = [recipe["name"] for recipe in response.json()["recipes"]]
        self.assertNotIn("Other User Pasta", recipe_names)

    def test_recipes_endpoint_creates_user_recipe(self):
        response = self.client.post(
            "/api/recipes/",
            {
                "name": "Chicken Rice Bowl",
                "description": "Simple weeknight dinner.",
                "prepTime": 20,
                "cookTime": 25,
                "servings": 4,
                "macrosPerServing": {
                    "calories": 520,
                    "protein": 38.5,
                    "carbs": 48.0,
                    "totalFat": 18.0,
                    "saturatedFat": 4.5,
                },
                "ingredients": [
                    {"name": "Chicken", "amount": 1.5, "unit": "lb"},
                    {"name": "Rice", "amount": 1, "unit": "cup"},
                    {"name": "Broccoli", "amount": 2, "unit": "cups"},
                ],
                "instructions": [
                    {"text": "Cook rice."},
                    {"text": "Grill chicken."},
                    {"text": "Assemble bowl."},
                ],
            },
            content_type="application/json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, 201)
        recipe = Recipe.objects.get(name="Chicken Rice Bowl")
        self.assertEqual(recipe.user, self.user)
        self.assertFalse(recipe.is_suggestion)
        created_recipe_response = response.json()["recipe"]
        self.assertEqual(created_recipe_response["name"], "Chicken Rice Bowl")
        self.assertEqual(created_recipe_response["ingredients"][0], {
            "id": recipe.ingredients.get(position=1).id,
            "position": 1,
            "name": "Chicken",
            "amount": 1.5,
            "unit": "lb",
        })
        self.assertEqual(created_recipe_response["instructions"][0], {
            "id": recipe.instruction_steps.get(position=1).id,
            "position": 1,
            "text": "Cook rice.",
        })

        list_response = self.client.get("/api/recipes/", **self.auth_header)
        recipe_names = [recipe["name"] for recipe in list_response.json()["recipes"]]
        self.assertIn("Chicken Rice Bowl", recipe_names)

    def test_recipes_endpoint_returns_401_when_creating_without_token(self):
        response = self.client.post(
            "/api/recipes/",
            {},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)

    def test_recipes_endpoint_requires_fields_when_creating(self):
        response = self.client.post(
            "/api/recipes/",
            {
                "description": "Missing name.",
                "prepTime": 20,
                "cookTime": 25,
                "servings": 4,
                "macrosPerServing": {
                    "calories": 520,
                    "protein": 38.5,
                    "carbs": 48.0,
                    "totalFat": 18.0,
                    "saturatedFat": 4.5,
                },
            },
            content_type="application/json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "name is required"})

    def test_recipes_endpoint_does_not_create_user_suggestions(self):
        response = self.client.post(
            "/api/recipes/",
            {
                "name": "User Suggestion Attempt",
                "description": "Should still be a user recipe.",
                "prepTime": 15,
                "cookTime": 10,
                "servings": 2,
                "macrosPerServing": {
                    "calories": 320,
                    "protein": 20.0,
                    "carbs": 35.0,
                    "totalFat": 12.0,
                    "saturatedFat": 3.0,
                },
                "ingredients": [
                    {"name": "Chicken", "amount": 1, "unit": "lb"},
                ],
                "instructions": [
                    {"text": "Cook chicken."},
                ],
                "isSuggestion": True,
                "is_suggestion": True,
            },
            content_type="application/json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, 201)
        recipe = Recipe.objects.get(name="User Suggestion Attempt")
        self.assertFalse(recipe.is_suggestion)

    def test_suggestions_endpoint_returns_suggestions(self):
        response = self.client.get("/api/suggestions/", **self.auth_header)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["suggestions"][0]["id"], self.suggestion.id)
        self.assertEqual(response.json()["suggestions"][0]["name"], "Sheet Pan Fajita Bowls")
        self.assertEqual(response.json()["suggestions"][0]["cookTime"], 25)
        self.assertEqual(response.json()["suggestions"][0]["servings"], 4)
        self.assertEqual(response.json()["suggestions"][0]["macrosPerServing"], {
            "calories": 480,
            "protein": 36.0,
            "carbs": 42.0,
            "totalFat": 16.5,
            "saturatedFat": 3.5,
        })

    def test_suggestions_endpoint_returns_global_suggestions(self):
        response = self.client.get("/api/suggestions/", **self.auth_header)

        suggestion_names = [recipe["name"] for recipe in response.json()["suggestions"]]
        self.assertIn("Sheet Pan Fajita Bowls", suggestion_names)

    def test_meal_plan_endpoint_returns_entries(self):
        response = self.client.get("/api/meal-plan/", **self.auth_header)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["mealPlan"]), 2)
        self.assertEqual(response.json()["mealPlan"][0]["date"], "2026-05-11")
        self.assertEqual(response.json()["mealPlan"][0]["recipe"]["name"], "Lemon Herb Chicken Bowls")
        self.assertEqual(response.json()["mealPlan"][0]["recipe"]["cookTime"], 20)
        self.assertEqual(response.json()["mealPlan"][0]["recipe"]["servings"], 4)
        self.assertEqual(response.json()["mealPlan"][0]["recipe"]["macrosPerServing"], {
            "calories": 520,
            "protein": 38.5,
            "carbs": 48.0,
            "totalFat": 18.0,
            "saturatedFat": 4.5,
        })
        self.assertIsNone(response.json()["mealPlan"][1]["recipe"])

    def test_meal_plan_endpoint_excludes_other_users_entries(self):
        response = self.client.get("/api/meal-plan/", **self.auth_header)

        meal_plan_recipes = [
            entry["recipe"]["name"]
            for entry in response.json()["mealPlan"]
            if entry["recipe"] is not None
        ]
        self.assertNotIn("Other User Pasta", meal_plan_recipes)

    def test_login_returns_tokens_for_valid_credentials(self):
        response = self.client.post(
            "/api/auth/login/",
            {"username": "testuser", "password": "password123"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())
        self.assertIn("refresh", response.json())
        self.assertEqual(response.json()["user"], {
            "id": self.user.id,
            "username": "testuser",
            "email": "testuser@example.com",
        })

    def test_login_returns_401_for_invalid_credentials(self):
        response = self.client.post(
            "/api/auth/login/",
            {"username": "testuser", "password": "wrong-password"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "Invalid credentials"})

    def test_signup_creates_user_and_returns_tokens(self):
        response = self.client.post(
            "/api/auth/signup/",
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123",
            },
            content_type="application/json",
        )

        user = User.objects.get(username="newuser")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["user"], {
            "id": user.id,
            "username": "newuser",
            "email": "newuser@example.com",
        })
        self.assertIn("access", response.json())
        self.assertIn("refresh", response.json())
        self.assertTrue(user.check_password("password123"))

    def test_signup_requires_email(self):
        response = self.client.post(
            "/api/auth/signup/",
            {"username": "newuser", "password": "password123"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Username, email, and password are required"})
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_signup_rejects_duplicate_username(self):
        response = self.client.post(
            "/api/auth/signup/",
            {
                "username": "testuser",
                "email": "another@example.com",
                "password": "password123",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Username is already in use"})

    def test_signup_rejects_duplicate_email(self):
        response = self.client.post(
            "/api/auth/signup/",
            {
                "username": "anotheruser",
                "email": "testuser@example.com",
                "password": "password123",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Email is already in use"})

    def test_signup_access_token_can_access_me_endpoint(self):
        signup_response = self.client.post(
            "/api/auth/signup/",
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123",
            },
            content_type="application/json",
        )
        access_token = signup_response.json()["access"]

        response = self.client.get(
            "/api/auth/me/",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["username"], "newuser")
        self.assertEqual(response.json()["user"]["email"], "newuser@example.com")

    def test_me_returns_current_user_with_token(self):
        response = self.client.get("/api/auth/me/", **self.auth_header)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "user": {
                "id": self.user.id,
                "username": "testuser",
                "email": "testuser@example.com",
            }
        })

    def test_me_returns_401_without_token(self):
        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 401)

    def test_me_returns_401_with_invalid_access_token(self):
        response = self.client.get(
            "/api/auth/me/",
            HTTP_AUTHORIZATION="Bearer not-a-token",
        )

        self.assertEqual(response.status_code, 401)

    def test_me_returns_401_with_expired_access_token(self):
        expired_access = AccessToken.for_user(self.user)
        expired_access.set_exp(lifetime=timedelta(seconds=-1))

        response = self.client.get(
            "/api/auth/me/",
            HTTP_AUTHORIZATION=f"Bearer {expired_access}",
        )

        self.assertEqual(response.status_code, 401)

    def test_refresh_returns_access_for_valid_refresh_token(self):
        response = self.client.post(
            "/api/auth/refresh/",
            {"refresh": str(self.refresh_token)},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())

    def test_refresh_returns_401_for_invalid_refresh_token(self):
        response = self.client.post(
            "/api/auth/refresh/",
            {"refresh": "not-a-token"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)

    def test_refresh_returns_401_for_expired_refresh_token(self):
        expired_refresh = RefreshToken.for_user(self.user)
        expired_refresh.set_exp(lifetime=timedelta(seconds=-1))

        response = self.client.post(
            "/api/auth/refresh/",
            {"refresh": str(expired_refresh)},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)

    def test_logout_blacklists_refresh_token(self):
        response = self.client.post(
            "/api/auth/logout/",
            {"refresh": str(self.refresh_token)},
            content_type="application/json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, 204)

        refresh_response = self.client.post(
            "/api/auth/refresh/",
            {"refresh": str(self.refresh_token)},
            content_type="application/json",
        )
        self.assertEqual(refresh_response.status_code, 401)

    def test_logout_requires_refresh_token(self):
        response = self.client.post(
            "/api/auth/logout/",
            {},
            content_type="application/json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Refresh token is required"})

    def test_recipes_endpoint_returns_401_without_token(self):
        response = self.client.get("/api/recipes/")

        self.assertEqual(response.status_code, 401)
