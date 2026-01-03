#!/usr/bin/env python3
"""Create database schema for GAM360"""

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

def create_schema():
    """Create all tables"""
    try:
        conn = mysql.connector.connect(**CONFIG)
        cursor = conn.cursor()
        
        # Create database
        cursor.execute("CREATE DATABASE IF NOT EXISTS gam360")
        cursor.execute("USE gam360")
        print("✅ Database created/selected")
        
        # Read and execute schema
        with open('database_schema.sql', 'r') as f:
            schema = f.read()
        
        # Split by semicolon and execute each statement
        statements = schema.split(';')
        
        for i, stmt in enumerate(statements):
            stmt = stmt.strip()
            if stmt and not stmt.startswith('--'):
                try:
                    cursor.execute(stmt)
                    if i % 10 == 0:
                        print(f"  Executing statement {i+1}...", end='\r')
                except Error as err:
                    if "already exists" in str(err).lower():
                        pass  # Table already exists, continue
                    else:
                        print(f"\n⚠️  Warning: {err}")
        
        conn.commit()
        print("\n✅ All tables created successfully!")
        
        # Get table counts
        cursor.execute("""
            SELECT TABLE_NAME, TABLE_ROWS 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'gam360' 
            ORDER BY TABLE_ROWS DESC
        """)
        
        print("\n📊 Table Summary:")
        for table_name, row_count in cursor.fetchall():
            print(f"  • {table_name:30s} {row_count:>10,} rows")
        
        cursor.close()
        conn.close()
        
    except Error as err:
        print(f"❌ Error: {err}")
        exit(1)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("GAM360 - DATABASE SCHEMA SETUP")
    print("="*60 + "\n")
    create_schema()
    print("\n" + "="*60 + "\n")
