#!/usr/bin/env python3
"""
GAM360 - Bulk Data Generator (500K Records)
Generates realistic test data for impressions, metrics, and events
"""

import mysql.connector
import random
import datetime
from datetime import timedelta
import time
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# MySQL Configuration
CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', 'root'),
    'database': os.getenv('MYSQL_DATABASE', 'gam360')
}

# Bulk insert batch size
BATCH_SIZE = 1000
TOTAL_RECORDS = 500000

# Data pools for random selection
COUNTRIES = ['US', 'UK', 'CA', 'AU', 'DE', 'FR', 'JP', 'IN', 'BR', 'MX', 'SG', 'HK', 'KR', 'NL', 'SE']
CITIES = ['New York', 'London', 'Toronto', 'Sydney', 'Berlin', 'Paris', 'Tokyo', 'Mumbai', 'São Paulo', 'Mexico City',
          'Singapore', 'Hong Kong', 'Seoul', 'Amsterdam', 'Stockholm', 'Los Angeles', 'San Francisco', 'Chicago']
BROWSERS = ['Chrome', 'Firefox', 'Safari', 'Edge', 'Opera', 'Chrome Mobile', 'Safari Mobile', 'Firefox Mobile']
OS_TYPES = ['Windows', 'macOS', 'iOS', 'Android', 'Linux', 'Chrome OS']
DEVICE_TYPES = ['DESKTOP', 'MOBILE', 'TABLET']
PLATFORMS = ['WEB', 'MOBILE_APP', 'CONNECTED_TV']

def connect_db():
    """Establish MySQL connection"""
    try:
        conn = mysql.connector.connect(**CONFIG)
        print(f"✅ Connected to MySQL database: {CONFIG['database']}")
        return conn
    except mysql.connector.Error as err:
        print(f"❌ Error connecting to MySQL: {err}")
        exit(1)

def get_existing_ids(conn):
    """Get existing IDs from database"""
    cursor = conn.cursor()
    
    try:
        # Get all valid order IDs
        cursor.execute("SELECT order_id FROM orders WHERE status = 'ACTIVE' LIMIT 100")
        order_ids = [row[0] for row in cursor.fetchall()]
        if not order_ids:
            print("⚠️ No ACTIVE orders found. Creating sample orders...")
            create_sample_orders(conn)
            cursor.execute("SELECT order_id FROM orders LIMIT 100")
            order_ids = [row[0] for row in cursor.fetchall()]
        
        # Get all valid creative IDs
        cursor.execute("SELECT creative_id FROM creatives LIMIT 100")
        creative_ids = [row[0] for row in cursor.fetchall()]
        if not creative_ids:
            print("⚠️ No creatives found. Creating sample creatives...")
            create_sample_creatives(conn)
            cursor.execute("SELECT creative_id FROM creatives LIMIT 100")
            creative_ids = [row[0] for row in cursor.fetchall()]
        
        # Get all publisher IDs
        cursor.execute("SELECT publisher_id FROM publishers LIMIT 100")
        publisher_ids = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        print(f"✅ Found {len(order_ids)} orders, {len(creative_ids)} creatives, {len(publisher_ids)} publishers")
        
        return order_ids, creative_ids, publisher_ids
        
    except mysql.connector.Error as err:
        print(f"❌ Error fetching IDs: {err}")
        cursor.close()
        return [], [], []

