# Memory Lane Backend API Documentation

**Version:** 1.0.0  
**Base URL:** `http://localhost:5000/api`  
**Authentication:** JWT Bearer Tokens  
**Content-Type:** `application/json`

---

## Table of Contents

- [🔐 Authentication APIs](#-authentication-apis)
- [👥 Users APIs](#-users-apis)
- [💭 Memories APIs](#-memories-apis)
- [💬 Interactions APIs](#-interactions-apis)
- [🗺️ Geospatial APIs](#️-geospatial-apis)
- [📤 Uploads APIs](#-uploads-apis)
- [🏥 System APIs](#-system-apis)
- [📊 Rate Limits](#-rate-limits)
- [🔑 Authentication Types](#-authentication-types)
- [📝 Common Query Parameters](#-common-query-parameters)
- [📚 Additional Information](#-additional-information)

---

## 🔐 Authentication APIs

**Base Path:** `/api/auth`

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/register` | Register a new user | ❌ |
| POST | `/login` | Login user and return JWT tokens | ❌ |
| POST | `/refresh` | Refresh access token using refresh token | 🔄 Refresh Token |
| POST | `/logout` | Logout user (blacklist current token) | ✅ |
| POST | `/logout-all` | Logout user from all devices | ✅ |
| GET | `/verify-token` | Verify if current token is valid | ✅ |
| PUT | `/change-password` | Change user password | ✅ |
| POST | `/forgot-password` | Request password reset | ❌ |
| POST | `/reset-password` | Reset password using reset token | ❌ |
| POST | `/check-username` | Check if username is available | ❌ |
| POST | `/check-email` | Check if email is available | ❌ |

### Example Request - Register User

```bash
POST /api/auth/register
Content-Type: application/json

{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "display_name": "John Doe"
}
```

### Example Response - Login Success

```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": {
      "user_id": "uuid-here",
      "username": "johndoe",
      "email": "john@example.com",
      "display_name": "John Doe"
    },
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }
}
```

---

## 👥 Users APIs

**Base Path:** `/api/users`

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/profile` | Get current user's profile | ✅ |
| PUT | `/profile` | Update current user's profile | ✅ |
| PUT | `/privacy-settings` | Update user's privacy settings | ✅ |
| GET | `/{user_id}` | Get another user's public profile | 🔶 Optional |
| GET | `/search` | Search for users by username/display name | 🔶 Optional |
| GET | `/stats` | Get current user's statistics | ✅ |
| POST | `/deactivate` | Deactivate user account | ✅ |
| POST | `/reactivate` | Reactivate user account | ❌ |
| GET | `/activity` | Get user's recent activity summary | ✅ |

### Example Request - Update Profile

```bash
PUT /api/users/profile
Authorization: Bearer your-access-token
Content-Type: application/json

{
  "display_name": "John Smith",
  "bio": "Love exploring new places and capturing memories!",
  "default_memory_privacy": "public"
}
```

### Example Request - Update Privacy Settings

```bash
PUT /api/users/privacy-settings
Authorization: Bearer your-access-token
Content-Type: application/json

{
  "profile_visibility": "public",
  "location_sharing": true,
  "memory_discovery": true,
  "show_activity_status": false,
  "allow_friend_requests": true
}
```

---

## 💭 Memories APIs

**Base Path:** `/api/memories`

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/` | Create a new memory | ✅ |
| GET | `/{memory_id}` | Get a specific memory by ID | 🔶 Optional |
| PUT | `/{memory_id}` | Update a memory (creator only) | ✅ |
| DELETE | `/{memory_id}` | Delete a memory (creator only) | ✅ |
| GET | `/user/{user_id}` | Get memories created by specific user | 🔶 Optional |
| GET | `/feed` | Get personalized feed of recent memories | 🔶 Optional |
| GET | `/search` | Search memories by text query | 🔶 Optional |
| GET | `/nearby` | Get memories near a location | 🔶 Optional |
| POST | `/discover` | Discover memories at current location | ✅ |
| POST | `/{memory_id}/add-tags` | Add tags to a memory | ✅ |

### Example Request - Create Memory

```bash
POST /api/memories
Authorization: Bearer your-access-token
Content-Type: application/json

{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "content_type": "photo",
  "title": "Beautiful sunset in Central Park",
  "description": "Amazing golden hour view from Bethesda Fountain",
  "privacy_level": "public",
  "content_url": "/uploads/images/sunset_photo.jpg",
  "category_tags": ["sunset", "nature", "nyc"],
  "location_name": "Central Park, New York"
}
```

### Example Request - Search Memories

```bash
GET /api/memories/search?q=sunset&time_filter=week&sort_by=popular
Authorization: Bearer your-access-token
```

### Example Request - Get Nearby Memories

```bash
GET /api/memories/nearby?latitude=40.7128&longitude=-74.0060&radius=500
Authorization: Bearer your-access-token
```

---

## 💬 Interactions APIs

**Base Path:** `/api/interactions`

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/like` | Like a memory | ✅ |
| POST | `/unlike` | Unlike a memory | ✅ |
| POST | `/comment` | Comment on a memory | ✅ |
| PUT | `/comment/{interaction_id}` | Update a comment | ✅ |
| DELETE | `/comment/{interaction_id}` | Delete a comment | ✅ |
| POST | `/share` | Share a memory | ✅ |
| POST | `/report` | Report a memory | ✅ |
| GET | `/memory/{memory_id}/comments` | Get comments for a memory | 🔶 Optional |
| GET | `/memory/{memory_id}/likes` | Get likes for a memory | 🔶 Optional |
| GET | `/user/{user_id}/interactions` | Get interactions by a user | ✅ |
| GET | `/memory/{memory_id}/check-like` | Check if user has liked memory | ✅ |

### Example Request - Like Memory

```bash
POST /api/interactions/like
Authorization: Bearer your-access-token
Content-Type: application/json

{
  "memory_id": "uuid-of-memory"
}
```

### Example Request - Add Comment

```bash
POST /api/interactions/comment
Authorization: Bearer your-access-token
Content-Type: application/json

{
  "memory_id": "uuid-of-memory",
  "content": "What a beautiful sunset! Great capture!"
}
```

### Example Request - Report Memory

```bash
POST /api/interactions/report
Authorization: Bearer your-access-token
Content-Type: application/json

{
  "memory_id": "uuid-of-memory",
  "reason": "inappropriate_content",
  "description": "Contains offensive language"
}
```

---

## 🗺️ Geospatial APIs

**Base Path:** `/api/geospatial`

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/discover` | Discover nearby memories | ✅ |
| GET | `/heatmap` | Get memory density heatmap data | ✅ |
| GET | `/nearby-users` | Get nearby users | ✅ |
| GET | `/areas/popular` | Get popular areas | ✅ |
| GET | `/distance` | Calculate distance between coordinates | ✅ |
| GET | `/nearby-memories` | Get memories near location | 🔶 Optional |
| GET | `/memory-heatmap` | Get memory density heatmap (v2) | 🔶 Optional |
| GET | `/popular-areas` | Get popular areas based on engagement | 🔶 Optional |
| GET | `/nearby-users-v2` | Get nearby users (v2) | ✅ |
| GET | `/location-stats` | Get statistics for a location | 🔶 Optional |
| POST | `/discover-route` | Get memories along a route | ✅ |

### Example Request - Discover Nearby Memories

```bash
GET /api/geospatial/discover?latitude=40.7128&longitude=-74.0060&radius=500&page=1&per_page=20
Authorization: Bearer your-access-token
```

### Example Request - Get Memory Heatmap

```bash
GET /api/geospatial/memory-heatmap?north=40.8&south=40.7&east=-73.9&west=-74.1&grid_size=20
Authorization: Bearer your-access-token
```

### Example Request - Route Discovery

```bash
POST /api/geospatial/discover-route
Authorization: Bearer your-access-token
Content-Type: application/json

{
  "waypoints": [
    {"latitude": 40.7128, "longitude": -74.0060},
    {"latitude": 40.7614, "longitude": -73.9776},
    {"latitude": 40.7505, "longitude": -73.9934}
  ],
  "radius": 200
}
```

---

## 📤 Uploads APIs

**Base Path:** `/api/uploads`

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/image` | Upload image file | ✅ |
| POST | `/audio` | Upload audio file | ✅ |
| POST | `/video` | Upload video file | ✅ |
| POST | `/profile-image` | Upload profile image | ✅ |
| DELETE | `/delete/{file_path}` | Delete uploaded file | ✅ |
| GET | `/info` | Get upload configuration/limits | ✅ |

### File Upload Specifications

| Content Type | Max Size | Allowed Extensions | Rate Limit |
|--------------|----------|-------------------|------------|
| **Images** | 16MB | jpg, jpeg, png, gif, webp | 20/hour |
| **Audio** | 32MB | mp3, wav, aac, m4a, ogg | 10/hour |
| **Video** | 100MB | mp4, mov, avi, webm, mkv | 5/hour |
| **Profile Images** | 5MB | jpg, jpeg, png, webp | 5/hour |

### Example Request - Upload Image

```bash
POST /api/uploads/image
Authorization: Bearer your-access-token
Content-Type: multipart/form-data

file: [binary_image_data]
```

### Example Response - Upload Success

```json
{
  "success": true,
  "message": "Image uploaded successfully",
  "data": {
    "file_url": "/uploads/images/20241205_143022_abc12345_sunset.jpg",
    "filename": "20241205_143022_abc12345_sunset.jpg",
    "file_size": 2048576,
    "content_type": "photo"
  }
}
```

---

## 🏥 System APIs

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/health` | Health check endpoint | ❌ |
| GET | `/` | Root endpoint with API info | ❌ |

### Example Response - Health Check

```json
{
  "status": "healthy",
  "message": "Memory Lane Backend is running!"
}
```

---

## 📊 Rate Limits

| Endpoint Category | Limit | Window |
|------------------|-------|--------|
| **Image uploads** | 20 requests | per hour |
| **Audio uploads** | 10 requests | per hour |
| **Video uploads** | 5 requests | per hour |
| **Profile image uploads** | 5 requests | per hour |
| **Memory discovery** | 100 requests | per hour |

---

## 🔑 Authentication Types

| Symbol | Type | Description |
|--------|------|-------------|
| ✅ | **Required** | Must include `Authorization: Bearer <access_token>` |
| 🔶 | **Optional** | Works without auth but provides more data when authenticated |
| ❌ | **None** | No authentication needed |
| 🔄 | **Refresh Token** | Requires refresh token instead of access token |

### JWT Token Format

```bash
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTYzOTU...
```

---

## 📝 Common Query Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `page` | Integer | Page number for pagination | `?page=1` |
| `per_page` | Integer | Items per page (max varies by endpoint) | `?per_page=20` |
| `latitude` | Float | GPS latitude coordinate (-90 to 90) | `?latitude=40.7128` |
| `longitude` | Float | GPS longitude coordinate (-180 to 180) | `?longitude=-74.0060` |
| `radius` | Integer | Search radius in meters (50-5000) | `?radius=500` |
| `q` | String | Search query string | `?q=sunset` |
| `sort_by` | String | Sorting option (`recent`, `popular`, `featured`) | `?sort_by=popular` |
| `time_filter` | String | Time range filter (`today`, `week`, `month`, `all`) | `?time_filter=week` |
| `content_type` | String | Filter by content type (`photo`, `audio`, `video`, `text`) | `?content_type=photo` |
| `privacy_level` | String | Memory privacy level (`public`, `friends`, `private`) | `?privacy_level=public` |

---

## 📚 Additional Information

### Response Format

All API endpoints return JSON responses with a standardized format:

#### Success Response (2xx)
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {
    // Response data here
  },
  "status_code": 200
}
```

#### Error Response (4xx/5xx)
```json
{
  "error": "Error Type",
  "message": "Detailed error description",
  "status_code": 400
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request format or parameters |
| 401 | Unauthorized | Authentication required or invalid |
| 403 | Forbidden | Access denied |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource already exists |
| 413 | Payload Too Large | File upload too large |
| 422 | Unprocessable Entity | Validation errors |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

### Memory Privacy Levels

| Level | Description | Visibility |
|-------|-------------|------------|
| `public` | Visible to everyone | All users can discover and view |
| `friends` | Visible to friends only | Only friends can see (future feature) |
| `private` | Visible to creator only | Only the creator can view |

### Content Types

| Type | Description | Upload Endpoint |
|------|-------------|-----------------|
| `photo` | Image files | `/api/uploads/image` |
| `audio` | Voice notes, music | `/api/uploads/audio` |
| `video` | Video recordings | `/api/uploads/video` |
| `text` | Text-only memories | No upload needed |

### Interaction Types

| Type | Description | Endpoint |
|------|-------------|----------|
| `like` | Like/unlike a memory | `/api/interactions/like` |
| `comment` | Comment on a memory | `/api/interactions/comment` |
| `share` | Share a memory | `/api/interactions/share` |
| `report` | Report inappropriate content | `/api/interactions/report` |
| `view` | Memory view tracking | Automatic |

### Geospatial Features

- **PostGIS Integration**: Advanced geospatial queries using PostgreSQL with PostGIS
- **Distance Calculations**: Accurate distance calculations using geographic coordinates
- **Radius Search**: Find memories within specified radius (50m to 5km)
- **Heatmap Generation**: Memory density visualization
- **Route Discovery**: Find memories along a travel route
- **Location Statistics**: Analytics for specific geographic areas

### Real-time Features (Socket.IO)

The API supports real-time features through Socket.IO:

- **Location-based Notifications**: Get notified when new memories are created nearby
- **Live Interactions**: Real-time likes and comments
- **User Presence**: See nearby users in real-time
- **Activity Updates**: Live updates on memory interactions

#### Socket.IO Connection

```javascript
const socket = io('http://localhost:5000', {
  auth: {
    token: 'your-jwt-token'
  }
});

// Join location room
socket.emit('join_location', {
  latitude: 40.7128,
  longitude: -74.0060
});

// Listen for nearby memories
socket.on('new_memory_nearby', (data) => {
  console.log('New memory created nearby:', data);
});
```

### Database Schema

#### Key Tables

- **users**: User accounts and profiles
- **memories**: Location-based memories with PostGIS geometry
- **interactions**: User interactions (likes, comments, shares, reports)

#### Indexing

Optimized indexes for:
- Geospatial queries (GiST indexes)
- User lookups (username, email)
- Memory searches (content, tags)
- Interaction queries (user-memory combinations)

---

## 🛠️ Development Notes

### Environment Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Database setup
python run.py init-db
python run.py seed-db

# Start development server
python run.py
```

### Testing API Endpoints

```bash
# Health check
curl http://localhost:5000/health

# Register user
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"TestPass123!"}'

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"TestPass123!"}'
```

---

**Memory Lane Backend API Documentation**  
**Generated:** December 2024  
**Version:** 1.0.0

For technical support or questions, please refer to the project repository or contact the development team.