"""توابع کمکی: قالب‌بندی اعداد، تجزیه ورودی و محاسبات مالی."""

from . import jalali


def parse_amount(text):
    """رشته مبلغ ورودی (با جداکننده/ارقام فارسی) را به عدد صحیح تومان تبدیل می‌کند.

    در صورت نامعتبر بودن، ``None`` برمی‌گرداند.
    """
    if text is None:
        return None
    s = jalali.to_english_digits(text).strip()
    s = s.replace(",", "").replace("،", "").replace(" ", "")
    if s == "":
        return None
    try:
        # اجازه ورودی اعشاری ولی نتیجه به تومان صحیح گرد می‌شود
        value = float(s)
    except ValueError:
        return None
    if value < 0:
        return None
    return int(round(value))


def parse_percent(text):
    """رشته درصد را به عدد اعشاری تبدیل می‌کند (۰ تا ۱۰۰)؛ نامعتبر → ``None``."""
    if text is None or str(text).strip() == "":
        return None
    s = jalali.to_english_digits(text).strip().replace("%", "").replace("٪", "")
    try:
        value = float(s)
    except ValueError:
        return None
    if value < 0 or value > 100:
        return None
    return round(value, 4)


def worker_share(labor_amount, percent):
    """سهم نیرو = مبلغ کل × درصد ÷ ۱۰۰ (گرد شده به تومان صحیح)."""
    return int(round((labor_amount or 0) * (percent or 0) / 100.0))


def compute_shares(labor_amount, percents):
    """لیست درصدها را گرفته و (لیست سهم‌ها، مجموع سهم نیروها، سهم مغازه) را می‌دهد.

    سهم مغازه = مبلغ کل − مجموع سهم نیروها.
    """
    shares = [worker_share(labor_amount, p) for p in percents]
    total = sum(shares)
    shop = (labor_amount or 0) - total
    return shares, total, shop


def format_money(value):
    """قالب‌بندی مبلغ با جداکننده هزارگان (ارقام انگلیسی)."""
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return "0"
    return "{:,}".format(n)


def format_money_fa(value):
    """قالب‌بندی مبلغ با جداکننده هزارگان و ارقام فارسی."""
    return jalali.to_persian_digits(format_money(value))


def format_percent(value):
    """نمایش درصد بدون صفرهای اضافی (مثلاً ۳۰ یا ۳۳٫۵)."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "0"
    if v == int(v):
        return str(int(v))
    return ("%g" % v)


STATUS_LABELS = {
    "not_started": "انجام نشده",
    "in_progress": "در حال انجام",
    "done": "انجام شده",
    "settled": "تسویه شده",
}

STATUS_ORDER = ["not_started", "in_progress", "done", "settled"]


def status_label(code):
    return STATUS_LABELS.get(code, code or "")
