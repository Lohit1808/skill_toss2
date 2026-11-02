
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import (
    User, 
    Batch, 
    Subject,
    Institution,
    Branch,
)    


class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(read_only=True)
    institution = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "name",
            "role",
            "is_active",
            "institution",
        ]

    def get_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_institution(self, obj):
        return None


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )


class ManagedUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    institution = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(
        source="date_joined",
        read_only=True,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "email",
            "role",
            "institution",
            "is_active",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "is_active", "status", "created_at"]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_institution(self, obj):
        return None

    def get_status(self, obj):
        if not obj.is_active:
            return "disabled"
        if not obj.has_usable_password():
            return "pending_setup"
        return "active"


class ManagedUserCreateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=User.Role.choices)
    batch_id = serializers.IntegerField(required=False, allow_null=True)
    subject_id = serializers.IntegerField(required=False, allow_null=True)
    student_id = serializers.CharField(required=False, allow_blank=True)
    relationship = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return value.lower()

    def create(self, validated_data):
        full_name = validated_data["full_name"].strip()
        parts = full_name.split(maxsplit=1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

        email = validated_data["email"]
        username_base = email.split("@", 1)[0]
        username = username_base
        suffix = 1

        while User.objects.filter(username=username).exists():
            username = f"{username_base}{suffix}"
            suffix += 1

        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=validated_data["role"],
            is_active=True,
        )

        # No invitation email is sent by this implementation.
        # Set an unusable password until password setup is implemented.
        user.set_unusable_password()
        user.save()
        return user


class ManagedUserUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False)
    role = serializers.ChoiceField(
        choices=User.Role.choices,
        required=False,
    )

    def validate_email(self, value):
        user = self.instance
        if User.objects.filter(email__iexact=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return value.lower()

    def update(self, instance, validated_data):
        if "full_name" in validated_data:
            full_name = validated_data["full_name"].strip()
            parts = full_name.split(maxsplit=1)
            instance.first_name = parts[0] if parts else ""
            instance.last_name = parts[1] if len(parts) > 1 else ""

        if "email" in validated_data:
            instance.email = validated_data["email"]

        if "role" in validated_data:
            instance.role = validated_data["role"]

        instance.save()
        return instance

class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = ["id", "name", "course", "status"]


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "code", "title", "course", "is_active"]
        

class InstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = [
            "id",
            "name",
            "code",
            "email",
            "phone",
            "address",
            "city",
            "state",
            "country",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class BranchSerializer(serializers.ModelSerializer):
    institution_name = serializers.CharField(
        source="institution.name",
        read_only=True,
        default=None,
    )
    admin_name = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = [
            "id",
            "institution",
            "institution_name",
            "name",
            "code",
            "email",
            "phone",
            "address",
            "city",
            "state",
            "country",
            "admin",
            "admin_name",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "institution_name",
            "admin_name",
            "created_at",
            "updated_at",
        ]

    def get_admin_name(self, obj):
        if obj.admin:
            return obj.admin.get_full_name() or obj.admin.username
        return None

    def validate_admin(self, value):
        if value is not None and value.role != User.Role.ADMIN:
            raise serializers.ValidationError(
                "The assigned user must have the Admin role."
            )
        return value
