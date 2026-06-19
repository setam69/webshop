"""ابزار تاریخ شمسی (جلالی).

اگر کتابخانه ``jdatetime`` نصب باشد از آن استفاده می‌شود؛ در غیر این صورت یک
پیاده‌سازی خالص پایتونی برای تبدیل شمسی <-> میلادی به کار می‌رود تا برنامه هیچ
وابستگی سختی نداشته باشد.
"""

import datetime
import re

try:  # مسیر ترجیحی: دقیق و آزموده‌شده.
    import jdatetime  # type: ignore

    _HAVE_JDATETIME = True
except Exception:  # pragma: no cover
    _HAVE_JDATETIME = False


# --- مدیریت ارقام فارسی ------------------------------------------------------
_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_DIGIT_MAP = {ord(p): str(i) for i, p in enumerate(_PERSIAN_DIGITS)}
_DIGIT_MAP.update({ord(a): str(i) for i, a in enumerate(_ARABIC_DIGITS)})
_EN_TO_FA = {str(i): _PERSIAN_DIGITS[i] for i in range(10)}

_MONTHS_FA = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]


def to_english_digits(text):
    if text is None:
        return ""
    return str(text).translate(_DIGIT_MAP)


def to_persian_digits(text):
    if text is None:
        return ""
    return "".join(_EN_TO_FA.get(ch, ch) for ch in str(text))


# --- تبدیل خالص پایتونی شمسی/میلادی -----------------------------------------
def _g2j(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy - 1600
    gm2 = gm - 1
    gd2 = gd - 1
    g_day_no = 365 * gy2 + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400
    g_day_no += g_d_m[gm2] + gd2
    if gm2 > 1 and ((gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)):
        g_day_no += 1
    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no %= 12053
    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461
    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365
    if j_day_no < 186:
        jm = 1 + j_day_no // 31
        jd = 1 + j_day_no % 31
    else:
        jm = 7 + (j_day_no - 186) // 30
        jd = 1 + (j_day_no - 186) % 30
    return jy, jm, jd


def _j2g(jy, jm, jd):
    jy2 = jy - 979
    jm2 = jm - 1
    jd2 = jd - 1
    j_day_no = 365 * jy2 + (jy2 // 33) * 8 + (jy2 % 33 + 3) // 4
    for i in range(jm2):
        j_day_no += 31 if i < 6 else 30
    j_day_no += jd2
    g_day_no = j_day_no + 79
    gy = 1600 + 400 * (g_day_no // 146097)
    g_day_no %= 146097
    leap = True
    if g_day_no >= 36525:
        g_day_no -= 1
        gy += 100 * (g_day_no // 36524)
        g_day_no %= 36524
        if g_day_no >= 365:
            g_day_no += 1
        else:
            leap = False
    gy += 4 * (g_day_no // 1461)
    g_day_no %= 1461
    if g_day_no >= 366:
        leap = False
        g_day_no -= 1
        gy += g_day_no // 365
        g_day_no %= 365
    g_days_in_month = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 0
    while gm < 12 and g_day_no >= g_days_in_month[gm]:
        g_day_no -= g_days_in_month[gm]
        gm += 1
    gd = g_day_no + 1
    return gy, gm + 1, gd


# --- API عمومی ---------------------------------------------------------------
def today_jalali_str():
    if _HAVE_JDATETIME:
        t = jdatetime.date.today()
        return "%04d/%02d/%02d" % (t.year, t.month, t.day)
    g = datetime.date.today()
    jy, jm, jd = _g2j(g.year, g.month, g.day)
    return "%04d/%02d/%02d" % (jy, jm, jd)


def normalize_jalali(text):
    if not text:
        return None
    cleaned = to_english_digits(text).strip()
    parts = [p for p in re.split(r"[\/\-\.\s]+", cleaned) if p != ""]
    if len(parts) != 3:
        return None
    try:
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None
    if not (1 <= m <= 12 and 1 <= d <= 31 and y > 0):
        return None
    return "%04d/%02d/%02d" % (y, m, d)


def jalali_to_gregorian_iso(jalali_str):
    norm = normalize_jalali(jalali_str)
    if not norm:
        return None
    try:
        y, m, d = [int(x) for x in norm.split("/")]
        if _HAVE_JDATETIME:
            return jdatetime.date(y, m, d).togregorian().isoformat()
        gy, gm, gd = _j2g(y, m, d)
        return datetime.date(gy, gm, gd).isoformat()
    except Exception:
        return None


def gregorian_iso_to_jalali(iso_str):
    """تبدیل تاریخ میلادی ISO به رشته شمسی ``YYYY/MM/DD`` برای نمایش."""
    if not iso_str:
        return ""
    try:
        g = datetime.date.fromisoformat(str(iso_str)[:10])
    except Exception:
        return str(iso_str)
    if _HAVE_JDATETIME:
        j = jdatetime.date.fromgregorian(date=g)
        return "%04d/%02d/%02d" % (j.year, j.month, j.day)
    jy, jm, jd = _g2j(g.year, g.month, g.day)
    return "%04d/%02d/%02d" % (jy, jm, jd)


def jalali_long(jalali_str):
    """نمایش بلند مانند «۱۵ خرداد ۱۴۰۳»."""
    norm = normalize_jalali(jalali_str)
    if not norm:
        return ""
    y, m, d = [int(x) for x in norm.split("/")]
    return to_persian_digits("%d %s %d" % (d, _MONTHS_FA[m - 1], y))


def parse_date_input(text):
    """ورودی کاربر را به (شمسی, میلادی ISO) تبدیل می‌کند."""
    norm = normalize_jalali(text)
    if not norm:
        return None, None
    return norm, jalali_to_gregorian_iso(norm)


def today_pair():
    j = today_jalali_str()
    return j, jalali_to_gregorian_iso(j)
