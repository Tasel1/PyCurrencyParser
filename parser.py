import csv
import json
import urllib.request
from datetime import datetime

URL = "https://open.er-api.com/v6/latest/USD"
try:
    with urllib.request.urlopen(URL, timeout=10) as response:
        data = json.loads(response.read().decode())
    rates = data.get("rates", {})
    timestamp = datetime.now().isoformat()
    rows = [
        {"currency": "USD/EUR", "rate": rates.get("EUR"), "timestamp": timestamp},
        {"currency": "USD/RUB", "rate": rates.get("RUB"), "timestamp": timestamp},
    ]
    with open("rates.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["currency", "rate", "timestamp"])
        writer.writeheader()
        writer.writerows(rows)
    print("Success: Rates updated.")
except Exception as e:
    print(f"Error: {e}")
