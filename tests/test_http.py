from datetime import timedelta

import requests
from django.contrib.auth import get_user_model
from django.test import LiveServerTestCase
from django.utils import timezone


class RealHTTPTests(LiveServerTestCase):
    def test_registration_jwt_book_borrow_return_and_html(self):
        base = self.live_server_url
        client = requests.Session()
        self.addCleanup(client.close)
        password = "Live-http-password-576!"
        response = client.post(
            f"{base}/api/users/",
            json={"email": "http-reader@example.com", "password": password},
            timeout=10,
        )
        self.assertEqual(response.status_code, 201, response.text)
        staff = get_user_model().objects.create_user(
            "http-staff@example.com", password, is_staff=True
        )
        response = client.post(
            f"{base}/api/users/token/",
            json={"email": staff.email, "password": password},
            timeout=10,
        )
        self.assertEqual(response.status_code, 200, response.text)
        staff_headers = {"Authorize": f"Bearer {response.json()['access']}"}
        response = client.post(
            f"{base}/api/books/",
            headers=staff_headers,
            json={
                "title": "HTTP Book",
                "author": "Tester",
                "cover": "HARD",
                "inventory": 1,
                "daily_fee": "1.50",
            },
            timeout=10,
        )
        self.assertEqual(response.status_code, 201, response.text)
        book_id = response.json()["id"]
        response = client.post(
            f"{base}/api/users/token/",
            json={"email": "http-reader@example.com", "password": password},
            timeout=10,
        )
        self.assertEqual(response.status_code, 200)
        tokens = response.json()
        headers = {"Authorize": f"Bearer {tokens['access']}"}
        response = client.post(
            f"{base}/api/borrowings/",
            headers=headers,
            json={
                "book": book_id,
                "expected_return_date": (
                    timezone.localdate() + timedelta(days=7)
                ).isoformat(),
            },
            timeout=10,
        )
        self.assertEqual(response.status_code, 201, response.text)
        borrowing_id = response.json()["id"]
        self.assertEqual(response.json()["book"]["inventory"], 0)
        response = client.get(
            f"{base}/api/borrowings/?is_active=true", headers=headers, timeout=10
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        response = client.post(
            f"{base}/api/borrowings/{borrowing_id}/return/", headers=headers, timeout=10
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["is_active"])
        self.assertEqual(
            client.post(
                f"{base}/api/borrowings/{borrowing_id}/return/",
                headers=headers,
                timeout=10,
            ).status_code,
            400,
        )
        response = client.post(
            f"{base}/api/users/token/refresh/",
            json={"refresh": tokens["refresh"]},
            timeout=10,
        )
        self.assertEqual(response.status_code, 200)
        headers["Authorize"] = f"Bearer {response.json()['access']}"
        for path in (
            "/api/",
            "/api/users/",
            "/api/users/me/",
            "/api/books/",
            f"/api/books/{book_id}/",
            "/api/borrowings/",
            f"/api/borrowings/{borrowing_id}/",
            "/api/docs/",
            "/api/redoc/",
            "/api-auth/login/",
        ):
            with self.subTest(path=path):
                response = client.get(
                    base + path, headers=dict(headers, Accept="text/html"), timeout=10
                )
                self.assertEqual(response.status_code, 200, response.text[:200])
        schema = client.get(f"{base}/api/schema/?format=json", timeout=10)
        self.assertEqual(schema.status_code, 200)
        scheme = schema.json()["components"]["securitySchemes"]["jwtAuth"]
        self.assertEqual(scheme["name"], "Authorize")
        self.assertEqual(scheme["in"], "header")
