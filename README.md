# Memory Lane Backend

A location-based memory sharing platform built with Flask, PostgreSQL with PostGIS, and real-time features using Socket.IO.

## 🏗️ Architecture

### Backend Stack
- **Flask** + Python 3.11+
- **Flask-RESTful**: RESTful API development
- **Flask-SQLAlchemy**: Database ORM
- **Flask-JWT-Extended**: JWT authentication
- **Flask-Limiter**: Rate limiting
- **Flask-CORS**: Cross-origin resource sharing
- **Flask-SocketIO**: Real-time features
- **Celery**: Background task processing
- **Redis**: Caching and session storage

### Database
- **PostgreSQL** with **PostGIS** extension
- Advanced geospatial queries and location-based features
- SQLAlchemy ORM with geospatial support
- Alembic for database migrations

## 🚀 Features

### Core Features
- **GPS-Based Time Capsules**: Create and discover memories tied to specific coordinates
- **Multi-Media Support**: Photos, voice notes, text messages, and short videos
- **Proximity Detection**: Location-based notifications when users are near hidden memories
- **Memory Discovery**: Browse memories within customizable radius (50m to 1km)
- **Content Creation**: Easy-to-use interface for leaving memories at current location
- **Social Interactions**: Like, comment, and share memories
- **User Profiles**: Personal memory collections and discovery statistics

### Real-time Features
- Location-based notifications
- Live memory discovery
- Real-time comments and interactions
- User presence in geographical areas

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL 12+ with PostGIS extension
- Redis server
- Git

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Memory-Lane-Backend
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup

#### Install PostgreSQL and PostGIS
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib postgis postgresql-12-postgis-3

# macOS (using Homebrew)
brew install postgresql postgis

# Windows: Download from https://www.postgresql.org/download/windows/
```

#### Create Database
```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE memory_lane_db;
CREATE USER memory_lane_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE memory_lane_db TO memory_lane_user;

-- Connect to the database and enable PostGIS
\c memory_lane_db
CREATE EXTENSION postgis;
```

### 5. Environment Configuration

Create a `.env` file in the project root:

```env
# Database Configuration
DATABASE_URL=postgresql://memory_lane_user:your_password@localhost:5432/memory_lane_db

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=86400

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-super-secret-flask-key-change-this-in-production

# File Upload Configuration
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216  # 16MB max file size

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Geospatial Configuration
DEFAULT_SEARCH_RADIUS_METERS=500
MAX_SEARCH_RADIUS_METERS=1000
MIN_SEARCH_RADIUS_METERS=50
```

### 6. Initialize Database
```bash
python run.py init-db
python run.py seed-db  # Optional: Add sample data
```

### 7. Start Redis Server
```bash
# Ubuntu/Debian
sudo systemctl start redis-server

# macOS
brew services start redis

# Windows: Start Redis from installation directory
```

### 8. Start Celery Worker (Optional)
```bash
celery -A celery_worker.celery worker --loglevel=info
```

### 9. Run the Application
```bash
python run.py
```

The API will be available at `http://localhost:5000`

## 📚 API Documentation

### Base URL
```
http://localhost:5000/api
```

### Authentication
All protected endpoints require a JWT token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

### API Endpoints

#### Authentication (`/api/auth`)
- `POST /register` - Register a new user
- `POST /login` - Login user
- `POST /refresh` - Refresh access token
- `POST /logout` - Logout user
- `GET /verify-token` - Verify token validity
- `PUT /change-password` - Change user password
- `POST /forgot-password` - Request password reset

#### Users (`/api/users`)
- `GET /profile` - Get current user profile
- `PUT /profile` - Update user profile
- `PUT /privacy-settings` - Update privacy settings
- `GET /<user_id>` - Get user profile
- `GET /search` - Search users
- `GET /stats` - Get user statistics
- `POST /deactivate` - Deactivate account

#### Memories (`/api/memories`)
- `POST /` - Create new memory
- `GET /<memory_id>` - Get specific memory
- `PUT /<memory_id>` - Update memory
- `DELETE /<memory_id>` - Delete memory
- `GET /user/<user_id>` - Get user's memories
- `GET /feed` - Get memory feed
- `GET /search` - Search memories

#### Interactions (`/api/interactions`)
- `POST /like/<memory_id>` - Like/unlike memory
- `POST /comment/<memory_id>` - Add comment
- `PUT /comment/<interaction_id>` - Update comment
- `DELETE /comment/<interaction_id>` - Delete comment
- `GET /comments/<memory_id>` - Get memory comments
- `POST /share/<memory_id>` - Share memory
- `POST /report/<memory_id>` - Report memory
- `GET /user/<user_id>/likes` - Get user's liked memories

