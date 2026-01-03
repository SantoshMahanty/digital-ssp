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


def get_orders_list(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch orders with advertiser/campaign names and delivery metrics."""
    query = f'''
        SELECT
            o.order_id,
            o.order_name,
            o.status,
            o.start_date,
            o.end_date,
            o.lifetime_impression_goal,
            o.lifetime_budget,
            o.order_type,
            o.pacing_rate,
            a.advertiser_name,
            c.campaign_name,
            p.publisher_name,
            COALESCE(SUM(i.impression_id IS NOT NULL), 0) AS delivered,
            COALESCE(SUM(i.click_through), 0) AS clicks,
            COALESCE(SUM(i.revenue), 0) AS revenue
        FROM orders o
        JOIN campaigns c ON o.campaign_id = c.campaign_id
        JOIN advertisers a ON c.advertiser_id = a.advertiser_id
        JOIN publishers p ON o.publisher_id = p.publisher_id
        LEFT JOIN impressions i ON i.order_id = o.order_id
        GROUP BY o.order_id
        ORDER BY o.updated_at DESC
        LIMIT {limit}
    '''
    rows = execute_query(query)
    for row in rows:
        delivered = row.get('delivered', 0) or 0
        goal = row.get('lifetime_impression_goal', 0) or 0
        row['pct_complete'] = round((delivered / goal * 100), 1) if goal else 0
        revenue = float(row.get('revenue', 0) or 0)
        row['cpm'] = round((revenue / max(delivered, 1) * 1000), 2)
        clicks = row.get('clicks', 0) or 0
        row['ctr'] = round((clicks / max(delivered, 1) * 100), 2)
    return rows


def get_line_items_list(limit: int = 50) -> List[Dict[str, Any]]:
    """Reuse orders as line items list for the console."""
    return get_orders_list(limit)


def get_creatives_list(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch creatives with delivery metrics."""
    query = f'''
        SELECT
            c.creative_id,
            c.creative_name,
            c.creative_type,
            c.width,
            c.height,
            c.status,
            c.approval_status,
            a.advertiser_name,
            c.campaign_id,
            cmp.campaign_name,
            COALESCE(SUM(i.impression_id IS NOT NULL), 0) AS delivered,
            COALESCE(SUM(i.click_through), 0) AS clicks,
            COALESCE(SUM(i.revenue), 0) AS revenue
        FROM creatives c
        JOIN campaigns cmp ON c.campaign_id = cmp.campaign_id
        JOIN advertisers a ON cmp.advertiser_id = a.advertiser_id
        LEFT JOIN impressions i ON i.creative_id = c.creative_id
        GROUP BY c.creative_id
        ORDER BY c.updated_at DESC
        LIMIT {limit}
    '''
    rows = execute_query(query)
    for row in rows:
        delivered = row.get('delivered', 0) or 0
        revenue = float(row.get('revenue', 0) or 0)
        row['ctr'] = round(((row.get('clicks', 0) or 0) / max(delivered, 1) * 100), 2)
        row['cpm'] = round((revenue / max(delivered, 1) * 1000), 2)
        row['size'] = f"{row.get('width') or 0}x{row.get('height') or 0}" if row.get('width') and row.get('height') else "—"
    return rows
