"""
Management command to create a superuser account with a staff profile.

The created user will have:
- Superuser privileges (is_staff=True, is_superuser=True)
- STAFF role
- Associated StaffProfile with name, job_title, department, and contact_phone

When this user logs in via /api/token/, the JWT access token will include:
- email: User's email address
- role: STAFF
- full_name: Staff profile name (or email if no profile)
- profile_picture_url: Absolute URL to profile photo (if photo is uploaded later)

Usage:
    python manage.py createsuperadmin
"""

import getpass

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from account.models import CustomUser, StaffProfile, UserRole


class Command(BaseCommand):
    help = 'Creates a superuser account with a staff profile'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email address for the superuser',
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Password for the superuser',
        )
        parser.add_argument(
            '--name',
            type=str,
            help='Full name for the staff profile',
        )
        parser.add_argument(
            '--job-title',
            type=str,
            dest='job_title',
            help='Job title for the staff profile',
        )
        parser.add_argument(
            '--department',
            type=str,
            help='Department for the staff profile',
        )
        parser.add_argument(
            '--contact-phone',
            type=str,
            dest='contact_phone',
            help='Contact phone number for the staff profile',
        )
        parser.add_argument(
            '--noinput',
            action='store_true',
            help='Run non-interactively (requires --email, --password, and --name)',
        )

    def handle(self, *args, **options):
        email = options.get('email')
        password = options.get('password')
        name = options.get('name')
        job_title = options.get('job_title')
        department = options.get('department')
        contact_phone = options.get('contact_phone')
        noinput = options.get('noinput', False)

        # Collect required information interactively if not provided
        if not email:
            if noinput:
                raise CommandError('--email is required when using --noinput')
            email = self._get_email()

        if not password:
            if noinput:
                raise CommandError('--password is required when using --noinput')
            password = self._get_password()
        else:
            # Validate password if provided via command line
            try:
                validate_password(password)
            except ValidationError as e:
                if noinput:
                    raise CommandError(f'Password validation failed: {"; ".join(e.messages)}')
                else:
                    self.stdout.write(self.style.ERROR('Password validation failed:'))
                    for error in e.messages:
                        self.stdout.write(self.style.ERROR(f'  - {error}'))
                    confirm = input('Continue anyway? (y/N): ').strip().lower()
                    if confirm != 'y':
                        raise CommandError('Password validation failed. Aborting.')

        if not name:
            if noinput:
                raise CommandError('--name is required when using --noinput')
            name = self._get_name()

        # Collect optional information interactively if not provided
        if job_title is None and not noinput:
            job_title = self._get_job_title()

        if department is None and not noinput:
            department = self._get_department()

        if contact_phone is None and not noinput:
            contact_phone = self._get_contact_phone()

        # Validate email uniqueness
        if CustomUser.objects.filter(email=email).exists():
            raise CommandError(f'A user with email "{email}" already exists.')

        # Create superuser and staff profile in a transaction
        try:
            with transaction.atomic():
                # Create superuser
                user = CustomUser.objects.create_superuser(
                    email=email,
                    password=password,
                    role=UserRole.STAFF,
                )

                # Create staff profile
                staff_profile = StaffProfile.objects.create(
                    user=user,
                    name=name,
                    job_title=job_title or '',
                    department=department or '',
                    contact_phone=contact_phone or '',
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'\nSuccessfully created superuser "{email}" with staff profile.'
                    )
                )
                self.stdout.write(f'  User ID: {user.id}')
                self.stdout.write(f'  Email: {user.email}')
                self.stdout.write(f'  Role: {user.role}')
                self.stdout.write(f'  Staff Profile ID: {staff_profile.id}')
                self.stdout.write(f'  Staff Name: {staff_profile.name}')
                if staff_profile.job_title:
                    self.stdout.write(f'  Job Title: {staff_profile.job_title}')
                if staff_profile.department:
                    self.stdout.write(f'  Department: {staff_profile.department}')
                
                self.stdout.write(
                    self.style.SUCCESS(
                        '\nNote: When this user logs in via /api/token/, the JWT access token '
                        'will include email, role (STAFF), and full_name (from staff profile name).'
                    )
                )

        except ValidationError as e:
            raise CommandError(f'Validation error: {e}')
        except Exception as e:
            raise CommandError(f'Error creating superuser: {e}')

    def _get_email(self):
        """Prompt for email address."""
        while True:
            email = input('Email address: ').strip()
            if email:
                # Basic email validation
                if '@' in email and '.' in email.split('@')[1]:
                    return email
                else:
                    self.stdout.write(self.style.ERROR('Enter a valid email address.'))
            else:
                self.stdout.write(self.style.ERROR('Email cannot be blank.'))

    def _get_password(self):
        """Prompt for password with confirmation and validation."""
        while True:
            password = getpass.getpass('Password: ')
            if not password:
                self.stdout.write(self.style.ERROR('Password cannot be blank.'))
                continue

            password_confirm = getpass.getpass('Password (again): ')
            if password != password_confirm:
                self.stdout.write(self.style.ERROR('Passwords do not match. Please try again.'))
                continue

            # Validate password using Django's password validators
            try:
                validate_password(password)
            except ValidationError as e:
                self.stdout.write(self.style.ERROR('Password validation failed:'))
                for error in e.messages:
                    self.stdout.write(self.style.ERROR(f'  - {error}'))
                confirm = input('Continue anyway? (y/N): ').strip().lower()
                if confirm != 'y':
                    continue

            return password

    def _get_name(self):
        """Prompt for staff name."""
        while True:
            name = input('Staff full name: ').strip()
            if name:
                return name
            else:
                self.stdout.write(self.style.ERROR('Name cannot be blank.'))

    def _get_job_title(self):
        """Prompt for job title (optional)."""
        job_title = input('Job title (optional): ').strip()
        return job_title if job_title else None

    def _get_department(self):
        """Prompt for department (optional)."""
        department = input('Department (optional): ').strip()
        return department if department else None

    def _get_contact_phone(self):
        """Prompt for contact phone (optional)."""
        contact_phone = input('Contact phone (optional): ').strip()
        return contact_phone if contact_phone else None

