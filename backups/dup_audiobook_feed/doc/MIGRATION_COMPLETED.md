# AudioStacker Migration to Database-Backed Watchlist

## Project Status

We've completed the migration of AudioStacker from YAML-based configuration to a database-backed watchlist with a web UI for management. Here's what has been accomplished:

### Backend (Node.js/Express)

1. Updated backend API endpoints to work with the new database-driven watchlist:
   - GET `/api/audiostacker/watchlist` - Get the full watchlist
   - POST `/api/audiostacker/watchlist` - Add a new author to the watchlist
   - PUT `/api/audiostacker/watchlist` - Update an existing author in the watchlist
   - DELETE `/api/audiostacker/watchlist?author=AuthorName` - Remove an author from the watchlist

2. Fixed Python/Node.js integration:
   - Ensured all Python script invocations use absolute imports
   - Set up proper path handling to avoid relative import errors

3. Removed the "feeds" system:
   - Removed all feed-related frontend components and routes
   - Removed "Add to Feed" functionality from the search UI
   - Simplified the application to focus on core watchlist functionality

4. Removed search functionality:
   - Removed search route from frontend
   - Removed Search button from main navigation
   - Disabled search and matching endpoints in backend API

### Database (SQLite)

1. Added new functions to `database.py` for author-based watchlist operations:
   - `update_watchlist_entry_by_author()` - Updates a watchlist entry by author name
   - `delete_watchlist_entry_by_author()` - Deletes a watchlist entry by author name

### Frontend (Vue.js)

1. Created `WatchlistView.vue` component for managing the watchlist:
   - Displays the current watchlist with authors and their criteria
   - Allows adding new authors with various filtering criteria
   - Enables editing existing author entries
   - Supports removing authors from the watchlist

2. Added "Watchlist" route to the application router

3. Updated navigation to include the Watchlist view

4. Removed feed-related components:
   - Removed "Feeds" navigation button from App.vue
   - Removed FeedsView.vue component and its route
   - Removed "Add to Feed" buttons and functionality from SearchView.vue

## Testing Completed

1. Tested API endpoints using curl:
   - Successfully added a new author to the watchlist
   - Successfully updated an existing author
   - Successfully removed an author

2. Tested the web UI navigation and access to the Watchlist page

## Next Steps

The migration is complete! You can now:

1. Access the watchlist management UI at [http://localhost:5006/watchlist](http://localhost:5006/watchlist)
2. Use the API endpoints to manage your watchlist programmatically
3. Run the pruning endpoint to clean up old database entries: `/api/audiostacker/prune`

The application has been simplified to focus on the core functionality of tracking audiobook releases by author or series. The "feeds" system has been removed to avoid confusion and provide a more streamlined experience.

## Notes

- The system now uses the SQLite database exclusively for watchlist management, eliminating the need for YAML files.
- All CRUD operations (Create, Read, Update, Delete) for the watchlist are available through both the API and the web UI.
- The watchlist can be filtered and searched in the UI for easier management.
