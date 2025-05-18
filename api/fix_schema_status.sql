-- SQL script to fix the schema status for schema ID 3
-- This will set db_loaded to 'no' to match the actual state in Neo4j

UPDATE schemas
SET db_loaded = 'no'
WHERE id = 3;
