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
      
      <!-- Advanced Matching Options -->
      <v-expansion-panels v-model="advancedPanel" class="mt-4">
        <v-expansion-panel title="Advanced Search Options">
          <v-expansion-panel-text>
            <v-row>
              <v-col cols="12" md="4">
                <v-switch
                  v-model="useMatching"
                  label="Enable Confidence-Based Matching"
                  color="primary"
                  hint="Use AI-powered matching to filter and rank results based on confidence scores"
                  persistent-hint
                ></v-switch>
              </v-col>
              
              <v-col cols="12" md="4" v-if="useMatching">
                <v-slider
                  v-model="minConfidence"
                  label="Minimum Confidence"
                  min="0.1"
                  max="1.0"
                  step="0.1"
                  thumb-label
                  :hint="`Only show results with confidence ≥ ${minConfidence}`"
                  persistent-hint
                ></v-slider>
              </v-col>
              
              <v-col cols="12" md="4" v-if="useMatching">
                <v-chip-group v-model="selectedConfidencePreset" mandatory>
                  <v-chip value="strict" @click="setConfidencePreset('strict')">Strict (0.7+)</v-chip>
                  <v-chip value="balanced" @click="setConfidencePreset('balanced')">Balanced (0.5+)</v-chip>
                  <v-chip value="loose" @click="setConfidencePreset('loose')">Loose (0.3+)</v-chip>
                </v-chip-group>
              </v-col>
            </v-row>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-form>
    
    <!-- Tabs for search results -->
    <v-tabs v-if="hasResults" v-model="activeTab" color="primary">
      <v-tab value="authors">Authors</v-tab>
      <v-tab value="series">Series</v-tab>
      <v-tab value="books">Books</v-tab>
      <v-tab value="narrators">Narrators</v-tab>
    </v-tabs>
    
    <!-- Search Results Summary -->
    <v-alert v-if="hasResults && searchResults.meta" type="info" variant="tonal" class="mt-4">
      <v-row>
        <v-col cols="12" md="8">
          <span v-if="searchResults.meta.matchingEnabled">
            <strong>Confidence Matching:</strong> Found {{ searchResults.meta.totalFilteredResults }} good matches
            from {{ searchResults.meta.totalRawResults }} raw results 
            (minimum confidence: {{ searchResults.meta.minConfidence }})
          </span>
          <span v-else>
            <strong>Raw Search:</strong> {{ searchResults.meta.totalRawResults }} results found
          </span>
        </v-col>
        <v-col cols="12" md="4" class="text-right">
          <v-chip 
            v-if="searchResults.meta.matchingEnabled" 
            :color="searchResults.meta.totalFilteredResults > 0 ? 'success' : 'warning'"
            size="small"
          >
            {{ searchResults.meta.totalFilteredResults }} matches
          </v-chip>
        </v-col>
      </v-row>
    </v-alert>
    
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
              ></v-btn>
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
                <!-- Show confidence score if available -->
                <div v-if="book.confidenceScore !== null && book.confidenceScore !== undefined" 
                     class="mt-2">
                  <v-chip 
                    :color="book.needsReview ? 'warning' : 'success'" 
                    size="small"
                    :prepend-icon="book.needsReview ? 'mdi-alert' : 'mdi-check-circle'"
                  >
                    {{ (book.confidenceScore * 100).toFixed(0) }}% confidence
                    <span v-if="book.needsReview"> (review needed)</span>
                  </v-chip>
                </div>
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

            </template>
          </v-list-item>
        </v-list>
      </v-window-item>
    </v-window>
    
    <!-- Search Results Summary -->
    <v-alert v-if="hasResults && searchResults.meta" type="info" variant="tonal" class="mt-4">
      <v-row>
        <v-col cols="12" md="8">
          <span v-if="searchResults.meta.matchingEnabled">
            <strong>Confidence Matching:</strong> Found {{ searchResults.meta.totalFilteredResults }} good matches
            from {{ searchResults.meta.totalRawResults }} raw results 
            (minimum confidence: {{ searchResults.meta.minConfidence }})
          </span>
          <span v-else>
            <strong>Raw Search:</strong> {{ searchResults.meta.totalRawResults }} results found
          </span>
        </v-col>
        <v-col cols="12" md="4" class="text-right">
          <v-chip 
            v-if="searchResults.meta.matchingEnabled" 
            :color="searchResults.meta.totalFilteredResults > 0 ? 'success' : 'warning'"
            size="small"
          >
            {{ searchResults.meta.totalFilteredResults }} matches
          </v-chip>
        </v-col>
      </v-row>
    </v-alert>
    
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
            color="grey darken-1"
            text
            @click="detailsDialog = false"
          >
            Close
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
        narrators: [],
        meta: null
      },
      activeTab: 'authors',
      detailsDialog: false,
      selectedBook: null,

      // Confidence matching options
      advancedPanel: [],
      useMatching: true,
      minConfidence: 0.5,
      selectedConfidencePreset: 'balanced'
    };
  },
  mounted() {
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
      this.searchResults = { authors: [], series: [], books: [], narrators: [], meta: null };
      
      try {
        // Make a real API call to our backend with confidence matching options
        const response = await axios.post('http://localhost:5005/api/search', {
          query: this.searchQuery,
          searchType: this.searchType,
          useMatching: this.useMatching,
          minConfidence: this.minConfidence
        });
        
        // Update search results with real data
        this.searchResults = response.data;
        
        // Set active tab based on which results are available
        if (this.searchResults.authors.length > 0) {
          this.activeTab = 'authors';
        } else if (this.searchResults.series.length > 0) {
          this.activeTab = 'series';
        } else if (this.searchResults.books.length > 0) {
          this.activeTab = 'books';
        } else if (this.searchResults.narrators.length > 0) {
          this.activeTab = 'narrators';
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
    

    
    setConfidencePreset(preset) {
      switch (preset) {
        case 'strict':
          this.minConfidence = 0.7;
          break;
        case 'balanced':
          this.minConfidence = 0.5;
          break;
        case 'loose':
          this.minConfidence = 0.3;
          break;
      }
      this.selectedConfidencePreset = preset;
    },
    

  }
};
</script>
