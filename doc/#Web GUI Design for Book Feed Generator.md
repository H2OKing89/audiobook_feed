# Web GUI Design for Book Feed Generator using Vue.js and Node.js

## **1. Overview**

This document outlines the design for a web GUI that allows users to create and manage feeds of audiobooks based on authors, series, or books. The GUI will interact with existing Python code and utilize APIs to fetch audiobook metadata. The goal is to provide a user-friendly interface for searching, selecting, and managing audiobook feeds. We will use Vue.js for the frontend and Node.js for the backend to handle API requests and feed generation. We will also utilize the existing Python code to generate the feeds. As a beginner to web development, this document serves as a learning guide and project roadmap.
 
## **2. Technology Stack**

- **Frontend:** Vue.js 3 with Composition API
- **UI Framework:** Vuetify (component library with Material Design)
- **Backend:** Node.js with Express.js
- **Python Integration:** Node.js child_process to execute Python scripts
- **Database:** SQLite (for simplicity) or MongoDB (if more flexibility needed)
- **Authentication:** JWT (JSON Web Tokens) for API authentication
- **Deployment:** Docker containers for easy deployment

## **3. Search Functionality Design**

### **Search Bar**

- **Input:** Allow users to search by author, book title, or narrator to find audiobooks to add to their feed list.
- **Multi-API Support:** Use Audible hidden API with fallback to <https://api.audnex.us> for metadata retrieval.

### **Results Display**

- **Tabs or Sections:** Authors / Books / Series / Narrators
- **Expandable Rows:** Click on an author to see their books and series.
- **Details Modal:** Click on a book to view its metadata (title, author, series, narrator, cover image, summary, etc.).
- **Select for Feed:** Checkbox or button to "Add to Feed."
- **Search History:** Show recent searches or saved authors/series for quick access.
- **Feed Sorting:** Options to sort feeds by series order, release date, etc.

## **4. Feed Management**

- **View Feeds:**
  - List created feeds with options to edit or delete.
  - Add Author/Series/Book to existing feeds manually.
  - Author can have multiple Series/Books in the feed.
  - Cron job to auto-update feeds periodically.
  - Export iCal files from feeds for calendar.

## **5. Feed Creation Workflow**

1. **Search for Author/Book/Series/Narrator.**
2. **Select Items:** Choose which books or series to add to the feed.
3. **Configure Feed Options:** (Options for customization)
   - Custom title, description, cover art
   - Include/exclude specific books
4. **Review Feed Preview:** Show what the feed would look like before saving.
5. **Save and Generate Feed:** Save config and trigger feed file creation.

## **6. Extra Features**

- **Recent Searches** or **Saved Authors/Series**
- **Manual Entry:** For rare cases, add a book manually if not found via API.
- **Batch Add:** Select multiple books/series at once.
- **Metadata Editing:** Option to override or correct details before saving.
- **Progress Spinner/Loading State:** While APIs are queried.

## **7. Technical/UX Notes**

- **Simplified State Management:** Start with Vue's Composition API for state management, migrate to Pinia (Vue's recommended state management) when needed
- **Responsive Design:** Use Vuetify's grid system to ensure the GUI works well on both desktop and mobile
- **Async Handling:** Use async/await for API calls with try/catch blocks for error handling
- **Fallback Handling:** If one API fails, use the other or notify the user
- **Authentication:** Implementation details:
  - Settings page for API keys (Audible, Pushover)
  - Email configuration panel for notification settings
  - Discord webhook configuration for notifications
  - User authentication with email/password or OAuth options

## **8. Data Storage**

- **Feed Configuration:** Store feed settings, included authors/books/series
- **User Preferences:** Theme preferences, notification settings, API keys
- **Search History:** Recent searches for quick access
- **Cache:** Store API responses to reduce API calls and improve performance

## **9. Implementation Path (For Beginners)**

1. **Setup Development Environment:**
   - Install Node.js and npm
   - Install Vue CLI
   - Create a new Vue project with Vue CLI

2. **Create Basic Frontend Structure:**
   - Setup Vue Router for navigation
   - Create placeholder components for main pages
   - Implement a basic responsive layout with Vuetify

3. **Setup Express Backend:**
   - Create basic API endpoints
   - Implement Python script execution
   - Test basic API functionality

4. **Implement Core Features (In Order):**
   - Search functionality with API integration
   - Results display with basic filtering
   - Simple feed creation and management
   - Feed generation by calling Python code

5. **Enhance and Refine:**
   - Add authentication
   - Implement advanced features
   - Polish UI/UX
   - Add comprehensive error handling

## **10. Learning Resources**

- **Vue.js:** [Official Vue.js Guide](https://vuejs.org/guide/introduction.html)
- **Vuetify:** [Vuetify Getting Started](https://vuetifyjs.com/en/getting-started/installation/)
- **Express.js:** [Express.js Guide](https://expressjs.com/en/guide/routing.html)
- **Node.js with Python:** [Node.js child_process](https://nodejs.org/api/child_process.html)
- **YouTube Tutorials:** Vue.js Crash Course by Traversy Media or Vue Mastery

## **11. Sample User Flow**

1. User visits the web GUI.
2. User types "Shirtaloon" in the search bar.
3. App queries APIs, displays a list of matching authors/books/series.
4. User clicks on "Shirtaloon" → sees all books and series.
5. User selects the "He Who Fights with Monsters" series, customizes feed title/cover, saves.
6. Feed is generated and appears in the dashboard.
