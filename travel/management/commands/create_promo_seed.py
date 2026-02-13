"""
Management command to create promo code seed data.

Usage:
    python manage.py create_promo_seed
    python manage.py create_promo_seed --clear  # Clear existing promo codes first
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from travel.models import PromoCode, PromoDiscountType, PromoApplicableTo


class Command(BaseCommand):
    help = "Creates promo code seed data for testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing promo codes before creating seed data",
        )

    def handle(self, *args, **options):
        clear = options.get("clear", False)

        if clear:
            count = PromoCode.objects.count()
            PromoCode.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Cleared {count} existing promo code(s)"))

        now = timezone.now()
        valid_from = now - timedelta(days=1)
        valid_until = now + timedelta(days=365)

        seed_promos = [
            {
                "code": "WELCOME10",
                "description": "Potongan 10% untuk pembelian pertama",
                "discount_type": PromoDiscountType.PERCENTAGE,
                "discount_value": 10,
                "min_purchase_amount": 500_000,
                "max_uses": None,
                "valid_from": valid_from,
                "valid_until": valid_until,
                "is_active": True,
                "applicable_to": PromoApplicableTo.BOTH,
            },
            {
                "code": "TOUR20",
                "description": "Diskon 20% khusus pemesanan tur",
                "discount_type": PromoDiscountType.PERCENTAGE,
                "discount_value": 20,
                "min_purchase_amount": 1_000_000,
                "max_uses": None,
                "valid_from": valid_from,
                "valid_until": valid_until,
                "is_active": True,
                "applicable_to": PromoApplicableTo.TOUR,
            },
            {
                "code": "VIRTUAL15",
                "description": "Potongan 15% untuk pembelian Virtual Guiding",
                "discount_type": PromoDiscountType.PERCENTAGE,
                "discount_value": 15,
                "min_purchase_amount": 300_000,
                "max_uses": None,
                "valid_from": valid_from,
                "valid_until": valid_until,
                "is_active": True,
                "applicable_to": PromoApplicableTo.ITINERARY,
            },
            {
                "code": "FLAT50K",
                "description": "Potongan flat Rp 50.000",
                "discount_type": PromoDiscountType.FIXED_AMOUNT,
                "discount_value": 50_000,
                "min_purchase_amount": 1_000_000,
                "max_uses": None,
                "valid_from": valid_from,
                "valid_until": valid_until,
                "is_active": True,
                "applicable_to": PromoApplicableTo.BOTH,
            },
            {
                "code": "EARLY25",
                "description": "Diskon early bird 25% (terbatas 100 penggunaan)",
                "discount_type": PromoDiscountType.PERCENTAGE,
                "discount_value": 25,
                "min_purchase_amount": 2_000_000,
                "max_uses": 100,
                "valid_from": valid_from,
                "valid_until": valid_until,
                "is_active": True,
                "applicable_to": PromoApplicableTo.BOTH,
            },
            {
                "code": "SAVE100K",
                "description": "Hemat Rp 100.000 untuk pembelian minimal Rp 3 juta",
                "discount_type": PromoDiscountType.FIXED_AMOUNT,
                "discount_value": 100_000,
                "min_purchase_amount": 3_000_000,
                "max_uses": None,
                "valid_from": valid_from,
                "valid_until": valid_until,
                "is_active": True,
                "applicable_to": PromoApplicableTo.BOTH,
            },
        ]

        with transaction.atomic():
            created = []
            for data in seed_promos:
                promo, created_flag = PromoCode.objects.get_or_create(
                    code=data["code"],
                    defaults=data,
                )
                if created_flag:
                    created.append(promo.code)

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created {len(created)} promo code(s): {', '.join(created)}"))
        else:
            self.stdout.write(self.style.NOTICE("All promo codes already exist. Use --clear to recreate."))

        self.stdout.write(self.style.SUCCESS("\nPromo codes available:"))
        for p in PromoCode.objects.all():
            self.stdout.write(
                f"  • {p.code}: {p.get_discount_type_display()} "
                f"{p.discount_value}{'%' if p.discount_type == PromoDiscountType.PERCENTAGE else ' IDR'}, "
                f"min Rp {p.min_purchase_amount:,}, berlaku untuk {p.get_applicable_to_display()}"
            )
