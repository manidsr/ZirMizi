import re

# Arabic letter variants -> the Persian letter people actually mean.
_CHAR_MAP = str.maketrans(
    {
        "ي": "ی",  # ي -> ی
        "ى": "ی",  # ى -> ی
        "ك": "ک",  # ك -> ک
        "ة": "ه",  # ة -> ه
        "ۀ": "ه",  # ۀ -> ه
        "آ": "ا",  # آ -> ا
        "أ": "ا",  # أ -> ا
        "إ": "ا",  # إ -> ا
        "ٱ": "ا",  # ٱ -> ا
    }
)
# Whitespace, zero-width (half-space) characters, tatweel and diacritics.
_STRIP = re.compile(r"[\s‌‍ـً-ٰٟ]")


def normalize_name(value: str) -> str:
    value = value.translate(_CHAR_MAP)
    value = _STRIP.sub("", value)
    return value.casefold()


def names_match(card_holder: str, first_name: str, last_name: str) -> bool:
    """Does the card holder name equal the registered name?

    Ignores spaces/half-spaces, Arabic-vs-Persian letter variants and
    first/last name order ("علی رضایی" == "رضایی علی").
    """
    holder = normalize_name(card_holder)
    if not holder:
        return False
    return holder in {
        normalize_name(first_name + last_name),
        normalize_name(last_name + first_name),
    }
