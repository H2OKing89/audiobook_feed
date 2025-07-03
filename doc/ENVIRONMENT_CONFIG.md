# AudioStacker Environment Configuration

This document explains how to configure the environment variables for AudioStacker.

## Backend Configuration

The backend environment variables are stored in `/src/web/backend/.env`:

```env
PORT=5005                   # The port the backend will listen on
NODE_ENV=development        # The Node.js environment (development, production)
PYTHON_PATH=../../audiostracker  # Path to the Python module
```

## Frontend Configuration

The frontend environment variables are stored in `/src/web/frontend/.env`:

```env
VUE_APP_API_BASE_URL=http://localhost:5005  # The URL to the backend API
VUE_APP_API_TIMEOUT=30000                  # API request timeout in milliseconds
```

## Configuring Ports

If you want to change the ports used by the application:

1. Update the `PORT` value in the backend's `.env` file
2. Update the `VUE_APP_API_BASE_URL` in the frontend's `.env` file
3. Restart both the backend and frontend services

The script `stop_web_ui.sh` will automatically detect the configured ports when stopping the services.

## Using Environment Variables in Development

During development, the `.env` files are automatically loaded.

For production builds, make sure to set these environment variables in your deployment environment.

## Additional Configuration

For more advanced configuration options, see the documentation in:

- `/doc/IMPLEMENTATION_GUIDE.md` - General implementation details
- `/doc/MIGRATION_COMPLETED.md` - Details on the migration to database-backed watchlist
- `/doc/MIGRATION_UPDATES.md` - Information on the latest improvements
