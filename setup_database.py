#!/usr/bin/env python3
"""
Database Setup and Management Script for Memory Lane

This script helps with database initialization, migration, and maintenance tasks.
"""

import os
import sys
import subprocess
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from app import create_app, db
from app.models import User, Memory, Interaction
from flask import current_app

def create_database():
    """Create the database if it doesn't exist."""
    print("🔄 Creating database...")
    
    # Database connection parameters
    db_params = {
        'host': 'localhost',
        'port': 5432,
        'user': 'memory_lane_user',
        'password': 'password'  # Update this based on your config
    }
    
    try:
        # Connect to PostgreSQL server (not specific database)
        conn = psycopg2.connect(**db_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname='memory_lane_db'")
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute("CREATE DATABASE memory_lane_db")
            print("✅ Database 'memory_lane_db' created successfully!")
        else:
            print("✅ Database 'memory_lane_db' already exists!")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"❌ Error creating database: {e}")
        return False
    
    return True

def run_init_sql():
    """Run the init-db.sql script."""
    print("🔄 Running database initialization script...")
    
    try:
        # Run the init-db.sql script
        cmd = [
            'psql',
            '-h', 'localhost',
            '-p', '5432',
            '-U', 'memory_lane_user',
            '-d', 'memory_lane_db',
            '-f', 'init-db.sql'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Database initialization script completed successfully!")
            return True
        else:
            print(f"❌ Error running init script: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ psql command not found. Please install PostgreSQL client tools.")
        return False
    except Exception as e:
        print(f"❌ Error running init script: {e}")
        return False

def create_tables():
    """Create all tables using SQLAlchemy."""
    print("🔄 Creating database tables...")
    
    try:
        with current_app.app_context():
            db.create_all()
            print("✅ All tables created successfully!")
            return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

def create_indexes():
    """Create additional indexes for performance."""
    print("🔄 Creating database indexes...")
    
    try:
        # Run the create_indexes.sql script
        cmd = [
            'psql',
            '-h', 'localhost',
            '-p', '5432',
            '-U', 'memory_lane_user',
            '-d', 'memory_lane_db',
            '-f', 'create_indexes.sql'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Database indexes created successfully!")
            return True
        else:
            print(f"❌ Error creating indexes: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating indexes: {e}")
        return False

def seed_sample_data():
    """Seed the database with sample data."""
    print("🔄 Seeding database with sample data...")
    
    try:
        with current_app.app_context():
            # Create sample users
            sample_users = [
                {
                    'username': 'demo_user',
                    'email': 'demo@memorylane.app',
                    'password': 'DemoPassword123!',
                    'display_name': 'Demo User',
                    'bio': 'This is a demo user for testing Memory Lane features.'
                },
                {
                    'username': 'explorer',
                    'email': 'explorer@memorylane.app',
                    'password': 'ExploreWorld123!',
                    'display_name': 'Memory Explorer',
                    'bio': 'Love discovering and sharing memories around the world!'
                }
            ]
            
            for user_data in sample_users:
                existing_user = User.query.filter_by(email=user_data['email']).first()
                if not existing_user:
                    user = User(**user_data)
                    db.session.add(user)
                    print(f"✅ Created user: {user_data['username']}")
            
            # Create sample memories
            users = User.query.all()
            if users:
                sample_memories = [
                    {
                        'creator_id': users[0].user_id,
                        'latitude': 37.7749,
                        'longitude': -122.4194,
                        'title': 'Golden Gate Bridge View',
                        'content_type': 'photo',
                        'description': 'Amazing sunset view from Crissy Field',
                        'location_name': 'San Francisco, CA'
                    },
                    {
                        'creator_id': users[0].user_id,
                        'latitude': 40.7128,
                        'longitude': -74.0060,
                        'title': 'Central Park Memories',
                        'content_type': 'text',
                        'content_text': 'Great day walking through Central Park with friends!',
                        'location_name': 'New York, NY'
                    }
                ]
                
                for memory_data in sample_memories:
                    memory = Memory(**memory_data)
                    db.session.add(memory)
                    print(f"✅ Created memory: {memory_data['title']}")
            
            db.session.commit()
            print("✅ Sample data seeded successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        db.session.rollback()
        return False

def full_setup():
    """Run the complete database setup process."""
    print("🚀 Starting Memory Lane Database Setup...\n")
    
    app = create_app('development')
    
    with app.app_context():
        steps = [
            ("Creating database", create_database),
            ("Running initialization script", run_init_sql),
            ("Creating tables", create_tables),
            ("Creating indexes", create_indexes),
            ("Seeding sample data", seed_sample_data)
        ]
        
        for step_name, step_func in steps:
            print(f"\n📋 {step_name}...")
            if not step_func():
                print(f"\n❌ Setup failed at step: {step_name}")
                return False
        
        print("\n🎉 Database setup completed successfully!")
        print("\n📊 Database Summary:")
        print(f"   • Users: {User.query.count()}")
        print(f"   • Memories: {Memory.query.count()}")
        print(f"   • Interactions: {Interaction.query.count()}")
        
        return True

def reset_database():
    """Reset the entire database."""
    print("⚠️  Resetting database (this will delete all data)...")
    
    app = create_app('development')
    with app.app_context():
        try:
            db.drop_all()
            print("✅ All tables dropped!")
            return full_setup()
        except Exception as e:
            print(f"❌ Error resetting database: {e}")
            return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "reset":
            reset_database()
        elif command == "seed":
            app = create_app('development')
            with app.app_context():
                seed_sample_data()
        else:
            print("Usage: python setup_database.py [reset|seed]")
    else:
        full_setup() 