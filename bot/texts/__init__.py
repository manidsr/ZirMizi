from .fa import MESSAGES as _FA_BASE
from .fa_market import MESSAGES as _FA_MARKET

DEFAULT_LANG = "fa"

# fa_market.py is merged on top of fa.py (it also overrides `wallet_balance`).
FA = {**_FA_BASE, **_FA_MARKET}

_CATALOGS: dict[str, dict[str, str]] = {
    "fa": FA,
}


def t(key: str, lang: str = DEFAULT_LANG, **kwargs: object) -> str:
    """Look up a message by key and fill in placeholders.

    Falls back to the default language if `lang` has no catalog.
    """
    catalog = _CATALOGS.get(lang, _CATALOGS[DEFAULT_LANG])
    return catalog[key].format(**kwargs)
