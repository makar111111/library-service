from django.db import models


class BorrowingNotification(models.Model):
    borrowing = models.OneToOneField(
        "borrowings.Borrowing", on_delete=models.CASCADE, related_name="notification"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ("id",)

    def __str__(self):
        return f"Notification for borrowing #{self.borrowing_id}"
