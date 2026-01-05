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
        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            error_msg = "Mailgun credentials not configured. EMAIL_HOST_USER or EMAIL_HOST_PASSWORD is missing."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if not settings.DEFAULT_FROM_EMAIL:
            error_msg = "DEFAULT_FROM_EMAIL is not configured."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"Email config check passed. From: {settings.DEFAULT_FROM_EMAIL}, Host: {settings.EMAIL_HOST}")
        
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
        
        logger.info(f"Attempting to send email to {user.email} via {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
        
        # Set socket timeout to prevent hanging (Django will use this for SMTP connections)
        timeout = getattr(settings, 'EMAIL_TIMEOUT', 30)
        old_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(timeout)
            logger.info(f"Set email connection timeout to {timeout} seconds")
            
            # Send the email with explicit connection using timeout
            connection = get_connection(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                use_tls=settings.EMAIL_USE_TLS,
                timeout=timeout,
            )
            
            logger.info("Attempting SMTP connection...")
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
                connection=connection,
            )
            
            success_msg = f"Verification email sent successfully to {user.email}"
            logger.info(success_msg)
            return success_msg
        except socket.timeout:
            error_msg = f"SMTP connection timeout after {timeout} seconds when sending to {user.email}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except socket.error as sock_err:
            error_msg = f"SMTP socket error when sending to {user.email}: {str(sock_err)}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)
        finally:
            socket.setdefaulttimeout(old_timeout)
        
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
        # Validate email configuration
        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            error_msg = "Mailgun credentials not configured. EMAIL_HOST_USER or EMAIL_HOST_PASSWORD is missing."
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
        
        logger.info(f"Attempting to send welcome email to {user.email} via {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
        
        # Set socket timeout to prevent hanging
        timeout = getattr(settings, 'EMAIL_TIMEOUT', 30)
        old_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(timeout)
            logger.info(f"Set email connection timeout to {timeout} seconds")
            
            connection = get_connection(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                use_tls=settings.EMAIL_USE_TLS,
                timeout=timeout,
            )
            
            logger.info("Attempting SMTP connection...")
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
                connection=connection,
            )
            
            success_msg = f"Welcome email sent successfully to {user.email}"
            logger.info(success_msg)
            return success_msg
        except socket.timeout:
            error_msg = f"SMTP connection timeout after {timeout} seconds when sending to {user.email}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except socket.error as sock_err:
            error_msg = f"SMTP socket error when sending to {user.email}: {str(sock_err)}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)
        finally:
            socket.setdefaulttimeout(old_timeout)
        
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
        # Validate email configuration
        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            error_msg = "Mailgun credentials not configured. EMAIL_HOST_USER or EMAIL_HOST_PASSWORD is missing."
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
        
        logger.info(f"Attempting to send password reset email to {user.email} via {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
        
        # Set socket timeout to prevent hanging
        timeout = getattr(settings, 'EMAIL_TIMEOUT', 30)
        old_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(timeout)
            logger.info(f"Set email connection timeout to {timeout} seconds")
            
            connection = get_connection(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                use_tls=settings.EMAIL_USE_TLS,
                timeout=timeout,
            )
            
            logger.info("Attempting SMTP connection...")
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
                connection=connection,
            )
            
            success_msg = f"Password reset email sent successfully to {user.email}"
            logger.info(success_msg)
            return success_msg
        except socket.timeout:
            error_msg = f"SMTP connection timeout after {timeout} seconds when sending to {user.email}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except socket.error as sock_err:
            error_msg = f"SMTP socket error when sending to {user.email}: {str(sock_err)}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)
        finally:
            socket.setdefaulttimeout(old_timeout)
        
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

