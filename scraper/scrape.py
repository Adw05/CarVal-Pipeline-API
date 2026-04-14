import os, time, random, json
import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL")

EMIRATES = {
    "Dubai": "https://www.dubicars.com/search?c=new-and-used&cr=AED&did=&emif=&emit=&gen=&k=&kf=&kt=&l=3&ma=&mo=0&moc=&o=&pf=&pt=&set=bu&trg=&ul=AE&yf=&yt=&",
    "Abu Dhabi": "https://www.dubicars.com/search?c=new-and-used&cr=AED&did=&emif=&emit=&eo%5B0%5D=can-be-exported&eo%5B1%5D=not-for-export&gen=&k=&kf=&kt=&l=1&ma=&mo=0&moc=&o=&pf=&pt=&set=bu&trg=&ul=AE&yf=&yt=&",
    "Sharjah": "https://www.dubicars.com/search?c=new-and-used&cr=AED&did=&emif=&emit=&eo%5B0%5D=can-be-exported&eo%5B1%5D=not-for-export&gen=&k=&kf=&kt=&l=6&ma=&mo=0&moc=&o=&pf=&pt=&set=bu&trg=&ul=AE&yf=&yt=&",
    "Ajman": "https://www.dubicars.com/search?c=new-and-used&cr=AED&did=&emif=&emit=&eo%5B0%5D=can-be-exported&eo%5B1%5D=not-for-export&gen=&k=&kf=&kt=&l=2&ma=&mo=0&moc=&o=&pf=&pt=&set=bu&trg=&ul=AE&yf=&yt=&",
    "Al Ain": "https://www.dubicars.com/search?o=&did=&gen=&trg=&moc=&c=new-and-used&ul=AE&cr=AED&k=&mg=&yf=&yt=&set=bu&pf=&pt=&emif=&emit=&kf=&kt=&eo%5B%5D=can-be-exported&eo%5B%5D=not-for-export&l=8&noi=30",
    "Fujairah": "https://www.dubicars.com/search?o=&did=&gen=&trg=&moc=&c=new-and-used&ul=AE&cr=AED&k=&mg=&yf=&yt=&set=bu&pf=&pt=&emif=&emit=&kf=&kt=&eo%5B%5D=can-be-exported&eo%5B%5D=not-for-export&l=4&noi=30",
    "Ras Al Khaimah": "https://www.dubicars.com/search?o=&did=&gen=&trg=&moc=&c=new-and-used&ul=AE&cr=AED&k=&mg=&yf=&yt=&set=bu&pf=&pt=&emif=&emit=&kf=&kt=&eo%5B%5D=can-be-exported&eo%5B%5D=not-for-export&l=5&noi=30",
    "Umm Al Quwain": "https://www.dubicars.com/search?o=&did=&gen=&trg=&moc=&c=new-and-used&ul=AE&cr=AED&k=&ma=&mo=0&yf=&yt=&set=bu&pf=&pt=&emif=&emit=&kf=&kt=&eo%5B%5D=can-be-exported&eo%5B%5D=not-for-export&l=7",
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
    listing_id   TEXT UNIQUE,
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
    scraped_at   TIMESTAMPTZ DEFAULT NOW()
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
        return int(val) if val not in (None, "", "N/A") else None
    except (ValueError, TypeError):
        return None


def parse_card(card, emirate: str) -> dict | None:
    try:
        
        raw = card.get("data-mixpanel-detail")
        if not raw:
            return None
            
        data = json.loads(raw)

        return {
            "listing_id":   str(card.get("data-item-id", "")), 
            "manufacturer": data.get("item_make", "N/A"),
            "model":        data.get("item_model", "N/A"),
            "year":         safe_int(data.get("item_year")),
            "price":        safe_int(data.get("item_local_price")),
            "mileage":      safe_int(data.get("item_mileage")),
            "fuel_type":    data.get("item_fuel_type", "N/A"),
            "transmission": data.get("item_gearbox", "N/A"),
            "body_type":    data.get("item_body_type", "N/A"),
            "seats":        safe_int(data.get("item_seats")),
            "cylinder":     safe_int(data.get("item_cylinder")),
            "location":     data.get("item_location", emirate),
        }
    except Exception as e:
        print(f"  Parse error for ID {card.get('data-item-id')}: {e}")
        return None



def scrape_emirate(emirate: str, base_url: str) -> list[dict]:
    listings = []
    for page in range(1, MAX_PAGES + 1):
        url = f"{base_url}&page={page}" if page > 1 else base_url
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            soup  = BeautifulSoup(response.content, "html.parser")
            cards = soup.find_all("li", {"class": "serp-list-item"})

            if not cards:
                print(f"  [{emirate}] no listings on page {page}, stopping.")
                break

            for card in cards:
                row = parse_card(card, emirate)
                if row:
                    listings.append(row)

            print(f"  [{emirate}] page {page}: {len(cards)} listings")
            time.sleep(random.uniform(5, 10))

        except requests.HTTPError as e:
            print(f"  [{emirate}] HTTP error page {page}: {e}")
            break
        except Exception as e:
            print(f"  [{emirate}] error page {page}: {e}")
            time.sleep(15)

    return listings



def upload(rows: list[dict]):
    conn = psycopg2.connect(DB_URL)
    cur  = conn.cursor()

    # Create table if not exists
    cur.execute(CREATE_TABLE_SQL)
    conn.commit()

    # Check row count before insert
    cur.execute("SELECT COUNT(*) FROM car_listings_raw;")
    before = cur.fetchone()[0]
    print(f"Rows in DB before insert: {before}")

    values = [
        (
            r["listing_id"], r["manufacturer"], r["model"], r["year"],
            r["price"], r["mileage"], r["fuel_type"], r["transmission"],
            r["body_type"], r["seats"], r["cylinder"], r["location"]
        )
        for r in rows if r and r.get("listing_id")
    ]

    print(f"Attempting to insert {len(values)} rows...")

    try:
        execute_values(cur, INSERT_SQL, values, page_size=100)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Insert failed, rolled back. Error: {e}")
        cur.close()
        conn.close()
        return

    # Check row count after insert
    cur.execute("SELECT COUNT(*) FROM car_listings_raw;")
    after = cur.fetchone()[0]
    print(f"Rows in DB after insert:  {after}")
    print(f"New rows added:           {after - before}")

    cur.close()
    conn.close()



if __name__ == "__main__":
    all_rows = []
    for emirate, url in EMIRATES.items():
        if not url:
            print(f"\nSkipping {emirate} — URL not set in .env")
            continue
        print(f"\nScraping {emirate}...")
        rows = scrape_emirate(emirate, url)
        all_rows.extend(rows)
        print(f"  → {len(rows)} from {emirate}")

    print(f"\nTotal scraped: {len(all_rows)}")
    if all_rows:
        upload(all_rows)