
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class User(AbstractUser):
    class Role(models.TextChoices):
        PRODUCT_ADMIN = "product_admin", "Product Admin"
        SUPER_ADMIN = "super_admin", "Super Admin"
        ADMIN = "admin", "Admin"
        TEACHER = "teacher", "Teacher"
        STUDENT = "student", "Student"
        PARENT = "parent", "Parent"

    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.STUDENT,
    )

    def __str__(self):
        return f"{self.email} ({self.role})"


class Batch(models.Model):
    name = models.CharField(max_length=150, unique=True)
    course = models.CharField(max_length=150)
    status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("inactive", "Inactive"),
            ("completed", "Completed"),
        ],
        default="active",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.course}"


class Subject(models.Model):
    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=150)
    course = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.title}"

class PasswordSetupInvitation(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_setup_invitation",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Password setup invitation for user {self.user_id}"

