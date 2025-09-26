from datetime import datetime

def fmt_currency(amount: float, symbol: str = '₦') -> str:
    try:
        return f"{symbol}{amount:,.2f}"
    except Exception:
        return f"{symbol}{amount}"


def today_str(fmt: str = '%Y-%m-%d') -> str:
    return datetime.utcnow().strftime(fmt)
