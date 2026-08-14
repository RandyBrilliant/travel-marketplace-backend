"""Integer-safe MLM commission math (per seat, then multiplied by passengers).

Rules:
- Level 0 (booking reseller): tour commission minus upline deduction.
- Deduction per seat: 100_000 if commission >= 100_000, else 50%.
- No sponsor (group root): no deduction, full amount.
- Levels 1–3 split the deduction 50% / 25% / 25%.
- Level 4+ receives nothing.
"""

UPLINE_DEDUCTION_PER_SEAT_MAX = 100_000
UPLINE_DISTRIBUTION_PERCENT = {
    1: 50,
    2: 25,
    3: 25,
}
MAX_UPLINE_LEVELS = 3


def to_rupiah(amount) -> int:
    if amount is None:
        return 0
    return max(0, int(round(amount)))


def deduction_per_seat(commission_per_seat: int, has_upline: bool) -> int:
    amount = to_rupiah(commission_per_seat)
    if not has_upline or amount == 0:
        return 0
    if amount >= UPLINE_DEDUCTION_PER_SEAT_MAX:
        return UPLINE_DEDUCTION_PER_SEAT_MAX
    return amount // 2


def net_commission_per_seat(commission_per_seat: int, has_upline: bool) -> int:
    amount = to_rupiah(commission_per_seat)
    return max(0, amount - deduction_per_seat(amount, has_upline))


def upline_shares(total_deduction: int) -> dict[int, int]:
    """Return {1: 50%, 2: 25%, 3: 25%} of the deduction pool.

    Any 1–2 IDR leftover from integer division is added to level 1 so the
    three shares always sum to total_deduction when all three uplines exist.
    Missing uplines are simply not paid (those shares are not compressed).
    """
    total = to_rupiah(total_deduction)
    shares = {
        level: (total * percent) // 100
        for level, percent in UPLINE_DISTRIBUTION_PERCENT.items()
    }
    remainder = total - sum(shares.values())
    shares[1] += remainder
    return shares
