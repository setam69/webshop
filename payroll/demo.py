"""ساخت داده نمونه (Demo Data) — فقط با دستور جداگانه اجرا می‌شود، نه همیشه.

اجرا:
    flask --app run seed-demo          (یا)    python -m payroll.demo

این داده‌ها برای آزمایش سریع برنامه هستند:
  * دو نیروی نمونه با درصد پیش‌فرض ۳۰٪
  * یک پروژه نمونه ۱۰٬۰۰۰٬۰۰۰ تومانی
  * محاسبه نمونه: ۳۰٪ + ۳۰٪ نیروها = ۶٬۰۰۰٬۰۰۰ ، سهم مغازه ۴۰٪ = ۴٬۰۰۰٬۰۰۰
"""

from datetime import datetime

import click
from flask import current_app
from flask.cli import with_appcontext

from .db import get_db
from .jalali import today_pair
from .utils import worker_share


def seed_demo(reset=False):
    """داده نمونه را می‌سازد. اگر ``reset`` باشد، داده‌های قبلی پاک می‌شوند.

    خروجی: متن خلاصه برای نمایش.
    """
    db = get_db()
    now = datetime.now().isoformat(timespec="seconds")
    j_today, iso_today = today_pair()

    if reset:
        db.executescript(
            "DELETE FROM payments;"
            "DELETE FROM project_workers;"
            "DELETE FROM projects;"
            "DELETE FROM workers;"
        )
        db.commit()

    # جلوگیری از ساخت تکراری
    existing = db.execute(
        "SELECT id FROM projects WHERE name = ?", ("پروژه نمونه نصب",)
    ).fetchone()
    if existing and not reset:
        return "داده نمونه از قبل وجود دارد. برای بازسازی از گزینه reset استفاده کنید."

    # --- دو نیروی نمونه با درصد پیش‌فرض ۳۰٪ ---
    w1 = db.execute(
        "INSERT INTO workers (name, phone, default_percent, is_active, note, created_at)"
        " VALUES (?, ?, ?, 1, ?, ?)",
        ("علی رضایی", "09120000001", 30, "نیروی نمونه", now),
    ).lastrowid
    w2 = db.execute(
        "INSERT INTO workers (name, phone, default_percent, is_active, note, created_at)"
        " VALUES (?, ?, ?, 1, ?, ?)",
        ("رضا محمدی", "09120000002", 30, "نیروی نمونه", now),
    ).lastrowid

    # --- یک پروژه نمونه ۱۰٬۰۰۰٬۰۰۰ تومانی ---
    labor = 10_000_000
    pid = db.execute(
        "INSERT INTO projects (name, customer_name, project_date, project_date_jalali,"
        " address, labor_amount, note, status, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, 'in_progress', ?)",
        ("پروژه نمونه نصب", "آقای کریمی", iso_today, j_today,
         "تهران، خیابان نمونه", labor, "پروژه برای آزمایش محاسبات", now),
    ).lastrowid

    # هر نیرو ۳۰٪ → سهم مغازه ۴۰٪
    for wid in (w1, w2):
        db.execute(
            "INSERT INTO project_workers (project_id, worker_id, percent, share_amount)"
            " VALUES (?, ?, ?, ?)",
            (pid, wid, 30, worker_share(labor, 30)),
        )
    db.commit()

    share = worker_share(labor, 30)
    return (
        "داده نمونه ساخته شد:\n"
        "  • ۲ نیرو (علی رضایی، رضا محمدی) با درصد پیش‌فرض ۳۰٪\n"
        "  • ۱ پروژه «پروژه نمونه نصب» با مبلغ ۱۰٬۰۰۰٬۰۰۰ تومان\n"
        "  • سهم هر نیرو: %s تومان | سهم مغازه (۴۰٪): %s تومان"
        % ("{:,}".format(share), "{:,}".format(labor - 2 * share))
    )


@click.command("seed-demo")
@click.option("--reset", is_flag=True, help="پاک‌سازی داده‌های فعلی پیش از ساخت نمونه.")
@with_appcontext
def seed_demo_command(reset):
    """دستور خط فرمان برای ساخت داده نمونه."""
    click.echo(seed_demo(reset=reset))


def init_app(app):
    app.cli.add_command(seed_demo_command)


if __name__ == "__main__":
    # امکان اجرا با: python -m payroll.demo
    from . import create_app

    app = create_app()
    with app.app_context():
        print(seed_demo())
