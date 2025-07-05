#!/usr/bin/env python3
"""
Database Status Checker for Memory Lane
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os

def check_databases():
    """Check available databases and their tables."""
    print("🔍 Checking available databases...\n")
    
    # Try different connection possibilities
    connection_configs = [
        {
            'host': 'localhost',
            'port': 5432,
            'user': 'memory_lane_user', 
            'password': 'memory_lane_password',
            'dbname': 'postgres'  # Connect to default postgres db
        },
        {
            'host': 'localhost',
            'port': 5432,
            'user': 'postgres',
            'password': 'Robherto82',
            'dbname': 'postgres'
        }
    ]
    
    for i, config in enumerate(connection_configs, 1):
        print(f"🔗 Trying connection method {i}...")
        try:
            conn = psycopg2.connect(**config)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # List all databases
            cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
            databases = cursor.fetchall()
            
            print(f"✅ Connected successfully!")
            print(f"📋 Available databases: {[db[0] for db in databases]}")
            
            # Check if memory_lane_db exists
            memory_lane_exists = any('memory_lane' in db[0].lower() for db in databases)
            
            if not memory_lane_exists:
                print("\n🔨 Creating memory_lane_db database...")
                cursor.execute("CREATE DATABASE memory_lane_db;")
                print("✅ Memory Lane database created!")
            else:
                print("✅ Memory Lane database already exists!")
            
            cursor.close()
            conn.close()
            return config  # Return successful config
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            continue
    
    print("❌ All connection attempts failed!")
    return None

def check_memory_lane_tables(db_config):
    """Check tables in the memory_lane_db database."""
    print("\n🔍 Checking Memory Lane database tables...")
    
    try:
        # Connect to memory_lane_db specifically
        config = db_config.copy()
        config['dbname'] = 'memory_lane_db'
        
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        
        # Check for PostGIS extension
        cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'postgis';")
        postgis_exists = cursor.fetchone()
        
        if not postgis_exists:
            print("🔧 Installing PostGIS extension...")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS 'uuid-ossp';")
            print("✅ PostGIS extension installed!")
        else:
            print("✅ PostGIS extension already exists!")
        
        # List tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
        """)
        tables = cursor.fetchall()
        
        print(f"📋 Current tables: {[table[0] for table in tables]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking Memory Lane tables: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Memory Lane Database Status Check\n")
    
    # Step 1: Check and create database
    db_config = check_databases()
    
    if db_config:
        # Step 2: Check Memory Lane specific setup
        check_memory_lane_tables(db_config)
        
        print(f"\n✅ Database configuration to use:")
        print(f"   Host: {db_config['host']}")
        print(f"   Port: {db_config['port']}")
        print(f"   User: {db_config['user']}")
        print(f"   Database: memory_lane_db")
        
        database_url = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/memory_lane_db"
        print(f"\n🔗 Use this DATABASE_URL:")
        print(f"   {database_url}")
    else:
        print("\n❌ Could not establish database connection!")
        print("\n💡 Make sure PostgreSQL is running and check your credentials.") 