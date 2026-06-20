"""تست دود (smoke test) برای اطمینان از سلامت مسیرها و محاسبات اصلی."""

import os
import tempfile

import pytest

from payroll import create_app
from payroll.jalali import to_persian_digits
from payroll.utils import compute_shares, format_money, parse_amount, parse_percent


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
    assert parse_amount("") is None
    assert parse_amount("-500") is None        # مبلغ منفی رد شود
    assert parse_percent("30") == 30
    assert parse_percent("150") is None         # درصد بالای ۱۰۰ رد شود
    assert parse_percent("-5") is None          # درصد منفی رد شود


def test_format_money_tolerates_strings():
    # نمایش مبلغ پس از خطای فرم (ورودی رشته‌ای با کاما) نباید صفر شود
    assert format_money("10,000,000") == "10,000,000"
    assert format_money("۱۰۰۰") == "1,000"
    assert format_money(2500000) == "2,500,000"


def test_password_is_hashed(client):
    # رمز عبور نباید به‌صورت متن ساده ذخیره شود
    login(client)
    app = client.application
    with app.app_context():
        from payroll.db import get_db
        row = get_db().execute(
            "SELECT password_hash FROM users WHERE username = 'admin'"
        ).fetchone()
    assert row["password_hash"] != "admin"
    assert row["password_hash"].startswith(("pbkdf2:", "scrypt:"))


def test_seed_demo(client):
    login(client)
    app = client.application
    with app.app_context():
        from payroll.demo import seed_demo
        seed_demo(reset=True)
        from payroll.db import get_db
        db = get_db()
        assert db.execute("SELECT COUNT(*) c FROM workers").fetchone()["c"] == 2
        proj = db.execute("SELECT * FROM projects").fetchone()
        assert proj["labor_amount"] == 10_000_000
        shares = db.execute(
            "SELECT share_amount FROM project_workers WHERE project_id = ?",
            (proj["id"],),
        ).fetchall()
        assert [s["share_amount"] for s in shares] == [3_000_000, 3_000_000]


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
        "customer_total": "12,000,000",
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

    # هزینه جانبی: ۵۰۰٬۰۰۰ → مانده واقعی مغازه = ۴٬۰۰۰٬۰۰۰ − ۵۰۰٬۰۰۰ = ۳٬۵۰۰٬۰۰۰
    client.post("/expenses/new", data={
        "project_id": "1", "category": "fuel", "amount": "500000",
        "expense_date": "1403/03/30",
    }, follow_redirects=True)
    resp = client.get("/projects/1")
    assert to_persian_digits("3,500,000").encode() in resp.data

    # دریافت از مشتری: ۵٬۰۰۰٬۰۰۰ از ۱۲٬۰۰۰٬۰۰۰ → مانده ۷٬۰۰۰٬۰۰۰ و وضعیت «دریافت ناقص»
    client.post("/customer-payments/new", data={
        "project_id": "1", "amount": "5000000", "method": "cash",
        "receive_date": "1403/03/30",
    }, follow_redirects=True)
    resp = client.get("/projects/1")
    assert to_persian_digits("7,000,000").encode() in resp.data
    assert "دریافت ناقص".encode() in resp.data

    # پرداخت بیشتر از مانده طلب بدون تأیید باید رد شود (مانده ۳م، تلاش ۹۹م)
    resp = client.post("/payments/new", data={
        "worker_id": "1", "project_id": "1", "amount": "99000000",
        "back": "/settlement/1",
    }, follow_redirects=True)
    assert "بیشتر از مانده طلب".encode() in resp.data
    # با تأیید باید ثبت شود
    client.post("/payments/new", data={
        "worker_id": "1", "project_id": "1", "amount": "99000000",
        "confirm_overpay": "1", "back": "/settlement/1",
    }, follow_redirects=True)

    # ثبت پرداخت عادی به نیرو ۱
    client.post("/payments/new", data={
        "worker_id": "2", "project_id": "1", "amount": "1000000",
        "method": "card", "payment_date": "1403/03/30", "back": "/settlement/2",
    }, follow_redirects=True)

    # چاپ پروژه باید کار کند
    assert client.get("/projects/1/print").status_code == 200

    # همه نوع گزارش‌ها و خروجی اکسل
    for rtype in ("projects", "shop_income", "shop_profit", "workers_share",
                  "worker_debt", "worker_performance", "customer_unpaid", "unsettled"):
        assert client.get("/reports/?type=%s" % rtype).status_code == 200
    xlsx = client.get("/reports/export.xlsx?type=customer_unpaid")
    assert xlsx.status_code == 200
    assert xlsx.headers["Content-Type"].startswith("application/vnd.openxml")

    # داشبورد
    resp = client.get("/")
    assert resp.status_code == 200


def test_migration_preserves_old_db(tmp_path):
    """مهاجرت روی دیتابیس قدیمی نباید داده‌ها را پاک کند و باید ستون‌ها را اضافه کند."""
    import sqlite3
    path = str(tmp_path / "old.db")
    con = sqlite3.connect(path)
    con.executescript(
        "CREATE TABLE users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT,"
        " full_name TEXT, role TEXT, is_active INTEGER, created_at TEXT);"
        "CREATE TABLE workers(id INTEGER PRIMARY KEY, name TEXT, phone TEXT, default_percent REAL,"
        " is_active INTEGER, note TEXT, created_at TEXT);"
        "CREATE TABLE projects(id INTEGER PRIMARY KEY, name TEXT, customer_name TEXT, project_date TEXT,"
        " project_date_jalali TEXT, address TEXT, labor_amount INTEGER, note TEXT, status TEXT, created_at TEXT);"
        "CREATE TABLE project_workers(id INTEGER PRIMARY KEY, project_id INTEGER, worker_id INTEGER, percent REAL, share_amount INTEGER);"
        "CREATE TABLE payments(id INTEGER PRIMARY KEY, worker_id INTEGER, project_id INTEGER, amount INTEGER,"
        " payment_date TEXT, payment_date_jalali TEXT, note TEXT, created_at TEXT);"
        "CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT);"
        "INSERT INTO projects(id,name,labor_amount,status,created_at) VALUES (1,'قدیمی',8000000,'done','2025');"
    )
    con.commit(); con.close()

    app = create_app({"DATABASE": path, "TESTING": True})
    with app.app_context():
        from payroll.db import get_db
        db = get_db()
        pcols = {r["name"] for r in db.execute("PRAGMA table_info(projects)")}
        assert {"customer_total", "internal_note"} <= pcols
        tables = {r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"expenses", "customer_payments"} <= tables
        row = db.execute("SELECT name, labor_amount, customer_total FROM projects WHERE id=1").fetchone()
        assert row["name"] == "قدیمی" and row["labor_amount"] == 8000000
        assert row["customer_total"] == 8000000  # backfill
