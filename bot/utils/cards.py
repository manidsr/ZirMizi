_PERSIAN_DIGITS = "".join(chr(0x06F0 + i) for i in range(10))
_ARABIC_DIGITS = "".join(chr(0x0660 + i) for i in range(10))
_TO_LATIN = str.maketrans(_PERSIAN_DIGITS + _ARABIC_DIGITS, "0123456789" * 2)

CARD_LENGTH = 16


def to_latin_digits(value: str) -> str:
    """Convert Persian/Arabic digits to 0-9."""
    return value.translate(_TO_LATIN)


def _luhn_ok(number: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(number)):
        digit = int(char)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def parse_card_number(raw: str | None) -> str | None:
    """Return a clean 16-digit card number, or None if the input is invalid.

    Accepts Persian/Arabic digits and spaces or dashes between groups.
    Also runs the standard Luhn check to catch typos.
    """
    if raw is None:
        return None
    number = to_latin_digits(raw)
    number = "".join(ch for ch in number if ch not in " -‌‏‎")
    if len(number) != CARD_LENGTH or not (number.isascii() and number.isdigit()):
        return None
    if not _luhn_ok(number):
        return None
    return number


def mask_card(number: str) -> str:
    """6037991899244447 -> 6037-****-****-4447 (safe to show in chat)."""
    return f"{number[:4]}-****-****-{number[-4:]}"
