from django.urls import path

from . import views_html

urlpatterns = [
    path("profile/", views_html.ProfileView.as_view(), name="profile"),
    path("users/", views_html.UserListView.as_view(), name="user-list"),
    path(
        "users/<int:pk>/edit/",
        views_html.UserUpdateRoleView.as_view(),
        name="user-edit",
    ),
]
