import hashlib

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import authenticate, get_user_model
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .invitation_service import create_password_setup_invitation
from .permissions import IsSuperAdmin
from .models import User
from .models import PasswordSetupInvitation

from .models import Batch, Subject
from .permissions import IsSuperAdmin
from .serializers import (
    LoginSerializer,
    UserSerializer,
    ManagedUserSerializer,
    ManagedUserCreateSerializer,
    ManagedUserUpdateSerializer,
    BatchSerializer,
    SubjectSerializer,
)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        User = get_user_model()
        user_record = User.objects.filter(email__iexact=email).first()

        if user_record is None:
            return Response(
                {"detail": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = authenticate(
            request,
            username=user_record.get_username(),
            password=password,
        )

        if user is None or not user.is_active:
            return Response(
                {"detail": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        })


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class SuperAdminCheckView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        return Response({
            "detail": "Super Admin access confirmed."
        })


class UserListCreateView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        users = get_user_model().objects.all().order_by("-date_joined")

        search = request.query_params.get("search", "").strip()
        role = request.query_params.get("role", "").strip()

        if search:
            from django.db.models import Q
            users = users.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(username__icontains=search)
                | Q(email__icontains=search)
            )

        if role:
            users = users.filter(role=role)

        return Response(ManagedUserSerializer(users, many=True).data)


    def post(self, request):
        serializer = ManagedUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        try:
            create_password_setup_invitation(user)
        except Exception:
            # Keep the account, but report that the invitation failed.
            return Response(
                {
                    **ManagedUserSerializer(user).data,
                    "invitation_sent": False,
                    "detail": (
                        "The account was created, but the invitation email "
                        "could not be sent. Please resend the invitation."
                    ),
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                **ManagedUserSerializer(user).data,
                "invitation_sent": True,
                "detail": "User created and invitation email sent.",
            },
            status=status.HTTP_201_CREATED,
        )



class UserDetailView(APIView):
    permission_classes = [IsSuperAdmin]

    def patch(self, request, user_id):
        User = get_user_model()
        user = get_object_or_404(User, pk=user_id)

        if user.pk == request.user.pk and request.data.get("role") not in (
            None,
            "super_admin",
        ):
            return Response(
                {"detail": "You cannot remove your own Super Admin role."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ManagedUserUpdateSerializer(
            user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(ManagedUserSerializer(user).data)

        
    def delete(self, request, user_id):
        User = get_user_model()
        user = get_object_or_404(User, pk=user_id)

        if user.pk == request.user.pk:
            return Response(
                {"detail": "You cannot delete your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.role == "super_admin":
            return Response(
                {"detail": "Deleting a Super Admin account is not allowed through this endpoint."},
                status=status.HTTP_403_FORBIDDEN,
            )

        user.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)



class UserDisableView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request, user_id):
        User = get_user_model()
        user = get_object_or_404(User, pk=user_id)

        if user.pk == request.user.pk:
            return Response(
                {"detail": "You cannot disable your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = False
        user.save(update_fields=["is_active"])

        return Response(ManagedUserSerializer(user).data)


class UserReactivateView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request, user_id):
        User = get_user_model()
        user = get_object_or_404(User, pk=user_id)

        user.is_active = True
        user.save(update_fields=["is_active"])

        return Response(ManagedUserSerializer(user).data)


class UserResendInviteView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not user.is_active:
            return Response(
                {"detail": "Cannot invite a disabled account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.has_usable_password():
            return Response(
                {
                    "detail": (
                        "This user already has a password. "
                        "Use the password-reset flow instead."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        try:
            create_password_setup_invitation(user)
        except Exception:
            # Do not return SMTP credentials or internal error details.
            return Response(
                {
                    "detail": (
                        "Invitation email could not be sent. "
                        "Check the server email configuration and logs."
                    ),
                    "invitation_sent": False,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "detail": "Invitation email sent successfully.",
                "invitation_sent": True,
            },
            status=status.HTTP_200_OK,
        )


class BatchListView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        batches = Batch.objects.all().order_by("name")
        return Response(BatchSerializer(batches, many=True).data)


class SubjectListView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        subjects = Subject.objects.all().order_by("title")
        return Response(SubjectSerializer(subjects, many=True).data)        


class PasswordSetupView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        token = request.data.get("token")
        password = request.data.get("password")

        if not isinstance(token, str) or not token:
            return Response(
                {"detail": "A valid invitation token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(password, str) or not password:
            return Response(
                {"detail": "Password is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token_hash = hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

        with transaction.atomic():
            try:
                invitation = (
                    PasswordSetupInvitation.objects
                    .select_for_update()
                    .select_related("user")
                    .get(token_hash=token_hash)
                )
            except PasswordSetupInvitation.DoesNotExist:
                return Response(
                    {"detail": "Invalid invitation link."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if invitation.used_at is not None:
                return Response(
                    {"detail": "This invitation has already been used."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if timezone.now() >= invitation.expires_at:
                return Response(
                    {"detail": "This invitation has expired. Request a new one."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user = invitation.user

            if not user.is_active:
                return Response(
                    {"detail": "This account is disabled."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if user.has_usable_password():
                return Response(
                    {
                        "detail": (
                            "This account already has a password. "
                            "Please use the password-reset process."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            try:
                validate_password(password, user=user)
            except DjangoValidationError as exc:
                return Response(
                    {"password": list(exc.messages)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user.set_password(password)
            user.save(update_fields=["password"])

            invitation.used_at = timezone.now()
            invitation.save(update_fields=["used_at"])

        return Response(
            {
                "detail": (
                    "Password set successfully. You can now sign in."
                )
            },
            status=status.HTTP_200_OK,
        )

