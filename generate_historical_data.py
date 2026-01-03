#!/usr/bin/env python3
"""
Digital-SSP - Historical Data Generator (2020-2025)
Generates multi-year historical data for dashboards and reporting
"""

import mysql.connector
import random
import datetime
from datetime import timedelta
import time
from dotenv import load_dotenv
import os

load_dotenv()

CFG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', 'root'),
    'database': os.getenv('MYSQL_DATABASE', 'gam360')
}

# Generate data from 2020 to present
START_DATE = datetime.datetime(2020, 1, 1)
END_DATE = datetime.datetime.now()
BATCH_SIZE = 5000

COUNTRIES = ['US', 'CA', 'MX', 'GB', 'DE', 'FR', 'JP', 'IN', 'BR', 'SG']
CITIES = ['New York', 'London', 'Toronto', 'Sydney', 'Berlin', 'Paris', 'Tokyo', 'Mumbai', 'São Paulo', 'Chicago']
BROWSERS = ['Chrome', 'Firefox', 'Safari', 'Edge', 'Opera']
OS_TYPES = ['Windows', 'macOS', 'iOS', 'Android', 'Linux']
DEVICE_TYPES = ['DESKTOP', 'MOBILE', 'TABLET']
PLATFORMS = ['WEB', 'MOBILE_APP', 'CONNECTED_TV']


def connect_db():
    try:
        conn = mysql.connector.connect(**CFG)
        print(f"✅ Connected to MySQL database: {CFG['database']}")
        return conn
    except mysql.connector.Error as err:
        print(f"❌ Error connecting to MySQL: {err}")
        exit(1)


