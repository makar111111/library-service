from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from books.models import Book
from borrowings.models import Borrowing


@skipUnless(
    connection.vendor == "postgresql", "Concurrency requires PostgreSQL (see Compose)."
)
class ConcurrentInventoryTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "reader@example.com", "password"
        )
        self.book = Book.objects.create(
            title="Python",
            author="A. Writer",
            cover="SOFT",
            inventory=1,
            daily_fee="1.00",
        )

    def parallel_posts(self, path, payload=None):
        barrier = Barrier(5)

        def post(_):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(self.user)
                barrier.wait(timeout=10)
                return client.post(path, payload or {}, format="json").status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=5) as executor:
            return sorted(executor.map(post, range(5)))

    def test_five_readers_cannot_borrow_the_same_last_copy(self):
        statuses = self.parallel_posts(
            "/api/borrowings/",
            {
                "book": self.book.pk,
                "expected_return_date": (
                    timezone.localdate() + timedelta(days=7)
                ).isoformat(),
            },
        )
        self.assertEqual(statuses, [201, 400, 400, 400, 400])
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 0)
        self.assertEqual(Borrowing.objects.count(), 1)

    def test_five_simultaneous_returns_restore_only_one_copy(self):
        self.book.inventory = 0
        self.book.save()
        borrowing = Borrowing.objects.create(
            book=self.book,
            user=self.user,
            expected_return_date=timezone.localdate() + timedelta(days=7),
        )
        statuses = self.parallel_posts(f"/api/borrowings/{borrowing.pk}/return/")
        self.assertEqual(statuses, [200, 400, 400, 400, 400])
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 1)
