
from django.urls import path

from .views import (
    LoginView,
    MeView,
    SuperAdminCheckView,
    UserListCreateView,
    UserDetailView,
    UserDisableView,
    UserReactivateView,
    UserResendInviteView,
)

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/me/", MeView.as_view(), name="me"),
    path(
        "auth/token/refresh/",
        __import__(
            "rest_framework_simplejwt.views",
            fromlist=["TokenRefreshView"],
        ).TokenRefreshView.as_view(),
        name="token_refresh",
    ),
    path(
        "auth/super-admin-check/",
        SuperAdminCheckView.as_view(),
        name="super_admin_check",
    ),
    path("users/", UserListCreateView.as_view(), name="user_list_create"),
    path("users/<int:user_id>/", UserDetailView.as_view(), name="user_detail"),
    path(
        "users/<int:user_id>/disable/",
        UserDisableView.as_view(),
        name="user_disable",
    ),
    path(
        "users/<int:user_id>/reactivate/",
        UserReactivateView.as_view(),
        name="user_reactivate",
    ),
    path(
        "users/<int:user_id>/resend-invite/",
        UserResendInviteView.as_view(),
        name="user_resend_invite",
    ),
]
