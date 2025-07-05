-- Additional indexes for Memory Lane Database
-- Run this after SQLAlchemy creates the tables

-- Users table indexes
CREATE INDEX IF NOT EXISTS idx_users_username_active ON users(username) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_users_email_active ON users(email) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active);

-- Memories table indexes
CREATE INDEX IF NOT EXISTS idx_memories_location_gist ON memories USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_memories_creator_active ON memories(creator_id) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at);
CREATE INDEX IF NOT EXISTS idx_memories_privacy_active ON memories(privacy_level) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_memories_content_type ON memories(content_type);
CREATE INDEX IF NOT EXISTS idx_memories_category_tags ON memories USING GIN(category_tags);
CREATE INDEX IF NOT EXISTS idx_memories_ai_tags ON memories USING GIN(ai_generated_tags);
CREATE INDEX IF NOT EXISTS idx_memories_likes_count ON memories(likes_count DESC);
CREATE INDEX IF NOT EXISTS idx_memories_expiration ON memories(expiration_date) WHERE expiration_date IS NOT NULL;

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_memories_location_privacy ON memories(privacy_level, is_active) 
    WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_memories_creator_created ON memories(creator_id, created_at DESC);

-- Interactions table indexes  
CREATE INDEX IF NOT EXISTS idx_interactions_user_memory_type ON interactions(user_id, memory_id, interaction_type);
CREATE INDEX IF NOT EXISTS idx_interactions_memory_type_active ON interactions(memory_id, interaction_type) 
    WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_interactions_user_type_active ON interactions(user_id, interaction_type) 
    WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_interactions_created_at ON interactions(created_at);
CREATE INDEX IF NOT EXISTS idx_interactions_type_created ON interactions(interaction_type, created_at DESC);

-- Spatial indexes for geospatial queries
CREATE INDEX IF NOT EXISTS idx_memories_geography ON memories USING GIST(ST_Transform(location, 4326));

-- Partial indexes for common filtered queries
CREATE INDEX IF NOT EXISTS idx_memories_public_active ON memories(created_at DESC) 
    WHERE privacy_level = 'public' AND is_active = true;
CREATE INDEX IF NOT EXISTS idx_interactions_likes_active ON interactions(memory_id, created_at DESC) 
    WHERE interaction_type = 'like' AND is_active = true;
CREATE INDEX IF NOT EXISTS idx_interactions_comments_active ON interactions(memory_id, created_at DESC) 
    WHERE interaction_type = 'comment' AND is_active = true;

-- Text search indexes (if using full-text search)
CREATE INDEX IF NOT EXISTS idx_memories_title_search ON memories USING GIN(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_memories_description_search ON memories USING GIN(to_tsvector('english', description));

-- Update statistics
ANALYZE users;
ANALYZE memories;
ANALYZE interactions; 