def create_sample_orders(conn):
    """Create sample orders if none exist"""
    cursor = conn.cursor()
    campaigns = list(range(1, 11))
    publishers = list(range(1, 11))
    
    orders = []
    for i in range(50):
        orders.append((
            f"Order_{i+1}",
            random.choice(campaigns),
            random.choice(publishers),
            random.choice(['GUARANTEED', 'PROGRAMMATIC_GUARANTEED', 'PREFERRED', 'OPEN_AUCTION']),
            (datetime.date.today() - timedelta(days=30)).isoformat(),
            (datetime.date.today() + timedelta(days=30)).isoformat(),
            random.randint(1000, 5000),
            random.randint(10000, 100000),
            random.randint(10000, 50000),
            random.randint(100000, 500000),
            100.00,
            'ACTIVE'
        ))
    
    cursor.executemany(
        """INSERT IGNORE INTO orders 
           (order_name, campaign_id, publisher_id, order_type, start_date, end_date, 
            daily_budget, lifetime_budget, daily_impression_goal, lifetime_impression_goal, pacing_rate, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        orders
    )
    conn.commit()
    print(f"✅ Created {len(orders)} sample orders")
    cursor.close()

def create_sample_creatives(conn):
    """Create sample creatives if none exist"""
    cursor = conn.cursor()
    campaigns = list(range(1, 11))
    
    creatives = []
    for i in range(50):
        creatives.append((
            f"Creative_{i+1}",
            random.choice(campaigns),
            random.choice(['BANNER', 'VIDEO', 'NATIVE', 'INSTREAM']),
            random.choice([300, 728, 160, 120]),
            random.choice([250, 90, 600, 250]),
            random.randint(50000, 500000),
            f'https://example.com/creative_{i+1}.html',
            'ACTIVE',
            'APPROVED'
        ))
    
    cursor.executemany(
        """INSERT IGNORE INTO creatives 
           (creative_name, campaign_id, creative_type, width, height, file_size, file_url, status, approval_status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        creatives
    )
    conn.commit()
    print(f"✅ Created {len(creatives)} sample creatives")
    cursor.close()

def generate_impression_data(order_ids, creative_ids, publisher_ids, batch_num, batch_size):
    """Generate batch of impression records"""
    impressions = []
    
    base_date = datetime.datetime.now() - timedelta(days=30)
    
    for i in range(batch_size):
        # Random timestamp within last 30 days
        random_hours = random.randint(0, 30 * 24)
        imp_time = base_date + timedelta(hours=random_hours)
        
        # Generate user ID
        user_id = f"user_{random.randint(100000, 1000000)}"
        
        # Random revenue (CPM-based: $2-20)
        revenue = round(random.uniform(2, 20) / 1000, 6)
        
        # Realistic CTR: 0.5-3%
        click_through = 1 if random.random() < 0.02 else 0
        
        # Realistic conversion: 0.1-1%
        conversion = 1 if click_through and random.random() < 0.1 else 0
        
        # Viewability: 50-80%
        viewable = 1 if random.random() < 0.65 else 0
        view_duration = random.randint(2, 60) if viewable else 0
        
        impression = (
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
            f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}",
            imp_time.strftime('%Y-%m-%d %H:%M:%S'),
            viewable,
            view_duration if viewable else None,
            click_through,
            conversion,
            revenue
        )
        impressions.append(impression)
    
    return impressions

