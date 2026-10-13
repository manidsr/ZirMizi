"""Farsi (fa) message catalog.

All user-facing text lives here, not in handlers. To support another
language later, add a sibling module (e.g. en.py) with the same keys and
register it in texts/__init__.py.
"""

MESSAGES: dict[str, str] = {
    # General
    "default_name": "دوست عزیز",
    "coming_soon": "این بخش به‌زودی فعال می‌شود. 🚧",
    "not_registered": "برای استفاده از ربات ابتدا باید ثبت‌نام کنید.\nلطفاً /start را بفرستید.",
    "start_over": "مشکلی پیش آمد. لطفاً دوباره /start را بفرستید.",
    "btn_cancel": "انصراف ❌",
    # Welcome
    "welcome": (
        "سلام {name}! 👋\n"
        "به ربات ما خوش آمدید.\n\n"
        "برای شروع، لطفاً ثبت‌نام کنید."
    ),
    "welcome_back": (
        "سلام {name}، خوش آمدید! 👋\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید."
    ),
    # Signup
    "btn_signup": "ثبت‌نام ✍️",
    "ask_first_name": "لطفاً نام خود را وارد کنید:",
    "ask_last_name": "حالا نام خانوادگی خود را وارد کنید:",
    "invalid_name": "ورودی نامعتبر است. لطفاً فقط با متن و حداکثر ۶۴ حرف وارد کنید.",
    "already_registered": "شما قبلاً ثبت‌نام کرده‌اید. لطفاً یکی از گزینه‌های زیر را انتخاب کنید.",
    "signup_done": (
        "✅ ثبت‌نام شما با موفقیت انجام شد.\n"
        "{name} عزیز، خوش آمدید!\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید."
    ),
    # Main menu
    "btn_buy_food": "خرید غذا 🍽️",
    "btn_sell_food": "فروش غذا 🍲",
    "btn_wallet": "کیف پول 💰",
    "btn_account": "حساب کاربری 👤",
    # Wallet
    "wallet_balance": (
        "💰 کیف پول\n\n"
        "موجودی شما: {balance} تومان"
    ),
    "btn_withdraw": "برداشت 📤",
    "btn_deposit": "واریز 📥",
    "btn_transfer": "انتقال 🔁",
    # Account
    "account_info": (
        "👤 حساب کاربری\n\n"
        "نام: {first_name}\n"
        "نام خانوادگی: {last_name}\n\n"
        "🏦 اطلاعات بانکی (اختیاری)\n"
        "{bank_info}"
    ),
    "bank_not_set": "ثبت نشده",
    "bank_info": (
        "شماره کارت: {card}\n"
        "نام صاحب کارت: {holder}"
    ),
    "btn_bank_add": "ثبت اطلاعات بانکی 🏦",
    "btn_bank_edit": "ویرایش اطلاعات بانکی ✏️",
    "bank_intro": (
        "🏦 ثبت اطلاعات بانکی\n\n"
        "این بخش اختیاری است و فقط هنگام برداشت از کیف پول به آن نیاز دارید.\n\n"
        "⚠️ توجه: کارت باید به نام خودتان باشد و «نام صاحب کارت» باید دقیقاً "
        "با نامی که هنگام ثبت‌نام وارد کرده‌اید یکی باشد. در غیر این صورت "
        "امکان برداشت وجود نخواهد داشت."
    ),
    "ask_card_number": "شماره کارت ۱۶ رقمی خود را وارد کنید:",
    "invalid_card_number": "شماره کارت نامعتبر است. لطفاً ۱۶ رقم شماره کارت را درست وارد کنید:",
    "ask_card_holder": "حالا نام صاحب کارت را به فارسی و دقیقاً مطابق نام ثبت‌نام خود وارد کنید:",
    "bank_saved": "✅ اطلاعات بانکی شما ذخیره شد.",
    "bank_name_mismatch": (
        "⚠️ نام صاحب کارت با نام ثبت‌نام شما ({first_name} {last_name}) یکی نیست.\n"
        "برداشت فقط به کارتی انجام می‌شود که به نام خودتان باشد. "
        "اگر اشتباه وارد کرده‌اید، اطلاعات را دوباره ثبت کنید."
    ),
    "bank_cancelled": "انصراف داده شد.",
}
