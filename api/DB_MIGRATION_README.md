# Database Configuration Guide for RSW

This guide explains how to configure and switch between SQLite and PostgreSQL databases in the RSW project.

## Configuration Overview

The RSW project now supports both SQLite and PostgreSQL databases through a configurable database layer. The database type is determined by environment variables.

## Environment Variables

The following environment variables control the database configuration:

- `DB_TYPE`: Type of database to use (`sqlite` or `postgresql`/`postgres`)
- `DB_HOST`: Database host (for PostgreSQL, default: `localhost`)
- `DB_PORT`: Database port (for PostgreSQL, default: `5432`)
- `DB_USER`: Database username (for PostgreSQL, default: `dhani`)
- `DB_PASSWORD`: Database password (for PostgreSQL, default: empty)
- `DB_NAME`: Database name (for PostgreSQL, default: `rsw`)

## Using SQLite (Default)

If no environment variables are set, the application will use SQLite by default. The SQLite database file is located at `api/database.db`.

## Using PostgreSQL

To use PostgreSQL, you need to:

1. Create a PostgreSQL database:
   ```bash
   createdb rsw
   ```

2. Set the environment variables:
   ```bash
   export DB_TYPE=postgresql
   export DB_HOST=localhost
   export DB_PORT=5432
   export DB_USER=dhani
   export DB_PASSWORD=your_password  # If needed
   export DB_NAME=rsw
   ```

## Migrating from SQLite to PostgreSQL

A migration script is provided to help transfer data from SQLite to PostgreSQL:

1. Make sure your PostgreSQL database is created and running:
   ```bash
   createdb rsw  # If you haven't created it yet
   ```

2. Run the migration script:
   ```bash
   python api/migrate_sqlite_to_postgres.py
   ```

This script will:
- Read all data from the SQLite database
- Drop and recreate tables in PostgreSQL to ensure a clean slate
- Insert the data into PostgreSQL
- Reset sequence values for primary key columns to ensure new records get correct IDs

### Important Notes on Migration

- The migration script will completely reset your PostgreSQL database, removing any existing data
- Primary key sequences are automatically reset to match the highest ID from SQLite
- If you encounter any unique constraint violations during normal application use after migration, you may need to manually reset sequences:
  ```sql
  -- Replace table_name and id_column with your actual table and column names
  SELECT setval('table_name_id_column_seq', (SELECT MAX(id_column) FROM table_name), true);
  ```

### Common Migration Issues

1. **Duplicate Key Errors**: If you see errors like "duplicate key value violates unique constraint", it means the sequence for auto-incrementing IDs is not properly set. The migration script should handle this automatically, but if issues persist, use the SQL command above.

2. **Transaction Aborted Errors**: If you see "current transaction is aborted" errors, it usually means a previous SQL statement failed. The migration script handles this by using separate transactions for each table.

## Testing Both Database Types

You can use the sample environment script to easily switch between database types for testing:

1. Copy the sample script to create your own:
   ```bash
   cp api/db_env_sample.py api/set_db_env.py
   ```

2. Edit `set_db_env.py` to set your PostgreSQL credentials if needed.

3. Run the application with SQLite:
   ```bash
   python -c "import api.set_db_env; api.set_db_env.set_sqlite_env()" && python api/run.py
   ```

4. Run the application with PostgreSQL:
   ```bash
   python -c "import api.set_db_env; api.set_db_env.set_postgres_env()" && python api/run.py
   ```

## Troubleshooting

### PostgreSQL Connection Issues

If you encounter connection issues with PostgreSQL:

1. Check that PostgreSQL is running:
   ```bash
   brew services status postgresql@17
   ```

2. Verify your database exists:
   ```bash
   psql -l
   ```

3. Check your connection credentials:
   ```bash
   psql -U dhani -d rsw
   ```

### SQLite Issues

If you encounter issues with SQLite:

1. Check that the database file exists:
   ```bash
   ls -l api/database.db
   ```

2. Ensure the file has proper permissions:
   ```bash
   chmod 644 api/database.db
   ```

## Dependencies

Make sure you have the required Python packages installed:

```bash
pip install sqlalchemy psycopg2-binary pandas
