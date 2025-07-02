# Web GUI Design for Book Feed Generator using node.js and Existing python.

## **Overview**

This document outlines the design for a web GUI that allows users to create and manage feeds of audiobooks based on authors, series, or books. The GUI will interact with existing Python code and utilize APIs to fetch audiobook metadata. The goal is to provide a user-friendly interface for searching, selecting, and managing audiobook feeds. We will use a combination of React or Vue.js for the frontend and Node.js for the backend to handle API requests and feed generation. we will also try and using the existing python code to generate the feeds if possible. I am new to web development and coding, so I will need to learn the basics of these technologies as we go along.
 
## **Search Functionality Design**

### **Search Bar**

- **Input:** Allow users to search by author, book title, or narrator. to find audiobooks to add to their feed list.
- **Multi-API Support:** Use Audible hidden API with fallback to <https://api.audnex.us>. for metadata retrieval.

## **Results Display**

- **Tabs or Sections:** Authors / Books / Series / Narrators
- **Expandable Rows:** Click on an author to see their books and series.
- **Details Modal:** Click on a book to view its metadata (title, author, series, narrator, cover image, summary, etc.).
- **Select for Feed:** Checkbox or button to “Add to Feed.”
- **Search History:** Show recent searches or saved authors/series for quick access.
- **Feed Sorting:** Options to sort feeds by series order, release date, etc.

---

## 2. **Feed Management**

- **View Feeds:** 
  - List created feeds with options to edit or delete.
  - Add Author/Series/Book to existing feeds manually.
  - Author can have multiple Series/Books in the feed.
  - cron job to auto-update feeds periodically.
  - Export ical files from feeds for calendar.


---

## 3. **Feed Creation Workflow**

1. **Search for Author/Book/Series/Narrator.**
2. **Select Items:** Choose which books or series to add to the feed.
3. **Configure Feed Options:** (Options for customization)
   - Custom title, description, cover art
   - Include/exclude specific books

4. **Review Feed Preview:** Show what the feed would look like before saving.
5. **Save and Generate Feed:** Save config and trigger feed file creation.

---

## 3. **Extra Features**

- **Recent Searches** or **Saved Authors/Series**
- **Manual Entry:** For rare cases, add a book manually if not found via API.
- **Batch Add:** Select multiple books/series at once.
- **Metadata Editing:** Option to override or correct details before saving.
- **Progress Spinner/Loading State:** While APIs are queried.

---

## 4. **Technical/UX Notes**

- **Framework:** Use React or Vue.js for a responsive, dynamic UI.
- **State Management:** Use Redux or Vuex for managing search results and feeds.
- **Responsive Design:** Ensure the GUI works well on both desktop and mobile.
- **Async Handling:** Both APIs can be slow—show loading states and handle failures gracefully.
- **Fallback Handling:** If one API fails, use the other or notify the user.
- **Authentication:** If either API needs a token, provide a settings page for API keys. for Pushover API. Email notifications can be configured in the settings. Discord webhook can be set up for notifications.

---

## 5. **Sample User Flow**

1. User visits the web GUI.
2. User types “Shirtaloon” in the search bar.
3. App queries APIs, displays a list of matching authors/books/series.
4. User clicks on “ Shirtaloon” → sees all books and series.
5. User selects the “He Who Fights with Monsters” series, customizes feed title/cover, saves.
6. Feed is generated and appears in the dashboard.
