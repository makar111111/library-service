from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from users.views import EmailTokenObtainPairView, ProfileView, RegisterView

app_name = "users"
urlpatterns = [
    path("", RegisterView.as_view(), name="register"),
    path("token/", EmailTokenObtainPairView.as_view(), name="token"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", ProfileView.as_view(), name="me"),
]
