# Amazon Price Tracker Dashboard

This project turns the original one-file Amazon scraper into a small Flask web app that:

- tracks multiple Amazon product URLs
- stores trackers in SQLite
- checks prices on a background loop
- sends email alerts when a target price is reached
- exposes a deployable website for Railway or any Python host

## Local setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

Open `http://127.0.0.1:5000`.

## Required environment variables

- `SECRET_KEY`: Flask session key.
- `SMTP_HOST`: SMTP server host.
- `SMTP_PORT`: SMTP server port, usually `587`.
- `SMTP_USERNAME`: SMTP login.
- `SMTP_PASSWORD`: SMTP password or Gmail app password.
- `ALERT_FROM_EMAIL`: sender address used for alerts.

The dashboard still works without SMTP variables, but it will only scrape prices and show status updates until email is configured.

## Deployment

This repo includes:

- `requirements.txt`
- `Procfile`
- `railway.json`

Deploy on Railway:

1. Push the repo to GitHub.
2. Create a Railway project from the repo.
3. Set the environment variables listed above.
4. Add a persistent volume and mount it at `/app/data` if you want tracker data to survive redeploys.

## Notes

- Amazon markup changes regularly, so scraping selectors may need maintenance.
- Amazon can rate-limit or block repeated server-side requests.
- The legacy CLI loop is still available through `python scraper.py` using environment variables.
