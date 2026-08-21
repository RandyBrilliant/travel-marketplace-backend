from django.test import SimpleTestCase

from travel.commission import (
    deduction_per_seat,
    net_commission_per_seat,
    upline_shares,
)
from travel.countries import canonicalize_country, matching_country_names


class CommissionMathTests(SimpleTestCase):
    def test_group_root_keeps_full_amount(self):
        self.assertEqual(net_commission_per_seat(300_000, has_upline=False), 300_000)
        self.assertEqual(deduction_per_seat(300_000, has_upline=False), 0)

    def test_upline_deducts_100k_when_commission_at_least_100k(self):
        self.assertEqual(deduction_per_seat(300_000, has_upline=True), 100_000)
        self.assertEqual(net_commission_per_seat(300_000, has_upline=True), 200_000)
        self.assertEqual(net_commission_per_seat(150_000, has_upline=True), 50_000)
        self.assertEqual(net_commission_per_seat(500_000, has_upline=True), 400_000)

    def test_upline_deducts_half_when_commission_below_100k(self):
        self.assertEqual(deduction_per_seat(80_000, has_upline=True), 40_000)
        self.assertEqual(net_commission_per_seat(80_000, has_upline=True), 40_000)

    def test_exactly_100k_with_upline_zero_for_seller_full_pool_for_uplines(self):
        self.assertEqual(net_commission_per_seat(100_000, has_upline=True), 0)
        self.assertEqual(deduction_per_seat(100_000, has_upline=True), 100_000)
        shares = upline_shares(100_000)
        self.assertEqual(shares[1], 50_000)
        self.assertEqual(shares[2], 25_000)
        self.assertEqual(shares[3], 25_000)
        self.assertEqual(sum(shares.values()), 100_000)

    def test_three_tier_split_matches_documented_example(self):
        # 1 pax, 150k/seat → deduct 100k → L0 50k, L1 50k, L2 25k, L3 25k
        self.assertEqual(net_commission_per_seat(150_000, has_upline=True), 50_000)
        shares = upline_shares(100_000)
        self.assertEqual(shares, {1: 50_000, 2: 25_000, 3: 25_000})
        total = 50_000 + sum(shares.values())
        self.assertEqual(total, 150_000)

    def test_three_passengers_scales_linearly(self):
        per_seat = 150_000
        seats = 3
        deduction = deduction_per_seat(per_seat, True) * seats
        level0 = net_commission_per_seat(per_seat, True) * seats
        shares = upline_shares(deduction)
        self.assertEqual(level0, 150_000)
        self.assertEqual(shares, {1: 150_000, 2: 75_000, 3: 75_000})
        self.assertEqual(level0 + sum(shares.values()), per_seat * seats)

    def test_odd_deduction_shares_sum_exactly(self):
        deduction = 99_999
        shares = upline_shares(deduction)
        self.assertEqual(sum(shares.values()), deduction)

    def test_float_noise_does_not_drop_one_rupiah(self):
        self.assertEqual(net_commission_per_seat(299999.99999999994, has_upline=False), 300_000)


class CanonicalCountryTests(SimpleTestCase):
    def test_city_and_local_names_map_to_filter_country(self):
        self.assertEqual(canonicalize_country("Hokkaido"), "Japan")
        self.assertEqual(canonicalize_country("jepang"), "Japan")
        self.assertEqual(canonicalize_country("Tokyo"), "Japan")
        self.assertEqual(canonicalize_country("Korea"), "South Korea")
        self.assertEqual(canonicalize_country("Seoul"), "South Korea")
        self.assertEqual(canonicalize_country("Beijing"), "China")
        self.assertEqual(canonicalize_country("Bali"), "Indonesia")
        self.assertEqual(canonicalize_country("Hokkaido, Japan"), "Japan")

    def test_already_canonical_names_are_unchanged(self):
        self.assertEqual(canonicalize_country("Japan"), "Japan")
        self.assertEqual(canonicalize_country("South Korea"), "South Korea")
        self.assertEqual(canonicalize_country("Papua New Guinea"), "Papua New Guinea")

    def test_japan_filter_includes_hokkaido(self):
        names = {name.casefold() for name in matching_country_names("Japan")}
        self.assertIn("japan", names)
        self.assertIn("jepang", names)
        self.assertIn("hokkaido", names)
