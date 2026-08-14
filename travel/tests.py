from django.test import SimpleTestCase

from travel.commission import (
    deduction_per_seat,
    net_commission_per_seat,
    upline_shares,
)


class CommissionMathTests(SimpleTestCase):
    def test_group_root_keeps_full_amount(self):
        self.assertEqual(net_commission_per_seat(300_000, has_upline=False), 300_000)
        self.assertEqual(deduction_per_seat(300_000, has_upline=False), 0)

    def test_upline_deducts_100k_when_commission_at_least_100k(self):
        self.assertEqual(deduction_per_seat(300_000, has_upline=True), 100_000)
        self.assertEqual(net_commission_per_seat(300_000, has_upline=True), 200_000)
        self.assertEqual(net_commission_per_seat(150_000, has_upline=True), 50_000)

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
