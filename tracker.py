import os
import re
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

import requests
from bs4 import BeautifulSoup


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}


class TrackerError(Exception):
    pass


@dataclass(slots=True)
class ProductSnapshot:
    title: str
    current_price: float
    product_url: str


def parse_price(raw_price: str) -> float:
    cleaned = raw_price.strip().replace(",", "")
    match = re.search(r"(\d+(?:\.\d+)?)", cleaned)
    if not match:
        raise TrackerError(f"Could not parse price from '{raw_price}'.")
    return float(match.group(1))


def fetch_product_snapshot(product_url: str) -> ProductSnapshot:
    try:
        response = requests.get(
            product_url,
            headers=DEFAULT_HEADERS,
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise TrackerError(f"Request failed: {exc}") from exc

    soup = BeautifulSoup(response.text, "html.parser")
    title_node = soup.select_one("#productTitle")
    price_node = soup.select_one(".a-price .a-offscreen")

    if title_node is None:
        raise TrackerError("Amazon did not return a product title.")
    if price_node is None:
        raise TrackerError("Amazon price element was not found.")

    title = title_node.get_text(strip=True)
    current_price = parse_price(price_node.get_text(strip=True))
    return ProductSnapshot(title=title, current_price=current_price, product_url=product_url)


def email_config_ready() -> bool:
    required_keys = (
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "ALERT_FROM_EMAIL",
    )
    return all(os.environ.get(key) for key in required_keys)


def send_price_alert(snapshot: ProductSnapshot, recipient_email: str, target_price: float) -> None:
    if not email_config_ready():
        raise TrackerError("SMTP settings are missing.")

    message = EmailMessage()
    sender = os.environ["ALERT_FROM_EMAIL"]
    message["Subject"] = f"Price alert: {snapshot.title[:60]}"
    message["From"] = sender
    message["To"] = recipient_email
    message.set_content(
        "\n".join(
            [
                f"{snapshot.title}",
                f"Current price: Rs {snapshot.current_price:,.2f}",
                f"Target price: Rs {target_price:,.2f}",
                "",
                f"Open product: {snapshot.product_url}",
            ]
        )
    )

    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ["SMTP_PORT"])) as server:
        server.starttls()
        server.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
        server.send_message(message)

