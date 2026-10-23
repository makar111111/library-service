from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from books.models import Book
from borrowings.models import Borrowing


class BorrowingFilterTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user("reader@example.com", "password")
        self.other = user_model.objects.create_user("other@example.com", "password")
        self.admin = user_model.objects.create_user(
            "admin@example.com", "password", is_staff=True
        )
        self.client.force_authenticate(self.user)
        book = Book.objects.create(
            title="Python",
            author="A. Writer",
            cover="SOFT",
            inventory=10,
            daily_fee="1.00",
        )
        today = timezone.localdate()
        values = {"book": book, "expected_return_date": today + timedelta(days=7)}
        self.active = Borrowing.objects.create(user=self.user, **values)
        self.returned = Borrowing.objects.create(
            user=self.user, actual_return_date=today, **values
        )
        self.other_borrowing = Borrowing.objects.create(user=self.other, **values)

    def ids(self, **params):
        response = self.client.get("/api/borrowings/", params)
        self.assertEqual(response.status_code, 200, response.content)
        return {row["id"] for row in response.data["results"]}

    def test_customer_sees_only_own_borrowings(self):
        self.assertEqual(self.ids(), {self.active.pk, self.returned.pk})

    def test_customer_cannot_read_another_customers_detail(self):
        response = self.client.get(f"/api/borrowings/{self.other_borrowing.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_customer_cannot_override_ownership_with_user_id(self):
        self.assertEqual(
            self.ids(user_id=self.other.pk), {self.active.pk, self.returned.pk}
        )

    def test_active_and_returned_filters(self):
        for value in ("true", "1"):
            self.assertEqual(self.ids(is_active=value), {self.active.pk})
        for value in ("false", "0"):
            self.assertEqual(self.ids(is_active=value), {self.returned.pk})

    def test_staff_sees_everyone(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(
            self.ids(), {self.active.pk, self.returned.pk, self.other_borrowing.pk}
        )

    def test_staff_filters_user_and_active_together(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(
            self.ids(user_id=self.user.pk), {self.active.pk, self.returned.pk}
        )
        self.assertEqual(
            self.ids(user_id=self.user.pk, is_active="true"), {self.active.pk}
        )

    def test_invalid_filters_are_validation_errors(self):
        self.assertEqual(
            self.client.get("/api/borrowings/?is_active=maybe").status_code, 400
        )
        self.client.force_authenticate(self.admin)
        for value in ("abc", "-1", "0"):
            self.assertEqual(
                self.client.get("/api/borrowings/", {"user_id": value}).status_code, 400
            )
