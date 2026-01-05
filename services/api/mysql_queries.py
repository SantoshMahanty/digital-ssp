"""
MySQL database queries for Digital-SSP dashboard
"""

import mysql.connector
from mysql.connector import Error
from typing import Dict, List, Optional, Any
import os
import json
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
    """Execute query (SELECT, INSERT, UPDATE, DELETE) and return results for SELECT"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # For SELECT queries, fetch and return results
        if query.strip().upper().startswith('SELECT'):
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return results
        else:
            # For INSERT/UPDATE/DELETE, commit the transaction
            conn.commit()
            cursor.close()
            conn.close()
            return []
    except Error as e:
        print(f"Query error: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return []

def get_dashboard_data(period: str = 'today') -> Dict[str, Any]:
    """Get dashboard data for specified time period
    
    Args:
        period: 'today', 'last24h', 'last7d'
    """
    
    # Determine date filter based on period
    if period == 'last24h':
        date_condition = "metric_date >= DATE_SUB(CURDATE(), INTERVAL 1 DAY)"
    elif period == 'last7d':
        date_condition = "metric_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)"
    else:  # today
        date_condition = "metric_date = CURDATE()"
    
    # Get metrics from daily_metrics (pre-computed)
    today_query = f"""
        SELECT 
            COALESCE(SUM(impressions), 0) as total_impressions,
            COALESCE(SUM(clicks), 0) as total_clicks,
            COALESCE(SUM(revenue), 0) as total_revenue,
            COALESCE(SUM(viewable_impressions), 0) as viewable_impressions
        FROM daily_metrics
        WHERE {date_condition}
    """
    
    today_results = execute_query(today_query)
    today_metrics = today_results[0] if today_results else {}
    
    impressions = today_metrics.get('total_impressions', 0) or 0
    clicks = today_metrics.get('total_clicks', 0) or 0
    revenue = float(today_metrics.get('total_revenue', 0) or 0)
    viewable = today_metrics.get('viewable_impressions', 0) or 0
    
    # Last 24 hours from impressions (with date filter)
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
    
    # Line item performance (use daily_metrics for efficiency)
    line_items_query = f"""
        SELECT 
            o.order_id,
            o.order_name,
            COALESCE(SUM(dm.impressions), 0) as delivered,
            o.lifetime_impression_goal as booked,
            o.status
        FROM orders o
        LEFT JOIN daily_metrics dm ON o.order_id = dm.order_id AND {date_condition}
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
    
    # Recent activity (last 24 hours only)
    activity_query = """
        SELECT 
            o.order_name,
            c.creative_name,
            i.impression_time
        FROM impressions i
        JOIN orders o ON i.order_id = o.order_id
        JOIN creatives c ON i.creative_id = c.creative_id
        WHERE i.impression_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        ORDER BY i.impression_time DESC
        LIMIT 10
    """
    activity = execute_query(activity_query)
    
    # Convert to float for calculations
    impressions = float(impressions) if impressions else 0
    clicks = float(clicks) if clicks else 0
    revenue = float(revenue) if revenue else 0
    viewable = float(viewable) if viewable else 0
    
    return {
        'impressions': int(impressions),
        'clicks': int(clicks),
        'revenue': revenue,
        'viewable': int(viewable),
        'ctr': round((clicks / impressions * 100), 2) if impressions > 0 else 0,
        'cpm': round((revenue / impressions * 1000), 2) if impressions > 0 else 0,
        'fill_rate': round((impressions / (impressions * 1.15)) * 100, 1) if impressions > 0 else 0,
        'hourly': hourly_data,
        'line_items': line_items,
        'activity': activity
    }


def ensure_indexes():
    """Create indexes for performance optimization"""
    conn = get_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_impressions_time ON impressions(impression_time)",
        "CREATE INDEX IF NOT EXISTS idx_impressions_order_time ON impressions(order_id, impression_time)",
        "CREATE INDEX IF NOT EXISTS idx_impressions_creative_time ON impressions(creative_id, impression_time)",
        "CREATE INDEX IF NOT EXISTS idx_daily_metrics_date ON daily_metrics(metric_date)",
        "CREATE INDEX IF NOT EXISTS idx_daily_metrics_order_date ON daily_metrics(order_id, metric_date)",
    ]
    
    for idx_sql in indexes:
        try:
            cursor.execute(idx_sql)
        except Exception:
            pass  # Index might already exist
    
    conn.commit()
    cursor.close()
    conn.close()


