from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from books.models import Book
from borrowings.models import Borrowing


class BorrowingCreateTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "reader@example.com", "password"
        )
        self.other = get_user_model().objects.create_user(
            "other@example.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.book = Book.objects.create(
            title="Python",
            author="A. Writer",
            cover="SOFT",
            inventory=1,
            daily_fee="1.25",
        )
        self.payload = {
            "book": self.book.pk,
            "expected_return_date": (
                timezone.localdate() + timedelta(days=7)
            ).isoformat(),
        }

    def test_create_attaches_current_user_and_decrements_inventory(self):
        response = self.client.post("/api/borrowings/", self.payload)
        self.assertEqual(response.status_code, 201, response.content)
        borrowing = Borrowing.objects.get(pk=response.data["id"])
        self.assertEqual(borrowing.user, self.user)
        self.assertEqual(borrowing.borrow_date, timezone.localdate())
        self.assertIsNone(borrowing.actual_return_date)
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 0)

    def test_no_stock_is_rejected_without_creating_borrowing(self):
        self.book.inventory = 0
        self.book.save()
        response = self.client.post("/api/borrowings/", self.payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("book", response.data)
        self.assertEqual(Borrowing.objects.count(), 0)
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 0)

    def test_last_copy_cannot_be_borrowed_twice(self):
        self.assertEqual(
            self.client.post("/api/borrowings/", self.payload).status_code, 201
        )
        self.assertEqual(
            self.client.post("/api/borrowings/", self.payload).status_code, 400
        )
        self.assertEqual(Borrowing.objects.count(), 1)

    def test_user_dates_and_return_status_cannot_be_spoofed(self):
        payload = dict(
            self.payload,
            user=self.other.pk,
            borrow_date="2000-01-01",
            actual_return_date=timezone.localdate().isoformat(),
        )
        response = self.client.post("/api/borrowings/", payload)
        self.assertEqual(response.status_code, 201)
        borrowing = Borrowing.objects.get()
        self.assertEqual(borrowing.user, self.user)
        self.assertEqual(borrowing.borrow_date, timezone.localdate())
        self.assertIsNone(borrowing.actual_return_date)

    def test_past_return_date_invalid_book_and_missing_fields_are_rejected(self):
        for payload in (
            dict(self.payload, expected_return_date="2000-01-01"),
            dict(self.payload, book=999999),
            {},
        ):
            with self.subTest(payload=payload):
                self.assertEqual(
                    self.client.post("/api/borrowings/", payload).status_code, 400
                )
        self.assertEqual(Borrowing.objects.count(), 0)
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 1)

    def test_anonymous_cannot_create(self):
        self.client.force_authenticate(None)
        self.assertEqual(
            self.client.post("/api/borrowings/", self.payload).status_code, 401
        )

    def test_database_failure_rolls_back_inventory(self):
        with patch.object(
            Borrowing.objects, "create", side_effect=RuntimeError("DB failure")
        ):
            with self.assertRaises(RuntimeError):
                self.client.post("/api/borrowings/", self.payload)
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 1)
        self.assertEqual(Borrowing.objects.count(), 0)