def get_existing_ids(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT order_id FROM orders WHERE status = 'ACTIVE' LIMIT 100")
    order_ids = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT creative_id FROM creatives LIMIT 100")
    creative_ids = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT publisher_id FROM publishers LIMIT 100")
    publisher_ids = [row[0] for row in cursor.fetchall()]
    
    cursor.close()
    print(f"✅ Found {len(order_ids)} orders, {len(creative_ids)} creatives, {len(publisher_ids)} publishers")
    
    return order_ids, creative_ids, publisher_ids


def generate_historical_impressions(conn, order_ids, creative_ids, publisher_ids, records_per_day=500):
    """Generate impressions distributed across the date range"""
    cursor = conn.cursor()
    
    sql = """INSERT INTO impressions 
             (order_id, creative_id, publisher_id, user_id, device_type, country_code, city, 
              platform, browser_type, os_type, ip_address, impression_time, viewable, 
              view_duration, click_through, conversion, revenue)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    
    total_days = (END_DATE - START_DATE).days
    total_records = total_days * records_per_day
    
    print(f"\n📊 Generating {total_records:,} impressions across {total_days} days...")
    print(f"   Date range: {START_DATE.date()} to {END_DATE.date()}\n")
    
    batch = []
    records_inserted = 0
    start_time = time.time()
    
    current_date = START_DATE
    while current_date < END_DATE:
        # Generate records for this day
        for _ in range(records_per_day):
            # Random time during the day
            random_seconds = random.randint(0, 86400)
            imp_time = current_date + timedelta(seconds=random_seconds)
            
            # Don't generate future data
            if imp_time > END_DATE:
                break
            
            user_id = f"user_{random.randint(100000, 999999)}"
            revenue = round(random.uniform(2, 20) / 1000, 6)
            click_through = 1 if random.random() < 0.02 else 0
            conversion = 1 if click_through and random.random() < 0.1 else 0
            viewable = 1 if random.random() < 0.65 else 0
            
            batch.append((
                random.choice(order_ids),
                random.choice(creative_ids),
                random.choice(publisher_ids),
                user_id,
                random.choice(DEVICE_TYPES),
                random.choice(COUNTRIES),
                random.choice(CITIES),
                random.choice(PLATFORMS),
                random.choice(BROWSERS),
                random.choice(OS_TYPES),
                f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
                imp_time.strftime('%Y-%m-%d %H:%M:%S'),
                viewable,
                random.randint(2, 60) if viewable else None,
                click_through,
                conversion,
                revenue
            ))
            
            # Insert batch
            if len(batch) >= BATCH_SIZE:
                cursor.executemany(sql, batch)
                conn.commit()
                records_inserted += len(batch)
                batch = []
                
                # Progress update
                elapsed = time.time() - start_time
                rate = records_inserted / elapsed if elapsed > 0 else 0
                percentage = (records_inserted / total_records) * 100
                eta_seconds = (total_records - records_inserted) / rate if rate > 0 else 0
                eta_min = int(eta_seconds / 60)
                
                print(f"  [{percentage:5.1f}%] {records_inserted:,} / {total_records:,} records | "
                      f"{rate:.0f} rec/sec | ETA: {eta_min}m | Date: {current_date.date()}", end='\r')
        
        # Move to next day
        current_date += timedelta(days=1)
    
    # Insert remaining batch
    if batch:
        cursor.executemany(sql, batch)
        conn.commit()
        records_inserted += len(batch)
    
    cursor.close()
    
    print(f"\n  [100.0%] {records_inserted:,} records inserted!                                    ")
    
    return records_inserted


def regenerate_daily_metrics(conn):
    """Regenerate all daily metrics from impressions"""
    print(f"\n📈 Regenerating daily metrics...")
    
    cursor = conn.cursor()
    
    # Clear existing metrics
    cursor.execute("TRUNCATE TABLE daily_metrics")
    
    # Regenerate from impressions
    cursor.execute("""
        INSERT INTO daily_metrics (order_id, metric_date, impressions, clicks, conversions, revenue, viewable_impressions, ctr, cvr, cpm)
        SELECT 
            order_id,
            DATE(impression_time) as metric_date,
            COUNT(*) as impressions,
            SUM(click_through) as clicks,
            SUM(conversion) as conversions,
            SUM(revenue) as revenue,
            SUM(viewable) as viewable_impressions,
            COALESCE(ROUND(SUM(click_through)/NULLIF(COUNT(*),0)*100,4),0) as ctr,
            COALESCE(ROUND(SUM(conversion)/NULLIF(COUNT(*),0)*100,4),0) as cvr,
            COALESCE(ROUND(SUM(revenue)/NULLIF(COUNT(*),0)*1000,4),0) as cpm
        FROM impressions
        GROUP BY order_id, DATE(impression_time)
    """)
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM daily_metrics")
    count = cursor.fetchone()[0]
    cursor.close()
    
    print(f"✅ Generated {count:,} daily metric records")


def main():
    print("\n" + "="*60)
    print("Digital-SSP - HISTORICAL DATA GENERATOR")
    print("="*60 + "\n")
    
    start_time = time.time()
    
    conn = connect_db()
    order_ids, creative_ids, publisher_ids = get_existing_ids(conn)
    
    if not order_ids or not creative_ids or not publisher_ids:
        print("❌ Cannot proceed: Missing required base data")
        conn.close()
        exit(1)
    
    # Generate historical impressions (500 per day = ~900K total for 5 years)
    records_inserted = generate_historical_impressions(conn, order_ids, creative_ids, publisher_ids, records_per_day=500)
    
    # Regenerate metrics
    regenerate_daily_metrics(conn)
    
    # Final statistics
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM impressions")
    total_impressions = cursor.fetchone()[0]
    
    cursor.execute("SELECT MIN(impression_time), MAX(impression_time) FROM impressions")
    date_range = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    elapsed_seconds = time.time() - start_time
    elapsed_minutes = elapsed_seconds / 60
    
    print(f"\n✅ SUCCESS!")
    print(f"   • Total Impressions: {total_impressions:,}")
    print(f"   • Date Range:        {date_range[0]} to {date_range[1]}")
    print(f"   • Time Elapsed:      {elapsed_minutes:.1f} minutes")
    print(f"   • Rate:              {records_inserted / elapsed_seconds:.0f} records/sec")
    
    print("\n" + "="*60 + "\n")


if __name__ == '__main__':
    main()
