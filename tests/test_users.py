from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase


class UserAPITests(APITestCase):
    password = "Strong-library-password-492!"

    def register(self, **extra):
        payload = {"email": "reader@example.com", "password": self.password}
        payload.update(extra)
        response = self.client.post("/api/users/", payload)
        self.assertEqual(response.status_code, 201, response.content)
        return response

    def authenticate(self):
        response = self.client.post(
            "/api/users/token/",
            {"email": "READER@example.com", "password": self.password},
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.client.credentials(HTTP_AUTHORIZE=f"Bearer {response.data['access']}")
        return response.data

    def test_register_normalizes_email_and_hashes_password(self):
        response = self.register(email="Reader@EXAMPLE.COM", first_name="Alice")
        user = get_user_model().objects.get(pk=response.data["id"])
        self.assertEqual(user.email, "reader@example.com")
        self.assertTrue(user.check_password(self.password))
        self.assertNotIn("password", response.data)
        self.assertNotIn("username", response.data)

    def test_register_cannot_grant_staff_or_superuser(self):
        response = self.register(is_staff=True, is_superuser=True)
        user = get_user_model().objects.get(pk=response.data["id"])
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_duplicate_email_is_case_insensitive(self):
        self.register()
        response = self.client.post(
            "/api/users/", {"email": "READER@example.com", "password": self.password}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_weak_password_and_invalid_email_are_rejected(self):
        for payload in (
            {"email": "reader@example.com", "password": "123"},
            {"email": "not-an-email", "password": self.password},
        ):
            with self.subTest(payload=payload):
                self.assertEqual(
                    self.client.post("/api/users/", payload).status_code, 400
                )

    def test_real_jwt_authorize_header_gets_private_profile(self):
        self.register()
        self.authenticate()
        response = self.client.get("/api/users/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "reader@example.com")

    def test_refresh_issues_usable_access_token(self):
        self.register()
        tokens = self.authenticate()
        self.client.credentials()
        response = self.client.post(
            "/api/users/token/refresh/", {"refresh": tokens["refresh"]}
        )
        self.assertEqual(response.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZE=f"Bearer {response.data['access']}")
        self.assertEqual(self.client.get("/api/users/me/").status_code, 200)

    def test_bad_credentials_and_invalid_jwt_are_rejected(self):
        self.register()
        response = self.client.post(
            "/api/users/token/", {"email": "reader@example.com", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 401)
        self.client.credentials(HTTP_AUTHORIZE="Bearer invalid")
        self.assertEqual(self.client.get("/api/users/me/").status_code, 401)

    def test_anonymous_profile_is_rejected(self):
        self.assertEqual(self.client.get("/api/users/me/").status_code, 401)

    def test_profile_updates_name_and_password_without_privilege_escalation(self):
        self.register()
        self.authenticate()
        new_password = "Changed-library-password-751!"
        response = self.client.patch(
            "/api/users/me/",
            {"first_name": "Alice", "password": new_password, "is_staff": True},
        )
        self.assertEqual(response.status_code, 200)
        user = get_user_model().objects.get(email="reader@example.com")
        self.assertEqual(user.first_name, "Alice")
        self.assertTrue(user.check_password(new_password))
        self.assertFalse(user.is_staff)
        self.assertNotIn("password", response.data)

    def test_browsable_registration_and_session_profile_pages_render(self):
        self.register()
        response = self.client.get("/api/users/", HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 200)
        user = get_user_model().objects.get(email="reader@example.com")
        self.client.force_login(user)
        response = self.client.get("/api/users/me/", HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 200)
