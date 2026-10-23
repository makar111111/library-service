from datetime import timedelta

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.test import APITestCase

from books.models import Book


class BorrowingReadTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "reader@example.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.book = Book.objects.create(
            title="Python",
            author="A. Writer",
            cover="SOFT",
            inventory=1,
            daily_fee="1.25",
        )
        self.today = timezone.localdate()

    def borrowing_model(self):
        self.assertTrue(apps.is_installed("borrowings"), "Borrowings app must exist.")
        return apps.get_model("borrowings", "Borrowing")

    def create_borrowing(self, **extra):
        payload = {
            "user": self.user,
            "book": self.book,
            "expected_return_date": self.today + timedelta(days=7),
        }
        payload.update(extra)
        return self.borrowing_model().objects.create(**payload)

    def test_anonymous_cannot_list_borrowings(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/borrowings/").status_code, 401)

    def test_authenticated_empty_list(self):
        response = self.client.get("/api/borrowings/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data["count"], 0)

    def test_detail_has_book_information_and_dates(self):
        borrowing = self.create_borrowing()
        response = self.client.get(f"/api/borrowings/{borrowing.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["book"]["title"], "Python")
        self.assertEqual(response.data["book"]["daily_fee"], "1.25")
        self.assertEqual(response.data["user"], self.user.pk)
        self.assertEqual(response.data["borrow_date"], self.today.isoformat())
        self.assertIsNone(response.data["actual_return_date"])

    def test_list_includes_borrowing(self):
        borrowing = self.create_borrowing()
        response = self.client.get("/api/borrowings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["id"], borrowing.pk)

    def test_borrowings_cannot_be_edited_or_deleted(self):
        borrowing = self.create_borrowing()
        url = f"/api/borrowings/{borrowing.pk}/"
        for method in (self.client.put, self.client.patch, self.client.delete):
            self.assertEqual(method(url, {}).status_code, 405)

    def test_invalid_date_order_is_rejected_by_database(self):
        model = self.borrowing_model()
        for dates in (
            {"expected_return_date": self.today - timedelta(days=1)},
            {"actual_return_date": self.today - timedelta(days=1)},
        ):
            with self.subTest(dates=dates), self.assertRaises(IntegrityError):
                with transaction.atomic():
                    values = {
                        "user": self.user,
                        "book": self.book,
                        "expected_return_date": self.today + timedelta(days=7),
                    }
                    model.objects.create(**dict(values, **dates))

    def test_borrowed_book_deletion_preserves_history(self):
        self.create_borrowing()
        self.user.is_staff = True
        self.user.save()
        response = self.client.delete(f"/api/books/{self.book.pk}/")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Book.objects.filter(pk=self.book.pk).exists())

    def test_browsable_list_and_detail_render(self):
        borrowing = self.create_borrowing()
        for path in ("/api/borrowings/", f"/api/borrowings/{borrowing.pk}/"):
            self.assertEqual(
                self.client.get(path, HTTP_ACCEPT="text/html").status_code, 200
            )
