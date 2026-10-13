from .fa import MESSAGES as FA

DEFAULT_LANG = "fa"

_CATALOGS: dict[str, dict[str, str]] = {
    "fa": FA,
}


def t(key: str, lang: str = DEFAULT_LANG, **kwargs: object) -> str:
    """Look up a message by key and fill in placeholders.

    Falls back to the default language if `lang` has no catalog.
    """
    catalog = _CATALOGS.get(lang, _CATALOGS[DEFAULT_LANG])
    return catalog[key].format(**kwargs)
