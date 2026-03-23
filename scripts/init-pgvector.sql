-- Run as superuser (postgres) to enable pgvector extension.
-- Docker entrypoint auto-executes .sql files in /docker-entrypoint-initdb.d/
CREATE EXTENSION IF NOT EXISTS vector;
