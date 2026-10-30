
import hashlib
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import PasswordSetupInvitation


INVITATION_VALID_HOURS = 24


def create_password_setup_invitation(user):
    """
    Create a new password-setup invitation and email its link.
    Only the token hash is persisted in the database.
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    now = timezone.now()

    # Invalidate any previous invitation for this user.
    PasswordSetupInvitation.objects.filter(user=user).delete()

    invitation = PasswordSetupInvitation.objects.create(
        user=user,
        token_hash=token_hash,
        expires_at=now + timedelta(hours=INVITATION_VALID_HOURS),
    )

    setup_url = (
        f"{settings.FRONTEND_URL.rstrip('/')}/set-password?"
        f"{urlencode({'token': raw_token})}"
    )

    subject = "Set up your SkillToss account"
    message = (
        f"Hello {user.get_full_name() or user.username},\n\n"
        "A SkillToss administrator has invited you to set up your account.\n\n"
        f"Use this link to choose your password:\n{setup_url}\n\n"
        f"This link expires in {INVITATION_VALID_HOURS} hours and can be used once.\n"
        "If you were not expecting this invitation, you can ignore this email.\n"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        # Avoid leaving an active invitation when delivery fails.
        invitation.delete()
        raise

    return invitation