#### Geospatial (`/api/geospatial`)
- `GET /discover` - Discover nearby memories
- `GET /heatmap` - Get memory density heatmap
- `GET /nearby-users` - Get nearby users
- `GET /areas/popular` - Get popular areas
- `GET /distance` - Calculate distance between coordinates

#### Uploads (`/api/uploads`)
- `POST /image` - Upload image
- `POST /audio` - Upload audio
- `POST /video` - Upload video
- `POST /profile-image` - Upload profile image
- `DELETE /delete/<file_path>` - Delete file
- `GET /info` - Get upload configuration

### Request/Response Examples

#### Create Memory
```bash
POST /api/memories
Content-Type: application/json
Authorization: Bearer <token>

{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "content_type": "photo",
  "title": "Beautiful sunset in NYC",
  "description": "Amazing sunset view from Central Park",
  "privacy_level": "public",
  "category_tags": ["sunset", "nyc", "nature"]
}
```

#### Discover Nearby Memories
```bash
GET /api/geospatial/discover?latitude=40.7128&longitude=-74.0060&radius=500
Authorization: Bearer <token>
```

#### Response Example
```json
{
  "memories": [
    {
      "memory_id": "uuid-here",
      "title": "Beautiful sunset in NYC",
      "content_type": "photo",
      "latitude": 40.7128,
      "longitude": -74.0060,
      "distance_meters": 150.5,
      "likes_count": 5,
      "comments_count": 2,
      "created_at": "2024-01-15T18:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 1,
    "has_next": false
  }
}
```

## 🔄 Real-time Features (Socket.IO)

### Connection
```javascript
const socket = io('http://localhost:5000', {
  auth: {
    token: 'your-jwt-token'
  }
});
```

### Events

#### Client to Server
- `join_location` - Join location-based room
- `leave_location` - Leave location room
- `memory_created` - Notify about new memory
- `memory_liked` - Notify about memory like
- `memory_commented` - Notify about new comment

#### Server to Client
- `connected` - Connection confirmation
- `new_memory_nearby` - New memory in area
- `memory_interaction` - Memory was liked/commented
- `nearby_users` - List of nearby users

## 🗄️ Database Schema

### Users Table
```sql
- user_id (UUID, Primary Key)
- username (String, Unique)
- email (String, Unique)
- password_hash (String)
- profile_photo_url (String)
- created_at (DateTime)
- privacy_settings (JSON)
- location_sharing_enabled (Boolean)
- is_active (Boolean)
```

### Memories Table
```sql
- memory_id (UUID, Primary Key)
- creator_id (UUID, Foreign Key)
- location (Geography POINT)
- latitude (Float)
- longitude (Float)
- content_type (Enum: photo, audio, video, text)
- content_url (String)
- title (String)
- description (Text)
- privacy_level (Enum: public, friends, private)
- expiration_date (DateTime)
- created_at (DateTime)
- likes_count (Integer)
- comments_count (Integer)
- category_tags (JSON)
- ai_generated_tags (JSON)
```

### Interactions Table
```sql
- interaction_id (UUID, Primary Key)
- user_id (UUID, Foreign Key)
- memory_id (UUID, Foreign Key)
- interaction_type (Enum: like, comment, report, share)
- content (Text)
- created_at (DateTime)
```

## 🧪 Testing

### Run Tests
```bash
python -m pytest tests/
```

### API Testing with cURL
```bash
# Register user
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"TestPass123!"}'

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier":"testuser","password":"TestPass123!"}'
```

## 🚀 Deployment

### Production Configuration
1. Set `FLASK_ENV=production`
2. Use strong secret keys
3. Configure PostgreSQL with connection pooling
4. Set up Redis cluster for high availability
5. Use Gunicorn or uWSGI for production server
6. Configure reverse proxy (Nginx)
7. Set up SSL/TLS certificates
8. Configure monitoring and logging

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up -d
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔧 Development Tools

### Useful Commands
```bash
# Reset database
python run.py reset-db

# Flask shell
flask shell

# Database migrations (if using Alembic)
flask db init
flask db migrate -m "Migration message"
flask db upgrade

# Start Celery worker
celery -A celery_worker.celery worker --loglevel=info

# Start Celery beat (for periodic tasks)
celery -A celery_worker.celery beat --loglevel=info
```

### Code Quality
```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

## 📞 Support

For support, email support@memorylane.app or create an issue in the repository.

---

**Memory Lane Backend** - Share memories, discover moments, connect with places. 🗺️✨
