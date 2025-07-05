#!/usr/bin/env python3
"""
Simple Database Initialization Script for Memory Lane
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import config

# Create a simple Flask app just for database operations
app = Flask(__name__)
app.config.from_object(config['development'])

# Initialize only what we need for database operations
db = SQLAlchemy()
migrate = Migrate()

db.init_app(app)
migrate.init_app(app, db)

# Import models after db is initialized
with app.app_context():
    from app.models.user import User
    from app.models.memory import Memory
    from app.models.interaction import Interaction

def create_database():
    """Create all database tables."""
    print("🔄 Creating database tables...")
    
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("✅ Database tables created successfully!")
            
            # Verify tables were created
            tables = db.inspect(db.engine).get_table_names()
            print(f"📋 Created tables: {', '.join(tables)}")
            
            return True
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            return False

def seed_sample_data():
    """Add sample data to the database."""
    print("🔄 Adding sample data...")
    
    with app.app_context():
        try:
            # Check if data already exists
            if User.query.first():
                print("📋 Sample data already exists, skipping...")
                return True
            
            # Create sample users
            users_data = [
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
            
            created_users = []
            for user_data in users_data:
                user = User(**user_data)
                db.session.add(user)
                created_users.append(user)
                print(f"✅ Created user: {user_data['username']}")
            
            # Commit users first
            db.session.commit()
            
            # Create sample memories
            memories_data = [
                {
                    'creator_id': created_users[0].user_id,
                    'latitude': 37.7749,
                    'longitude': -122.4194,
                    'title': 'Golden Gate Bridge View',
                    'content_type': 'photo',
                    'description': 'Amazing sunset view from Crissy Field',
                    'location_name': 'San Francisco, CA'
                },
                {
                    'creator_id': created_users[0].user_id,
                    'latitude': 40.7128,
                    'longitude': -74.0060,
                    'title': 'Central Park Memories',
                    'content_type': 'text',
                    'content_text': 'Great day walking through Central Park with friends!',
                    'location_name': 'New York, NY'
                }
            ]
            
            for memory_data in memories_data:
                memory = Memory(**memory_data)
                db.session.add(memory)
                print(f"✅ Created memory: {memory_data['title']}")
            
            db.session.commit()
            print("✅ Sample data added successfully!")
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding sample data: {e}")
            db.session.rollback()
            return False

def show_database_info():
    """Show information about the database."""
    with app.app_context():
        try:
            print("\n📊 Database Information:")
            print(f"   • Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
            print(f"   • Users: {User.query.count()}")
            print(f"   • Memories: {Memory.query.count()}")
            print(f"   • Interactions: {Interaction.query.count()}")
            
            # Show sample users
            users = User.query.limit(5).all()
            if users:
                print("\n👥 Sample Users:")
                for user in users:
                    print(f"   • {user.username} ({user.email})")
            
            # Show sample memories
            memories = Memory.query.limit(5).all()
            if memories:
                print("\n💭 Sample Memories:")
                for memory in memories:
                    print(f"   • {memory.title} at {memory.location_name}")
            
        except Exception as e:
            print(f"❌ Error getting database info: {e}")

def main():
    """Main initialization function."""
    print("🚀 Initializing Memory Lane Database...\n")
    
    # Step 1: Create tables
    if not create_database():
        print("❌ Failed to create database tables")
        return False
    
    # Step 2: Add sample data
    if not seed_sample_data():
        print("❌ Failed to add sample data")
        return False
    
    # Step 3: Show info
    show_database_info()
    
    print("\n🎉 Database initialization completed successfully!")
    print("\n🔗 You can now start your application with:")
    print("   python run.py")
    
    return True

if __name__ == '__main__':
    main() 