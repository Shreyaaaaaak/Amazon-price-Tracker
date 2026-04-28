import os
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import Flask, flash, redirect, render_template, request, url_for

from storage import create_tracker, delete_tracker, due_trackers, get_tracker, init_db, list_trackers, update_error, update_success
from tracker import TrackerError, email_config_ready, fetch_product_snapshot, send_price_alert


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "development-secret-key")

_scheduler_started = False
_scheduler_lock = threading.Lock()


def is_valid_amazon_url(product_url: str) -> bool:
    parsed = urlparse(product_url)
    return parsed.scheme in {"http", "https"} and "amazon." in parsed.netloc


def format_timestamp(value: str | None) -> str:
    if not value:
        return "Not checked yet"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value
    return parsed.astimezone().strftime("%d %b %Y, %I:%M %p")


def run_tracker_check(tracker_row, *, allow_email: bool) -> tuple[bool, str]:
    try:
        snapshot = fetch_product_snapshot(tracker_row["product_url"])
        status = f"Watching at Rs {snapshot.current_price:,.2f}"
        alerted = False
        should_send_alert = (
            tracker_row["last_alerted_price"] is None
            or snapshot.current_price < tracker_row["last_alerted_price"]
        )

        if snapshot.current_price <= tracker_row["target_price"]:
            status = "Target reached"
            if allow_email and email_config_ready() and should_send_alert:
                send_price_alert(snapshot, tracker_row["recipient_email"], tracker_row["target_price"])
                status = "Alert sent"
                alerted = True
            elif allow_email and email_config_ready():
                status = "Target still met, alert already sent"
            elif allow_email:
                status = "Target reached, email not configured"

        update_success(
            tracker_row["id"],
            title=snapshot.title,
            current_price=snapshot.current_price,
            status=status,
            interval_hours=tracker_row["interval_hours"],
            alerted=alerted,
        )
        return True, status
    except TrackerError as exc:
        update_error(
            tracker_row["id"],
            error_message=str(exc),
            interval_hours=tracker_row["interval_hours"],
        )
        return False, str(exc)


def scheduler_loop() -> None:
    while True:
        for tracker_row in due_trackers():
            run_tracker_check(tracker_row, allow_email=True)
            time.sleep(2)
        time.sleep(30)


def should_start_scheduler() -> bool:
    if os.environ.get("FLASK_DEBUG") == "1":
        return os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    return True


def ensure_scheduler_started() -> None:
    global _scheduler_started
    if not should_start_scheduler():
        return
    with _scheduler_lock:
        if _scheduler_started:
            return
        scheduler = threading.Thread(target=scheduler_loop, daemon=True, name="price-tracker-scheduler")
        scheduler.start()
        _scheduler_started = True


@app.before_request
def start_scheduler_on_request() -> None:
    ensure_scheduler_started()


@app.template_filter("pretty_time")
def pretty_time_filter(value: str | None) -> str:
    return format_timestamp(value)


@app.template_filter("currency_inr")
def currency_filter(value) -> str:
    if value is None:
        return "Pending"
    return f"Rs {float(value):,.2f}"


@app.context_processor
def inject_template_context():
    return {
        "email_ready": email_config_ready(),
        "now": datetime.now(timezone.utc),
    }


@app.route("/", methods=["GET"])
def index():
    trackers = list_trackers()
    return render_template("index.html", trackers=trackers)


@app.route("/trackers", methods=["POST"])
def add_tracker():
    product_url = request.form.get("product_url", "").strip()
    recipient_email = request.form.get("recipient_email", "").strip()
    target_price_raw = request.form.get("target_price", "").strip()
    interval_hours_raw = request.form.get("interval_hours", "6").strip()

    if not product_url or not recipient_email or not target_price_raw:
        flash("Product URL, target price, and recipient email are required.", "error")
        return redirect(url_for("index"))

    if not is_valid_amazon_url(product_url):
        flash("Enter a valid Amazon product URL.", "error")
        return redirect(url_for("index"))

    try:
        target_price = float(target_price_raw)
        interval_hours = int(interval_hours_raw)
    except ValueError:
        flash("Target price and interval must be numeric.", "error")
        return redirect(url_for("index"))

    if target_price <= 0 or interval_hours <= 0:
        flash("Target price and interval must be greater than zero.", "error")
        return redirect(url_for("index"))

    tracker_id = create_tracker(product_url, target_price, recipient_email, interval_hours)
    tracker_row = get_tracker(tracker_id)
    if tracker_row is not None:
        ok, message = run_tracker_check(tracker_row, allow_email=False)
        if ok:
            flash("Tracker added.", "success")
        else:
            flash(f"Tracker added, but the first check failed: {message}", "error")
    else:
        flash("Tracker added.", "success")
    return redirect(url_for("index"))


@app.route("/trackers/<int:tracker_id>/check", methods=["POST"])
def check_tracker(tracker_id: int):
    tracker_row = get_tracker(tracker_id)
    if tracker_row is None:
        flash("Tracker not found.", "error")
        return redirect(url_for("index"))

    ok, message = run_tracker_check(tracker_row, allow_email=True)
    flash(message, "success" if ok else "error")
    return redirect(url_for("index"))


@app.route("/trackers/<int:tracker_id>/delete", methods=["POST"])
def remove_tracker(tracker_id: int):
    delete_tracker(tracker_id)
    flash("Tracker removed.", "success")
    return redirect(url_for("index"))


@app.route("/healthz", methods=["GET"])
def healthcheck():
    return {"ok": True}


init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    ensure_scheduler_started()
    app.run(host="0.0.0.0", port=port, debug=True)
