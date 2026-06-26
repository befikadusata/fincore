from decimal import Decimal


def to_minor_units(amount: Decimal, decimals: int = 2) -> int:
    """Converts a decimal amount to its integer minor unit (cents/santim)."""
    return int(round(amount * (10 ** decimals)))


def from_minor_units(minor: int, decimals: int = 2) -> Decimal:
    """Converts an integer minor unit (cents/santim) to a decimal amount."""
    return Decimal(minor) / (10 ** decimals)


def format_money(minor: int, currency_code: str, decimals: int = 2) -> str:
    """Formats an integer minor unit into currency string: e.g. 1,200.50 ETB."""
    decimal_val = from_minor_units(minor, decimals)
    return f"{decimal_val:,.{decimals}f} {currency_code}"
