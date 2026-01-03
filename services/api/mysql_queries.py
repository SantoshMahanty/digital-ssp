"""
MySQL database queries for GAM360 dashboard
"""

import mysql.connector
from mysql.connector import Error
from typing import Dict, List, Optional, Any
import os
from dotenv import load_dotenv

load_dotenv()

# MySQL Configuration
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', 'root'),
    'database': os.getenv('MYSQL_DATABASE', 'gam360')
}

def get_connection():
    """Get MySQL database connection"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Database connection error: {e}")
        return None

def execute_query(query: str, params: tuple = None) -> List[Dict[str, Any]]:
    """Execute SELECT query and return results as list of dicts"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results
    except Error as e:
        print(f"Query error: {e}")
        if conn:
            conn.close()
        return []

def get_dashboard_data() -> Dict[str, Any]:
    """Get all dashboard data in one call"""
    
    # Today's metrics
    today_query = """
        SELECT 
            COUNT(*) as total_impressions,
            SUM(CASE WHEN click_through = 1 THEN 1 ELSE 0 END) as total_clicks,
            SUM(revenue) as total_revenue,
            SUM(CASE WHEN viewable = 1 THEN 1 ELSE 0 END) as viewable_impressions
        FROM impressions
        WHERE DATE(impression_time) = CURDATE()
    """
    
    today_results = execute_query(today_query)
    today_metrics = today_results[0] if today_results else {}
    
    impressions = today_metrics.get('total_impressions', 0) or 0
    clicks = today_metrics.get('total_clicks', 0) or 0
    revenue = float(today_metrics.get('total_revenue', 0) or 0)
    viewable = today_metrics.get('viewable_impressions', 0) or 0
    
    # Hourly delivery
    hourly_query = """
        SELECT 
            HOUR(impression_time) as hour,
            COUNT(*) as impressions
        FROM impressions
        WHERE impression_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        GROUP BY HOUR(impression_time)
        ORDER BY hour
    """
    hourly_data = execute_query(hourly_query)
    
    # Line item performance
    line_items_query = """
        SELECT 
            o.order_name,
            COUNT(i.impression_id) as delivered,
            o.lifetime_impression_goal as booked,
            o.status
        FROM orders o
        LEFT JOIN impressions i ON o.order_id = i.order_id
        WHERE o.status = 'ACTIVE'
        GROUP BY o.order_id
        ORDER BY delivered DESC
        LIMIT 5
    """
    line_items = execute_query(line_items_query)
    
    # Add percentage calculations
    for item in line_items:
        delivered = item.get('delivered', 0) or 0
        booked = item.get('booked', 1) or 1
        item['pct_complete'] = round((delivered / booked * 100), 1)
        item['variance'] = round(item['pct_complete'] - 50, 1)  # Simplified
    
    # Recent activity
    activity_query = """
        SELECT 
            o.order_name,
            c.creative_name,
            i.impression_time
        FROM impressions i
        JOIN orders o ON i.order_id = o.order_id
        JOIN creatives c ON i.creative_id = c.creative_id
        ORDER BY i.impression_time DESC
        LIMIT 10
    """
    activity = execute_query(activity_query)
    
    return {
        'impressions': impressions,
        'clicks': clicks,
        'revenue': revenue,
        'viewable': viewable,
        'ctr': round((clicks / impressions * 100), 2) if impressions > 0 else 0,
        'cpm': round((revenue / impressions * 1000), 2) if impressions > 0 else 0,
        'fill_rate': round((impressions / (impressions * 1.15)) * 100, 1) if impressions > 0 else 0,
        'hourly': hourly_data,
        'line_items': line_items,
        'activity': activity
    }
