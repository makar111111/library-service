from django.contrib import admin

from notifications.models import BorrowingNotification


@admin.register(BorrowingNotification)
class BorrowingNotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "borrowing", "created_at", "sent_at")
    list_filter = ("sent_at",)
    readonly_fields = ("borrowing", "created_at", "sent_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
