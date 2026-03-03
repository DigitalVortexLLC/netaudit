from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import UserViewSet

router = DefaultRouter()
router.register("auth/users", UserViewSet, basename="user")

urlpatterns = [
    path("auth/", include("dj_rest_auth.urls")),
    path("auth/register/", include("dj_rest_auth.registration.urls")),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
] + router.urls
