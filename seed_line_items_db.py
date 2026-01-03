#!/usr/bin/env python3
"""
One-time helper to ensure line-item-specific columns exist and seed sample line items with targeting into MySQL.
Safe to re-run; skips inserts if names already present.
"""
import os
import json
import mysql.connector
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

CFG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "root"),
    "database": os.getenv("MYSQL_DATABASE", "gam360"),
}

SAMPLE_ITEMS = [
    {
        "name": "Sponsor Tech Home",
        "priority": 16,
        "cpm": 15.0,
        "pacing": "even",
        "campaign_id": 1,
        "publisher_id": 1,
        "daily_budget": 5000,
        "lifetime_budget": 120000,
        "daily_goal": 20000,
        "lifetime_goal": 100000,
        "targeting": {
            "adUnits": ["tech/home/hero", "tech/home/sidebar"],
            "kv": {"section": "technology"},
            "geo": ["US"],
            "devices": ["desktop", "mobile"],
        },
    },
    {
        "name": "Partner Tech Hero",
        "priority": 12,
        "cpm": 10.0,
        "pacing": "even",
        "campaign_id": 2,
        "publisher_id": 1,
        "daily_budget": 4000,
        "lifetime_budget": 90000,
        "daily_goal": 15000,
        "lifetime_goal": 50000,
        "targeting": {
            "adUnits": ["tech/home/hero"],
            "kv": {"section": ["technology", "ai"]},
            "geo": ["US", "CA"],
            "devices": ["desktop", "mobile"],
        },
    },
    {
        "name": "Price Priority Run",
        "priority": 10,
        "cpm": 6.5,
        "pacing": "asap",
        "campaign_id": 3,
        "publisher_id": 2,
        "daily_budget": 3000,
        "lifetime_budget": 70000,
        "daily_goal": 12000,
        "lifetime_goal": 200000,
        "targeting": {
            "adUnits": ["tech/home/hero", "tech/home/sidebar"],
            "kv": {},
            "geo": ["US", "CA", "MX"],
            "devices": ["desktop", "mobile"],
        },
    },
    {
        "name": "Standard News",
        "priority": 8,
        "cpm": 4.0,
        "pacing": "even",
        "campaign_id": 4,
        "publisher_id": 2,
        "daily_budget": 2000,
        "lifetime_budget": 60000,
        "daily_goal": 8000,
        "lifetime_goal": 150000,
        "targeting": {
            "adUnits": ["tech/home/hero", "tech/home/sidebar", "tech/articles"],
            "kv": {"category": ["news", "opinion", "analysis"]},
            "geo": ["US"],
            "devices": ["desktop", "mobile"],
        },
    },
    {
        "name": "Remnant Tech",
        "priority": 6,
        "cpm": 1.5,
        "pacing": "asap",
        "campaign_id": 5,
        "publisher_id": 3,
        "daily_budget": 1000,
        "lifetime_budget": 20000,
        "daily_goal": 4000,
        "lifetime_goal": 80000,
        "targeting": {
            "adUnits": ["tech/home", "tech/articles", "tech/sidebar"],
            "kv": {},
            "geo": ["US", "CA", "MX", "GB"],
            "devices": ["desktop", "mobile", "app"],
        },
    },
    {
        "name": "House Tech",
        "priority": 4,
        "cpm": 0.0,
        "pacing": "asap",
        "campaign_id": 6,
        "publisher_id": 3,
        "daily_budget": 500,
        "lifetime_budget": 5000,
        "daily_goal": None,
        "lifetime_goal": None,
        "targeting": {
            "adUnits": ["tech/home", "tech/articles", "tech/sidebar"],
            "kv": {},
            "geo": [],
            "devices": [],
        },
    },
]


def ensure_columns(cursor):
    alters = [
        "ALTER TABLE orders ADD COLUMN priority INT DEFAULT 8 AFTER order_type",
        "ALTER TABLE orders ADD COLUMN cpm DECIMAL(10,4) DEFAULT 1.0 AFTER priority",
        "ALTER TABLE orders ADD COLUMN pacing_strategy ENUM('even','asap') DEFAULT 'even' AFTER cpm",
        "ALTER TABLE orders ADD COLUMN targeting JSON NULL AFTER pacing_strategy",
    ]
    for stmt in alters:
        try:
            cursor.execute(stmt)
        except mysql.connector.Error as err:
            if "Duplicate column" in str(err):
                continue
            raise


def upsert_line_items(conn):
    cursor = conn.cursor()
    ensure_columns(cursor)
    today = date.today()
    start = today - timedelta(days=5)
    end = today + timedelta(days=25)

    inserted = []
    for item in SAMPLE_ITEMS:
        cursor.execute("SELECT order_id FROM orders WHERE order_name = %s LIMIT 1", (item["name"],))
        existing = cursor.fetchone()
        if existing:
            order_id = existing[0]
        else:
            cursor.execute(
                """
                INSERT INTO orders (
                    order_name, campaign_id, publisher_id, order_type, start_date, end_date,
                    daily_budget, lifetime_budget, daily_impression_goal, lifetime_impression_goal,
                    pacing_rate, status, priority, cpm, pacing_strategy, targeting
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'ACTIVE',%s,%s,%s,%s)
                """,
                (
                    item["name"],
                    item["campaign_id"],
                    item["publisher_id"],
                    "GUARANTEED",
                    start.isoformat(),
                    end.isoformat(),
                    item["daily_budget"],
                    item["lifetime_budget"],
                    item["daily_goal"],
                    item["lifetime_goal"],
                    100.0,
                    item["priority"],
                    item["cpm"],
                    item["pacing"],
                    json.dumps(item["targeting"]),
                ),
            )
            order_id = cursor.lastrowid
        inserted.append((order_id, item["name"]))
    conn.commit()
    cursor.close()
    return inserted


def main():
    conn = mysql.connector.connect(**CFG)
    ids = upsert_line_items(conn)
    print("Seeded line items (order_id, name):")
    for oid, name in ids:
        print(f" - {oid}: {name}")
    conn.close()


if __name__ == "__main__":
    main()
