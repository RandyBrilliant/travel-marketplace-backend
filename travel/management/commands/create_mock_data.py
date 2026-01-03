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

from account.models import CustomUser, SupplierProfile, ResellerProfile, UserRole
from travel.models import (
    TourPackage, TourDate, TourImage, ItineraryItem, Booking, Payment,
    SeatSlot, SeatSlotStatus, BookingStatus, PaymentStatus,
    TourCategory, TourBadge, TourType, ResellerGroup
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
        ItineraryItem.objects.all().delete()
        TourPackage.objects.all().delete()
        ResellerGroup.objects.all().delete()
        ResellerProfile.objects.all().delete()
        SupplierProfile.objects.all().delete()
        CustomUser.objects.filter(role__in=[UserRole.SUPPLIER, UserRole.RESELLER]).delete()

    def _create_suppliers(self):
        """Create mock suppliers - all Indonesian tour companies."""
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
        for data in suppliers_data:
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
            suppliers.append(supplier)
        
        return suppliers

    def _create_resellers(self):
        """Create mock resellers with MLM relationships - Indonesian names."""
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
                commission_rate=random.uniform(8.0, 15.0),
                upline_commission_rate=random.uniform(2.0, 5.0),
                bank_name=data['bank_name'],
                bank_account_name=data['bank_account_name'],
                bank_account_number=data['bank_account_number'],
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
                'summary': 'Discover the rich culture and stunning landscapes of Bali',
                'description': 'Experience the best of Bali with visits to ancient temples, rice terraces, and traditional villages. Includes accommodation, meals, and guided tours.',
                'city': 'Ubud',
                'country': 'Indonesia',
                'days': 3,
                'nights': 2,
                'max_group_size': 12,
                'group_type': 'Small Group',
                'tour_type': TourType.CONVENTIONAL,
                'category': TourCategory.CULTURAL,
                'tags': ['Temple', 'Rice Terrace', 'Traditional'],
                'highlights': ['Tegalalang Rice Terrace', 'Tirta Empul Temple', 'Ubud Monkey Forest', 'Traditional Balinese Dance'],
                'inclusions': ['2 nights hotel accommodation', 'Daily breakfast', 'Airport transfers', 'English speaking guide', 'Entrance fees'],
                'exclusions': ['International flights', 'Lunch and dinner', 'Travel insurance', 'Personal expenses'],
                'meeting_point': 'Ngurah Rai International Airport (DPS)',
                'cancellation_policy': 'Free cancellation up to 7 days before departure. 50% refund for cancellations 3-7 days before. No refund for cancellations less than 3 days.',
                'important_notes': 'Please bring comfortable walking shoes and appropriate clothing for temple visits.',
                'base_price': 3500000,
                'currency': 'IDR',
                'badge': TourBadge.BEST_SELLER,
                'is_featured': True,
                'reseller_groups': [0],  # Premium Partners
            },
            {
                'supplier_idx': 0,  # Bali Paradise Tours
                'name': '4D3N Bali Beach & Island Hopping',
                'summary': 'Explore Bali\'s beautiful beaches and surrounding islands',
                'description': 'Visit Nusa Penida, enjoy water sports, and relax on pristine beaches. Perfect for beach lovers and adventure seekers.',
                'city': 'Nusa Dua',
                'country': 'Indonesia',
                'days': 4,
                'nights': 3,
                'max_group_size': 15,
                'group_type': 'Small Group',
                'tour_type': TourType.CONVENTIONAL,
                'category': TourCategory.ADVENTURE,
                'tags': ['Beach', 'Island Hopping', 'Snorkeling'],
                'highlights': ['Nusa Penida Island', 'Crystal Bay', 'Kelingking Beach', 'Snorkeling with Manta Rays', 'Water sports'],
                'inclusions': ['3 nights beachfront hotel', 'Daily breakfast', 'Boat transfers', 'Snorkeling equipment', 'English speaking guide'],
                'exclusions': ['International flights', 'Lunch and dinner', 'Travel insurance', 'Personal expenses'],
                'meeting_point': 'Ngurah Rai International Airport (DPS)',
                'cancellation_policy': 'Free cancellation up to 7 days before departure. 50% refund for cancellations 3-7 days before.',
                'important_notes': 'Swimming skills recommended for water activities.',
                'base_price': 4500000,
                'currency': 'IDR',
                'badge': TourBadge.POPULAR,
                'is_featured': True,
                'reseller_groups': [0, 3],  # Premium Partners & Bali Specialists
            },
            {
                'supplier_idx': 0,  # Bali Paradise Tours
                'name': '5D4N Bali Muslim Tour',
                'summary': 'Halal-friendly tour of Bali with halal meals and prayer facilities',
                'description': 'A specially curated tour for Muslim travelers with halal-certified restaurants, prayer facilities, and visits to all major attractions.',
                'city': 'Denpasar',
                'country': 'Indonesia',
                'days': 5,
                'nights': 4,
                'max_group_size': 12,
                'group_type': 'Small Group',
                'tour_type': TourType.MUSLIM,
                'category': TourCategory.CULTURAL,
                'tags': ['Halal', 'Muslim-Friendly', 'Temple'],
                'highlights': ['Tanah Lot Temple', 'Uluwatu Temple', 'Halal restaurants', 'Prayer facilities', 'Cultural shows'],
                'inclusions': ['4 nights halal-certified hotel', 'Halal breakfast and lunch', 'Private transportation', 'English speaking guide', 'Prayer time arrangements'],
                'exclusions': ['International flights', 'Dinner', 'Travel insurance', 'Personal expenses'],
                'meeting_point': 'Ngurah Rai International Airport (DPS)',
                'cancellation_policy': 'Free cancellation up to 7 days before departure. 50% refund for cancellations 3-7 days before.',
                'important_notes': 'All meals are halal-certified. Prayer times will be accommodated during the tour.',
                'base_price': 5500000,
                'currency': 'IDR',
                'badge': TourBadge.NEW,
                'is_featured': True,
                'reseller_groups': [0, 3],  # Premium Partners & Bali Specialists
            },
            {
                'supplier_idx': 1,  # Jogja Heritage Travel
                'name': '3D2N Yogyakarta Heritage Tour',
                'summary': 'Explore the ancient Javanese kingdom and cultural heritage',
                'description': 'Visit Borobudur and Prambanan temples, explore the Kraton palace, and experience traditional Javanese culture.',
                'city': 'Yogyakarta',
                'country': 'Indonesia',
                'days': 3,
                'nights': 2,
                'max_group_size': 20,
                'group_type': 'Large Group',
                'tour_type': TourType.CONVENTIONAL,
                'category': TourCategory.CULTURAL,
                'tags': ['Borobudur', 'Prambanan', 'Temple'],
                'highlights': ['Borobudur Temple', 'Prambanan Temple', 'Kraton Palace', 'Taman Sari', 'Malioboro Street'],
                'inclusions': ['2 nights hotel accommodation', 'Daily breakfast', 'Private transportation', 'English speaking guide', 'All entrance fees'],
                'exclusions': ['International flights', 'Lunch and dinner', 'Travel insurance', 'Personal expenses'],
                'meeting_point': 'Adisucipto International Airport (JOG)',
                'cancellation_policy': 'Free cancellation up to 7 days before departure. 50% refund for cancellations 3-7 days before.',
                'important_notes': 'Early morning visit to Borobudur recommended for sunrise view.',
                'base_price': 2800000,
                'currency': 'IDR',
                'badge': TourBadge.BEST_SELLER,
                'is_featured': True,
                'reseller_groups': [],  # Available to all
            },
            {
                'supplier_idx': 1,  # Jogja Heritage Travel
                'name': '4D3N Jogja & Solo Cultural Tour',
                'summary': 'Immerse yourself in Javanese culture and royal heritage',
                'description': 'Discover both Yogyakarta and Solo, visit ancient temples, royal palaces, and experience traditional batik making.',
                'city': 'Yogyakarta',
                'country': 'Indonesia',
                'days': 4,
                'nights': 3,
                'max_group_size': 15,
                'group_type': 'Small Group',
                'tour_type': TourType.CONVENTIONAL,
                'category': TourCategory.CULTURAL,
                'tags': ['Culture', 'Palace', 'Batik'],
                'highlights': ['Borobudur Temple', 'Prambanan Temple', 'Kraton Solo', 'Batik Workshop', 'Traditional Market'],
                'inclusions': ['3 nights hotel accommodation', 'Daily breakfast', 'Private transportation', 'English speaking guide', 'Batik workshop'],
                'exclusions': ['International flights', 'Lunch and dinner', 'Travel insurance'],
                'meeting_point': 'Adisucipto International Airport (JOG)',
                'cancellation_policy': 'Free cancellation up to 7 days before departure.',
                'important_notes': 'Comfortable clothes for batik workshop.',
                'base_price': 3800000,
                'currency': 'IDR',
                'badge': None,
                'is_featured': False,
                'reseller_groups': [0, 1],  # Premium & Standard
            },
            {
                'supplier_idx': 2,  # Bromo Adventure Tours
                'name': '2D1N Mount Bromo Sunrise Tour',
                'summary': 'Witness the spectacular sunrise over Mount Bromo',
                'description': 'Early morning trek to Mount Bromo viewpoint, watch the sunrise, and explore the volcanic landscape. Perfect for nature and photography enthusiasts.',
                'city': 'Probolinggo',
                'country': 'Indonesia',
                'days': 2,
                'nights': 1,
                'max_group_size': 12,
                'group_type': 'Small Group',
                'tour_type': TourType.CONVENTIONAL,
                'category': TourCategory.ADVENTURE,
                'tags': ['Volcano', 'Sunrise', 'Adventure'],
                'highlights': ['Mount Bromo Sunrise', 'Savannah Viewpoint', 'Mount Bromo Crater', 'Sea of Sand', 'Madakaripura Waterfall'],
                'inclusions': ['1 night hotel accommodation', 'Breakfast', 'Jeep transportation', 'English speaking guide', 'Entrance fees'],
                'exclusions': ['Lunch and dinner', 'Travel insurance', 'Personal expenses'],
                'meeting_point': 'Juanda International Airport (SUB) or Probolinggo Station',
                'cancellation_policy': 'Free cancellation up to 5 days before departure. 50% refund for cancellations 2-5 days before.',
                'important_notes': 'Early departure (2-3 AM) for sunrise. Warm clothing recommended due to cold temperatures.',
                'base_price': 1800000,
                'currency': 'IDR',
                'badge': TourBadge.POPULAR,
                'is_featured': True,
                'reseller_groups': [],  # Available to all
            },
            {
                'supplier_idx': 2,  # Bromo Adventure Tours
                'name': '3D2N Bromo & Ijen Blue Fire Tour',
                'summary': 'Experience two iconic volcanoes - Bromo and Ijen',
                'description': 'Watch sunrise at Mount Bromo and see the famous blue fire at Ijen Crater. An unforgettable adventure through Java\'s volcanic landscape.',
                'city': 'Banyuwangi',
                'country': 'Indonesia',
                'days': 3,
                'nights': 2,
                'max_group_size': 10,
                'group_type': 'Small Group',
                'tour_type': TourType.CONVENTIONAL,
                'category': TourCategory.ADVENTURE,
                'tags': ['Volcano', 'Blue Fire', 'Adventure'],
                'highlights': ['Mount Bromo Sunrise', 'Ijen Blue Fire', 'Ijen Crater', 'Sulfur Mining', 'Volcanic Landscape'],
                'inclusions': ['2 nights hotel accommodation', 'Daily breakfast', 'Jeep transportation', 'English speaking guide', 'All entrance fees'],
                'exclusions': ['Lunch and dinner', 'Travel insurance', 'Gas mask rental'],
                'meeting_point': 'Juanda International Airport (SUB)',
                'cancellation_policy': 'Free cancellation up to 7 days before departure.',
                'important_notes': 'Strenuous activity. Good physical fitness required. Gas mask required for Ijen visit.',
                'base_price': 3500000,
                'currency': 'IDR',
                'badge': TourBadge.TOP_RATED,
                'is_featured': True,
                'reseller_groups': [0, 1],  # Premium & Standard
            },
            {
                'supplier_idx': 3,  # Raja Ampat Explorer
                'name': '5D4N Raja Ampat Diving Paradise',
                'summary': 'Dive into the world\'s most biodiverse marine ecosystem',
                'description': 'Experience world-class diving and snorkeling in Raja Ampat, home to 75% of the world\'s coral species. Perfect for divers and marine enthusiasts.',
                'city': 'Raja Ampat',
                'country': 'Indonesia',
                'days': 5,
                'nights': 4,
                'max_group_size': 8,
                'group_type': 'Small Group',
                'tour_type': TourType.CONVENTIONAL,
                'category': TourCategory.ADVENTURE,
                'tags': ['Diving', 'Snorkeling', 'Marine Life'],
                'highlights': ['Manta Ray Spotting', 'Coral Reef Diving', 'Island Hopping', 'Bird Watching', 'Pristine Beaches'],
                'inclusions': ['4 nights accommodation', 'All meals', 'Diving/snorkeling equipment', 'Boat transfers', 'English speaking guide'],
                'exclusions': ['International flights', 'Travel insurance', 'Diving certification'],
                'meeting_point': 'Domine Eduard Osok Airport (SOQ)',
                'cancellation_policy': 'Free cancellation up to 14 days before departure. 30% refund for cancellations 7-14 days before.',
                'important_notes': 'Diving certification required for diving activities. Snorkeling available for non-divers.',
                'base_price': 12500000,
                'currency': 'IDR',
                'badge': TourBadge.BEST_SELLER,
                'is_featured': True,
                'reseller_groups': [0],  # Premium Partners only
            },
            {
                'supplier_idx': 4,  # Komodo Dragons Adventure
                'name': '3D2N Komodo Island Adventure',
                'summary': 'Meet the legendary Komodo dragons in their natural habitat',
                'description': 'Visit Komodo National Park, see Komodo dragons up close, enjoy pink beach, and experience one of Indonesia\'s most unique destinations.',
                'city': 'Labuan Bajo',
                'country': 'Indonesia',
                'days': 3,
                'nights': 2,
                'max_group_size': 15,
                'group_type': 'Small Group',
                'tour_type': TourType.CONVENTIONAL,
                'category': TourCategory.ADVENTURE,
                'tags': ['Komodo Dragon', 'National Park', 'Beach'],
                'highlights': ['Komodo Dragon Sightings', 'Pink Beach', 'Padar Island', 'Snorkeling', 'Sunset Viewing'],
                'inclusions': ['2 nights hotel/accommodation', 'Daily meals', 'Boat transportation', 'Park entrance fees', 'English speaking guide'],
                'exclusions': ['International flights', 'Travel insurance', 'Personal expenses'],
                'meeting_point': 'Komodo Airport (LBJ)',
                'cancellation_policy': 'Free cancellation up to 7 days before departure.',
                'important_notes': 'Follow guide instructions when near Komodo dragons. Sunscreen and hat recommended.',
                'base_price': 4500000,
                'currency': 'IDR',
                'badge': TourBadge.POPULAR,
                'is_featured': True,
                'reseller_groups': [],  # Available to all
            },
            {
                'supplier_idx': 4,  # Komodo Dragons Adventure
                'name': '4D3N Komodo & Rinca Island Tour',
                'summary': 'Comprehensive tour of Komodo National Park',
                'description': 'Explore both Komodo and Rinca islands, see multiple dragons, enjoy world-class snorkeling, and relax on pristine beaches.',
                'city': 'Labuan Bajo',
                'country': 'Indonesia',
                'days': 4,
                'nights': 3,
                'max_group_size': 12,
                'group_type': 'Small Group',
                'tour_type': TourType.CONVENTIONAL,
                'category': TourCategory.ADVENTURE,
                'tags': ['Komodo Dragon', 'Island Hopping', 'Snorkeling'],
                'highlights': ['Komodo Island', 'Rinca Island', 'Pink Beach', 'Manta Point', 'Kanawa Island'],
                'inclusions': ['3 nights accommodation', 'All meals', 'Boat transportation', 'All entrance fees', 'English speaking guide'],
                'exclusions': ['International flights', 'Travel insurance'],
                'meeting_point': 'Komodo Airport (LBJ)',
                'cancellation_policy': 'Free cancellation up to 7 days before departure.',
                'important_notes': 'Physical activity involved. Follow safety guidelines around Komodo dragons.',
                'base_price': 6500000,
                'currency': 'IDR',
                'badge': None,
                'is_featured': False,
                'reseller_groups': [0, 1],  # Premium & Standard
            },
            {
                'supplier_idx': 5,  # Lombok Wisata Sejahtera
                'name': '4D3N Lombok Beach Paradise',
                'summary': 'Discover the pristine beaches and waterfalls of Lombok',
                'description': 'Experience Lombok\'s stunning beaches, waterfalls, and traditional Sasak culture. Visit Gili Islands and enjoy water activities.',
                'city': 'Senggigi',
                'country': 'Indonesia',
                'days': 4,
                'nights': 3,
                'max_group_size': 15,
                'group_type': 'Small Group',
                'tour_type': TourType.CONVENTIONAL,
                'category': TourCategory.BEACH,
                'tags': ['Beach', 'Gili Islands', 'Waterfall'],
                'highlights': ['Gili Trawangan', 'Sendang Gile Waterfall', 'Sasak Village', 'Snorkeling', 'Sunset Viewing'],
                'inclusions': ['3 nights beachfront hotel', 'Daily breakfast', 'Boat transfers to Gili', 'English speaking guide', 'Snorkeling equipment'],
                'exclusions': ['Lunch and dinner', 'Travel insurance', 'Personal expenses'],
                'meeting_point': 'Lombok International Airport (LOP)',
                'cancellation_policy': 'Free cancellation up to 7 days before departure.',
                'important_notes': 'Swimming skills recommended. Sunscreen essential.',
                'base_price': 3800000,
                'currency': 'IDR',
                'badge': TourBadge.NEW,
                'is_featured': False,
                'reseller_groups': [1, 2],  # Standard & New Partners
            },
            {
                'supplier_idx': 6,  # Jakarta City Tours
                'name': '2D1N Jakarta City Experience',
                'summary': 'Explore the vibrant capital city of Indonesia',
                'description': 'Discover Jakarta\'s modern attractions, historical sites, and culinary scene. Perfect for city lovers and food enthusiasts.',
                'city': 'Jakarta',
                'country': 'Indonesia',
                'days': 2,
                'nights': 1,
                'max_group_size': 20,
                'group_type': 'Large Group',
                'tour_type': TourType.CONVENTIONAL,
                'category': TourCategory.CITY_BREAK,
                'tags': ['City', 'Culture', 'Food'],
                'highlights': ['National Monument', 'Old Batavia', 'Jakarta Cathedral', 'Istiqlal Mosque', 'Culinary Tour'],
                'inclusions': ['1 night hotel accommodation', 'Breakfast', 'City tour transportation', 'English speaking guide', 'Entrance fees'],
                'exclusions': ['Lunch and dinner', 'Travel insurance', 'Personal expenses'],
                'meeting_point': 'Soekarno-Hatta International Airport (CGK)',
                'cancellation_policy': 'Free cancellation up to 3 days before departure.',
                'important_notes': 'Traffic can be heavy. Comfortable walking shoes recommended.',
                'base_price': 1500000,
                'currency': 'IDR',
                'badge': None,
                'is_featured': False,
                'reseller_groups': [1, 2],  # Standard & New Partners
            },
            {
                'supplier_idx': 7,  # Bandung Travel Agency
                'name': '3D2N Bandung Highland Escape',
                'summary': 'Enjoy cool weather and beautiful landscapes in Bandung',
                'description': 'Experience Bandung\'s cool climate, volcanic hot springs, tea plantations, and shopping outlets. Perfect for relaxation and nature lovers.',
                'city': 'Bandung',
                'country': 'Indonesia',
                'days': 3,
                'nights': 2,
                'max_group_size': 18,
                'group_type': 'Large Group',
                'tour_type': TourType.CONVENTIONAL,
                'category': TourCategory.NATURE,
                'tags': ['Highland', 'Tea Plantation', 'Hot Spring'],
                'highlights': ['Tangkuban Perahu Volcano', 'Kawah Putih', 'Ciater Hot Springs', 'Tea Plantations', 'Shopping Outlets'],
                'inclusions': ['2 nights hotel accommodation', 'Daily breakfast', 'Private transportation', 'English speaking guide', 'Entrance fees'],
                'exclusions': ['Lunch and dinner', 'Travel insurance', 'Personal expenses'],
                'meeting_point': 'Husein Sastranegara Airport (BDO)',
                'cancellation_policy': 'Free cancellation up to 5 days before departure.',
                'important_notes': 'Cool weather, bring jacket. Mountain roads can be winding.',
                'base_price': 2200000,
                'currency': 'IDR',
                'badge': None,
                'is_featured': False,
                'reseller_groups': [1],  # Standard Partners
            },
            {
                'supplier_idx': 8,  # Lake Toba Tours
                'name': '4D3N Lake Toba Cultural Tour',
                'summary': 'Experience the beauty and culture of Lake Toba',
                'description': 'Visit the largest volcanic lake in Indonesia, learn about Batak culture, and enjoy the scenic beauty of Samosir Island.',
                'city': 'Parapat',
                'country': 'Indonesia',
                'days': 4,
                'nights': 3,
                'max_group_size': 15,
                'group_type': 'Small Group',
                'tour_type': TourType.CONVENTIONAL,
                'category': TourCategory.CULTURAL,
                'tags': ['Lake', 'Batak Culture', 'Nature'],
                'highlights': ['Lake Toba', 'Samosir Island', 'Batak Houses', 'Traditional Dance', 'Sipiso-piso Waterfall'],
                'inclusions': ['3 nights hotel accommodation', 'Daily breakfast', 'Boat transfers', 'English speaking guide', 'Cultural show'],
                'exclusions': ['Lunch and dinner', 'Travel insurance', 'Personal expenses'],
                'meeting_point': 'Kualanamu International Airport (KNO)',
                'cancellation_policy': 'Free cancellation up to 7 days before departure.',
                'important_notes': 'Relaxed pace, perfect for cultural immersion.',
                'base_price': 3500000,
                'currency': 'IDR',
                'badge': None,
                'is_featured': False,
                'reseller_groups': [1],  # Standard Partners
            },
            {
                'supplier_idx': 9,  # Toraja Cultural Tours
                'name': '4D3N Toraja Funeral Ceremony Experience',
                'summary': 'Witness unique Torajan funeral ceremonies and traditional architecture',
                'description': 'Experience the fascinating Torajan culture, traditional houses, burial cliffs, and if timing allows, witness a traditional funeral ceremony.',
                'city': 'Rantepao',
                'country': 'Indonesia',
                'days': 4,
                'nights': 3,
                'max_group_size': 12,
                'group_type': 'Small Group',
                'tour_type': TourType.CONVENTIONAL,
                'category': TourCategory.CULTURAL,
                'tags': ['Culture', 'Traditional', 'Funeral Ceremony'],
                'highlights': ['Traditional Torajan Houses', 'Lemo Burial Cliffs', 'Kete Kesu Village', 'Buntu Kalando', 'Torajan Markets'],
                'inclusions': ['3 nights hotel accommodation', 'Daily breakfast', 'Private transportation', 'English speaking guide', 'Cultural experiences'],
                'exclusions': ['Lunch and dinner', 'Travel insurance', 'Personal expenses'],
                'meeting_point': 'Sultan Hasanuddin Airport (UPG)',
                'cancellation_policy': 'Free cancellation up to 7 days before departure.',
                'important_notes': 'Cultural sensitivity important. Funeral ceremonies are sacred events.',
                'base_price': 4200000,
                'currency': 'IDR',
                'badge': None,
                'is_featured': False,
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
            
            tour = TourPackage.objects.create(
                supplier=supplier,
                name=data['name'],
                slug=slug,
                summary=data['summary'],
                description=data['description'],
                city=data['city'],
                country=data['country'],
                days=data['days'],
                nights=data['nights'],
                max_group_size=data['max_group_size'],
                group_type=data['group_type'],
                tour_type=data['tour_type'],
                category=data['category'],
                tags=data['tags'],
                highlights=data['highlights'],
                inclusions=data['inclusions'],
                exclusions=data['exclusions'],
                meeting_point=data['meeting_point'],
                cancellation_policy=data['cancellation_policy'],
                important_notes=data['important_notes'],
                base_price=data['base_price'],
                currency=data['currency'],
                badge=data['badge'],
                is_active=True,
                is_featured=data['is_featured'],
                commission_rate=random.uniform(8.0, 12.0),
                commission_type='PERCENTAGE',
            )
            
            # Assign reseller groups
            for group_idx in data['reseller_groups']:
                if group_idx < len(reseller_groups):
                    tour.reseller_groups.add(reseller_groups[group_idx])
            
            # Create tour dates
            self._create_tour_dates(tour, data['base_price'])
            
            # Create itinerary items
            self._create_itinerary_items(tour, data['days'])
            
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

    def _create_itinerary_items(self, tour, days):
        """Create itinerary items for a tour package."""
        itinerary_templates = {
            3: [
                {'day': 1, 'title': 'Arrival & Welcome', 'description': 'Airport pickup, hotel check-in, welcome dinner, and tour briefing.'},
                {'day': 2, 'title': 'Full Day Tour', 'description': 'Visit main attractions, enjoy local experiences, and cultural activities.'},
                {'day': 3, 'title': 'Departure', 'description': 'Final activities, souvenir shopping, and airport transfer.'},
            ],
            4: [
                {'day': 1, 'title': 'Arrival & City Tour', 'description': 'Airport pickup, hotel check-in, and afternoon city tour.'},
                {'day': 2, 'title': 'Main Attractions', 'description': 'Full day tour of major attractions and landmarks.'},
                {'day': 3, 'title': 'Cultural Experience', 'description': 'Visit cultural sites, local markets, and traditional experiences.'},
                {'day': 4, 'title': 'Departure', 'description': 'Free time, souvenir shopping, and airport transfer.'},
            ],
            5: [
                {'day': 1, 'title': 'Arrival & Orientation', 'description': 'Airport pickup, hotel check-in, and welcome orientation.'},
                {'day': 2, 'title': 'Day Trip Adventure', 'description': 'Full day trip to nearby attractions or natural wonders.'},
                {'day': 3, 'title': 'City Exploration', 'description': 'Explore the city, visit museums, and enjoy local cuisine.'},
                {'day': 4, 'title': 'Cultural Immersion', 'description': 'Deep dive into local culture, traditions, and experiences.'},
                {'day': 5, 'title': 'Departure', 'description': 'Final activities, last-minute shopping, and airport transfer.'},
            ],
        }
        
        template = itinerary_templates.get(days, itinerary_templates[3])
        
        for item in template:
            ItineraryItem.objects.create(
                package=tour,
                day_number=item['day'],
                title=item['title'],
                description=item['description'],
            )

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
            
            # Create booking
            customer_name = passenger_names[idx][0] if idx < len(passenger_names) else 'Customer'
            customer_email = f'customer{idx+1}@example.com'
            
            booking = Booking.objects.create(
                reseller=reseller,
                tour_date=tour_date,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=f'+62-812-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}',
                status=scenario['status'],
                platform_fee=50000,
                notes=f'Booking created for {scenario["num_passengers"]} passengers.',
            )
            
            # Assign seat slots and add passenger details
            passengers = passenger_names[idx] if idx < len(passenger_names) else [f'Passenger {i+1}' for i in range(scenario['num_passengers'])]
            
            for slot_idx, slot in enumerate(available_slots):
                passenger_name = passengers[slot_idx] if slot_idx < len(passengers) else f'Passenger {slot_idx+1}'
                
                # Generate passport details
                passport_number = f'P{random.randint(100000, 999999)}'
                passport_issue_date = timezone.now().date() - timedelta(days=random.randint(365, 1825))
                passport_expiry_date = passport_issue_date + timedelta(days=3650)
                
                slot.booking = booking
                slot.status = SeatSlotStatus.BOOKED
                slot.passenger_name = passenger_name
                slot.passenger_email = customer_email if slot_idx == 0 else f'{slugify(passenger_name)}@example.com'
                slot.passenger_phone = f'+62-812-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}'
                slot.passenger_date_of_birth = timezone.now().date() - timedelta(days=random.randint(7300, 18250))
                slot.passenger_gender = random.choice(['MALE', 'FEMALE'])
                slot.passenger_nationality = 'IDN'
                slot.passport_number = passport_number
                slot.passport_issue_date = passport_issue_date
                slot.passport_expiry_date = passport_expiry_date
                slot.passport_issue_country = 'Indonesia'
                # All tours are in Indonesia, so no visa required for Indonesian nationals
                slot.visa_required = False
                slot.special_requests = random.choice(['', 'Makanan vegetarian', 'Kursi dekat jendela', 'Tidak ada permintaan khusus', 'Makanan halal'])
                # Generate Indonesian emergency contact names
                emergency_names = ['Ayah ' + passenger_name.split()[0], 'Ibu ' + passenger_name.split()[0], 'Saudara ' + passenger_name.split()[0]]
                slot.emergency_contact_name = random.choice(emergency_names)
                slot.emergency_contact_phone = f'+62-812-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}'
                slot.save()
            
            # Create payment
            payment = Payment.objects.create(
                booking=booking,
                amount=booking.total_amount,
                currency='IDR',
                transfer_date=timezone.now().date() - timedelta(days=random.randint(1, 7)),
                sender_account_name=customer_name,
                sender_bank_name=random.choice(['Bank Mandiri', 'BCA', 'Bank BNI', 'Bank BRI']),
                sender_account_number=f'{random.randint(1000000000, 9999999999)}',
                status=scenario['payment_status'],
            )
            
            bookings.append(booking)
        
        return bookings

