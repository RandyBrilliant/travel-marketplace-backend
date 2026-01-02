"""
Email tasks for async email sending using Celery.
"""
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from account.models import CustomUser


@shared_task(bind=True, max_retries=3)
def send_email_verification(self, user_id):
    """
    Send email verification link to user.
    
    Args:
        user_id: ID of the user to send verification email to
    """
    try:
        user = CustomUser.objects.get(pk=user_id)
        
        # Generate verification token (you'll need to implement this)
        # For now, using a simple approach - you might want to use django-allauth or similar
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{uid}/{token}/"
        
        subject = "Verify your email address"
        html_message = render_to_string('account/email_verification.html', {
            'user': user,
            'verification_url': verification_url,
            'FRONTEND_URL': settings.FRONTEND_URL,
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return f"Verification email sent to {user.email}"
        
    except CustomUser.DoesNotExist:
        return f"User with ID {user_id} does not exist"
    except Exception as exc:
        # Retry the task with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_welcome_email(self, user_id):
    """
    Send welcome email to newly registered user.
    
    Args:
        user_id: ID of the user to send welcome email to
    """
    try:
        user = CustomUser.objects.get(pk=user_id)
        
        # Get profile name based on role
        profile_name = user.email
        if user.role == 'SUPPLIER' and hasattr(user, 'supplier_profile'):
            profile_name = user.supplier_profile.company_name
        elif user.role == 'RESELLER' and hasattr(user, 'reseller_profile'):
            profile_name = user.reseller_profile.full_name
        elif user.role == 'STAFF' and hasattr(user, 'staff_profile'):
            profile_name = user.staff_profile.full_name
        
        subject = "Welcome to Travel Marketplace!"
        html_message = render_to_string('account/welcome_email.html', {
            'user': user,
            'profile_name': profile_name,
            'FRONTEND_URL': settings.FRONTEND_URL,
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return f"Welcome email sent to {user.email}"
        
    except CustomUser.DoesNotExist:
        return f"User with ID {user_id} does not exist"
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_password_reset_email(self, user_id, reset_token):
    """
    Send password reset email.
    
    Args:
        user_id: ID of the user requesting password reset
        reset_token: Token for password reset (should be uidb64/token format)
    """
    try:
        user = CustomUser.objects.get(pk=user_id)
        
        # reset_token should already be in format: uidb64/token
        # If it's just a token, you'll need to encode the user ID
        if '/' not in reset_token:
            from django.utils.encoding import force_bytes
            from django.utils.http import urlsafe_base64_encode
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{reset_token}/"
        else:
            reset_url = f"{settings.FRONTEND_URL}/reset-password/{reset_token}/"
        
        subject = "Reset your password"
        html_message = render_to_string('account/password_reset.html', {
            'user': user,
            'reset_url': reset_url,
            'FRONTEND_URL': settings.FRONTEND_URL,
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return f"Password reset email sent to {user.email}"
        
    except CustomUser.DoesNotExist:
        return f"User with ID {user_id} does not exist"
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

