
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import (
    LoginView,
    MeView,
    SuperAdminCheckView,
    UserListCreateView,
    UserDetailView,
    UserDisableView,
    UserReactivateView,
    UserResendInviteView,
    BatchListView,
    SubjectListView,
    PasswordSetupView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("accounts.urls")),

    path("api/batches/", BatchListView.as_view(), name="batch_list"),
    path("api/subjects/", SubjectListView.as_view(), name="subject_list"),
    
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/me/", MeView.as_view(), name="me"),
    path(
        "api/auth/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),

    path(
    "api/auth/set-password/",
    PasswordSetupView.as_view(),
    name="set_password",
    ),

    path(
        "api/auth/super-admin-check/",
        SuperAdminCheckView.as_view(),
        name="super_admin_check",
    ),

    path("api/users/", UserListCreateView.as_view(), name="user_list_create"),
    path(
        "api/users/<int:user_id>/",
        UserDetailView.as_view(),
        name="user_detail",
    ),
    path(
        "api/users/<int:user_id>/disable/",
        UserDisableView.as_view(),
        name="user_disable",
    ),
    path(
        "api/users/<int:user_id>/reactivate/",
        UserReactivateView.as_view(),
        name="user_reactivate",
    ),
    path(
        "api/users/<int:user_id>/resend-invite/",
        UserResendInviteView.as_view(),
        name="user_resend_invite",
    ),
]