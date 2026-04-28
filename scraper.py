import os
import time

from tracker import TrackerError, fetch_product_snapshot, send_price_alert


URL = os.environ.get("PRODUCT_URL", "")
TARGET_PRICE = float(os.environ.get("TARGET_PRICE", "0"))
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", "")
CHECK_INTERVAL_HOURS = int(os.environ.get("CHECK_INTERVAL_HOURS", "6"))


def check_amazon_price() -> None:
    if not URL or TARGET_PRICE <= 0 or not RECIPIENT_EMAIL:
        raise SystemExit(
            "Set PRODUCT_URL, TARGET_PRICE, and RECIPIENT_EMAIL before running scraper.py."
        )

    try:
        snapshot = fetch_product_snapshot(URL)
        print(f"Product: {snapshot.title}")
        print(f"Current price: Rs {snapshot.current_price:,.2f}")
        print(f"Target price: Rs {TARGET_PRICE:,.2f}")

        if snapshot.current_price <= TARGET_PRICE:
            print("Deal found. Sending alert email.")
            send_price_alert(snapshot, RECIPIENT_EMAIL, TARGET_PRICE)
        else:
            print("No deal yet.")
    except TrackerError as exc:
        print(f"Check failed: {exc}")


if __name__ == "__main__":
    while True:
        check_amazon_price()
        print(f"Sleeping for {CHECK_INTERVAL_HOURS} hour(s).")
        time.sleep(CHECK_INTERVAL_HOURS * 60 * 60)

