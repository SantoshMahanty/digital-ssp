#!/usr/bin/env python
"""
Setup MySQL database for GAM-360 Simulator
"""
import mysql.connector

def setup_database():
    """Create database"""
    try:
        # Connect as root
        print("Connecting to MySQL as root...")
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='root',
            autocommit=True
        )
        cursor = conn.cursor()
        
        # Create database
        print("Creating database 'gam360'...")
        cursor.execute('CREATE DATABASE IF NOT EXISTS gam360')
        print("✓ Database created successfully")
        
        cursor.close()
        conn.close()
        
        print("\n✓ MySQL setup complete!")
        print("\nNext steps:")
        print("  1. Start the API server")
        print("  2. Visit: http://localhost:8001")
        print("  3. View docs: http://localhost:8001/docs")
        print("\nDatabase URL: mysql+mysqlconnector://root:root@localhost:3306/gam360")
        
    except mysql.connector.Error as err:
        print(f"✗ MySQL Error: {err}")
        print("\nTroubleshooting:")
        print("  1. Ensure MySQL is running")
        print("  2. Verify root password is 'root'")
        print("  3. Check MySQL is on localhost:3306")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    setup_database()
