#!/usr/bin/env python3
"""
GAM360 - Complete Database Schema Setup
Creates all tables and inserts base data
"""

import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', 'root'),
}

def execute_sql(cursor, sql):
    """Execute SQL statement"""
    try:
        cursor.execute(sql)
        return True
    except Error as e:
        if "already exists" in str(e).lower():
            return True
        print(f"⚠️ {e}")
        return False

def setup_database():
    """Setup complete database"""
    try:
        conn = mysql.connector.connect(**CONFIG)
        cursor = conn.cursor()
        
        print("\n📊 Creating Database & Tables...\n")
        
        # Create database
        cursor.execute("CREATE DATABASE IF NOT EXISTS gam360")
        cursor.execute("USE gam360")
        conn.commit()
        print("✅ Database 'gam360' created")
        
        # Publishers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS publishers (
                publisher_id INT PRIMARY KEY AUTO_INCREMENT,
                publisher_name VARCHAR(255) NOT NULL UNIQUE,
                domain VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_name (publisher_name),
                INDEX idx_domain (domain)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        print("✅ Table 'publishers' created")
        
        # Advertisers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS advertisers (
                advertiser_id INT PRIMARY KEY AUTO_INCREMENT,
                advertiser_name VARCHAR(255) NOT NULL UNIQUE,
                advertiser_url VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_name (advertiser_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        print("✅ Table 'advertisers' created")
        
        # Campaigns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                campaign_id INT PRIMARY KEY AUTO_INCREMENT,
                campaign_name VARCHAR(255) NOT NULL UNIQUE,
                advertiser_id INT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                budget DECIMAL(15, 2),
                status ENUM('ACTIVE', 'PAUSED', 'COMPLETED', 'DRAFT') DEFAULT 'ACTIVE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (advertiser_id) REFERENCES advertisers(advertiser_id),
                INDEX idx_advertiser (advertiser_id),
                INDEX idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        print("✅ Table 'campaigns' created")
        
        # Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INT PRIMARY KEY AUTO_INCREMENT,
                order_name VARCHAR(255) NOT NULL UNIQUE,
                campaign_id INT NOT NULL,
                publisher_id INT NOT NULL,
                order_type ENUM('GUARANTEED', 'PROGRAMMATIC_GUARANTEED', 'PREFERRED', 'OPEN_AUCTION') DEFAULT 'OPEN_AUCTION',
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                daily_budget DECIMAL(15, 2),
                lifetime_budget DECIMAL(15, 2),
                daily_impression_goal INT,
                lifetime_impression_goal INT,
                pacing_rate DECIMAL(5, 2) DEFAULT 100.00,
                status ENUM('ACTIVE', 'PAUSED', 'COMPLETED', 'DRAFT') DEFAULT 'ACTIVE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_campaign (campaign_id),
                INDEX idx_publisher (publisher_id),
                INDEX idx_status (status),
                FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id),
                FOREIGN KEY (publisher_id) REFERENCES publishers(publisher_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        print("✅ Table 'orders' created")
        
        # Creatives table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS creatives (
                creative_id INT PRIMARY KEY AUTO_INCREMENT,
                creative_name VARCHAR(255) NOT NULL UNIQUE,
                campaign_id INT NOT NULL,
                creative_type ENUM('BANNER', 'VIDEO', 'NATIVE', 'INSTREAM', 'OUTSTREAM') DEFAULT 'BANNER',
                width INT,
                height INT,
                file_size INT,
                file_url VARCHAR(500),
                status ENUM('ACTIVE', 'PAUSED', 'APPROVED', 'REJECTED', 'PENDING') DEFAULT 'ACTIVE',
                approval_status ENUM('APPROVED', 'REJECTED', 'PENDING_REVIEW') DEFAULT 'APPROVED',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_campaign (campaign_id),
                INDEX idx_status (status),
                FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        print("✅ Table 'creatives' created")
        
        # Impressions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS impressions (
                impression_id BIGINT PRIMARY KEY AUTO_INCREMENT,
                order_id INT NOT NULL,
                creative_id INT NOT NULL,
                publisher_id INT NOT NULL,
                user_id VARCHAR(128),
                device_type ENUM('DESKTOP', 'MOBILE', 'TABLET') DEFAULT 'DESKTOP',
                country_code CHAR(2),
                city VARCHAR(100),
                platform ENUM('WEB', 'MOBILE_APP', 'CONNECTED_TV') DEFAULT 'WEB',
                browser_type VARCHAR(50),
                os_type VARCHAR(50),
                ip_address VARCHAR(45),
                impression_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                viewable INT DEFAULT 0,
                view_duration INT,
                click_through INT DEFAULT 0,
                conversion INT DEFAULT 0,
                revenue DECIMAL(15, 6),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(order_id),
                FOREIGN KEY (creative_id) REFERENCES creatives(creative_id),
                FOREIGN KEY (publisher_id) REFERENCES publishers(publisher_id),
                INDEX idx_order (order_id),
                INDEX idx_creative (creative_id),
                INDEX idx_publisher (publisher_id),
                INDEX idx_impression_time (impression_time),
                INDEX idx_user (user_id),
                INDEX idx_device (device_type),
                INDEX idx_country (country_code)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        print("✅ Table 'impressions' created")
        
        # Daily metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_metrics (
                metric_id BIGINT PRIMARY KEY AUTO_INCREMENT,
                order_id INT,
                metric_date DATE NOT NULL,
                impressions INT DEFAULT 0,
                clicks INT DEFAULT 0,
                conversions INT DEFAULT 0,
                revenue DECIMAL(15, 2) DEFAULT 0,
                viewable_impressions INT DEFAULT 0,
                ctr DECIMAL(5, 4),
                cvr DECIMAL(5, 4),
                cpm DECIMAL(10, 4),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(order_id),
                INDEX idx_order (order_id),
                INDEX idx_date (metric_date),
                UNIQUE KEY unique_order_date (order_id, metric_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        print("✅ Table 'daily_metrics' created")
        
        conn.commit()
        
        # Insert base data
        print("\n📝 Inserting Base Data...\n")
        
        # Insert publishers
        publishers = [
            ('New York Times', 'nytimes.com'),
            ('CNN', 'cnn.com'),
            ('ESPN', 'espn.com'),
            ('TechCrunch', 'techcrunch.com'),
            ('Forbes', 'forbes.com'),
            ('Wired', 'wired.com'),
            ('Mashable', 'mashable.com'),
            ('Vimeo', 'vimeo.com'),
            ('Medium', 'medium.com'),
            ('LinkedIn', 'linkedin.com'),
        ]
        cursor.executemany(
            "INSERT IGNORE INTO publishers (publisher_name, domain) VALUES (%s, %s)",
            publishers
        )
        print(f"✅ Inserted {len(publishers)} publishers")
        
        # Insert advertisers
        advertisers = [
            ('Google', 'google.com'),
            ('Apple', 'apple.com'),
            ('Microsoft', 'microsoft.com'),
            ('Amazon', 'amazon.com'),
            ('Meta', 'meta.com'),
            ('Tesla', 'tesla.com'),
            ('Nike', 'nike.com'),
            ('Coca-Cola', 'coca-cola.com'),
            ('Samsung', 'samsung.com'),
            ('Intel', 'intel.com'),
        ]
        cursor.executemany(
            "INSERT IGNORE INTO advertisers (advertiser_name, advertiser_url) VALUES (%s, %s)",
            advertisers
        )
        print(f"✅ Inserted {len(advertisers)} advertisers")
        
        # Insert campaigns
        from datetime import date, timedelta
        campaigns = []
        for i in range(100):
            campaigns.append((
                f'Campaign_{i+1}',
                (i % 10) + 1,
                (date.today() - timedelta(days=30)).isoformat(),
                (date.today() + timedelta(days=30)).isoformat(),
                100000 + i * 1000,
                'ACTIVE'
            ))
        cursor.executemany(
            "INSERT IGNORE INTO campaigns (campaign_name, advertiser_id, start_date, end_date, budget, status) VALUES (%s, %s, %s, %s, %s, %s)",
            campaigns
        )
        print(f"✅ Inserted {len(campaigns)} campaigns")
        
        # Insert orders
        orders = []
        for i in range(100):
            orders.append((
                f'Order_{i+1}',
                (i % 100) + 1,
                (i % 10) + 1,
                ['GUARANTEED', 'PROGRAMMATIC_GUARANTEED', 'PREFERRED', 'OPEN_AUCTION'][i % 4],
                (date.today() - timedelta(days=30)).isoformat(),
                (date.today() + timedelta(days=30)).isoformat(),
                5000 + i * 100,
                100000 + i * 1000,
                50000 + i * 500,
                500000 + i * 5000,
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
        print(f"✅ Inserted {len(orders)} orders")
        
        # Insert creatives
        creatives = []
        creative_types = ['BANNER', 'VIDEO', 'NATIVE', 'INSTREAM']
        dimensions = [(300, 250), (728, 90), (160, 600), (120, 600), (970, 250)]
        
        for i in range(100):
            w, h = dimensions[i % len(dimensions)]
            creatives.append((
                f'Creative_{i+1}',
                (i % 100) + 1,
                creative_types[i % len(creative_types)],
                w,
                h,
                100000 + i * 10000,
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
        print(f"✅ Inserted {len(creatives)} creatives")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n" + "="*60)
        print("✅ Database setup complete!")
        print("="*60 + "\n")
        
        return True
        
    except Error as err:
        print(f"\n❌ Error: {err}")
        return False

if __name__ == '__main__':
    print("\n" + "="*60)
    print("GAM360 - DATABASE SETUP")
    print("="*60)
    setup_database()
