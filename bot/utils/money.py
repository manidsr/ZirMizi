from bot.utils.cards import to_latin_digits

_SEPARATORS = " ,\u066c\u060c_\u200c\u200f\u200e"  # space, commas (Latin/Arabic), half-space, RTL marks
_MAX_DIGITS = 12


def format_amount(amount: int) -> str:
    """1500000 -> '1,500,000'."""
    return f"{amount:,}"


def parse_amount(raw: str | None) -> int | None:
    """'۱,۵۰۰,۰۰۰' / '1500000' -> 1500000. None if it isn't a plain whole number."""
    if raw is None:
        return None
    value = "".join(ch for ch in to_latin_digits(raw) if ch not in _SEPARATORS)
    if not value or len(value) > _MAX_DIGITS or not (value.isascii() and value.isdigit()):
        return None
    return int(value)


def calc_fee(price: int, fee_bps: int) -> int:
    """Platform fee in Toman. `fee_bps` is in basis points (100 = 1%). Rounds down."""
    return price * fee_bps // 10_000
