
import os, time, random
import requests
from bs4 import BeautifulSoup
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
from dotenv import load_dotenv

DB_URL = os.getenv("SUPABASE_DB_URL")

EMIRATES = {
    "Dubai":           os.getenv("Dubai_url"),
    "Abu Dhabi":       os.getenv("Abu_Dhabi_url"),
    "Sharjah":         os.getenv("Sharjah_url"),
    "Ajman":           os.getenv("Ajman_url"),
    "Al Ain":          os.getenv("Al_Ain_url"),
    "Fujairah":        os.getenv("Fujairah_url"),
    "Ras Al Khaimah":  os.getenv("Ras_Al_Khaimah_url"),
    "Umm Al Quwain":   os.getenv("Umm_Al_Quwain_url"),
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
MAX_PAGES = 5



CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS car_listings_raw (
    id           SERIAL PRIMARY KEY,
    listing_id   TEXT,
    manufacturer TEXT,
    model        TEXT,
    year         INT,
    price        INT,
    mileage      INT,
    fuel_type    TEXT,
    transmission TEXT,
    body_type    TEXT,
    seats        INT,
    cylinder     INT,
    location     TEXT,
    scraped_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (listing_id)
);
"""

INSERT_SQL = """
INSERT INTO car_listings_raw
    (listing_id, manufacturer, model, year, price, mileage,
     fuel_type, transmission, body_type, seats, cylinder, location)
VALUES %s
ON CONFLICT (listing_id) DO NOTHING;
"""


def safe_int(val):
    try:
        return int(val) if val not in (None, "", "0") else None
    except (ValueError, TypeError):
        return None


def parse_card(card, emirate: str) -> dict | None:
    try:
        return {
            "listing_id":   card.get("data-listing-id", ""),
            "manufacturer": card.get("data-make", "").strip(),
            "model":        card.get("data-model", "").strip(),
            "year":         safe_int(card.get("data-year")),
            "price":        safe_int(card.get("data-price")),
            "mileage":      safe_int(card.get("data-mileage")),
            "fuel_type":    card.get("data-fuel", "").strip(),
            "transmission": card.get("data-transmission", "").strip(),
            "body_type":    card.get("data-body-type", "").strip(),
            "seats":        safe_int(card.get("data-seats")),
            "cylinder":     safe_int(card.get("data-cylinder")),
            "location":     emirate,
        }
    except Exception as e:
        print(f"  parse error: {e}")
        return None


def scrape_emirate(emirate: str, base_url: str) -> list[dict]:
    listings = []
    for page in range(1, MAX_PAGES + 1):
        url = f"{base_url}?page={page}" if page > 1 else base_url
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                break
            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select("[data-listing-id]")
            if not cards:
                break
            for card in cards:
                row = parse_card(card, emirate)
                if row:
                    listings.append(row)
            print(f"  [{emirate}] page {page}: {len(cards)} listings")
            time.sleep(random.uniform(5, 10))
        except Exception as e:
            print(f"  [{emirate}] error page {page}: {e}")
            time.sleep(15)
    return listings


def upload(rows: list[dict]):
    conn = psycopg2.connect(DB_URL)
    cur  = conn.cursor()
    cur.execute(CREATE_TABLE_SQL)
    values = [
        (r["listing_id"], r["manufacturer"], r["model"], r["year"],
         r["price"], r["mileage"], r["fuel_type"], r["transmission"],
         r["body_type"], r["seats"], r["cylinder"], r["location"])
        for r in rows if r and r.get("listing_id")
    ]
    execute_values(cur, INSERT_SQL, values)
    conn.commit()
    print(f"Inserted {cur.rowcount} new rows (duplicates skipped).")
    cur.close()
    conn.close()


if __name__ == "__main__":
    all_rows = []
    for emirate, url in EMIRATES.items():
        print(f"\nScraping {emirate}...")
        rows = scrape_emirate(emirate, url)
        all_rows.extend(rows)
        print(f"  → {len(rows)} from {emirate}")

    print(f"\nTotal scraped: {len(all_rows)}")
    if all_rows:
        upload(all_rows)