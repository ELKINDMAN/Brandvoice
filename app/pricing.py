"""Central pricing & currency utilities."""
from typing import Tuple, Dict

# Fixed pricing per currency (amounts as floats)
FIXED_PRICING: Dict[str, float] = {
    'NGN': 1400.00,
    'USD': 4.00,
    'GBP': 3.00,
}

DEFAULT_CURRENCY = 'USD'

ALLOWED_CURRENCIES = set(FIXED_PRICING.keys())

def get_price_for_currency(currency: str) -> float:
    currency = (currency or '').upper().strip()
    if currency in FIXED_PRICING:
        return FIXED_PRICING[currency]
    return FIXED_PRICING[DEFAULT_CURRENCY]

def resolve_currency(preferred: str | None) -> Tuple[str, float]:
    """Resolve currency from optional preferred value and return (currency, amount)."""
    if preferred:
        preferred = preferred.upper().strip()
        if preferred in ALLOWED_CURRENCIES:
            return preferred, get_price_for_currency(preferred)
    return DEFAULT_CURRENCY, get_price_for_currency(DEFAULT_CURRENCY)
