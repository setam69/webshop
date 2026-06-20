"""کارخانه ساخت اپلیکیشن Flask پلتفرم حسابداری دستمزد."""

import os

from flask import Flask, g

from . import db, jalali, utils
from .config import Config
from .paths import resource_path


def create_app(test_config=None):
    # مسیر مطلق templates/static تا هم در اجرای عادی و هم در حالت exe درست باشد
    app = Flask(
        __name__,
        instance_relative_config=False,
        template_folder=resource_path("templates"),
        static_folder=resource_path("static"),
    )
    app.config.from_object(Config)
    if test_config is not None:
        app.config.update(test_config)

    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)
    os.makedirs(app.config["BACKUP_DIR"], exist_ok=True)

    db.init_app(app)
    _register_jinja(app)
    _register_blueprints(app)

    from . import demo
    demo.init_app(app)

    # راه‌اندازی امن دیتابیس در هر اجرا:
    #   ۰) واردکردن امن دیتابیس قدیمی اگر مقصد خالی است (بدون بازنویسی داده)
    #   ۱) ساخت جداول پایه در صورت نبود
    #   ۲) بکاپ خودکار پیش از هر تغییر ساختار (داده قبلی حفظ می‌شود)
    #   ۳) مهاجرت افزایشی و امن ساختار
    with app.app_context():
        if not app.config.get("TESTING"):
            db.bootstrap_database()
        db.init_db()
        db.auto_backup()
        db.migrate()

    return app


def _register_jinja(app):
    """فیلترها و متغیرهای سراسری قالب‌ها."""
    app.jinja_env.filters["money"] = utils.format_money
    app.jinja_env.filters["money_fa"] = utils.format_money_fa
    app.jinja_env.filters["percent"] = utils.format_percent
    app.jinja_env.filters["fa"] = jalali.to_persian_digits
    app.jinja_env.filters["jalali"] = jalali.gregorian_iso_to_jalali
    app.jinja_env.filters["status"] = utils.status_label
    app.jinja_env.filters["method"] = utils.method_label
    app.jinja_env.filters["expense"] = utils.expense_label
    app.jinja_env.filters["cstatus"] = utils.customer_status_label

    @app.context_processor
    def inject_globals():
        currency = "تومان"
        try:
            currency = db.get_setting("currency", "تومان") or "تومان"
        except Exception:
            pass
        return {
            "currency": currency,
            "STATUS_LABELS": utils.STATUS_LABELS,
            "STATUS_ORDER": utils.STATUS_ORDER,
            "PAYMENT_METHODS": utils.PAYMENT_METHODS,
            "PAYMENT_METHOD_ORDER": utils.PAYMENT_METHOD_ORDER,
            "EXPENSE_CATEGORIES": utils.EXPENSE_CATEGORIES,
            "EXPENSE_CATEGORY_ORDER": utils.EXPENSE_CATEGORY_ORDER,
            "current_user": g.get("user"),
        }


def _register_blueprints(app):
    from . import auth
    from .blueprints import (
        dashboard, workers, projects, payments, settlement, reports, settings,
        expenses, customer,
    )

    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(workers.bp)
    app.register_blueprint(projects.bp)
    app.register_blueprint(payments.bp)
    app.register_blueprint(settlement.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(settings.bp)
    app.register_blueprint(expenses.bp)
    app.register_blueprint(customer.bp)
