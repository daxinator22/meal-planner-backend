from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token

from .models import MealPlanEntry, Recipe


class ApiEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="password123",
        )
        self.token = Token.objects.create(user=self.user)
        self.auth_header = {"HTTP_AUTHORIZATION": f"Token {self.token.key}"}
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
            tags=["Healthy", "Dinner"],
            ingredients=["Chicken", "Rice"],
            instructions=["Cook rice", "Grill chicken"],
        )
        self.other_recipe = Recipe.objects.create(
            user=self.other_user,
            name="Other User Pasta",
            description="A recipe owned by another user.",
            prep_time=20,
            tags=["Dinner"],
            ingredients=["Pasta"],
            instructions=["Cook pasta"],
        )
        self.suggestion = Recipe.objects.create(
            user=self.other_user,
            name="Sheet Pan Fajita Bowls",
            description="Peppers, onions, and chicken roasted together.",
            prep_time=35,
            tags=["Suggested", "Sheet Pan"],
            ingredients=["Chicken", "Peppers"],
            instructions=["Slice ingredients", "Roast on sheet pan"],
            is_suggestion=True,
        )
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
        self.assertEqual(response.json(), {
            "recipes": [
                {
                    "id": self.recipe.id,
                    "name": "Lemon Herb Chicken Bowls",
                    "description": "Grilled chicken with rice and vegetables.",
                    "prepTime": 35,
                    "tags": ["Healthy", "Dinner"],
                    "ingredients": ["Chicken", "Rice"],
                    "instructions": ["Cook rice", "Grill chicken"],
                }
            ]
        })

    def test_recipes_endpoint_excludes_other_users_recipes(self):
        response = self.client.get("/api/recipes/", **self.auth_header)

        recipe_names = [recipe["name"] for recipe in response.json()["recipes"]]
        self.assertNotIn("Other User Pasta", recipe_names)

    def test_suggestions_endpoint_returns_suggestions(self):
        response = self.client.get("/api/suggestions/", **self.auth_header)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["suggestions"][0]["id"], self.suggestion.id)
        self.assertEqual(response.json()["suggestions"][0]["name"], "Sheet Pan Fajita Bowls")

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
        self.assertIsNone(response.json()["mealPlan"][1]["recipe"])

    def test_meal_plan_endpoint_excludes_other_users_entries(self):
        response = self.client.get("/api/meal-plan/", **self.auth_header)

        meal_plan_recipes = [
            entry["recipe"]["name"]
            for entry in response.json()["mealPlan"]
            if entry["recipe"] is not None
        ]
        self.assertNotIn("Other User Pasta", meal_plan_recipes)

    def test_login_returns_token_for_valid_credentials(self):
        response = self.client.post(
            "/api/auth/login/",
            {"username": "testuser", "password": "password123"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["token"], self.token.key)
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

    def test_signup_creates_user_and_returns_token(self):
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
        self.assertEqual(response.json()["token"], Token.objects.get(user=user).key)
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

    def test_signup_token_can_access_me_endpoint(self):
        signup_response = self.client.post(
            "/api/auth/signup/",
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123",
            },
            content_type="application/json",
        )
        token = signup_response.json()["token"]

        response = self.client.get(
            "/api/auth/me/",
            HTTP_AUTHORIZATION=f"Token {token}",
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

    def test_logout_deletes_token(self):
        response = self.client.post("/api/auth/logout/", **self.auth_header)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_recipes_endpoint_returns_401_without_token(self):
        response = self.client.get("/api/recipes/")

        self.assertEqual(response.status_code, 401)
