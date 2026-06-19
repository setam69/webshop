"""تست دود (smoke test) برای اطمینان از سلامت مسیرها و محاسبات اصلی."""

import os
import tempfile

import pytest

from payroll import create_app
from payroll.jalali import to_persian_digits
from payroll.utils import compute_shares, parse_amount, parse_percent


@pytest.fixture
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app({
        "TESTING": True,
        "DATABASE": path,
        "WTF_CSRF_ENABLED": False,
    })
    with app.test_client() as c:
        yield c
    os.unlink(path)


def login(client, username="admin", password="admin"):
    return client.post("/login", data={"username": username, "password": password},
                       follow_redirects=True)


# --- محاسبات ----------------------------------------------------------------
def test_compute_shares_example():
    # نمونه صورت مسئله: ۱۰٬۰۰۰٬۰۰۰ با دو نیرو ۳۰٪
    shares, total, shop = compute_shares(10_000_000, [30, 30])
    assert shares == [3_000_000, 3_000_000]
    assert total == 6_000_000
    assert shop == 4_000_000


def test_parse_helpers():
    assert parse_amount("۱۰,۰۰۰,۰۰۰") == 10_000_000
    assert parse_amount("abc") is None
    assert parse_percent("30") == 30
    assert parse_percent("150") is None


# --- مسیرها ------------------------------------------------------------------
def test_login_required_redirect(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_full_flow(client):
    assert login(client).status_code == 200

    # افزودن نیرو
    client.post("/workers/new", data={
        "name": "علی", "phone": "0912", "default_percent": "30", "is_active": "1",
    }, follow_redirects=True)
    client.post("/workers/new", data={
        "name": "رضا", "default_percent": "30", "is_active": "1",
    }, follow_redirects=True)

    # ثبت پروژه با دو نیرو ۳۰٪
    resp = client.post("/projects/new", data={
        "name": "نصب پروژه ۱", "labor_amount": "10,000,000",
        "project_date": "1403/03/29", "status": "done",
        "worker_id": ["1", "2"], "percent_1": "30", "percent_2": "30",
    }, follow_redirects=True)
    assert "نصب پروژه ۱".encode() in resp.data
    # سهم مغازه باید ۴٬۰۰۰٬۰۰۰ باشد (نمایش با ارقام فارسی)
    assert to_persian_digits("4,000,000").encode() in resp.data

    # درصد بیش از ۱۰۰ نباید ثبت شود
    resp = client.post("/projects/new", data={
        "name": "پروژه خطا", "labor_amount": "1000000",
        "worker_id": ["1", "2"], "percent_1": "60", "percent_2": "60",
    }, follow_redirects=True)
    assert "۱۰۰".encode() in resp.data or "100".encode() in resp.data

    # ثبت پرداخت به نیرو ۱
    client.post("/payments/new", data={
        "worker_id": "1", "project_id": "1", "amount": "1000000",
        "payment_date": "1403/03/30", "back": "/settlement/1",
    }, follow_redirects=True)

    # صفحه تسویه: مانده باید ۲٬۰۰۰٬۰۰۰ باشد (۳م سهم منهای ۱م پرداخت)
    resp = client.get("/settlement/1")
    assert to_persian_digits("2,000,000").encode() in resp.data

    # گزارش‌ها و خروجی اکسل
    assert client.get("/reports/?type=projects").status_code == 200
    xlsx = client.get("/reports/export.xlsx?type=worker_debt")
    assert xlsx.status_code == 200
    assert xlsx.headers["Content-Type"].startswith("application/vnd.openxml")

    # داشبورد
    resp = client.get("/")
    assert resp.status_code == 200
