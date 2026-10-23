from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from books.models import Book
from borrowings.models import Borrowing


class BorrowingReturnTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "reader@example.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.book = Book.objects.create(
            title="Python",
            author="A. Writer",
            cover="SOFT",
            inventory=0,
            daily_fee="1.25",
        )
        self.borrowing = Borrowing.objects.create(
            book=self.book,
            user=self.user,
            expected_return_date=timezone.localdate() + timedelta(days=7),
        )
        self.url = f"/api/borrowings/{self.borrowing.pk}/return/"

    def test_return_sets_today_and_restores_stock(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200, response.content)
        self.book.refresh_from_db()
        self.borrowing.refresh_from_db()
        self.assertEqual(self.book.inventory, 1)
        self.assertEqual(self.borrowing.actual_return_date, timezone.localdate())
        self.assertFalse(response.data["is_active"])

    def test_cannot_return_twice_or_increment_stock_twice(self):
        self.assertEqual(self.client.post(self.url).status_code, 200)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 400)
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 1)

    def test_reader_cannot_return_someone_elses_book(self):
        other = get_user_model().objects.create_user("other@example.com", "password")
        self.client.force_authenticate(other)
        self.assertEqual(self.client.post(self.url).status_code, 404)
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 0)

    def test_staff_can_return_a_readers_book(self):
        admin = get_user_model().objects.create_user(
            "admin@example.com", "password", is_staff=True
        )
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.post(self.url).status_code, 200)

    def test_anonymous_and_get_cannot_return_books(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(self.url).status_code, 401)

    def test_user_cannot_supply_another_actual_return_date(self):
        response = self.client.post(self.url, {"actual_return_date": "2000-01-01"})
        self.assertEqual(response.status_code, 200)
        self.borrowing.refresh_from_db()
        self.assertEqual(self.borrowing.actual_return_date, timezone.localdate())

    def test_inventory_failure_rolls_back_return_date(self):
        with patch(
            "borrowings.services.Book.objects.filter",
            side_effect=RuntimeError("DB failure"),
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(self.url)
        self.borrowing.refresh_from_db()
        self.book.refresh_from_db()
        self.assertIsNone(self.borrowing.actual_return_date)
        self.assertEqual(self.book.inventory, 0)
