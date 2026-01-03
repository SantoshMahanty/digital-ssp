"""
Script to add recent impression data (last 7 days) to the database.
This ensures the dashboard always has recent data to display.
"""

import random
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import Error

def get_connection():
    """Create database connection"""
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="gam360"
        )
        return conn
    except Error as e:
        print(f"Database connection error: {e}")
        return None

def add_recent_impressions(num_records=1000):
    """
    Add recent impression records spanning the last 7 days.
    
    Args:
        num_records: Number of impression records to add (default 1000)
    """
    conn = get_connection()
    if not conn:
        print("Failed to connect to database")
        return
    
    cursor = conn.cursor()
    
    # Get existing order IDs, creative IDs, and publisher IDs
    cursor.execute("SELECT order_id FROM orders LIMIT 20")
    order_ids = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT creative_id FROM creatives LIMIT 20")
    creative_ids = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT publisher_id FROM publishers LIMIT 10")
    publisher_ids = [row[0] for row in cursor.fetchall()]
    
    if not order_ids or not creative_ids or not publisher_ids:
        print("No orders, creatives, or publishers found in database")
        cursor.close()
        conn.close()
        return
    
    # Generate timestamps for last 7 days
    now = datetime.now()
    start_date = now - timedelta(days=6)  # 7 days including today
    
    records = []
    for i in range(num_records):
        # Random timestamp within last 7 days
        random_seconds = random.randint(0, 7 * 24 * 60 * 60)
        impression_time = start_date + timedelta(seconds=random_seconds)
        
        # Random selection of IDs
        order_id = random.choice(order_ids)
        creative_id = random.choice(creative_ids)
        publisher_id = random.choice(publisher_ids)
        
        # Generate realistic metrics
        click_through = 1 if random.random() < 0.02 else 0  # 2% CTR
        viewable = 1 if random.random() < 0.65 else 0  # 65% viewability
        conversion = 1 if click_through and random.random() < 0.05 else 0  # 5% conversion if clicked
        revenue = round(random.uniform(2.0, 20.0) / 1000, 6)  # CPM between $2-$20, per impression
        
        # Random device and geo
        device_type = random.choice(['DESKTOP', 'MOBILE', 'TABLET'])
        country_code = random.choice(['US', 'CA', 'GB', 'AU', 'DE'])
        
        records.append((
            impression_time,
            order_id,
            creative_id,
            publisher_id,
            device_type,
            country_code,
            viewable,
            click_through,
            conversion,
            revenue
        ))
    
    # Batch insert
    insert_query = """
        INSERT INTO impressions 
        (impression_time, order_id, creative_id, publisher_id, device_type, 
         country_code, viewable, click_through, conversion, revenue)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        cursor.executemany(insert_query, records)
        conn.commit()
        print(f"✅ Successfully added {num_records} recent impression records (last 7 days)")
        
        # Also regenerate daily_metrics for the last 7 days
        regenerate_daily_metrics(cursor, conn, start_date)
        
    except Error as e:
        print(f"Error inserting records: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def regenerate_daily_metrics(cursor, conn, start_date):
    """Regenerate daily_metrics table for recent data"""
    try:
        # Delete old metrics for last 7 days
        cursor.execute("""
            DELETE FROM daily_metrics 
            WHERE metric_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
        """)
        
        # Regenerate metrics from impressions
        cursor.execute("""
            INSERT INTO daily_metrics 
            (metric_date, order_id, impressions, clicks, viewable_impressions, conversions, revenue)
            SELECT 
                DATE(impression_time) as metric_date,
                order_id,
                COUNT(*) as impressions,
                SUM(click_through) as clicks,
                SUM(viewable) as viewable_impressions,
                SUM(conversion) as conversions,
                SUM(revenue) as revenue
            FROM impressions
            WHERE impression_time >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
            GROUP BY DATE(impression_time), order_id
        """)
        
        conn.commit()
        print(f"✅ Daily metrics regenerated for last 7 days")
        
    except Error as e:
        print(f"Error regenerating daily metrics: {e}")
        conn.rollback()

if __name__ == "__main__":
    add_recent_impressions(1000)
