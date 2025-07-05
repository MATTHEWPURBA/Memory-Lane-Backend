# Memory Lane Database Setup Guide

## 🎯 Overview

Your Memory Lane backend database has been successfully configured with PostgreSQL and PostGIS for geospatial functionality.

## 📋 Database Configuration

- **Database Name**: `memory_lane_db`
- **Engine**: PostgreSQL 15 with PostGIS 3.3
- **Host**: localhost:5432
- **Username**: postgres
- **Database URL**: `postgresql://postgres:Robherto82@localhost:5432/memory_lane_db`

## 🗄️ Database Schema

### Tables Created

1. **users** - User management and authentication
   - UUID primary keys
   - Profile information, privacy settings
   - Account status and statistics

2. **memories** - Location-based memories
   - PostGIS geometry for locations
   - Content types (photo, video, audio, text)
   - Privacy levels and engagement metrics

3. **interactions** - User engagement
   - Likes, comments, shares, reports, views
   - Relationship tracking between users and memories

## 🚀 Quick Start

### Start the Application
```bash
./start_app.sh
```

Or manually:
```bash
source venv/bin/activate
export DATABASE_URL="postgresql://postgres:Robherto82@localhost:5432/memory_lane_db"
python run.py
```

### Access Points
- **API Base**: http://localhost:5000
- **Health Check**: http://localhost:5000/health
- **API Documentation**: http://localhost:5000/api/docs

## 🔧 Database Management Commands

### Initialize Database (if needed)
```bash
DATABASE_URL="postgresql://postgres:Robherto82@localhost:5432/memory_lane_db" FLASK_APP=run.py flask init-db
```

### Seed Sample Data
```bash
DATABASE_URL="postgresql://postgres:Robherto82@localhost:5432/memory_lane_db" FLASK_APP=run.py flask seed-db
```

### Reset Database
```bash
DATABASE_URL="postgresql://postgres:Robherto82@localhost:5432/memory_lane_db" FLASK_APP=run.py flask reset-db
```

## 👥 Sample Data

The database includes test users:
- **Username**: `demo_user` | **Email**: demo@memorylane.app | **Password**: DemoPassword123!
- **Username**: `explorer` | **Email**: explorer@memorylane.app | **Password**: ExploreWorld123!

## 🛠️ Development Tools

### Database Status Check
```bash
python check_db.py
```

### Direct Database Access
```bash
psql -h localhost -p 5432 -U postgres -d memory_lane_db
```

## 🔍 Key Features

- **Geospatial Queries**: Find memories within radius using PostGIS
- **UUID Support**: Consistent unique identifiers
- **Performance Optimized**: Indexes for common query patterns
- **Privacy Controls**: User and memory privacy settings
- **Rich Interactions**: Comprehensive user engagement tracking

## 📊 API Endpoints

- `POST /api/auth/login` - User authentication
- `GET /api/memories/nearby` - Find memories by location
- `POST /api/memories` - Create new memory
- `POST /api/interactions` - Like/comment on memories
- `GET /api/users/profile` - User profile management

## 🔧 Environment Variables

Set these in your `.env` file or environment:
```
DATABASE_URL=postgresql://postgres:Robherto82@localhost:5432/memory_lane_db
FLASK_ENV=development
SECRET_KEY=development-flask-secret-key
JWT_SECRET_KEY=development-jwt-secret-key
REDIS_URL=redis://localhost:6379/0
```

## ⚠️ Security Notes

- Change default passwords in production
- Use environment variables for sensitive data
- Enable SSL/TLS for production databases
- Implement proper backup strategies

## 🐛 Troubleshooting

### Connection Issues
- Ensure PostgreSQL is running
- Check credentials and database name
- Verify PostGIS extensions are installed

### Common Commands
```bash
# Check database status
python check_db.py

# Recreate database
DATABASE_URL="..." FLASK_APP=run.py flask reset-db

# View logs
tail -f instance/app.log
```

---

🎉 **Your Memory Lane database is ready for development!** 