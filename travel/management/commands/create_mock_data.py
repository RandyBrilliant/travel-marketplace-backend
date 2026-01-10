"""
Management command to create mock data for tours, suppliers, resellers, and bookings.

This command creates:
- Multiple suppliers with profiles
- Multiple resellers with profiles (including MLM relationships)
- Multiple tour packages with dates, images, and itineraries
- Multiple bookings with payments and seat slot details

Usage:
    python manage.py create_mock_data
    python manage.py create_mock_data --clear  # Clear existing data first
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta
import random
import string
import requests
from io import BytesIO
from django.core.files.base import ContentFile

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from account.models import CustomUser, SupplierProfile, ResellerProfile, StaffProfile, UserRole
from travel.models import (
    TourPackage, TourDate, TourImage, Booking, Payment,
    SeatSlot, SeatSlotStatus, BookingStatus, PaymentStatus,
    TourType, ResellerGroup
)


class Command(BaseCommand):
    help = 'Creates mock data for tours, suppliers, resellers, and bookings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing mock data before creating new data',
        )

    def handle(self, *args, **options):
        clear = options.get('clear', False)
        
        if clear:
            self.stdout.write(self.style.WARNING('Clearing existing mock data...'))
            self._clear_mock_data()
        
        self.stdout.write(self.style.SUCCESS('Creating mock data...'))
        
        with transaction.atomic():
            # Create staff
            staff = self._create_staff()
            self.stdout.write(self.style.SUCCESS(f'Created {len(staff)} staff members'))
            
            # Create suppliers
            suppliers = self._create_suppliers()
            self.stdout.write(self.style.SUCCESS(f'Created {len(suppliers)} suppliers'))
            
            # Create resellers
            resellers = self._create_resellers()
            self.stdout.write(self.style.SUCCESS(f'Created {len(resellers)} resellers'))
            
            # Create reseller groups
            reseller_groups = self._create_reseller_groups(resellers)
            self.stdout.write(self.style.SUCCESS(f'Created {len(reseller_groups)} reseller groups'))
            
            # Create tours
            tours = self._create_tours(suppliers, reseller_groups)
            self.stdout.write(self.style.SUCCESS(f'Created {len(tours)} tour packages'))
            
            # Create bookings
            bookings = self._create_bookings(resellers, tours)
            self.stdout.write(self.style.SUCCESS(f'Created {len(bookings)} bookings'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Mock data creation completed!'))

    def _clear_mock_data(self):
        """Clear existing mock data."""
        Booking.objects.all().delete()
        Payment.objects.all().delete()
        SeatSlot.objects.all().delete()
        TourDate.objects.all().delete()
        TourImage.objects.all().delete()
        TourPackage.objects.all().delete()
        ResellerGroup.objects.all().delete()
        ResellerProfile.objects.all().delete()
        SupplierProfile.objects.all().delete()
        StaffProfile.objects.all().delete()
        CustomUser.objects.filter(role__in=[UserRole.SUPPLIER, UserRole.RESELLER, UserRole.STAFF]).delete()

    def _download_image(self, url, max_size=(800, 800)):
        """Download an image from URL and return a Django ContentFile."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            if PIL_AVAILABLE:
                # Open image with PIL for processing
                img = Image.open(BytesIO(response.content))
                
                # Convert to RGB if necessary (handles RGBA, P, etc.)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Save to BytesIO
                img_io = BytesIO()
                img.save(img_io, format='JPEG', quality=85)
                img_io.seek(0)
                
                return ContentFile(img_io.read())
            else:
                # If PIL not available, just use the raw image (may be larger)
                return ContentFile(response.content)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Failed to download image from {url}: {e}'))
            return None

    def _create_staff(self):
        """Create mock staff members - Indonesian names."""
        # Unsplash images for staff profile photos (professional portraits)
        staff_photo_urls = [
            'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=400&h=400&fit=crop',  # Professional man
            'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400&h=400&fit=crop',  # Professional woman
            'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop',  # Professional man
            'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=400&h=400&fit=crop',  # Professional woman
            'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&h=400&fit=crop',  # Professional man
            'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=400&h=400&fit=crop',  # Professional woman
            'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=400&h=400&fit=crop',  # Professional man
            'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&h=400&fit=crop',  # Professional woman
            'https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=400&h=400&fit=crop',  # Professional man
            'https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=400&h=400&fit=crop',  # Professional man
            'https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91?w=400&h=400&fit=crop',  # Professional woman
            'https://images.unsplash.com/photo-1507591064344-4c6ce005b128?w=400&h=400&fit=crop',  # Professional woman
            'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=400&h=400&fit=crop',  # Professional woman
            'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop',  # Professional man
            'https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=400&h=400&fit=crop',  # Professional man
            'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&h=400&fit=crop',  # Professional woman
            'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=400&h=400&fit=crop',  # Professional man
            'https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=400&h=400&fit=crop',  # Professional man
            'https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=400&h=400&fit=crop',  # Professional man
            'https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91?w=400&h=400&fit=crop',  # Professional woman
            'https://images.unsplash.com/photo-1507591064344-4c6ce005b128?w=400&h=400&fit=crop',  # Professional woman
            'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=400&h=400&fit=crop',  # Professional woman
            'https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=400&h=400&fit=crop',  # Professional man
            'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop',  # Professional man
            'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&h=400&fit=crop',  # Professional woman
            'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=400&h=400&fit=crop',  # Professional man
            'https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=400&h=400&fit=crop',  # Professional man
            'https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=400&h=400&fit=crop',  # Professional man
            'https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91?w=400&h=400&fit=crop',  # Professional woman
        ]
        
        staff_data = [
            {
                'email': 'staff1@travelmarketplace.com',
                'full_name': 'Ahmad Wijaya',
                'contact_phone': '+62-811-1001-1001',
            },
            {
                'email': 'staff2@travelmarketplace.com',
                'full_name': 'Siti Rahayu',
                'contact_phone': '+62-811-1002-1002',
            },
            {
                'email': 'staff3@travelmarketplace.com',
                'full_name': 'Bambang Sutrisno',
                'contact_phone': '+62-811-1003-1003',
            },
            {
                'email': 'staff4@travelmarketplace.com',
                'full_name': 'Dewi Lestari',
                'contact_phone': '+62-811-1004-1004',
            },
            {
                'email': 'staff5@travelmarketplace.com',
                'full_name': 'Eko Prasetyo',
                'contact_phone': '+62-811-1005-1005',
            },
            {
                'email': 'staff6@travelmarketplace.com',
                'full_name': 'Fitri Handayani',
                'contact_phone': '+62-811-1006-1006',
            },
            {
                'email': 'staff7@travelmarketplace.com',
                'full_name': 'Gunawan Setiawan',
                'contact_phone': '+62-811-1007-1007',
            },
            {
                'email': 'staff8@travelmarketplace.com',
                'full_name': 'Hesti Novianti',
                'contact_phone': '+62-811-1008-1008',
            },
            {
                'email': 'staff9@travelmarketplace.com',
                'full_name': 'Indra Kurniawan',
                'contact_phone': '+62-811-1009-1009',
            },
            {
                'email': 'staff10@travelmarketplace.com',
                'full_name': 'Juli Susanti',
                'contact_phone': '+62-811-1010-1010',
            },
            {
                'email': 'staff11@travelmarketplace.com',
                'full_name': 'Kurniawan Wibowo',
                'contact_phone': '+62-811-1011-1011',
            },
            {
                'email': 'staff12@travelmarketplace.com',
                'full_name': 'Lina Marlina',
                'contact_phone': '+62-811-1012-1012',
            },
            {
                'email': 'staff13@travelmarketplace.com',
                'full_name': 'Muhammad Fauzan',
                'contact_phone': '+62-811-1013-1013',
            },
            {
                'email': 'staff14@travelmarketplace.com',
                'full_name': 'Nurhayati Sari',
                'contact_phone': '+62-811-1014-1014',
            },
            {
                'email': 'staff15@travelmarketplace.com',
                'full_name': 'Oka Mahendra',
                'contact_phone': '+62-811-1015-1015',
            },
            {
                'email': 'staff16@travelmarketplace.com',
                'full_name': 'Putri Anggraeni',
                'contact_phone': '+62-811-1016-1016',
            },
            {
                'email': 'staff17@travelmarketplace.com',
                'full_name': 'Rudi Hermawan',
                'contact_phone': '+62-811-1017-1017',
            },
            {
                'email': 'staff18@travelmarketplace.com',
                'full_name': 'Sari Indrawati',
                'contact_phone': '+62-811-1018-1018',
            },
            {
                'email': 'staff19@travelmarketplace.com',
                'full_name': 'Teguh Santoso',
                'contact_phone': '+62-811-1019-1019',
            },
            {
                'email': 'staff20@travelmarketplace.com',
                'full_name': 'Umi Rahmawati',
                'contact_phone': '+62-811-1020-1020',
            },
            {
                'email': 'staff21@travelmarketplace.com',
                'full_name': 'Vito Ramadhan',
                'contact_phone': '+62-811-1021-1021',
            },
            {
                'email': 'staff22@travelmarketplace.com',
                'full_name': 'Winda Sari',
                'contact_phone': '+62-811-1022-1022',
            },
            {
                'email': 'staff23@travelmarketplace.com',
                'full_name': 'Yoga Pratama',
                'contact_phone': '+62-811-1023-1023',
            },
            {
                'email': 'staff24@travelmarketplace.com',
                'full_name': 'Zahra Fadilah',
                'contact_phone': '+62-811-1024-1024',
            },
            {
                'email': 'staff25@travelmarketplace.com',
                'full_name': 'Andika Permana',
                'contact_phone': '+62-811-1025-1025',
            },
            {
                'email': 'staff26@travelmarketplace.com',
                'full_name': 'Bella Kusuma',
                'contact_phone': '+62-811-1026-1026',
            },
            {
                'email': 'staff27@travelmarketplace.com',
                'full_name': 'Cahya Nugroho',
                'contact_phone': '+62-811-1027-1027',
            },
            {
                'email': 'staff28@travelmarketplace.com',
                'full_name': 'Diana Puspita',
                'contact_phone': '+62-811-1028-1028',
            },
            {
                'email': 'staff29@travelmarketplace.com',
                'full_name': 'Eko Yulianto',
                'contact_phone': '+62-811-1029-1029',
            },
            {
                'email': 'staff30@travelmarketplace.com',
                'full_name': 'Febrianti Wardani',
                'contact_phone': '+62-811-1030-1030',
            },
        ]
        
        staff = []
        for idx, data in enumerate(staff_data):
            user = CustomUser.objects.create_user(
                email=data['email'],
                password='password123',
                role=UserRole.STAFF,
                email_verified=True,
                email_verified_at=timezone.now(),
                is_active=True,
            )
            
            staff_profile = StaffProfile.objects.create(
                user=user,
                full_name=data['full_name'],
                contact_phone=data['contact_phone'],
            )
            
            # Download and assign profile photo
            if idx < len(staff_photo_urls):
                photo_file = self._download_image(staff_photo_urls[idx])
                if photo_file:
                    staff_profile.photo.save(
                        f'staff_{staff_profile.id}.jpg',
                        photo_file,
                        save=True
                    )
            
            staff.append(staff_profile)
        
        return staff

    def _create_suppliers(self):
        """Create mock suppliers - all Indonesian tour companies."""
        # Unsplash images for supplier profile photos (business/travel related)
        supplier_photo_urls = [
            'https://images.unsplash.com/photo-1556761175-5973dc0f32e7?w=400&h=400&fit=crop',  # Business team
            'https://images.unsplash.com/photo-1552664730-d307ca884978?w=400&h=400&fit=crop',  # Travel agency
            'https://images.unsplash.com/photo-1556761175-4b46a572b786?w=400&h=400&fit=crop',  # Office
            'https://images.unsplash.com/photo-1556761175-b413da4baf72?w=400&h=400&fit=crop',  # Team meeting
            'https://images.unsplash.com/photo-1552664730-d307ca884978?w=400&h=400&fit=crop',  # Travel
            'https://images.unsplash.com/photo-1556761175-5973dc0f32e7?w=400&h=400&fit=crop',  # Business
            'https://images.unsplash.com/photo-1552664730-d307ca884978?w=400&h=400&fit=crop',  # Agency
            'https://images.unsplash.com/photo-1556761175-4b46a572b786?w=400&h=400&fit=crop',  # Office
            'https://images.unsplash.com/photo-1556761175-b413da4baf72?w=400&h=400&fit=crop',  # Meeting
            'https://images.unsplash.com/photo-1552664730-d307ca884978?w=400&h=400&fit=crop',  # Travel
        ]
        
        suppliers_data = [
            {
                'email': 'bali.paradise@example.com',
                'company_name': 'Bali Paradise Tours',
                'contact_person': 'Wayan Surya',
                'contact_phone': '+62-812-3456-7890',
                'address': 'Jl. Raya Ubud No. 123, Ubud, Gianyar, Bali 80571, Indonesia',
            },
            {
                'email': 'jogja.heritage@example.com',
                'company_name': 'Jogja Heritage Travel',
                'contact_person': 'Budi Santoso',
                'contact_phone': '+62-812-3456-7891',
                'address': 'Jl. Malioboro No. 45, Yogyakarta, DIY 55211, Indonesia',
            },
            {
                'email': 'bromo.adventure@example.com',
                'company_name': 'Bromo Adventure Tours',
                'contact_person': 'Siti Nurhaliza',
                'contact_phone': '+62-812-3456-7892',
                'address': 'Jl. Raya Bromo, Probolinggo, Jawa Timur 67254, Indonesia',
            },
            {
                'email': 'raja.ampat.explorer@example.com',
                'company_name': 'Raja Ampat Explorer',
                'contact_person': 'Ahmad Fauzi',
                'contact_phone': '+62-812-3456-7893',
                'address': 'Jl. Raya Waisai, Raja Ampat, Papua Barat 98482, Indonesia',
            },
            {
                'email': 'komodo.dragons@example.com',
                'company_name': 'Komodo Dragons Adventure',
                'contact_person': 'Maria Magdalena',
                'contact_phone': '+62-812-3456-7894',
                'address': 'Jl. Soekarno Hatta, Labuan Bajo, NTT 86754, Indonesia',
            },
            {
                'email': 'lombok.wisata@example.com',
                'company_name': 'Lombok Wisata Sejahtera',
                'contact_person': 'Rahmat Hidayat',
                'contact_phone': '+62-812-3456-7895',
                'address': 'Jl. Raya Senggigi, Lombok Barat, NTB 83355, Indonesia',
            },
            {
                'email': 'jakarta.citytours@example.com',
                'company_name': 'Jakarta City Tours',
                'contact_person': 'Dewi Sartika',
                'contact_phone': '+62-812-3456-7896',
                'address': 'Jl. Thamrin No. 12, Jakarta Pusat, DKI Jakarta 10240, Indonesia',
            },
            {
                'email': 'bandung.travel@example.com',
                'company_name': 'Bandung Travel Agency',
                'contact_person': 'Asep Gunawan',
                'contact_phone': '+62-812-3456-7897',
                'address': 'Jl. Dago No. 88, Bandung, Jawa Barat 40135, Indonesia',
            },
            {
                'email': 'lake.toba.tours@example.com',
                'company_name': 'Lake Toba Tours',
                'contact_person': 'Samosir Siregar',
                'contact_phone': '+62-812-3456-7898',
                'address': 'Jl. Lingkar Danau Toba, Parapat, Sumatera Utara 22384, Indonesia',
            },
            {
                'email': 'toraja.cultural@example.com',
                'company_name': 'Toraja Cultural Tours',
                'contact_person': 'Andi Makassar',
                'contact_phone': '+62-812-3456-7899',
                'address': 'Jl. Pongtiku No. 25, Rantepao, Sulawesi Selatan 91831, Indonesia',
            },
        ]
        
        suppliers = []
        for idx, data in enumerate(suppliers_data):
            user = CustomUser.objects.create_user(
                email=data['email'],
                password='password123',
                role=UserRole.SUPPLIER,
                email_verified=True,
                email_verified_at=timezone.now(),
            )
            supplier = SupplierProfile.objects.create(
                user=user,
                company_name=data['company_name'],
                contact_person=data['contact_person'],
                contact_phone=data['contact_phone'],
                address=data['address'],
            )
            
            # Download and assign profile photo
            if idx < len(supplier_photo_urls):
                photo_file = self._download_image(supplier_photo_urls[idx])
                if photo_file:
                    supplier.photo.save(
                        f'supplier_{supplier.id}.jpg',
                        photo_file,
                        save=True
                    )
            
            suppliers.append(supplier)
        
        return suppliers

    def _create_resellers(self):
        """Create mock resellers with MLM relationships - Indonesian names."""
        # Unsplash images for reseller profile photos (portraits)
        reseller_photo_urls = [
            'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400&h=400&fit=crop',  # Woman
            'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop',  # Man
            'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=400&h=400&fit=crop',  # Woman
            'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&h=400&fit=crop',  # Man
            'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=400&h=400&fit=crop',  # Woman
            'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=400&h=400&fit=crop',  # Man
            'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&h=400&fit=crop',  # Woman
            'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=400&h=400&fit=crop',  # Man
            'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&h=400&fit=crop',  # Woman
            'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop',  # Man
            'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400&h=400&fit=crop',  # Woman
            'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&h=400&fit=crop',  # Man
        ]
        
        resellers_data = [
            {
                'email': 'reseller1@example.com',
                'full_name': 'Siti Nurhaliza',
                'contact_phone': '+62-812-1111-1111',
                'address': 'Jakarta Selatan, DKI Jakarta, Indonesia',
                'sponsor': None,  # Root reseller
                'bank_name': 'Bank Mandiri',
                'bank_account_name': 'Siti Nurhaliza',
                'bank_account_number': '1234567890',
            },
            {
                'email': 'reseller2@example.com',
                'full_name': 'Budi Santoso',
                'contact_phone': '+62-812-2222-2222',
                'address': 'Surabaya, Jawa Timur, Indonesia',
                'sponsor': 0,  # Sponsored by first reseller
                'bank_name': 'BCA',
                'bank_account_name': 'Budi Santoso',
                'bank_account_number': '2345678901',
            },
            {
                'email': 'reseller3@example.com',
                'full_name': 'Dewi Sartika',
                'contact_phone': '+62-812-3333-3333',
                'address': 'Bandung, Jawa Barat, Indonesia',
                'sponsor': 0,  # Sponsored by first reseller
                'bank_name': 'Bank BNI',
                'bank_account_name': 'Dewi Sartika',
                'bank_account_number': '3456789012',
            },
            {
                'email': 'reseller4@example.com',
                'full_name': 'Ahmad Fauzi',
                'contact_phone': '+62-812-4444-4444',
                'address': 'Yogyakarta, DIY, Indonesia',
                'sponsor': 1,  # Sponsored by second reseller
                'bank_name': 'Bank Mandiri',
                'bank_account_name': 'Ahmad Fauzi',
                'bank_account_number': '4567890123',
            },
            {
                'email': 'reseller5@example.com',
                'full_name': 'Maria Magdalena',
                'contact_phone': '+62-812-5555-5555',
                'address': 'Medan, Sumatera Utara, Indonesia',
                'sponsor': 1,  # Sponsored by second reseller
                'bank_name': 'BCA',
                'bank_account_name': 'Maria Magdalena',
                'bank_account_number': '5678901234',
            },
            {
                'email': 'reseller6@example.com',
                'full_name': 'Rahmat Hidayat',
                'contact_phone': '+62-812-6666-6666',
                'address': 'Makassar, Sulawesi Selatan, Indonesia',
                'sponsor': 2,  # Sponsored by third reseller
                'bank_name': 'Bank BRI',
                'bank_account_name': 'Rahmat Hidayat',
                'bank_account_number': '6789012345',
            },
            {
                'email': 'reseller7@example.com',
                'full_name': 'Wulan Sari',
                'contact_phone': '+62-812-7777-7777',
                'address': 'Semarang, Jawa Tengah, Indonesia',
                'sponsor': 2,  # Sponsored by third reseller
                'bank_name': 'Bank Mandiri',
                'bank_account_name': 'Wulan Sari',
                'bank_account_number': '7890123456',
            },
            {
                'email': 'reseller8@example.com',
                'full_name': 'Asep Gunawan',
                'contact_phone': '+62-812-8888-8888',
                'address': 'Palembang, Sumatera Selatan, Indonesia',
                'sponsor': 3,  # Sponsored by fourth reseller
                'bank_name': 'BCA',
                'bank_account_name': 'Asep Gunawan',
                'bank_account_number': '8901234567',
            },
            {
                'email': 'reseller9@example.com',
                'full_name': 'Indah Permata',
                'contact_phone': '+62-812-9999-9999',
                'address': 'Denpasar, Bali, Indonesia',
                'sponsor': 3,  # Sponsored by fourth reseller
                'bank_name': 'Bank BNI',
                'bank_account_name': 'Indah Permata',
                'bank_account_number': '9012345678',
            },
            {
                'email': 'reseller10@example.com',
                'full_name': 'Dedi Kurniawan',
                'contact_phone': '+62-812-1010-1010',
                'address': 'Balikpapan, Kalimantan Timur, Indonesia',
                'sponsor': 4,  # Sponsored by fifth reseller
                'bank_name': 'Bank Mandiri',
                'bank_account_name': 'Dedi Kurniawan',
                'bank_account_number': '1023456789',
            },
            {
                'email': 'reseller11@example.com',
                'full_name': 'Fitri Ayu',
                'contact_phone': '+62-812-2020-2020',
                'address': 'Padang, Sumatera Barat, Indonesia',
                'sponsor': 4,  # Sponsored by fifth reseller
                'bank_name': 'BCA',
                'bank_account_name': 'Fitri Ayu',
                'bank_account_number': '2034567890',
            },
            {
                'email': 'reseller12@example.com',
                'full_name': 'Andi Makassar',
                'contact_phone': '+62-812-3030-3030',
                'address': 'Manado, Sulawesi Utara, Indonesia',
                'sponsor': 5,  # Sponsored by sixth reseller
                'bank_name': 'Bank BRI',
                'bank_account_name': 'Andi Makassar',
                'bank_account_number': '3045678901',
            },
        ]
        
        resellers = []
        for idx, data in enumerate(resellers_data):
            # Generate unique referral code
            referral_code = f'REF{idx+1:03d}{"".join(random.choices(string.ascii_uppercase, k=3))}'
            
            user = CustomUser.objects.create_user(
                email=data['email'],
                password='password123',
                role=UserRole.RESELLER,
                email_verified=True,
                email_verified_at=timezone.now(),
            )
            
            sponsor = None
            if data['sponsor'] is not None and data['sponsor'] < len(resellers):
                sponsor = resellers[data['sponsor']]
            
            reseller = ResellerProfile.objects.create(
                user=user,
                full_name=data['full_name'],
                contact_phone=data['contact_phone'],
                address=data['address'],
                referral_code=referral_code,
                sponsor=sponsor,
                base_commission=random.randint(50000, 200000),  # Fixed amount in IDR
                upline_commission_amount=random.randint(25000, 100000),  # Fixed amount in IDR
                bank_name=data['bank_name'],
                bank_account_name=data['bank_account_name'],
                bank_account_number=data['bank_account_number'],
            )
            
            # Download and assign profile photo
            if idx < len(reseller_photo_urls):
                photo_file = self._download_image(reseller_photo_urls[idx])
                if photo_file:
                    reseller.photo.save(
                        f'reseller_{reseller.id}.jpg',
                        photo_file,
                        save=True
                    )
            
            resellers.append(reseller)
        
        return resellers

    def _create_reseller_groups(self, resellers):
        """Create reseller groups."""
        groups_data = [
            {
                'name': 'Premium Partners',
                'description': 'Top performing resellers with exclusive access to premium tours',
            },
            {
                'name': 'Standard Partners',
                'description': 'Regular reseller group with access to standard tours',
            },
            {
                'name': 'New Partners',
                'description': 'Newly joined resellers with limited access',
            },
            {
                'name': 'Bali Specialists',
                'description': 'Resellers specializing in Bali tours',
            },
        ]
        
        groups = []
        for data in groups_data:
            group = ResellerGroup.objects.create(
                name=data['name'],
                description=data['description'],
                is_active=True,
            )
            # Assign resellers to groups
            if data['name'] == 'Premium Partners':
                group.resellers.add(resellers[0], resellers[1], resellers[2])
            elif data['name'] == 'Standard Partners':
                group.resellers.add(resellers[3], resellers[4], resellers[5])
            elif data['name'] == 'New Partners':
                group.resellers.add(resellers[6], resellers[7])
            elif data['name'] == 'Bali Specialists':
                group.resellers.add(resellers[8], resellers[9])
            
            groups.append(group)
        
        return groups

    def _create_tours(self, suppliers, reseller_groups):
        """Create mock tour packages - all Indonesian destinations."""
        tours_data = [
            {
                'supplier_idx': 0,  # Bali Paradise Tours
                'name': '3D2N Bali Cultural Experience',
                'itinerary': 'Day 1: Arrival in Bali & Ubud Orientation - Airport pickup from Ngurah Rai International Airport. Transfer to Ubud hotel with check-in. Welcome dinner at traditional Balinese restaurant.\n\nDay 2: Cultural Immersion Day - Early morning visit to Tegalalang Rice Terrace for sunrise views. Visit Tirta Empul Temple for holy water purification ritual. Explore Ubud Monkey Forest and learn about Balinese Hinduism.\n\nDay 3: Departure - Morning breakfast at hotel. Last-minute souvenir shopping at Ubud Market. Check-out and transfer to Ngurah Rai International Airport.',
                'country': 'Indonesia',
                'days': 3,
                'nights': 2,
                'max_group_size': 12,
                'tour_type': TourType.CONVENTIONAL,
                'highlights': ['Tegalalang Rice Terrace', 'Tirta Empul Temple', 'Ubud Monkey Forest', 'Traditional Balinese Dance'],
                'inclusions': ['2 nights hotel accommodation', 'Daily breakfast', 'Airport transfers', 'English speaking guide', 'Entrance fees'],
                'exclusions': ['International flights', 'Lunch and dinner', 'Travel insurance', 'Personal expenses'],
                'cancellation_policy': 'Free cancellation up to 7 days before departure. 50% refund for cancellations 3-7 days before. No refund for cancellations less than 3 days.',
                'important_notes': 'Please bring comfortable walking shoes and appropriate clothing for temple visits.',
                'base_price': 3500000,
                'visa_price': 0,
                'tipping_price': 50000,
                'reseller_groups': [0],  # Premium Partners
            },
            {
                'supplier_idx': 0,  # Bali Paradise Tours
                'name': '4D3N Bali Beach & Island Hopping',
                'itinerary': None,  # Will be generated
                'country': 'Indonesia',
                'days': 4,
                'nights': 3,
                'max_group_size': 15,
                'tour_type': TourType.CONVENTIONAL,
                'highlights': ['Nusa Penida Island', 'Crystal Bay', 'Kelingking Beach', 'Snorkeling with Manta Rays', 'Water sports'],
                'inclusions': ['3 nights beachfront hotel', 'Daily breakfast', 'Boat transfers', 'Snorkeling equipment', 'English speaking guide'],
                'exclusions': ['International flights', 'Lunch and dinner', 'Travel insurance', 'Personal expenses'],
                'cancellation_policy': 'Free cancellation up to 7 days before departure. 50% refund for cancellations 3-7 days before.',
                'important_notes': 'Swimming skills recommended for water activities.',
                'base_price': 4500000,
                'visa_price': 0,
                'tipping_price': 75000,
                'reseller_groups': [0, 3],  # Premium Partners & Bali Specialists
            },
            {
                'supplier_idx': 0,  # Bali Paradise Tours
                'name': '5D4N Bali Muslim Tour',
                'itinerary': None,  # Will be generated
                'country': 'Indonesia',
                'days': 5,
                'nights': 4,
                'max_group_size': 12,
                'tour_type': TourType.MUSLIM,
                'highlights': ['Tanah Lot Temple', 'Uluwatu Temple', 'Halal restaurants', 'Prayer facilities', 'Cultural shows'],
                'inclusions': ['4 nights halal-certified hotel', 'Halal breakfast and lunch', 'Private transportation', 'English speaking guide', 'Prayer time arrangements'],
                'exclusions': ['International flights', 'Dinner', 'Travel insurance', 'Personal expenses'],
                'cancellation_policy': 'Free cancellation up to 7 days before departure. 50% refund for cancellations 3-7 days before.',
                'important_notes': 'All meals are halal-certified. Prayer times will be accommodated during the tour.',
                'base_price': 5500000,
                'visa_price': 0,
                'tipping_price': 100000,
                'reseller_groups': [0, 3],  # Premium Partners & Bali Specialists
            },
            {
                'supplier_idx': 1,  # Jogja Heritage Travel
                'name': '3D2N Yogyakarta Heritage Tour',
                'itinerary': None,  # Will be generated
                'country': 'Indonesia',
                'days': 3,
                'nights': 2,
                'max_group_size': 20,
                'tour_type': TourType.CONVENTIONAL,
                'highlights': ['Borobudur Temple', 'Prambanan Temple', 'Kraton Palace', 'Taman Sari', 'Malioboro Street'],
                'inclusions': ['2 nights hotel accommodation', 'Daily breakfast', 'Private transportation', 'English speaking guide', 'All entrance fees'],
                'exclusions': ['International flights', 'Lunch and dinner', 'Travel insurance', 'Personal expenses'],
                'cancellation_policy': 'Free cancellation up to 7 days before departure. 50% refund for cancellations 3-7 days before.',
                'important_notes': 'Early morning visit to Borobudur recommended for sunrise view.',
                'base_price': 2800000,
                'visa_price': 0,
                'tipping_price': 40000,
                'reseller_groups': [],  # Available to all
            },
            {
                'supplier_idx': 1,  # Jogja Heritage Travel
                'name': '4D3N Jogja & Solo Cultural Tour',
                'itinerary': None,  # Will be generated
                'country': 'Indonesia',
                'days': 4,
                'nights': 3,
                'max_group_size': 15,
                'tour_type': TourType.CONVENTIONAL,
                'highlights': ['Borobudur Temple', 'Prambanan Temple', 'Kraton Solo', 'Batik Workshop', 'Traditional Market'],
                'inclusions': ['3 nights hotel accommodation', 'Daily breakfast', 'Private transportation', 'English speaking guide', 'Batik workshop'],
                'exclusions': ['International flights', 'Lunch and dinner', 'Travel insurance'],
                'cancellation_policy': 'Free cancellation up to 7 days before departure.',
                'important_notes': 'Comfortable clothes for batik workshop.',
                'base_price': 3800000,
                'visa_price': 0,
                'tipping_price': 60000,
                'reseller_groups': [0, 1],  # Premium & Standard
            },
            {
                'supplier_idx': 2,  # Bromo Adventure Tours
                'name': '2D1N Mount Bromo Sunrise Tour',
                'itinerary': None,  # Will be generated
                'country': 'Indonesia',
                'days': 2,
                'nights': 1,
                'max_group_size': 12,
                'tour_type': TourType.CONVENTIONAL,
                'highlights': ['Mount Bromo Sunrise', 'Savannah Viewpoint', 'Mount Bromo Crater', 'Sea of Sand', 'Madakaripura Waterfall'],
                'inclusions': ['1 night hotel accommodation', 'Breakfast', 'Jeep transportation', 'English speaking guide', 'Entrance fees'],
                'exclusions': ['Lunch and dinner', 'Travel insurance', 'Personal expenses'],
                'cancellation_policy': 'Free cancellation up to 5 days before departure. 50% refund for cancellations 2-5 days before.',
                'important_notes': 'Early departure (2-3 AM) for sunrise. Warm clothing recommended due to cold temperatures.',
                'base_price': 1800000,
                'visa_price': 0,
                'tipping_price': 25000,
                'reseller_groups': [],  # Available to all
            },
            {
                'supplier_idx': 2,  # Bromo Adventure Tours
                'name': '3D2N Bromo & Ijen Blue Fire Tour',
                'itinerary': None,  # Will be generated
                'country': 'Indonesia',
                'days': 3,
                'nights': 2,
                'max_group_size': 10,
                'tour_type': TourType.CONVENTIONAL,
                'highlights': ['Mount Bromo Sunrise', 'Ijen Blue Fire', 'Ijen Crater', 'Sulfur Mining', 'Volcanic Landscape'],
                'inclusions': ['2 nights hotel accommodation', 'Daily breakfast', 'Jeep transportation', 'English speaking guide', 'All entrance fees'],
                'exclusions': ['Lunch and dinner', 'Travel insurance', 'Gas mask rental'],
                'cancellation_policy': 'Free cancellation up to 7 days before departure.',
                'important_notes': 'Strenuous activity. Good physical fitness required. Gas mask required for Ijen visit.',
                'base_price': 3500000,
                'visa_price': 0,
                'tipping_price': 50000,
                'reseller_groups': [0, 1],  # Premium & Standard
            },
            {
                'supplier_idx': 3,  # Raja Ampat Explorer
                'name': '5D4N Raja Ampat Diving Paradise',
                'itinerary': None,  # Will be generated
                'country': 'Indonesia',
                'days': 5,
                'nights': 4,
                'max_group_size': 8,
                'tour_type': TourType.CONVENTIONAL,
                'highlights': ['Manta Ray Spotting', 'Coral Reef Diving', 'Island Hopping', 'Bird Watching', 'Pristine Beaches'],
                'inclusions': ['4 nights accommodation', 'All meals', 'Diving/snorkeling equipment', 'Boat transfers', 'English speaking guide'],
                'exclusions': ['International flights', 'Travel insurance', 'Diving certification'],
                'cancellation_policy': 'Free cancellation up to 14 days before departure. 30% refund for cancellations 7-14 days before.',
                'important_notes': 'Diving certification required for diving activities. Snorkeling available for non-divers.',
                'base_price': 12500000,
                'visa_price': 0,
                'tipping_price': 200000,
                'reseller_groups': [0],  # Premium Partners only
            },
            {
                'supplier_idx': 4,  # Komodo Dragons Adventure
                'name': '3D2N Komodo Island Adventure',
                'itinerary': None,  # Will be generated
                'country': 'Indonesia',
                'days': 3,
                'nights': 2,
                'max_group_size': 15,
                'tour_type': TourType.CONVENTIONAL,
                'highlights': ['Komodo Dragon Sightings', 'Pink Beach', 'Padar Island', 'Snorkeling', 'Sunset Viewing'],
                'inclusions': ['2 nights hotel/accommodation', 'Daily meals', 'Boat transportation', 'Park entrance fees', 'English speaking guide'],
                'exclusions': ['International flights', 'Travel insurance', 'Personal expenses'],
                'cancellation_policy': 'Free cancellation up to 7 days before departure.',
                'important_notes': 'Follow guide instructions when near Komodo dragons. Sunscreen and hat recommended.',
                'base_price': 4500000,
                'visa_price': 0,
                'tipping_price': 75000,
                'reseller_groups': [],  # Available to all
            },
            {
                'supplier_idx': 4,  # Komodo Dragons Adventure
                'name': '4D3N Komodo & Rinca Island Tour',
                'itinerary': None,  # Will be generated
                'country': 'Indonesia',
                'days': 4,
                'nights': 3,
                'max_group_size': 12,
                'tour_type': TourType.CONVENTIONAL,
                'highlights': ['Komodo Island', 'Rinca Island', 'Pink Beach', 'Manta Point', 'Kanawa Island'],
                'inclusions': ['3 nights accommodation', 'All meals', 'Boat transportation', 'All entrance fees', 'English speaking guide'],
                'exclusions': ['International flights', 'Travel insurance'],
                'cancellation_policy': 'Free cancellation up to 7 days before departure.',
                'important_notes': 'Physical activity involved. Follow safety guidelines around Komodo dragons.',
                'base_price': 6500000,
                'visa_price': 0,
                'tipping_price': 100000,
                'reseller_groups': [0, 1],  # Premium & Standard
            },
            {
                'supplier_idx': 5,  # Lombok Wisata Sejahtera
                'name': '4D3N Lombok Beach Paradise',
                'itinerary': None,  # Will be generated
                'country': 'Indonesia',
                'days': 4,
                'nights': 3,
                'max_group_size': 15,
                'tour_type': TourType.CONVENTIONAL,
                'highlights': ['Gili Trawangan', 'Sendang Gile Waterfall', 'Sasak Village', 'Snorkeling', 'Sunset Viewing'],
                'inclusions': ['3 nights beachfront hotel', 'Daily breakfast', 'Boat transfers to Gili', 'English speaking guide', 'Snorkeling equipment'],
                'exclusions': ['Lunch and dinner', 'Travel insurance', 'Personal expenses'],
                'cancellation_policy': 'Free cancellation up to 7 days before departure.',
                'important_notes': 'Swimming skills recommended. Sunscreen essential.',
                'base_price': 3800000,
                'visa_price': 0,
                'tipping_price': 60000,
                'reseller_groups': [1, 2],  # Standard & New Partners
            },
            {
                'supplier_idx': 6,  # Jakarta City Tours
                'name': '2D1N Jakarta City Experience',
                'itinerary': None,  # Will be generated
                'country': 'Indonesia',
                'days': 2,
                'nights': 1,
                'max_group_size': 20,
                'tour_type': TourType.CONVENTIONAL,
                'highlights': ['National Monument', 'Old Batavia', 'Jakarta Cathedral', 'Istiqlal Mosque', 'Culinary Tour'],
                'inclusions': ['1 night hotel accommodation', 'Breakfast', 'City tour transportation', 'English speaking guide', 'Entrance fees'],
                'exclusions': ['Lunch and dinner', 'Travel insurance', 'Personal expenses'],
                'cancellation_policy': 'Free cancellation up to 3 days before departure.',
                'important_notes': 'Traffic can be heavy. Comfortable walking shoes recommended.',
                'base_price': 1500000,
                'visa_price': 0,
                'tipping_price': 20000,
                'reseller_groups': [1, 2],  # Standard & New Partners
            },
            {
                'supplier_idx': 7,  # Bandung Travel Agency
                'name': '3D2N Bandung Highland Escape',
                'itinerary': None,  # Will be generated
                'country': 'Indonesia',
                'days': 3,
                'nights': 2,
                'max_group_size': 18,
                'tour_type': TourType.CONVENTIONAL,
                'highlights': ['Tangkuban Perahu Volcano', 'Kawah Putih', 'Ciater Hot Springs', 'Tea Plantations', 'Shopping Outlets'],
                'inclusions': ['2 nights hotel accommodation', 'Daily breakfast', 'Private transportation', 'English speaking guide', 'Entrance fees'],
                'exclusions': ['Lunch and dinner', 'Travel insurance', 'Personal expenses'],
                'cancellation_policy': 'Free cancellation up to 5 days before departure.',
                'important_notes': 'Cool weather, bring jacket. Mountain roads can be winding.',
                'base_price': 2200000,
                'visa_price': 0,
                'tipping_price': 35000,
                'reseller_groups': [1],  # Standard Partners
            },
            {
                'supplier_idx': 8,  # Lake Toba Tours
                'name': '4D3N Lake Toba Cultural Tour',
                'itinerary': None,  # Will be generated
                'country': 'Indonesia',
                'days': 4,
                'nights': 3,
                'max_group_size': 15,
                'tour_type': TourType.CONVENTIONAL,
                'highlights': ['Lake Toba', 'Samosir Island', 'Batak Houses', 'Traditional Dance', 'Sipiso-piso Waterfall'],
                'inclusions': ['3 nights hotel accommodation', 'Daily breakfast', 'Boat transfers', 'English speaking guide', 'Cultural show'],
                'exclusions': ['Lunch and dinner', 'Travel insurance', 'Personal expenses'],
                'cancellation_policy': 'Free cancellation up to 7 days before departure.',
                'important_notes': 'Relaxed pace, perfect for cultural immersion.',
                'base_price': 3500000,
                'visa_price': 0,
                'tipping_price': 55000,
                'reseller_groups': [1],  # Standard Partners
            },
            {
                'supplier_idx': 9,  # Toraja Cultural Tours
                'name': '4D3N Toraja Funeral Ceremony Experience',
                'itinerary': None,  # Will be generated
                'country': 'Indonesia',
                'days': 4,
                'nights': 3,
                'max_group_size': 12,
                'tour_type': TourType.CONVENTIONAL,
                'highlights': ['Traditional Torajan Houses', 'Lemo Burial Cliffs', 'Kete Kesu Village', 'Buntu Kalando', 'Torajan Markets'],
                'inclusions': ['3 nights hotel accommodation', 'Daily breakfast', 'Private transportation', 'English speaking guide', 'Cultural experiences'],
                'exclusions': ['Lunch and dinner', 'Travel insurance', 'Personal expenses'],
                'cancellation_policy': 'Free cancellation up to 7 days before departure.',
                'important_notes': 'Cultural sensitivity important. Funeral ceremonies are sacred events.',
                'base_price': 4200000,
                'visa_price': 0,
                'tipping_price': 65000,
                'reseller_groups': [0, 1],  # Premium & Standard
            },
        ]
        
        tours = []
        for data in tours_data:
            supplier = suppliers[data['supplier_idx']]
            slug = slugify(data['name'])
            # Ensure unique slug
            base_slug = slug
            counter = 1
            while TourPackage.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            # Generate itinerary if not provided
            itinerary = data.get('itinerary')
            if not itinerary:
                itinerary = self._generate_itinerary_text(data['name'], data['days'], data.get('highlights', []))
            
            tour = TourPackage.objects.create(
                supplier=supplier,
                name=data['name'],
                slug=slug,
                itinerary=itinerary,
                country=data['country'],
                days=data['days'],
                nights=data['nights'],
                max_group_size=data['max_group_size'],
                tour_type=data['tour_type'],
                highlights=data['highlights'],
                inclusions=data['inclusions'],
                exclusions=data['exclusions'],
                cancellation_policy=data['cancellation_policy'],
                important_notes=data['important_notes'],
                base_price=data['base_price'],
                visa_price=data.get('visa_price', 0),
                tipping_price=data.get('tipping_price', 0),
                is_active=True,
                commission=random.randint(100000, 500000),  # Fixed commission amount in IDR
            )
            
            # Assign reseller groups
            for group_idx in data['reseller_groups']:
                if group_idx < len(reseller_groups):
                    tour.reseller_groups.add(reseller_groups[group_idx])
            
            # Create tour dates
            self._create_tour_dates(tour, data['base_price'])
            
            tours.append(tour)
        
        return tours

    def _create_tour_dates(self, tour, base_price):
        """Create tour dates for a tour package."""
        today = timezone.now().date()
        
        # Create 6 tour dates over the next 3 months
        for i in range(6):
            departure_date = today + timedelta(days=30 + (i * 15))
            
            # Vary price based on season (high season = 20% more)
            is_high_season = i % 3 == 0  # Every 3rd date is high season
            price = int(base_price * (1.2 if is_high_season else 1.0))
            
            # Random seats between 8 and 20
            total_seats = random.randint(8, 20)
            
            tour_date = TourDate.objects.create(
                package=tour,
                departure_date=departure_date,
                price=price,
                total_seats=total_seats,
                is_high_season=is_high_season,
            )
            
            # TourDate automatically generates seat slots on save

    def _generate_itinerary_text(self, tour_name, days, highlights):
        """Generate itinerary text for a tour package based on tour name and highlights."""
        # Get tour-specific itinerary based on tour name and highlights
        tour_name_lower = tour_name.lower()
        
        # Create detailed itinerary based on tour characteristics
        if 'bali' in tour_name_lower:
            if 'cultural' in tour_name_lower or 'culture' in tour_name_lower:
                itinerary = [
                    {'day': 1, 'title': 'Arrival in Bali & Ubud Orientation', 
                     'description': 'Airport pickup from Ngurah Rai International Airport. Transfer to Ubud hotel with check-in. Welcome dinner at traditional Balinese restaurant. Evening tour briefing and introduction to Balinese culture.'},
                    {'day': 2, 'title': 'Cultural Immersion Day', 
                     'description': 'Early morning visit to Tegalalang Rice Terrace for sunrise views and photography. Visit Tirta Empul Temple for holy water purification ritual. Explore Ubud Monkey Forest and learn about Balinese Hinduism. Afternoon traditional Balinese dance performance. Evening free time to explore Ubud Market.'},
                    {'day': 3, 'title': 'Departure', 
                     'description': 'Morning breakfast at hotel. Last-minute souvenir shopping at Ubud Market. Check-out and transfer to Ngurah Rai International Airport for departure flight.'},
                ]
            elif 'beach' in tour_name_lower or 'island' in tour_name_lower:
                itinerary = [
                    {'day': 1, 'title': 'Arrival & Nusa Dua Check-in', 
                     'description': 'Airport pickup and transfer to beachfront hotel in Nusa Dua. Hotel check-in and welcome briefing. Afternoon free time to relax on the beach. Evening dinner at hotel restaurant.'},
                    {'day': 2, 'title': 'Nusa Penida Island Hopping', 
                     'description': 'Early morning boat transfer to Nusa Penida Island. Visit Kelingking Beach (T-Rex viewpoint) and take photos. Explore Crystal Bay for snorkeling with colorful fish. Visit Angel\'s Billabong and Broken Beach. Snorkeling with Manta Rays at Manta Point (seasonal). Return to Nusa Dua in the evening.'},
                    {'day': 3, 'title': 'Water Sports & Beach Activities', 
                     'description': 'Morning water sports activities (jet ski, parasailing, banana boat). Afternoon visit to Uluwatu Temple for sunset views and Kecak dance performance. Traditional seafood dinner at Jimbaran Beach.'},
                    {'day': 4, 'title': 'Departure', 
                     'description': 'Morning breakfast and beach relaxation. Check-out from hotel. Transfer to Ngurah Rai International Airport for departure flight.'},
                ]
            elif 'muslim' in tour_name_lower:
                itinerary = [
                    {'day': 1, 'title': 'Arrival & Halal Welcome', 
                     'description': 'Airport pickup from Ngurah Rai International Airport. Transfer to halal-certified hotel in Denpasar. Hotel check-in and welcome briefing. Evening halal dinner at certified restaurant. Prayer time arrangements.'},
                    {'day': 2, 'title': 'Tanah Lot & Uluwatu Temple Tour', 
                     'description': 'Morning visit to Tanah Lot Temple (sea temple) with halal lunch break. Afternoon visit to Uluwatu Temple for sunset views. Evening Kecak dance performance. Halal dinner at certified restaurant. Prayer facilities available throughout the day.'},
                    {'day': 3, 'title': 'Cultural Sites & Halal Experiences', 
                     'description': 'Visit Taman Ayun Temple and learn about Balinese architecture. Explore traditional markets with halal food options. Visit local halal-certified restaurants. Cultural show with traditional performances. Evening halal dinner.'},
                    {'day': 4, 'title': 'Tegallalang & Traditional Villages', 
                     'description': 'Morning visit to Tegalalang Rice Terrace. Explore traditional Balinese villages. Visit local halal-certified coffee plantation. Traditional Balinese dance workshop. Halal lunch and dinner.'},
                    {'day': 5, 'title': 'Departure', 
                     'description': 'Morning breakfast at hotel. Last-minute shopping at halal-certified souvenir shops. Check-out and transfer to Ngurah Rai International Airport. Prayer time arrangements before departure.'},
                ]
            else:
                itinerary = self._get_generic_itinerary(days)
        elif 'yogyakarta' in tour_name_lower or 'jogja' in tour_name_lower:
            if 'solo' in tour_name_lower:
                itinerary = [
                    {'day': 1, 'title': 'Arrival & Yogyakarta City Tour', 
                     'description': 'Airport pickup from Adisucipto International Airport. Transfer to hotel in Yogyakarta. Afternoon city tour: Visit Kraton Palace (Sultan\'s Palace) and learn about Javanese royal history. Explore Taman Sari (Water Castle). Evening walk along Malioboro Street for shopping and street food.'},
                    {'day': 2, 'title': 'Borobudur & Prambanan Temples', 
                     'description': 'Early morning departure to Borobudur Temple (world\'s largest Buddhist temple). Sunrise viewing and temple exploration. Visit Prambanan Temple (largest Hindu temple in Indonesia). Learn about ancient Javanese architecture and history. Traditional Javanese lunch. Return to Yogyakarta in the evening.'},
                    {'day': 3, 'title': 'Solo City & Batik Workshop', 
                     'description': 'Morning transfer to Solo (Surakarta). Visit Kraton Solo (Surakarta Palace). Participate in traditional batik making workshop. Explore traditional markets and local crafts. Traditional Javanese dinner with cultural performance.'},
                    {'day': 4, 'title': 'Departure', 
                     'description': 'Morning breakfast at hotel. Visit local batik showroom for souvenir shopping. Check-out and transfer to Adisucipto International Airport for departure flight.'},
                ]
            else:
                itinerary = [
                    {'day': 1, 'title': 'Arrival & Yogyakarta Orientation', 
                     'description': 'Airport pickup from Adisucipto International Airport. Transfer to hotel in Yogyakarta city center. Hotel check-in and welcome briefing. Afternoon visit to Kraton Palace (Sultan\'s Palace). Evening walk along Malioboro Street for shopping and local cuisine.'},
                    {'day': 2, 'title': 'Borobudur Sunrise & Prambanan', 
                     'description': 'Early morning (4:00 AM) departure to Borobudur Temple for sunrise experience. Explore the world\'s largest Buddhist temple and learn about its history. Visit Prambanan Temple (largest Hindu temple in Indonesia). Traditional Javanese lunch. Return to Yogyakarta. Evening free time.'},
                    {'day': 3, 'title': 'Departure', 
                     'description': 'Morning breakfast at hotel. Visit Taman Sari (Water Castle) for final exploration. Last-minute souvenir shopping at Malioboro Street. Check-out and transfer to Adisucipto International Airport for departure flight.'},
                ]
        elif 'bromo' in tour_name_lower:
            if 'ijen' in tour_name_lower:
                itinerary = [
                    {'day': 1, 'title': 'Arrival & Transfer to Probolinggo', 
                     'description': 'Airport pickup from Juanda International Airport (Surabaya). Transfer to hotel in Probolinggo (approximately 3 hours). Hotel check-in and tour briefing. Early dinner and rest for early morning departure.'},
                    {'day': 2, 'title': 'Mount Bromo Sunrise Adventure', 
                     'description': 'Early morning (2:00 AM) departure by jeep to Mount Bromo area. Arrive at Penanjakan viewpoint for sunrise (around 5:00 AM). Witness spectacular sunrise over Mount Bromo and surrounding volcanoes. Cross the Sea of Sand to Mount Bromo crater. Climb to the crater rim and explore. Return to hotel for breakfast and rest. Afternoon transfer to Banyuwangi (approximately 6 hours). Hotel check-in in Banyuwangi.'},
                    {'day': 3, 'title': 'Ijen Blue Fire Experience', 
                     'description': 'Late night (11:00 PM) departure to Ijen Crater. Begin trek to Ijen Crater (approximately 2 hours). Witness the famous blue fire phenomenon (best viewed 2-4 AM). Watch sunrise from Ijen Crater rim. Explore sulfur mining area and learn about local miners. Return to hotel for breakfast and rest. Afternoon visit to local attractions or free time.'},
                    {'day': 4, 'title': 'Departure', 
                     'description': 'Morning breakfast at hotel. Check-out and transfer to Juanda International Airport (Surabaya) for departure flight.'},
                ]
            else:
                itinerary = [
                    {'day': 1, 'title': 'Arrival & Transfer to Bromo Area', 
                     'description': 'Airport pickup from Juanda International Airport (Surabaya) or Probolinggo Station. Transfer to hotel near Mount Bromo (approximately 2-3 hours). Hotel check-in and tour briefing. Early dinner and rest for early morning adventure.'},
                    {'day': 2, 'title': 'Mount Bromo Sunrise & Crater Exploration', 
                     'description': 'Early morning (2:00 AM) departure by jeep to Penanjakan viewpoint. Arrive at viewpoint before sunrise (around 5:00 AM). Witness spectacular sunrise over Mount Bromo, Mount Batok, and Mount Semeru. Cross the Sea of Sand (Lautan Pasir) by jeep or on foot. Climb Mount Bromo stairs to reach the crater rim. Explore the active volcano crater and take photos. Visit Madakaripura Waterfall (optional, if time permits). Return to hotel for breakfast and rest. Check-out and transfer back to airport/station for departure.'},
                ]
        elif 'raja ampat' in tour_name_lower or 'diving' in tour_name_lower:
            itinerary = [
                {'day': 1, 'title': 'Arrival in Raja Ampat', 
                 'description': 'Airport pickup from Domine Eduard Osok Airport (Sorong). Transfer to harbor and boat to Raja Ampat (approximately 2-3 hours). Arrive at accommodation (homestay or resort). Welcome briefing and diving/snorkeling equipment check. Evening dinner and rest.'},
                {'day': 2, 'title': 'Diving & Snorkeling - Manta Ray Spotting', 
                 'description': 'Early morning boat departure to Manta Sandy or Manta Ridge for manta ray spotting. Snorkeling or diving with manta rays (seasonal, best from October to April). Visit Arborek Island for village tour and cultural interaction. Afternoon snorkeling at nearby coral reefs. Return to accommodation in the evening.'},
                {'day': 3, 'title': 'Island Hopping & Bird Watching', 
                 'description': 'Morning boat trip to Wayag Islands for iconic viewpoint (weather permitting). Snorkeling at various dive sites with diverse marine life. Visit Pianemo Islands for stunning karst formations. Bird watching at local bird sanctuaries. Afternoon snorkeling at pristine coral reefs.'},
                {'day': 4, 'title': 'Coral Reef Exploration', 
                 'description': 'Full day diving/snorkeling at multiple sites. Explore diverse coral reef ecosystems (home to 75% of world\'s coral species). Encounter various marine species including colorful fish, turtles, and reef sharks. Visit local islands for beach relaxation. Evening return to accommodation.'},
                {'day': 5, 'title': 'Departure', 
                 'description': 'Morning breakfast at accommodation. Final snorkeling session or free time. Check-out and boat transfer back to Sorong. Transfer to Domine Eduard Osok Airport for departure flight.'},
            ]
        elif 'komodo' in tour_name_lower:
            if 'rinca' in tour_name_lower:
                itinerary = [
                    {'day': 1, 'title': 'Arrival in Labuan Bajo', 
                     'description': 'Airport pickup from Komodo Airport (Labuan Bajo). Transfer to hotel. Hotel check-in and welcome briefing. Evening sunset viewing at local viewpoint. Dinner at local restaurant.'},
                    {'day': 2, 'title': 'Komodo Island & Pink Beach', 
                     'description': 'Early morning boat departure to Komodo Island. Guided trek to see Komodo dragons in their natural habitat. Learn about Komodo dragon behavior and conservation. Visit Pink Beach for swimming and snorkeling. Lunch on the boat. Afternoon snorkeling at nearby sites. Return to Labuan Bajo in the evening.'},
                    {'day': 3, 'title': 'Rinca Island & Padar Island', 
                     'description': 'Morning boat trip to Rinca Island. Another opportunity to see Komodo dragons with different landscape. Visit Padar Island for iconic viewpoint and hiking. Panoramic views of three bays with different colored beaches. Snorkeling at Manta Point (if conditions permit). Return to Labuan Bajo.'},
                    {'day': 4, 'title': 'Kanawa Island & Departure', 
                     'description': 'Morning visit to Kanawa Island for final snorkeling session. Explore pristine coral reefs and marine life. Beach relaxation. Return to Labuan Bajo. Check-out from hotel. Transfer to Komodo Airport for departure flight.'},
                ]
            else:
                itinerary = [
                    {'day': 1, 'title': 'Arrival & Labuan Bajo Orientation', 
                     'description': 'Airport pickup from Komodo Airport (Labuan Bajo). Transfer to hotel. Hotel check-in and welcome briefing. Evening sunset viewing at local viewpoint. Traditional dinner at local restaurant.'},
                    {'day': 2, 'title': 'Komodo Island Adventure', 
                     'description': 'Early morning boat departure to Komodo National Park. Arrive at Komodo Island and begin guided trek. See Komodo dragons in their natural habitat with experienced rangers. Learn about Komodo dragon behavior, diet, and conservation efforts. Visit Pink Beach for swimming and snorkeling in pink sand. Lunch on the boat. Afternoon snorkeling at nearby coral reefs. Return to Labuan Bajo in the evening.'},
                    {'day': 3, 'title': 'Departure', 
                     'description': 'Morning breakfast at hotel. Optional short boat trip to nearby snorkeling sites or free time. Check-out from hotel. Transfer to Komodo Airport for departure flight.'},
                ]
        elif 'lombok' in tour_name_lower:
            itinerary = [
                {'day': 1, 'title': 'Arrival & Senggigi Check-in', 
                 'description': 'Airport pickup from Lombok International Airport. Transfer to beachfront hotel in Senggigi. Hotel check-in and welcome briefing. Evening beach walk and dinner at hotel restaurant.'},
                {'day': 2, 'title': 'Gili Trawangan Island Hopping', 
                 'description': 'Morning boat transfer to Gili Trawangan Island. Snorkeling with sea turtles at Turtle Point. Explore the island by bicycle or horse cart. Visit local restaurants and beach bars. Afternoon snorkeling at various coral reef sites. Return to Senggigi in the evening.'},
                {'day': 3, 'title': 'Sendang Gile Waterfall & Sasak Village', 
                 'description': 'Morning visit to Sendang Gile Waterfall in North Lombok. Trek through lush forest to reach the waterfall. Swimming in natural pools. Visit traditional Sasak village to learn about local culture and traditions. Traditional Sasak lunch. Return to hotel in the afternoon.'},
                {'day': 4, 'title': 'Departure', 
                 'description': 'Morning breakfast at hotel. Beach relaxation or optional activities. Check-out from hotel. Transfer to Lombok International Airport for departure flight.'},
            ]
        elif 'jakarta' in tour_name_lower:
            itinerary = [
                {'day': 1, 'title': 'Arrival & City Tour', 
                 'description': 'Airport pickup from Soekarno-Hatta International Airport. Transfer to hotel in Jakarta city center. Hotel check-in and welcome briefing. Afternoon city tour: Visit National Monument (Monas) and learn about Indonesian history. Explore Old Batavia (Kota Tua) with colonial architecture. Visit Jakarta History Museum. Evening culinary tour at local food markets.'},
                {'day': 2, 'title': 'Cultural & Religious Sites', 
                 'description': 'Morning visit to Istiqlal Mosque (largest mosque in Southeast Asia). Visit Jakarta Cathedral nearby. Explore National Museum of Indonesia. Afternoon visit to Taman Mini Indonesia Indah (Miniature Park of Indonesia). Traditional Indonesian dinner with cultural show. Return to hotel.'},
                {'day': 3, 'title': 'Departure', 
                 'description': 'Morning breakfast at hotel. Last-minute shopping at modern malls or traditional markets. Check-out and transfer to Soekarno-Hatta International Airport for departure flight.'},
            ]
        elif 'bandung' in tour_name_lower:
            itinerary = [
                {'day': 1, 'title': 'Arrival & Bandung Orientation', 
                 'description': 'Airport pickup from Husein Sastranegara Airport. Transfer to hotel in Bandung. Hotel check-in and welcome briefing. Afternoon visit to shopping outlets for factory outlets and local products. Evening dinner at local restaurant.'},
                {'day': 2, 'title': 'Volcano & Hot Springs', 
                 'description': 'Morning visit to Tangkuban Perahu Volcano. Explore the active crater and learn about volcanic activity. Visit Kawah Putih (White Crater) for stunning turquoise lake views. Afternoon visit to Ciater Hot Springs for relaxation. Traditional Sundanese lunch. Return to hotel in the evening.'},
                {'day': 3, 'title': 'Tea Plantations & Departure', 
                 'description': 'Morning visit to tea plantations in the highlands. Learn about tea production and processing. Enjoy tea tasting session. Scenic views of rolling tea fields. Traditional lunch. Check-out from hotel. Transfer to Husein Sastranegara Airport for departure flight.'},
            ]
        elif 'toba' in tour_name_lower:
            itinerary = [
                {'day': 1, 'title': 'Arrival & Lake Toba Orientation', 
                 'description': 'Airport pickup from Kualanamu International Airport (Medan). Transfer to Parapat on Lake Toba (approximately 4 hours). Boat transfer to Samosir Island. Hotel check-in and welcome briefing. Evening dinner with traditional Batak music performance.'},
                {'day': 2, 'title': 'Samosir Island Cultural Tour', 
                 'description': 'Morning visit to traditional Batak houses (rumah adat). Learn about Batak culture, traditions, and architecture. Visit ancient stone chairs and megalithic sites. Traditional Batak dance performance. Visit local markets and handicraft centers. Traditional Batak lunch.'},
                {'day': 3, 'title': 'Lake Activities & Sipiso-piso Waterfall', 
                 'description': 'Morning boat trip on Lake Toba for scenic views. Visit Sipiso-piso Waterfall (one of Indonesia\'s highest waterfalls). Explore surrounding areas and take photos. Afternoon return to Samosir Island. Free time for relaxation or optional activities.'},
                {'day': 4, 'title': 'Departure', 
                 'description': 'Morning breakfast at hotel. Final cultural experiences or souvenir shopping. Boat transfer back to Parapat. Transfer to Kualanamu International Airport for departure flight.'},
            ]
        elif 'toraja' in tour_name_lower:
            itinerary = [
                {'day': 1, 'title': 'Arrival in Toraja', 
                 'description': 'Airport pickup from Sultan Hasanuddin Airport (Makassar). Transfer to Rantepao, Toraja (approximately 8 hours by road). Hotel check-in and welcome briefing. Evening dinner and rest after long journey.'},
                {'day': 2, 'title': 'Traditional Torajan Houses & Burial Sites', 
                 'description': 'Morning visit to Kete Kesu Village to see traditional Torajan houses (tongkonan). Learn about Torajan architecture and cultural significance. Visit Lemo Burial Cliffs with hanging graves and tau-tau (wooden effigies). Explore Londa Cave burial site. Traditional Torajan lunch. Afternoon visit to traditional markets.'},
                {'day': 3, 'title': 'Cultural Sites & Funeral Ceremonies', 
                 'description': 'Visit Buntu Kalando (traditional house of Torajan nobility). Explore more burial sites and learn about Torajan funeral traditions. If timing permits, witness traditional funeral ceremony (sacred event, requires cultural sensitivity). Visit local handicraft centers. Traditional Torajan dinner with cultural performance.'},
                {'day': 4, 'title': 'Departure', 
                 'description': 'Morning breakfast at hotel. Final cultural experiences or souvenir shopping. Transfer back to Sultan Hasanuddin Airport (Makassar) for departure flight.'},
            ]
        else:
            itinerary = self._get_generic_itinerary(days)
        
        # Generate itinerary text from items
        itinerary_text = '\n\n'.join([
            f"Day {item['day']}: {item['title']}\n{item['description']}"
            for item in itinerary
        ])
        
        return itinerary_text
    
    def _get_generic_itinerary(self, days):
        """Get generic itinerary template based on number of days."""
        templates = {
            2: [
                {'day': 1, 'title': 'Arrival & Full Day Tour', 
                 'description': 'Airport pickup, hotel check-in, and full day tour of main attractions. Enjoy local experiences and cultural activities. Evening dinner and rest.'},
                {'day': 2, 'title': 'Departure', 
                 'description': 'Morning breakfast and final activities. Souvenir shopping. Check-out and airport transfer for departure flight.'},
            ],
            3: [
                {'day': 1, 'title': 'Arrival & Welcome', 
                 'description': 'Airport pickup, hotel check-in, welcome dinner, and tour briefing. Introduction to local culture and customs.'},
                {'day': 2, 'title': 'Full Day Tour', 
                 'description': 'Visit main attractions, enjoy local experiences, and participate in cultural activities. Traditional lunch. Evening free time or optional activities.'},
                {'day': 3, 'title': 'Departure', 
                 'description': 'Morning breakfast at hotel. Final activities and souvenir shopping. Check-out and airport transfer for departure flight.'},
            ],
            4: [
                {'day': 1, 'title': 'Arrival & City Tour', 
                 'description': 'Airport pickup, hotel check-in, and afternoon city tour. Explore local landmarks and get oriented with the area. Evening dinner at local restaurant.'},
                {'day': 2, 'title': 'Main Attractions', 
                 'description': 'Full day tour of major attractions and landmarks. Visit historical sites, natural wonders, or cultural centers. Traditional lunch included.'},
                {'day': 3, 'title': 'Cultural Experience', 
                 'description': 'Visit cultural sites, local markets, and participate in traditional experiences. Learn about local customs and traditions. Evening cultural performance (if available).'},
                {'day': 4, 'title': 'Departure', 
                 'description': 'Morning breakfast at hotel. Free time for last-minute shopping or relaxation. Check-out and airport transfer for departure flight.'},
            ],
            5: [
                {'day': 1, 'title': 'Arrival & Orientation', 
                 'description': 'Airport pickup, hotel check-in, and welcome orientation. Introduction to the tour program and local area. Evening welcome dinner.'},
                {'day': 2, 'title': 'Day Trip Adventure', 
                 'description': 'Full day trip to nearby attractions or natural wonders. Explore unique destinations and enjoy outdoor activities. Packed lunch or local restaurant.'},
                {'day': 3, 'title': 'City Exploration', 
                 'description': 'Explore the city, visit museums, historical sites, and enjoy local cuisine. Learn about local history and culture. Evening free time.'},
                {'day': 4, 'title': 'Cultural Immersion', 
                 'description': 'Deep dive into local culture, traditions, and experiences. Visit traditional villages, participate in workshops, or attend cultural events. Traditional dinner with cultural show.'},
                {'day': 5, 'title': 'Departure', 
                 'description': 'Morning breakfast at hotel. Final activities, last-minute shopping, and souvenir hunting. Check-out and airport transfer for departure flight.'},
            ],
        }
        return templates.get(days, templates[3])

    def _create_bookings(self, resellers, tours):
        """Create mock bookings with payments and seat slots."""
        bookings = []
        
        # Get all tour dates
        tour_dates_list = list(TourDate.objects.select_related('package').all())
        
        if not tour_dates_list:
            self.stdout.write(self.style.WARNING('No tour dates available. Skipping booking creation.'))
            return bookings
        
        # Create bookings for different scenarios
        booking_scenarios = [
            {
                'reseller_idx': 0,
                'tour_date_idx': 0,
                'num_passengers': 2,
                'status': BookingStatus.CONFIRMED,
                'payment_status': PaymentStatus.APPROVED,
            },
            {
                'reseller_idx': 1,
                'tour_date_idx': min(1, len(tour_dates_list) - 1),
                'num_passengers': 4,
                'status': BookingStatus.CONFIRMED,
                'payment_status': PaymentStatus.APPROVED,
            },
            {
                'reseller_idx': 2,
                'tour_date_idx': min(2, len(tour_dates_list) - 1),
                'num_passengers': 1,
                'status': BookingStatus.PENDING,
                'payment_status': PaymentStatus.PENDING,
            },
            {
                'reseller_idx': 0,
                'tour_date_idx': min(3, len(tour_dates_list) - 1),
                'num_passengers': 3,
                'status': BookingStatus.CONFIRMED,
                'payment_status': PaymentStatus.APPROVED,
            },
            {
                'reseller_idx': 3,
                'tour_date_idx': min(4, len(tour_dates_list) - 1),
                'num_passengers': 2,
                'status': BookingStatus.PENDING,
                'payment_status': PaymentStatus.PENDING,
            },
            {
                'reseller_idx': 4,
                'tour_date_idx': min(5, len(tour_dates_list) - 1),
                'num_passengers': 2,
                'status': BookingStatus.CONFIRMED,
                'payment_status': PaymentStatus.APPROVED,
            },
            {
                'reseller_idx': 5,
                'tour_date_idx': min(6, len(tour_dates_list) - 1),
                'num_passengers': 1,
                'status': BookingStatus.CONFIRMED,
                'payment_status': PaymentStatus.APPROVED,
            },
            {
                'reseller_idx': 6,
                'tour_date_idx': min(7, len(tour_dates_list) - 1),
                'num_passengers': 3,
                'status': BookingStatus.PENDING,
                'payment_status': PaymentStatus.PENDING,
            },
            {
                'reseller_idx': 7,
                'tour_date_idx': min(8, len(tour_dates_list) - 1),
                'num_passengers': 2,
                'status': BookingStatus.CONFIRMED,
                'payment_status': PaymentStatus.APPROVED,
            },
            {
                'reseller_idx': 8,
                'tour_date_idx': min(9, len(tour_dates_list) - 1),
                'num_passengers': 4,
                'status': BookingStatus.CONFIRMED,
                'payment_status': PaymentStatus.APPROVED,
            },
        ]
        
        passenger_names = [
            ['Budi Santoso', 'Siti Nurhaliza'],
            ['Ahmad Fauzi', 'Dewi Sartika', 'Rahmat Hidayat', 'Maria Magdalena'],
            ['Wulan Sari'],
            ['Asep Gunawan', 'Indah Permata', 'Dedi Kurniawan'],
            ['Fitri Ayu', 'Andi Makassar'],
            ['Joko Widodo', 'Ibu Joko'],
            ['Samsul Hadi'],
            ['Rina Wati', 'Bambang Sutrisno', 'Ani Setiawan'],
            ['Agus Prasetyo', 'Sri Handayani'],
            ['Kartika Sari', 'Ahmad Yani', 'Sinta Dewi', 'Rudi Hartono'],
        ]
        
        for idx, scenario in enumerate(booking_scenarios):
            if scenario['tour_date_idx'] >= len(tour_dates_list):
                continue
            
            tour_date = tour_dates_list[scenario['tour_date_idx']]
            reseller = resellers[scenario['reseller_idx']]
            
            # Get available seat slots
            available_slots = tour_date.seat_slots.filter(status=SeatSlotStatus.AVAILABLE)[:scenario['num_passengers']]
            
            if available_slots.count() < scenario['num_passengers']:
                continue  # Skip if not enough seats
            
            # Calculate total amount: (tour_date.price * num_passengers) + platform_fee
            platform_fee = 50000
            total_amount = (tour_date.price * scenario['num_passengers']) + platform_fee
            
            booking = Booking.objects.create(
                reseller=reseller,
                tour_date=tour_date,
                status=scenario['status'],
                platform_fee=platform_fee,
                total_amount=total_amount,
                notes=f'Booking created for {scenario["num_passengers"]} passengers.',
            )
            
            # Assign seat slots and add passenger details
            passengers = passenger_names[idx] if idx < len(passenger_names) else [f'Passenger {i+1}' for i in range(scenario['num_passengers'])]
            
            for slot_idx, slot in enumerate(available_slots):
                passenger_name = passengers[slot_idx] if slot_idx < len(passengers) else f'Passenger {slot_idx+1}'
                
                slot.booking = booking
                slot.status = SeatSlotStatus.BOOKED
                slot.passenger_name = passenger_name
                # All tours are in Indonesia, so no visa required for Indonesian nationals
                slot.visa_required = False
                slot.special_requests = random.choice(['', 'Makanan vegetarian', 'Kursi dekat jendela', 'Tidak ada permintaan khusus', 'Makanan halal'])
                slot.save()
            
            # Create payment
            payment = Payment.objects.create(
                booking=booking,
                amount=booking.total_amount,
                transfer_date=timezone.now().date() - timedelta(days=random.randint(1, 7)),
                status=scenario['payment_status'],
            )
            
            bookings.append(booking)
        
        return bookings

