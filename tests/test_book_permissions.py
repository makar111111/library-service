from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from books.models import Book


class BookPermissionTests(APITestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title="Python",
            author="A. Writer",
            cover="SOFT",
            inventory=1,
            daily_fee="1.00",
        )
        self.url = f"/api/books/{self.book.pk}/"

    def test_public_can_list_and_retrieve_books(self):
        for path in ("/api/books/", self.url):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_anonymous_cannot_modify_books(self):
        for method, path, payload in (
            (self.client.post, "/api/books/", {}),
            (self.client.put, self.url, {}),
            (self.client.patch, self.url, {"inventory": 10}),
            (self.client.delete, self.url, {}),
        ):
            with self.subTest(method=method.__name__):
                self.assertEqual(method(path, payload).status_code, 401)

    def test_customer_can_read_but_cannot_modify_books(self):
        user = get_user_model().objects.create_user("reader@example.com", "strong-pass")
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        for method in (
            self.client.post,
            self.client.put,
            self.client.patch,
            self.client.delete,
        ):
            with self.subTest(method=method.__name__):
                path = "/api/books/" if method == self.client.post else self.url
                self.assertEqual(method(path, {}).status_code, 403)
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 1)

    def test_staff_can_update_inventory(self):
        staff = get_user_model().objects.create_user(
            "admin@example.com", "strong-pass", is_staff=True
        )
        self.client.force_authenticate(staff)
        self.assertEqual(self.client.patch(self.url, {"inventory": 5}).status_code, 200)
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 5)