def insert_impressions_batch(conn, impressions):
    """Insert batch of impressions"""
    cursor = conn.cursor()
    
    sql = """INSERT INTO impressions 
             (order_id, creative_id, publisher_id, user_id, device_type, country_code, city, 
              platform, browser_type, os_type, ip_address, impression_time, viewable, 
              view_duration, click_through, conversion, revenue)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    
    cursor.executemany(sql, impressions)
    conn.commit()
    cursor.close()

def generate_metrics_data(conn):
    """Generate daily metrics from impressions"""
    cursor = conn.cursor()
    
    # Get impression statistics per order per day
    cursor.execute("""
        SELECT 
            order_id,
            DATE(impression_time) as metric_date,
            COUNT(*) as impressions,
            SUM(click_through) as clicks,
            SUM(conversion) as conversions,
            SUM(revenue) as revenue,
            SUM(viewable) as viewable_impressions
        FROM impressions
        GROUP BY order_id, DATE(impression_time)
    """)
    
    metrics = []
    for row in cursor.fetchall():
        order_id, metric_date, impressions, clicks, conversions, revenue, viewable = row
        clicks = clicks or 0
        conversions = conversions or 0
        revenue = revenue or 0
        viewable = viewable or 0
        
        ctr = round(min((clicks / impressions * 100), 99.99), 4) if impressions > 0 else 0
        cvr = round(min((conversions / impressions * 100), 99.99), 4) if impressions > 0 else 0
        cpm = round(min((revenue / impressions * 1000), 9999.99), 4) if impressions > 0 else 0
        
        metrics.append((
            order_id,
            metric_date,
            impressions,
            clicks,
            conversions,
            revenue,
            viewable,
            ctr,
            cvr,
            cpm
        ))
    
    cursor.close()
    
    # Insert metrics
    if metrics:
        cursor = conn.cursor()
        sql = """INSERT INTO daily_metrics 
                 (order_id, metric_date, impressions, clicks, conversions, revenue, 
                  viewable_impressions, ctr, cvr, cpm)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                 ON DUPLICATE KEY UPDATE
                 impressions = VALUES(impressions),
                 clicks = VALUES(clicks),
                 conversions = VALUES(conversions),
                 revenue = VALUES(revenue),
                 viewable_impressions = VALUES(viewable_impressions),
                 ctr = VALUES(ctr),
                 cvr = VALUES(cvr),
                 cpm = VALUES(cpm)"""
        
        cursor.executemany(sql, metrics)
        conn.commit()
        cursor.close()
        print(f"✅ Generated {len(metrics)} daily metric records")

def main():
    """Main execution"""
    print("\n" + "="*60)
    print("GAM360 - BULK DATA GENERATOR (500K Records)")
    print("="*60 + "\n")
    
    start_time = time.time()
    
    # Connect to database
    conn = connect_db()
    
    # Get existing IDs
    order_ids, creative_ids, publisher_ids = get_existing_ids(conn)
    
    if not order_ids or not creative_ids or not publisher_ids:
        print("❌ Cannot proceed: Missing required base data")
        conn.close()
        exit(1)
    
    # Insert impressions in batches
    print(f"\n📊 Inserting {TOTAL_RECORDS:,} impression records...\n")
    
    batches = TOTAL_RECORDS // BATCH_SIZE
    remaining = TOTAL_RECORDS % BATCH_SIZE
    
    for batch_num in range(batches):
        impressions = generate_impression_data(order_ids, creative_ids, publisher_ids, batch_num, BATCH_SIZE)
        insert_impressions_batch(conn, impressions)
        
        elapsed = time.time() - start_time
        rate = (batch_num + 1) * BATCH_SIZE / elapsed
        percentage = ((batch_num + 1) * BATCH_SIZE / TOTAL_RECORDS) * 100
        eta_seconds = (TOTAL_RECORDS - (batch_num + 1) * BATCH_SIZE) / rate if rate > 0 else 0
        eta_min = int(eta_seconds / 60)
        
        print(f"  [{percentage:5.1f}%] Batch {batch_num + 1}/{batches} | "
              f"{(batch_num + 1) * BATCH_SIZE:,} records | "
              f"{rate:.0f} records/sec | "
              f"ETA: {eta_min}m", end='\r')
    
    # Insert remaining records
    if remaining > 0:
        impressions = generate_impression_data(order_ids, creative_ids, publisher_ids, batches, remaining)
        insert_impressions_batch(conn, impressions)
        print(f"  [100.0%] Batch {batches + 1}/{batches + 1} | {TOTAL_RECORDS:,} records inserted!", end='\n')
    else:
        print(f"  [100.0%] Batch {batches}/{batches} | {TOTAL_RECORDS:,} records inserted!", end='\n')
    
    # Generate metrics
    print(f"\n📈 Generating daily metrics...")
    generate_metrics_data(conn)
    
    # Get final counts
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM impressions")
    impression_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM daily_metrics")
    metrics_count = cursor.fetchone()[0]
    
    cursor.close()
    
    elapsed_seconds = time.time() - start_time
    elapsed_minutes = elapsed_seconds / 60
    
    print(f"\n✅ SUCCESS!")
    print(f"   • Impressions:    {impression_count:,}")
    print(f"   • Daily Metrics:  {metrics_count:,}")
    print(f"   • Time Elapsed:   {elapsed_minutes:.1f} minutes")
    print(f"   • Rate:           {impression_count / elapsed_seconds:.0f} records/sec")
    
    conn.close()
    print("\n" + "="*60 + "\n")

if __name__ == '__main__':
    main()
