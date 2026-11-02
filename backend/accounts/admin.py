
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    User,
    Institution,
    Branch,
    Batch,
    Subject,
    PasswordSetupInvitation,
)


# --------------------------------------------------
# USER ADMIN
# --------------------------------------------------

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "role",
        "is_staff",
        "is_active",
        "is_superuser",
    )

    list_filter = (
        "role",
        "is_staff",
        "is_active",
        "is_superuser",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
    )

    fieldsets = BaseUserAdmin.fieldsets + (
        ("SkillToss Access", {"fields": ("role",)}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("SkillToss Access", {"fields": ("email", "role")}),
    )


# --------------------------------------------------
# INSTITUTION ADMIN
# --------------------------------------------------

@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "code",
        "email",
        "phone",
        "city",
        "state",
        "status",
    )
    search_fields = ("name", "code", "email", "city")
    list_filter = ("status", "state", "country")


# --------------------------------------------------
# BRANCH ADMIN
# --------------------------------------------------

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "code",
        "institution",
        "city",
        "status",
    )
    search_fields = ("name", "code", "city", "institution__name")
    list_filter = ("status", "city")


# --------------------------------------------------
# BATCH ADMIN
# --------------------------------------------------

@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ("id", "__str__")
    search_fields = ("id",)


# --------------------------------------------------
# SUBJECT ADMIN
# --------------------------------------------------

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("id", "__str__")
    search_fields = ("id",)


# --------------------------------------------------
# PASSWORD INVITATION ADMIN
# --------------------------------------------------

@admin.register(PasswordSetupInvitation)
class PasswordSetupInvitationAdmin(admin.ModelAdmin):
    list_display = ("id", "__str__")
    search_fields = ("id",)
