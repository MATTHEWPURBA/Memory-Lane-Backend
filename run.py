#!/usr/bin/env python3
"""
Memory Lane Backend - Main Application Entry Point

This file serves as the entry point for the Memory Lane Flask application.
It creates the app instance and runs the development server.
"""

import os
from app import create_app, socketio, db
from app.models import User, Memory, Interaction

# Determine configuration
config_name = os.environ.get('FLASK_ENV', 'development')

# Create Flask application
app = create_app(config_name)

@app.shell_context_processor
def make_shell_context():
    """Make database models available in Flask shell."""
    return {
        'db': db,
        'User': User,
        'Memory': Memory,
        'Interaction': Interaction
    }

@app.cli.command()
def init_db():
    """Initialize the database."""
    print("Creating database tables...")
    
    # Import all models to ensure they're registered
    from app.models.user import User
    from app.models.memory import Memory
    from app.models.interaction import Interaction
    
    db.create_all()
    print("Database tables created successfully!")
    
    # Show created tables
    inspector = db.inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"Created tables: {', '.join(tables)}")

@app.cli.command()
def seed_db():
    """Seed the database with sample data."""
    print("Seeding database with sample data...")
    
    # Create sample users
    sample_users = [
        {
            'username': 'demo_user',
            'email': 'demo@memorylane.app',
            'password': 'DemoPassword123!',
            'full_name': 'Demo User',
            'bio': 'This is a demo user for testing Memory Lane features.'
        },
        {
            'username': 'explorer',
            'email': 'explorer@memorylane.app',
            'password': 'ExploreWorld123!',
            'full_name': 'Memory Explorer',
            'bio': 'Love discovering and sharing memories around the world!'
        }
    ]
    
    for user_data in sample_users:
        existing_user = User.query.filter_by(email=user_data['email']).first()
        if not existing_user:
            user = User(**user_data)
            db.session.add(user)
            print(f"Created user: {user_data['username']}")
    
    db.session.commit()
    print("Database seeded successfully!")

@app.cli.command()
def reset_db():
    """Reset the database (drop and recreate all tables)."""
    print("Resetting database...")
    db.drop_all()
    db.create_all()
    print("Database reset completed!")

if __name__ == '__main__':
    # Run the application with Socket.IO support
    socketio.run(
        app,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=app.config.get('DEBUG', False),
        use_reloader=True,
        log_output=True,
        allow_unsafe_werkzeug=True
    ) 