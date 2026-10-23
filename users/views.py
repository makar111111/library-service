from rest_framework import generics
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from users.serializers import EmailTokenObtainPairSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = (AllowAny,)

    @extend_schema(
        responses=inline_serializer(
            name="RegistrationInstructions", fields={"detail": serializers.CharField()}
        )
    )
    def get(self, request, *args, **kwargs):
        return Response({"detail": "Register with email and password using POST."})


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


@extend_schema(
    responses=inline_serializer(
        name="TokenPair",
        fields={"access": serializers.CharField(), "refresh": serializers.CharField()},
    )
)
class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
