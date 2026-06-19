"""داشبورد اصلی."""

from flask import Blueprint, render_template

from ..auth import login_required
from ..db import get_db
from ..queries import dashboard_stats, workers_with_balances

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def index():
    stats = dashboard_stats()
    debts = [w for w in workers_with_balances() if w["balance"] != 0]
    recent = get_db().execute(
        "SELECT * FROM projects ORDER BY id DESC LIMIT 6"
    ).fetchall()
    unsettled = get_db().execute(
        "SELECT * FROM projects WHERE status != 'settled' ORDER BY id DESC LIMIT 8"
    ).fetchall()
    return render_template(
        "dashboard.html",
        stats=stats,
        debts=debts,
        recent=recent,
        unsettled=unsettled,
    )
