import requests
from bs4 import BeautifulSoup
import smtplib
import time

# --- CONFIGURATION ---
URL = "https://www.amazon.in/Autofocus-Photography-Vlogging-Anti-Shake-Batteries/dp/B0FV38K4VW/"
TARGET_PRICE = 8000.0
MY_EMAIL = "your_email@gmail.com"        
MY_PASSWORD = "xxxx xxxx xxxx xxxx"      
RECIPIENT_EMAIL = "friend@example.com"
CHECK_INTERVAL_HOURS = 6  # How often to check

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def send_email(product_title, price):
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(MY_EMAIL, MY_PASSWORD)

        subject = "Price Drop Alert!"
        body = f"Good news! The price for {product_title} has dropped to {price}.\n\nCheck it here: {URL}"
        msg = f"Subject: {subject}\nTo: {RECIPIENT_EMAIL}\nFrom: {MY_EMAIL}\n\n{body}"

        server.sendmail(MY_EMAIL, RECIPIENT_EMAIL, msg)
        print(f"📧 Email sent to {RECIPIENT_EMAIL} successfully!")
        server.quit()
    except Exception as e:
        print(f"Error sending email: {e}")

def check_amazon_price():
    print("🔎 Checking price...")
    try:
        page = requests.get(URL, headers=headers)
        if page.status_code != 200:
            print("Amazon blocked the access!")
            return

        soup = BeautifulSoup(page.content, 'html.parser')
        title = soup.find(id="productTitle").get_text().strip()
        price_whole = soup.find("span", class_="a-price-whole")
        
        if price_whole:
            current_price = float(price_whole.get_text().replace(",", "").replace(".", ""))
            print(f"   Product: {title[:30]}...") # Print just first 30 chars to keep it clean
            print(f"   Current Price: {current_price}")

            if current_price <= TARGET_PRICE:
                print("✅ DEAL FOUND! Sending email...")
                send_email(title, current_price)
            else:
                print(f"❌ No deal yet. Target: {TARGET_PRICE}")
        else:
            print("Price element not found.")

    except Exception as e:
        print(f"Error: {e}")

# --- THE INFINITE LOOP ---
while True:
    check_amazon_price()
    print(f"😴 Sleeping for {CHECK_INTERVAL_HOURS} hours...")
    
    # time.sleep takes seconds, so: Hours * 60 minutes * 60 seconds
    time.sleep(CHECK_INTERVAL_HOURS * 60 * 60)