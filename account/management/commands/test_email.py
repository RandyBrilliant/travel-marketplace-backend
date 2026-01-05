"""
Management command to test email configuration and SMTP connection.
"""
import socket
import smtplib
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import get_connection


class Command(BaseCommand):
    help = 'Test email configuration and SMTP connection to Mailgun'

    def handle(self, *args, **options):
        self.stdout.write("Testing email configuration...")
        
        # Check configuration
        self.stdout.write(f"EMAIL_HOST: {settings.EMAIL_HOST}")
        self.stdout.write(f"EMAIL_PORT: {settings.EMAIL_PORT}")
        self.stdout.write(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER[:10]}..." if settings.EMAIL_HOST_USER else "EMAIL_HOST_USER: (not set)")
        self.stdout.write(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"EMAIL_TIMEOUT: {getattr(settings, 'EMAIL_TIMEOUT', 'not set')}")
        
        # Test DNS resolution
        self.stdout.write("\n1. Testing DNS resolution...")
        try:
            host_ip = socket.gethostbyname(settings.EMAIL_HOST)
            self.stdout.write(self.style.SUCCESS(f"✓ DNS resolved: {settings.EMAIL_HOST} -> {host_ip}"))
        except socket.gaierror as e:
            self.stdout.write(self.style.ERROR(f"✗ DNS resolution failed: {e}"))
            return
        
        # Test port connectivity
        self.stdout.write("\n2. Testing port connectivity...")
        timeout = getattr(settings, 'EMAIL_TIMEOUT', 30)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((settings.EMAIL_HOST, settings.EMAIL_PORT))
            sock.close()
            if result == 0:
                self.stdout.write(self.style.SUCCESS(f"✓ Port {settings.EMAIL_PORT} is reachable"))
            else:
                self.stdout.write(self.style.ERROR(f"✗ Port {settings.EMAIL_PORT} is not reachable (error code: {result})"))
                self.stdout.write(self.style.WARNING("This might be a firewall or network issue"))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Port connectivity test failed: {e}"))
            return
        
        # Test SMTP connection
        self.stdout.write("\n3. Testing SMTP connection...")
        try:
            connection = get_connection(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                use_tls=settings.EMAIL_USE_TLS,
                timeout=timeout,
            )
            connection.open()
            self.stdout.write(self.style.SUCCESS("✓ SMTP connection successful"))
            connection.close()
        except smtplib.SMTPAuthenticationError as e:
            self.stdout.write(self.style.ERROR(f"✗ SMTP authentication failed: {e}"))
            self.stdout.write(self.style.WARNING("Check your MAILGUN_SMTP_LOGIN and MAILGUN_SMTP_PASSWORD"))
        except smtplib.SMTPException as e:
            self.stdout.write(self.style.ERROR(f"✗ SMTP error: {e}"))
        except socket.timeout:
            self.stdout.write(self.style.ERROR(f"✗ SMTP connection timeout after {timeout} seconds"))
            self.stdout.write(self.style.WARNING("This might indicate a firewall blocking the connection"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ SMTP connection failed: {e}"))
        
        self.stdout.write("\nTest completed!")

