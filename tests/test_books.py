from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase


class BookCRUDTests(APITestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            email="librarian@example.com",
            password="Strong-book-password-492!",
            is_staff=True,
        )
        self.client.force_authenticate(self.staff)
        self.payload = {
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "cover": "HARD",
            "inventory": 2,
            "daily_fee": "1.50",
        }

    def create_book(self, **extra):
        payload = dict(self.payload, **extra)
        response = self.client.post("/api/books/", payload)
        self.assertEqual(response.status_code, 201, response.content)
        return response.data

    def test_create_and_retrieve_book(self):
        book = self.create_book()
        response = self.client.get(f"/api/books/{book['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["author"], self.payload["author"])
        self.assertEqual(Decimal(response.data["daily_fee"]), Decimal("1.50"))

    def test_list_is_paginated_and_ordered(self):
        first = self.create_book()
        second = self.create_book(title="The Pragmatic Programmer")
        response = self.client.get("/api/books/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            [b["id"] for b in response.data["results"]], [first["id"], second["id"]]
        )

    def test_update_and_delete_book(self):
        book = self.create_book()
        url = f"/api/books/{book['id']}/"
        updated = dict(self.payload, inventory=4)
        self.assertEqual(self.client.put(url, updated).status_code, 200)
        response = self.client.patch(url, {"inventory": 0})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["inventory"], 0)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_invalid_inventory_cover_and_fee_are_rejected(self):
        for invalid in ({"inventory": -1}, {"daily_fee": "0.00"}, {"cover": "UNKNOWN"}):
            with self.subTest(invalid=invalid):
                response = self.client.post(
                    "/api/books/", dict(self.payload, **invalid)
                )
                self.assertEqual(response.status_code, 400, response.content)

    def test_browsable_book_pages_render(self):
        book = self.create_book()
        for path in ("/api/books/", f"/api/books/{book['id']}/"):
            response = self.client.get(path, HTTP_ACCEPT="text/html")
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Clean Code")
