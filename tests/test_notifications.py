from datetime import timedelta
from importlib import import_module
from unittest.mock import patch

import requests
from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from books.models import Book
from borrowings.models import Borrowing


class NotificationTests(APITestCase):
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
        self.payload = {
            "book": self.book.pk,
            "expected_return_date": (
                timezone.localdate() + timedelta(days=7)
            ).isoformat(),
        }

    def model(self):
        self.assertTrue(
            apps.is_installed("notifications"), "Notifications must be installed."
        )
        return apps.get_model("notifications", "BorrowingNotification")

    def module(self, name):
        self.model()
        return import_module(f"notifications.{name}")

    def create_notification(self):
        model = self.model()
        response = self.client.post("/api/borrowings/", self.payload)
        self.assertEqual(response.status_code, 201, response.content)
        return model.objects.get(borrowing_id=response.data["id"])

    def test_borrowing_creates_persistent_unsent_notification(self):
        notification = self.create_notification()
        self.assertIsNone(notification.sent_at)
        self.assertEqual(notification.borrowing.user, self.user)

    @override_settings(TELEGRAM_BOT_TOKEN="test-token", TELEGRAM_CHAT_ID="test-chat")
    def test_enqueue_happens_after_commit(self):
        self.model()
        with patch("notifications.services.deliver_notification.delay") as delay:
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                notification = self.create_notification()
            delay.assert_not_called()
            self.assertEqual(len(callbacks), 1)
            callbacks[0]()
            delay.assert_called_once_with(notification.pk)

    def test_failed_borrowing_does_not_create_or_queue_notification(self):
        model = self.model()
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            response = self.client.post(
                "/api/borrowings/",
                dict(self.payload, expected_return_date="2000-01-01"),
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(model.objects.count(), 0)
        self.assertEqual(callbacks, [])

    def test_outbox_failure_rolls_back_borrowing_and_stock(self):
        model = self.model()
        with patch.object(
            model.objects, "create", side_effect=RuntimeError("DB failure")
        ):
            with self.assertRaises(RuntimeError):
                self.client.post("/api/borrowings/", self.payload)
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 1)
        self.assertEqual(Borrowing.objects.count(), 0)

    @override_settings(TELEGRAM_BOT_TOKEN="", TELEGRAM_CHAT_ID="")
    def test_missing_configuration_keeps_pending_without_network(self):
        tasks = self.module("tasks")
        notification = self.create_notification()
        with patch("notifications.telegram.requests.post") as post:
            self.assertFalse(tasks.deliver_notification.run(notification.pk))
            post.assert_not_called()
        notification.refresh_from_db()
        self.assertIsNone(notification.sent_at)

    @override_settings(TELEGRAM_BOT_TOKEN="test-token", TELEGRAM_CHAT_ID="test-chat")
    def test_telegram_payload_and_successful_delivery_once(self):
        tasks = self.module("tasks")
        notification = self.create_notification()
        with patch("notifications.telegram.requests.post") as post:
            post.return_value.json.return_value = {"ok": True}
            self.assertTrue(tasks.deliver_notification.run(notification.pk))
            self.assertFalse(tasks.deliver_notification.run(notification.pk))
            post.assert_called_once()
            args, kwargs = post.call_args
            self.assertEqual(kwargs["json"]["chat_id"], "test-chat")
            self.assertIn("Python", kwargs["json"]["text"])
            self.assertIn(self.user.email, kwargs["json"]["text"])
            self.assertIn(self.payload["expected_return_date"], kwargs["json"]["text"])
            self.assertEqual(kwargs["timeout"], 10)
            self.assertTrue(args[0].endswith("/sendMessage"))
        notification.refresh_from_db()
        self.assertIsNotNone(notification.sent_at)

    @override_settings(
        TELEGRAM_BOT_TOKEN="private-test-token", TELEGRAM_CHAT_ID="test-chat"
    )
    def test_network_and_api_failures_are_sanitized(self):
        telegram = self.module("telegram")
        for error in (
            requests.Timeout("private-test-token in URL"),
            requests.HTTPError("private-test-token in URL"),
            ValueError("private-test-token in response"),
        ):
            with self.subTest(error=type(error).__name__):
                with patch("notifications.telegram.requests.post", side_effect=error):
                    with self.assertRaises(telegram.TelegramDeliveryError) as raised:
                        telegram.send_message("Test")
                self.assertNotIn("private-test-token", str(raised.exception))
        with patch("notifications.telegram.requests.post") as post:
            post.return_value.json.return_value = {
                "ok": False,
                "description": "private-test-token",
            }
            with self.assertRaises(telegram.TelegramDeliveryError) as raised:
                telegram.send_message("Test")
        self.assertNotIn("private-test-token", str(raised.exception))

    @override_settings(TELEGRAM_BOT_TOKEN="test-token", TELEGRAM_CHAT_ID="test-chat")
    def test_broker_failure_keeps_row_for_recovery_without_failing_borrowing(self):
        self.model()
        from kombu.exceptions import OperationalError

        with patch(
            "notifications.services.deliver_notification.delay",
            side_effect=OperationalError("private URL"),
        ):
            with self.assertLogs("notifications.services", level="WARNING") as logs:
                with self.captureOnCommitCallbacks(execute=True):
                    notification = self.create_notification()
        self.assertNotIn("private URL", " ".join(logs.output))
        self.assertIsNone(notification.sent_at)

    @override_settings(TELEGRAM_BOT_TOKEN="test-token", TELEGRAM_CHAT_ID="test-chat")
    def test_retry_pending_enqueues_unsent_rows(self):
        tasks = self.module("tasks")
        notification = self.create_notification()
        with patch("notifications.tasks.deliver_notification.delay") as delay:
            self.assertEqual(tasks.retry_pending_notifications.run(), 1)
            delay.assert_called_once_with(notification.pk)

    def test_unknown_notification_does_not_send(self):
        tasks = self.module("tasks")
        with patch("notifications.telegram.requests.post") as post:
            self.assertFalse(tasks.deliver_notification.run(999999))
            post.assert_not_called()
