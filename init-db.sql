-- Create the pgvector extension for vector similarity search.
-- This runs once on first database initialization (container creation).
CREATE EXTENSION IF NOT EXISTS vector;
