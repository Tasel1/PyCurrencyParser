import asyncio
import json
import urllib.request
from datetime import datetime, timezone
import logging

from sqlalchemy.orm import Session
from . import models
from .database import SessionLocal

logger = logging.getLogger(__name__)
URL = "https://open.er-api.com/v6/latest/USD"

def fetch_and_store_rates():
    try:
        with urllib.request.urlopen(URL, timeout=10) as response:
            data = json.loads(response.read().decode())
        rates = data.get("rates", {})
        
        db: Session = SessionLocal()
        try:
            timestamp = datetime.now(timezone.utc)
            for currency, rate_key in [("USD/EUR", "EUR"), ("USD/RUB", "RUB")]:
                rate_value = rates.get(rate_key)
                if rate_value is not None:
                    new_rate = models.CurrencyHistory(
                        currency=currency,
                        rate=rate_value,
                        timestamp=timestamp
                    )
                    db.add(new_rate)
            db.commit()
            # print("Success: Rates updated.")
        finally:
            db.close()
    except Exception as e:
        print(f"Error: {e}")

async def periodic_rate_fetcher():
    while True:
        await asyncio.to_thread(fetch_and_store_rates)
        await asyncio.sleep(60)
