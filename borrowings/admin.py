from django.contrib import admin

from borrowings.models import Borrowing


@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "book",
        "user",
        "borrow_date",
        "expected_return_date",
        "actual_return_date",
    )
    list_filter = ("borrow_date", "actual_return_date")
    list_select_related = ("book", "user")
    search_fields = ("book__title", "user__email")

    # All stock changes must go through the transactional API operations.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
