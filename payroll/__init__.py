"""کارخانه ساخت اپلیکیشن Flask پلتفرم حسابداری دستمزد."""

import os

from flask import Flask, g

from . import db, jalali, utils
from .config import Config


def create_app(test_config=None):
    app = Flask(
        __name__,
        instance_relative_config=False,
        template_folder=os.path.join(os.pardir, "templates"),
        static_folder=os.path.join(os.pardir, "static"),
    )
    app.config.from_object(Config)
    if test_config is not None:
        app.config.update(test_config)

    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)
    os.makedirs(app.config["BACKUP_DIR"], exist_ok=True)

    db.init_app(app)
    _register_jinja(app)
    _register_blueprints(app)

    # اطمینان از وجود جداول در اولین اجرا
    with app.app_context():
        db.init_db()

    return app


def _register_jinja(app):
    """فیلترها و متغیرهای سراسری قالب‌ها."""
    app.jinja_env.filters["money"] = utils.format_money
    app.jinja_env.filters["money_fa"] = utils.format_money_fa
    app.jinja_env.filters["percent"] = utils.format_percent
    app.jinja_env.filters["fa"] = jalali.to_persian_digits
    app.jinja_env.filters["jalali"] = jalali.gregorian_iso_to_jalali
    app.jinja_env.filters["status"] = utils.status_label

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
            "current_user": g.get("user"),
        }


def _register_blueprints(app):
    from . import auth
    from .blueprints import (
        dashboard, workers, projects, payments, settlement, reports, settings,
    )

    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(workers.bp)
    app.register_blueprint(projects.bp)
    app.register_blueprint(payments.bp)
    app.register_blueprint(settlement.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(settings.bp)