# Create indexes on module load
ensure_indexes()


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
        ORDER BY o.order_id DESC
        LIMIT {limit}
    '''
    rows = execute_query(query)
    for row in rows:
        delivered = int(row.get('delivered', 0) or 0)
        goal = int(row.get('lifetime_impression_goal', 0) or 0)
        row['pct_complete'] = round((delivered / goal * 100), 1) if goal else 0
        revenue = float(row.get('revenue', 0) or 0)
        row['cpm'] = round((revenue / max(delivered, 1) * 1000), 2)
        clicks = int(row.get('clicks', 0) or 0)
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
        ORDER BY c.creative_id DESC
        LIMIT {limit}
    '''
    rows = execute_query(query)
    for row in rows:
        delivered = int(row.get('delivered', 0) or 0)
        revenue = float(row.get('revenue', 0) or 0)
        clicks = int(row.get('clicks', 0) or 0)
        row['ctr'] = round((clicks / max(delivered, 1) * 100), 2)
        row['cpm'] = round((revenue / max(delivered, 1) * 1000), 2)
        row['size'] = f"{row.get('width') or 0}x{row.get('height') or 0}" if row.get('width') and row.get('height') else "—"
    return rows


def get_line_items_for_engine(limit: int = 200):
    """Load active line items from MySQL and hydrate delivery-engine objects."""
    try:
        from services.delivery_engine.types import LineItem, Creative, Size
    except Exception:
        return []

    query = f'''
        SELECT 
            o.order_id,
            o.order_name,
            o.priority,
            o.cpm,
            o.pacing_strategy,
            o.targeting,
            o.start_date,
            o.end_date,
            o.lifetime_impression_goal,
            o.status,
            o.campaign_id,
            o.publisher_id,
            COALESCE(SUM(i.impression_id IS NOT NULL), 0) AS delivered
        FROM orders o
        LEFT JOIN impressions i ON i.order_id = o.order_id
        WHERE o.status = 'ACTIVE'
        GROUP BY o.order_id
        ORDER BY o.priority DESC, o.created_at DESC
        LIMIT {limit}
    '''
    rows = execute_query(query)
    if not rows:
        return []

    # Fetch creatives by campaign for hydration
    campaign_ids = [r['campaign_id'] for r in rows if r.get('campaign_id')]
    creative_map: Dict[int, List[Dict[str, Any]]] = {}
    if campaign_ids:
        ids_csv = ",".join(str(cid) for cid in sorted(set(campaign_ids)))
        creative_rows = execute_query(
            f"""
            SELECT creative_id, campaign_id, creative_type, width, height, creative_name
            FROM creatives
            WHERE campaign_id IN ({ids_csv}) AND status = 'ACTIVE'
            """
        )
        for cr in creative_rows:
            creative_map.setdefault(cr['campaign_id'], []).append(cr)

    hydrated = []
    for r in rows:
        targeting_raw = r.get('targeting')
        try:
            targeting = json.loads(targeting_raw) if targeting_raw else {}
        except Exception:
            targeting = {}

        start_ts = None
        end_ts = None
        if r.get('start_date'):
            date_obj = r['start_date']
            # Convert date to datetime if needed
            if hasattr(date_obj, 'timestamp'):
                start_ts = date_obj.timestamp()
            else:
                from datetime import datetime
                start_ts = datetime.combine(date_obj, datetime.min.time()).timestamp()
        if r.get('end_date'):
            date_obj = r['end_date']
            # Convert date to datetime if needed
            if hasattr(date_obj, 'timestamp'):
                end_ts = date_obj.timestamp()
            else:
                from datetime import datetime
                end_ts = datetime.combine(date_obj, datetime.min.time()).timestamp()

        creatives_dom = []
        for cr in creative_map.get(r.get('campaign_id'), []):
            creatives_dom.append(
                Creative(
                    id=str(cr['creative_id']),
                    size=Size(w=cr.get('width') or 0, h=cr.get('height') or 0),
                    type=cr.get('creative_type') or 'display',
                    adm=None,
                )
            )

        hydrated.append(
            LineItem(
                id=str(r['order_id']),
                priority=int(r.get('priority') or 8),
                cpm=float(r.get('cpm') or 0),
                targeting=targeting or {},
                pacing=r.get('pacing_strategy') or 'even',
                booked_imps=r.get('lifetime_impression_goal'),
                delivered_imps=int(r.get('delivered') or 0),
                start=start_ts,
                end=end_ts,
                creatives=creatives_dom,
            )
        )

    return hydrated
