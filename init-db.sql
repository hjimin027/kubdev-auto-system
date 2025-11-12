-- KubeDev Auto System - Database Initialization
-- This file runs when PostgreSQL container starts for the first time

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create initial admin user (will be handled by application later)
-- This is just for database initialization

-- Set timezone
SET timezone = 'UTC';