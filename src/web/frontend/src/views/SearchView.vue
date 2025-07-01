<template>
  <div class="search-view">
    <h1 class="text-h4 mb-6">Search Audiobooks</h1>
    
    <v-form @submit.prevent="searchAudiobooks">
      <v-row>
        <v-col cols="12" md="6">
          <v-text-field
            v-model="searchQuery"
            label="Search for authors, books, series, or narrators"
            placeholder="e.g., Brandon Sanderson, Project Hail Mary"
            append-icon="mdi-magnify"
            @click:append="searchAudiobooks"
            clearable
            outlined
          ></v-text-field>
        </v-col>
        
        <v-col cols="12" md="4">
          <v-select
            v-model="searchType"
            :items="searchTypes"
            label="Search Type"
            outlined
          ></v-select>
        </v-col>
        
        <v-col cols="12" md="2">
          <v-btn 
            color="primary" 
            block
            @click="searchAudiobooks"
            :loading="loading"
            height="56"
          >
            Search
          </v-btn>
        </v-col>
      </v-row>
    </v-form>
    
    <!-- Tabs for search results -->
    <v-tabs v-if="hasResults" v-model="activeTab" color="primary">
      <v-tab value="authors">Authors</v-tab>
      <v-tab value="series">Series</v-tab>
      <v-tab value="books">Books</v-tab>
      <v-tab value="narrators">Narrators</v-tab>
    </v-tabs>
    
    <!-- Loading indicator -->
    <div v-if="loading" class="d-flex justify-center my-10">
      <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
    </div>
    
    <!-- Search Results -->
    <v-window v-model="activeTab" v-if="hasResults && !loading">
      <!-- Authors Tab -->
      <v-window-item value="authors">
        <v-list lines="three">
          <v-list-item
            v-for="(author, index) in searchResults.authors"
            :key="index"
            :value="author"
          >
            <template v-slot:prepend>
              <v-avatar color="grey-lighten-1">
                <v-icon icon="mdi-account"></v-icon>
              </v-avatar>
            </template>
            
            <v-list-item-title>{{ author.name }}</v-list-item-title>
            <v-list-item-subtitle>Books: {{ author.bookCount || 'Unknown' }}</v-list-item-subtitle>
            
            <template v-slot:append>
              <v-btn
                color="primary"
                variant="text"
                @click="addToFeed(author, 'author')"
              >
                Add to Feed
              </v-btn>
            </template>
          </v-list-item>
        </v-list>
      </v-window-item>
      
      <!-- Series Tab -->
      <v-window-item value="series">
        <v-list lines="three">
          <v-list-item
            v-for="(series, index) in searchResults.series"
            :key="index"
            :value="series"
          >
            <template v-slot:prepend>
              <v-avatar color="grey-lighten-1">
                <v-icon icon="mdi-book-multiple"></v-icon>
              </v-avatar>
            </template>
            
            <v-list-item-title>{{ series.name }}</v-list-item-title>
            <v-list-item-subtitle>
              by {{ series.author }} • Books: {{ series.bookCount || 'Unknown' }}
            </v-list-item-subtitle>
            
            <template v-slot:append>
              <v-btn
                color="primary"
                variant="text"
                @click="addToFeed(series, 'series')"
              >
                Add to Feed
              </v-btn>
            </template>
          </v-list-item>
        </v-list>
      </v-window-item>
      
      <!-- Books Tab -->
      <v-window-item value="books">
        <v-row>
          <v-col
            v-for="(book, index) in searchResults.books"
            :key="index"
            cols="12"
            sm="6"
            md="4"
            lg="3"
          >
            <v-card height="100%">
              <v-img
                :src="book.cover || 'https://via.placeholder.com/150'"
                height="200"
                cover
                class="align-end"
              >
                <v-card-title class="text-white bg-black bg-opacity-50">
                  {{ book.title }}
                </v-card-title>
              </v-img>
              
              <v-card-subtitle>
                by {{ book.author }}
                <div v-if="book.series">Series: {{ book.series }}</div>
              </v-card-subtitle>
              
              <v-card-actions>
                <v-btn
                  color="primary"
                  variant="text"
                  @click="showBookDetails(book)"
                >
                  Details
                </v-btn>
                <v-spacer></v-spacer>
                <v-btn
                  color="primary"
                  variant="text"
                  @click="addToFeed(book, 'book')"
                >
                  Add to Feed
                </v-btn>
              </v-card-actions>
            </v-card>
          </v-col>
        </v-row>
      </v-window-item>
      
      <!-- Narrators Tab -->
      <v-window-item value="narrators">
        <v-list lines="three">
          <v-list-item
            v-for="(narrator, index) in searchResults.narrators"
            :key="index"
            :value="narrator"
          >
            <template v-slot:prepend>
              <v-avatar color="grey-lighten-1">
                <v-icon icon="mdi-microphone"></v-icon>
              </v-avatar>
            </template>
            
            <v-list-item-title>{{ narrator.name }}</v-list-item-title>
            <v-list-item-subtitle>
              Books narrated: {{ narrator.bookCount || 'Unknown' }}
            </v-list-item-subtitle>
            
            <template v-slot:append>
              <v-btn
                color="primary"
                variant="text"
                @click="addToFeed(narrator, 'narrator')"
              >
                Add to Feed
              </v-btn>
            </template>
          </v-list-item>
        </v-list>
      </v-window-item>
    </v-window>
    
    <!-- No Results Message -->
    <v-alert
      v-if="noResults"
      type="info"
      class="mt-4"
    >
      No results found for "{{ searchQuery }}". Try a different search term.
    </v-alert>
    
    <!-- Book Details Dialog -->
    <v-dialog v-model="detailsDialog" max-width="600px">
      <v-card v-if="selectedBook">
        <v-card-title>{{ selectedBook.title }}</v-card-title>
        
        <v-card-text>
          <v-row>
            <v-col cols="4">
              <v-img
                :src="selectedBook.cover || 'https://via.placeholder.com/150'"
                height="200"
                contain
              ></v-img>
            </v-col>
            <v-col cols="8">
              <p><strong>Author:</strong> {{ selectedBook.author }}</p>
              <p v-if="selectedBook.series">
                <strong>Series:</strong> {{ selectedBook.series }}
                <span v-if="selectedBook.seriesNumber">(#{{ selectedBook.seriesNumber }})</span>
              </p>
              <p><strong>Narrator:</strong> {{ selectedBook.narrator }}</p>
              <p><strong>Publisher:</strong> {{ selectedBook.publisher }}</p>
              <p v-if="selectedBook.releaseDate">
                <strong>Release Date:</strong> {{ formatDate(selectedBook.releaseDate) }}
              </p>
            </v-col>
          </v-row>
          
          <div class="mt-4" v-if="selectedBook.summary">
            <h3>Summary</h3>
            <p>{{ selectedBook.summary }}</p>
          </div>
        </v-card-text>
        
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            color="primary"
            text
            @click="addToFeed(selectedBook, 'book')"
          >
            Add to Feed
          </v-btn>
          <v-btn
            color="grey darken-1"
            text
            @click="detailsDialog = false"
          >
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- Add to Feed Dialog -->
    <v-dialog v-model="addToFeedDialog" max-width="500px">
      <v-card>
        <v-card-title>Add to Feed</v-card-title>
        
        <v-card-text>
          <v-radio-group v-model="feedOption">
            <v-radio label="Add to existing feed" value="existing"></v-radio>
            <v-radio label="Create new feed" value="new"></v-radio>
          </v-radio-group>
          
          <v-select
            v-if="feedOption === 'existing'"
            v-model="selectedFeed"
            :items="existingFeeds"
            item-title="name"
            item-value="id"
            label="Select Feed"
            outlined
          ></v-select>
          
          <div v-if="feedOption === 'new'">
            <v-text-field
              v-model="newFeedName"
              label="Feed Name"
              outlined
            ></v-text-field>
            <v-textarea
              v-model="newFeedDescription"
              label="Description (optional)"
              outlined
              rows="2"
            ></v-textarea>
          </div>
        </v-card-text>
        
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            color="primary"
            text
            @click="saveFeed"
          >
            Save
          </v-btn>
          <v-btn
            color="grey darken-1"
            text
            @click="addToFeedDialog = false"
          >
            Cancel
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'SearchView',
  data() {
    return {
      searchQuery: '',
      searchType: 'author',
      searchTypes: [
        { title: 'Author', value: 'author' },
        { title: 'Book Title', value: 'title' },
        { title: 'Series', value: 'series' },
        { title: 'Narrator', value: 'narrator' }
      ],
      loading: false,
      searchResults: {
        authors: [],
        series: [],
        books: [],
        narrators: []
      },
      activeTab: 'authors',
      detailsDialog: false,
      selectedBook: null,
      addToFeedDialog: false,
      itemToAdd: null,
      itemType: null,
      feedOption: 'new',
      selectedFeed: null,
      existingFeeds: [
        { name: 'Fantasy Books', id: 1 },
        { name: 'Sci-Fi Collection', id: 2 },
        { name: 'Mystery Thrillers', id: 3 }
      ],
      newFeedName: '',
      newFeedDescription: ''
    };
  },
  computed: {
    hasResults() {
      return this.searchResults.authors.length > 0 || 
             this.searchResults.series.length > 0 || 
             this.searchResults.books.length > 0 || 
             this.searchResults.narrators.length > 0;
    },
    noResults() {
      return !this.loading && 
             this.searchQuery && 
             !this.hasResults;
    }
  },
  methods: {
    async searchAudiobooks() {
      if (!this.searchQuery) return;
      
      this.loading = true;
      
      try {
        // API call would go here
        // For demo, we'll simulate a response
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // Simulate search results based on search type
        if (this.searchType === 'author') {
          this.searchResults = {
            authors: [
              { name: 'Brandon Sanderson', bookCount: 42 },
              { name: 'Andy Weir', bookCount: 3 },
              { name: 'Martha Wells', bookCount: 12 }
            ],
            series: [],
            books: [],
            narrators: []
          };
          this.activeTab = 'authors';
        } else if (this.searchType === 'title') {
          this.searchResults = {
            authors: [],
            series: [],
            books: [
              { 
                title: 'Project Hail Mary', 
                author: 'Andy Weir', 
                narrator: 'Ray Porter', 
                publisher: 'Audible Studios',
                cover: 'https://m.media-amazon.com/images/I/51Fqn4gE5HL._SL500_.jpg',
                releaseDate: '2021-05-04',
                summary: 'Ryland Grace is the sole survivor on a desperate, last-chance mission...'
              },
              { 
                title: 'The Way of Kings', 
                author: 'Brandon Sanderson', 
                series: 'The Stormlight Archive',
                seriesNumber: '1',
                narrator: 'Michael Kramer, Kate Reading', 
                publisher: 'Macmillan Audio',
                cover: 'https://m.media-amazon.com/images/I/51tZz4XCvCL._SL500_.jpg'
              }
            ],
            narrators: []
          };
          this.activeTab = 'books';
        }
        
      } catch (error) {
        console.error('Error searching audiobooks:', error);
        // Handle error
      } finally {
        this.loading = false;
      }
    },
    
    showBookDetails(book) {
      this.selectedBook = book;
      this.detailsDialog = true;
    },
    
    formatDate(dateString) {
      const date = new Date(dateString);
      return new Intl.DateTimeFormat('en-US', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      }).format(date);
    },
    
    addToFeed(item, type) {
      this.itemToAdd = item;
      this.itemType = type;
      this.addToFeedDialog = true;
    },
    
    saveFeed() {
      // In a real app, this would save to the backend
      console.log('Saving to feed:', {
        item: this.itemToAdd,
        type: this.itemType,
        feedOption: this.feedOption,
        feedId: this.selectedFeed,
        newFeedName: this.newFeedName,
        newFeedDescription: this.newFeedDescription
      });
      
      // Reset and close dialog
      this.addToFeedDialog = false;
      this.newFeedName = '';
      this.newFeedDescription = '';
      
      // Show success message
      // this.$toast.success('Added to feed successfully!');
    }
  }
};
</script>
