# 📉 Amazon Price Tracker

A Python automation script that monitors product prices on Amazon India and sends real-time email alerts when prices drop.

## Features
* **Web Scraping:** Uses `BeautifulSoup` to parse live Amazon product pages.
* **Anti-Bot Evasion:** Implements custom headers to mimic real browser traffic.
* **Email Notifications:** Integrated with `smtplib` to send instant alerts via Gmail.
* **Automation:** Runs on a continuous loop to check prices every 6 hours.

## Tech Stack
* Python
* BeautifulSoup4
* Requests
* SMTP (Email Protocol)

## How to Run
1. Clone the repo.
2. Install dependencies: `pip install requests beautifulsoup4`
3. Update `config variables` with your own email/password.
4. Run `python scraper.py`
