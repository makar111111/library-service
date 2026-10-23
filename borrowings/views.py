from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from borrowings.models import Borrowing
from borrowings.services import return_borrowing
from borrowings.serializers import (
    BorrowingCreateSerializer,
    BorrowingFilterSerializer,
    BorrowingReadSerializer,
)


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                "is_active", bool, description="true: not returned; false: returned."
            ),
            OpenApiParameter(
                "user_id",
                int,
                description="Staff only. Customers always see their own records.",
            ),
        ]
    )
)
class BorrowingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Borrowing.objects.select_related("book", "user")
    serializer_class = BorrowingReadSerializer
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.action == "create":
            return BorrowingCreateSerializer
        return BorrowingReadSerializer

    @extend_schema(
        request=BorrowingCreateSerializer, responses={201: BorrowingReadSerializer}
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        borrowing = serializer.save(user=request.user)
        return Response(
            BorrowingReadSerializer(
                borrowing, context=self.get_serializer_context()
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=None,
        responses=BorrowingReadSerializer,
        description=(
            "Return your book once. Staff can return any user's borrowing. "
            "Sets today's date and atomically restores one copy. "
            "Repeat returns get 400."
        ),
    )
    @action(detail=True, methods=["post"], url_path="return", url_name="return")
    def return_book(self, request, pk=None):
        borrowing = return_borrowing(self.get_object())
        return Response(self.get_serializer(borrowing).data)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        queryset = self.queryset.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        if self.action == "list":
            data = self.request.query_params.dict()
            if not self.request.user.is_staff:
                data.pop("user_id", None)
            filters = BorrowingFilterSerializer(data=data)
            filters.is_valid(raise_exception=True)
            values = filters.validated_data
            if "is_active" in values:
                queryset = queryset.filter(
                    actual_return_date__isnull=values["is_active"]
                )
            if "user_id" in values:
                queryset = queryset.filter(user_id=values["user_id"])
        return queryset
