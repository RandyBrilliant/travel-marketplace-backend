"""
Utility functions for account management.
"""
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
import hashlib


def generate_verification_token(user):
    """
    Generate a verification token for a user.
    
    Used for:
    - Email verification
    - Password reset
    
    Returns:
        tuple: (uidb64, token) - Base64 encoded user ID and verification token
        
    Example:
        >>> uidb64, token = generate_verification_token(user)
        >>> # Use in URL: /verify-email/{uidb64}/{token}/
    """
    token = default_token_generator.make_token(user)
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    return uidb64, token


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

