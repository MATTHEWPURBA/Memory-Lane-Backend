-- Memory Lane Database Initialization Script
-- This script sets up the PostgreSQL database with PostGIS for geospatial operations

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "postgis_topology";

-- Create custom functions for common geospatial operations
CREATE OR REPLACE FUNCTION calculate_distance_meters(lat1 float, lon1 float, lat2 float, lon2 float)
RETURNS float AS $$
BEGIN
    RETURN ST_Distance(
        ST_GeogFromText('POINT(' || lon1 || ' ' || lat1 || ')'),
        ST_GeogFromText('POINT(' || lon2 || ' ' || lat2 || ')')
    );
END;
$$ LANGUAGE plpgsql;

-- Create function to find memories within radius
CREATE OR REPLACE FUNCTION memories_within_radius(center_lat float, center_lon float, radius_meters float)
RETURNS TABLE(memory_id uuid, distance_meters float) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.memory_id,
        ST_Distance(
            m.location::geography,
            ST_GeogFromText('POINT(' || center_lon || ' ' || center_lat || ')')
        ) as distance_meters
    FROM memories m
    WHERE ST_DWithin(
        m.location::geography,
        ST_GeogFromText('POINT(' || center_lon || ' ' || center_lat || ')'),
        radius_meters
    )
    AND m.is_active = true
    ORDER BY distance_meters;
END;
$$ LANGUAGE plpgsql;

-- Create indexes for better performance (will be created after tables are made by SQLAlchemy)
-- Note: These will be added programmatically after table creation

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE memory_lane_db TO memory_lane_user;
GRANT ALL ON SCHEMA public TO memory_lane_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO memory_lane_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO memory_lane_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO memory_lane_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO memory_lane_user;

-- Basic database configuration for performance
ALTER SYSTEM SET shared_preload_libraries = 'postgis-3';
ALTER SYSTEM SET max_connections = 100;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Reload configuration
SELECT pg_reload_conf();

-- Create schema info table for version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version VARCHAR(20) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_version (version, description) 
VALUES ('1.0.0', 'Initial database setup with PostGIS support')
ON CONFLICT (version) DO NOTHING;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Memory Lane database initialized successfully with PostGIS support';
    RAISE NOTICE 'Available extensions: %, %, %', 
        (SELECT extname FROM pg_extension WHERE extname = 'uuid-ossp'),
        (SELECT extname FROM pg_extension WHERE extname = 'postgis'),
        (SELECT extname FROM pg_extension WHERE extname = 'postgis_topology');
END $$; 