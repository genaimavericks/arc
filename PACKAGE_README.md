# RSW Deployment Package

This package contains a deployable version of the RSW application.

## Deployment Instructions

1. Extract the archive to your target server:
   ```
   tar -xzf rsw-deployment.tar.gz
   cd package
   ```

2. Run the deployment script:
   ```
   ./deploy.sh
   ```
   This will set up the Python environment and configure the application.

3. Edit the configuration file in `config/.env` with your specific settings.

4. Start the application:
   ```
   ./start.sh
   ```

## Configuration Options

### Database Configuration
- The package supports both SQLite and PostgreSQL databases
- Set `DB_TYPE` in config/.env to 'sqlite' or 'postgresql'
- For PostgreSQL, also set `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME`
- A migration script is included to transfer data from SQLite to PostgreSQL

### API URL Configuration
- Set `NEXT_PUBLIC_API_URL` in config/.env to the public URL of your API
- By default, it will use http://localhost:9090

## Troubleshooting

If you encounter any issues during deployment:
1. Check the logs in the console output
2. Verify that all configuration settings are correct
3. Ensure your database is properly set up and accessible
