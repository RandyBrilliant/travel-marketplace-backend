"""
Email tasks for async email sending using Celery.
"""
import logging
import socket
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail, get_connection
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from account.models import CustomUser

logger = logging.getLogger(__name__)


def send_email_with_backend_detection(subject, plain_message, html_message, recipient_list, email_type="email"):
    """
    Helper function to send emails with automatic backend detection.
    Handles both SMTP (with timeout) and HTTP API backends (anymail).
    
    Args:
        subject: Email subject line
        plain_message: Plain text version of the email
        html_message: HTML version of the email
        recipient_list: List of recipient email addresses
        email_type: Type of email being sent (for logging)
    """
    backend = settings.EMAIL_BACKEND
    recipient = recipient_list[0] if recipient_list else "unknown"
    logger.info(f"Attempting to send {email_type} to {recipient} using backend: {backend}")
    
    # Only apply socket timeout for SMTP backend
    if 'smtp' in backend.lower():
        logger.info("Using SMTP backend - applying connection timeout")
        timeout = getattr(settings, 'EMAIL_TIMEOUT', 30)
        old_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(timeout)
            
            connection = get_connection(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                use_tls=settings.EMAIL_USE_TLS,
                timeout=timeout,
            )
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False,
                connection=connection,
            )
        except socket.timeout:
            error_msg = f"SMTP connection timeout after {timeout} seconds when sending to {recipient}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except socket.error as sock_err:
            error_msg = f"SMTP socket error when sending to {recipient}: {str(sock_err)}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)
        finally:
            socket.setdefaulttimeout(old_timeout)
    else:
        # HTTP API backend (anymail) - simpler and more reliable
        logger.info("Using HTTP API backend (anymail) - no timeout handling needed")
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
    
    logger.info(f"{email_type.capitalize()} sent successfully to {recipient}")
    return f"{email_type.capitalize()} sent successfully to {recipient}"


@shared_task(bind=True, max_retries=3)
def send_email_verification(self, user_id):
    """
    Send email verification link to user.
    
    Args:
        user_id: ID of the user to send verification email to
    """
    logger.info(f"Starting email verification task for user_id={user_id}")
    
    try:
        # Validate email configuration
        backend = settings.EMAIL_BACKEND
        if 'anymail' in backend.lower():
            # HTTP API backend - check for API key
            mailgun_api_key = getattr(settings, 'MAILGUN_API_KEY', '') or settings.ANYMAIL.get('MAILGUN_API_KEY', '')
            if not mailgun_api_key:
                error_msg = "Mailgun API key not configured. Set MAILGUN_API_KEY in .env"
                logger.error(error_msg)
                raise ValueError(error_msg)
            logger.info(f"Email config check passed. Using Mailgun HTTP API")
        else:
            # SMTP backend - check for SMTP credentials
            if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
                error_msg = "Mailgun SMTP credentials not configured. EMAIL_HOST_USER or EMAIL_HOST_PASSWORD is missing."
                logger.error(error_msg)
                raise ValueError(error_msg)
            logger.info(f"Email config check passed. Using SMTP: {settings.EMAIL_HOST}")
        
        if not settings.DEFAULT_FROM_EMAIL:
            error_msg = "DEFAULT_FROM_EMAIL is not configured."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        user = CustomUser.objects.get(pk=user_id)
        logger.info(f"Found user: {user.email}")
        
        # Generate verification token (you'll need to implement this)
        # For now, using a simple approach - you might want to use django-allauth or similar
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{uid}/{token}/"
        logger.info(f"Generated verification URL for user {user.email}")
        
        subject = "Verify your email address"
        html_message = render_to_string('account/email_verification.html', {
            'user': user,
            'verification_url': verification_url,
            'FRONTEND_URL': settings.FRONTEND_URL,
        })
        plain_message = strip_tags(html_message)
        
        # Send email using helper function
        return send_email_with_backend_detection(
            subject=subject,
            plain_message=plain_message,
            html_message=html_message,
            recipient_list=[user.email],
            email_type="verification email"
        )
        
    except CustomUser.DoesNotExist:
        error_msg = f"User with ID {user_id} does not exist"
        logger.error(error_msg)
        return error_msg
    except Exception as exc:
        error_msg = f"Error sending verification email to user_id={user_id}: {str(exc)}"
        logger.error(error_msg, exc_info=True)
        
        # Retry the task with exponential backoff
        if self.request.retries < self.max_retries:
            logger.warning(f"Retrying email verification task (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        else:
            logger.error(f"Max retries reached for email verification task. Giving up.")
            raise


@shared_task(bind=True, max_retries=3)
def send_welcome_email(self, user_id):
    """
    Send welcome email to newly registered user.
    
    Args:
        user_id: ID of the user to send welcome email to
    """
    logger.info(f"Starting welcome email task for user_id={user_id}")
    
    try:
        # Validate email configuration (basic check)
        if not settings.DEFAULT_FROM_EMAIL:
            error_msg = "DEFAULT_FROM_EMAIL is not configured."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        user = CustomUser.objects.get(pk=user_id)
        logger.info(f"Found user: {user.email}")
        
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
        
        # Send email using helper function
        return send_email_with_backend_detection(
            subject=subject,
            plain_message=plain_message,
            html_message=html_message,
            recipient_list=[user.email],
            email_type="welcome email"
        )
        
    except CustomUser.DoesNotExist:
        error_msg = f"User with ID {user_id} does not exist"
        logger.error(error_msg)
        return error_msg
    except Exception as exc:
        error_msg = f"Error sending welcome email to user_id={user_id}: {str(exc)}"
        logger.error(error_msg, exc_info=True)
        
        if self.request.retries < self.max_retries:
            logger.warning(f"Retrying welcome email task (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        else:
            logger.error(f"Max retries reached for welcome email task. Giving up.")
            raise


@shared_task(bind=True, max_retries=3)
def send_password_reset_email(self, user_id, reset_token):
    """
    Send password reset email.
    
    Args:
        user_id: ID of the user requesting password reset
        reset_token: Token for password reset (should be uidb64/token format)
    """
    logger.info(f"Starting password reset email task for user_id={user_id}")
    
    try:
        # Validate email configuration (basic check)
        if not settings.DEFAULT_FROM_EMAIL:
            error_msg = "DEFAULT_FROM_EMAIL is not configured."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        user = CustomUser.objects.get(pk=user_id)
        logger.info(f"Found user: {user.email}")
        
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
        
        # Send email using helper function
        return send_email_with_backend_detection(
            subject=subject,
            plain_message=plain_message,
            html_message=html_message,
            recipient_list=[user.email],
            email_type="password reset email"
        )
        
    except CustomUser.DoesNotExist:
        error_msg = f"User with ID {user_id} does not exist"
        logger.error(error_msg)
        return error_msg
    except Exception as exc:
        error_msg = f"Error sending password reset email to user_id={user_id}: {str(exc)}"
        logger.error(error_msg, exc_info=True)
        
        if self.request.retries < self.max_retries:
            logger.warning(f"Retrying password reset email task (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        else:
            logger.error(f"Max retries reached for password reset email task. Giving up.")
            raise

