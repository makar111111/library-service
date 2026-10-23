from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from books.models import Book
from books.serializers import BookSerializer
from borrowings.models import Borrowing
from borrowings.services import create_borrowing, return_borrowing


class BookEditInventoryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "reader@example.com", "password"
        )
        self.book = Book.objects.create(
            title="Before",
            author="A. Writer",
            cover="SOFT",
            inventory=1,
            daily_fee="1.25",
        )
        self.return_date = timezone.localdate() + timedelta(days=7)

    def test_stale_title_edit_does_not_restore_a_borrowed_copy(self):
        serializer = BookSerializer(self.book, data={"title": "After"}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        create_borrowing(
            book=Book.objects.get(pk=self.book.pk),
            user=self.user,
            expected_return_date=self.return_date,
        )
        serializer.save()
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 0)
        self.assertEqual(self.book.title, "After")
        self.assertEqual(serializer.data["inventory"], 0)

    def test_stale_author_edit_does_not_erase_a_returned_copy(self):
        self.book.inventory = 0
        self.book.save()
        borrowing = Borrowing.objects.create(
            book=self.book, user=self.user, expected_return_date=self.return_date
        )
        serializer = BookSerializer(
            self.book, data={"author": "New Author"}, partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        return_borrowing(borrowing)
        serializer.save()
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 1)
        self.assertEqual(self.book.author, "New Author")
