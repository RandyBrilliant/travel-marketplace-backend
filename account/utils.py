"""
Utility functions for account management.
"""
from django.contrib.auth.tokens import PasswordResetTokenGenerator, default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
import hashlib


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Tokens for email-verification links only.

    A different key_salt means these tokens are rejected by the password reset
    check (and vice versa), so a verification link cannot be used to take over
    an account. Including email_verified in the hash makes a link single-use.
    """

    key_salt = "account.utils.EmailVerificationTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.email}{user.email_verified}{timestamp}"


email_verification_token_generator = EmailVerificationTokenGenerator()

# Password reset uses Django's generator: its hash includes the password, so a
# reset link stops working once the password has been changed.
password_reset_token_generator = default_token_generator


def _uidb64(user):
    return urlsafe_base64_encode(force_bytes(user.pk))


def generate_email_verification_token(user):
    """Return (uidb64, token) for an email-verification link."""
    return _uidb64(user), email_verification_token_generator.make_token(user)


def generate_password_reset_token(user):
    """Return (uidb64, token) for a password-reset link."""
    return _uidb64(user), password_reset_token_generator.make_token(user)


def mask_email(email, hash_length=8):
    """
    Hash an email address for logging purposes to protect privacy.
    
    Useful for security logs where we don't want to expose actual email addresses
    but still need to identify users.
    
    Args:
        email (str): Email address to mask
        hash_length (int): Number of characters to show from the hash
        
    Returns:
        str: Masked email hash (e.g., 'user...#a1b2c3d4')
        
    Example:
        >>> mask_email('user@example.com')
        'user...#a1b2c3d4'
    """
    if not email:
        return 'unknown'
    
    email_lower = email.lower().strip()
    # Get the part before @ if available
    email_prefix = email_lower.split('@')[0]
    
    # Create a hash of the full email for uniqueness
    email_hash = hashlib.sha256(email_lower.encode()).hexdigest()[:hash_length]
    
    # Return masked version
    return f"{email_prefix}...#{email_hash}"

