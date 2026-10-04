"""Integer cents in, dollar strings out. The model never owns this."""

from decimal import Decimal, ROUND_HALF_UP


def dollars_to_cents(raw: str) -> int | None:
    text = raw.strip().lstrip("$").strip()
    if not text:
        return None
    try:
        amount = Decimal(text)
    except Exception:
        return None
    if amount != amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP):
        return None
    cents = int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if cents <= 0:
        return None
    return cents


def money(cents: int) -> str:
    return f"${cents / 100:.2f}"


def signed_net(cents: int) -> str:
    if cents > 0:
        return f"+${cents / 100:.2f}"
    if cents < 0:
        return f"−${abs(cents) / 100:.2f}"
    return "$0.00"


def aligned_net(cents: int) -> str:
    """Pad a zero so the dollar sign lines up under +$ and −$."""
    if cents == 0:
        return " $0.00"
    return signed_net(cents)
