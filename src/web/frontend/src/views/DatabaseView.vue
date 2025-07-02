<template>
  <div class="database-view">
    <h1 class="text-h4 mb-6">AudioStacker Database</h1>
    
    <!-- Filter Controls -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row>
          <v-col cols="12" md="3">
            <v-select
              v-model="selectedFilter"
              :items="filterOptions"
              label="Filter Books"
              @update:modelValue="loadBooks"
            ></v-select>
          </v-col>
          <v-col cols="12" md="3">
            <v-text-field
              v-model="searchQuery"
              label="Search"
              append-icon="mdi-magnify"
              @input="debouncedSearch"
              clearable
            ></v-text-field>
          </v-col>
          <v-col cols="12" md="6" class="d-flex align-center">
            <v-spacer></v-spacer>
            <v-btn color="primary" @click="loadBooks" :loading="loading">
              <v-icon left>mdi-refresh</v-icon>
              Refresh
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Database Stats -->
    <v-row class="mb-4">
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text class="text-center">
            <div class="text-h5 primary--text">{{ totalBooks }}</div>
            <div class="text-caption">Total Books</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text class="text-center">
            <div class="text-h5 success--text">{{ upcomingCount }}</div>
            <div class="text-caption">Upcoming</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text class="text-center">
            <div class="text-h5 info--text">{{ notifiedCount }}</div>
            <div class="text-caption">Notified</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text class="text-center">
            <div class="text-h5 warning--text">{{ pendingCount }}</div>
            <div class="text-caption">Pending</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Books Table -->
    <v-card>
      <v-card-title>
        Cached Audiobooks
        <v-spacer></v-spacer>
        <v-chip>{{ filteredBooks.length }} of {{ totalBooks }} books</v-chip>
      </v-card-title>
      
      <v-data-table
        :headers="headers"
        :items="filteredBooks"
        :loading="loading"
        item-key="asin"
        :items-per-page="25"
        class="elevation-1"
      >
        <!-- Title column with book info -->
        <template #[`item.title`]="{ item }">
          <div>
            <div class="font-weight-medium">{{ item.title }}</div>
            <div class="text-caption text-grey">{{ item.asin }}</div>
          </div>
        </template>

        <!-- Author column -->
        <template #[`item.author`]="{ item }">
          <div>
            <div>{{ item.author }}</div>
            <div v-if="item.narrator" class="text-caption text-grey">
              Narrator: {{ item.narrator }}
            </div>
          </div>
        </template>

        <!-- Series column -->
        <template #[`item.series`]="{ item }">
          <div v-if="item.series">
            <div>{{ item.series }}</div>
            <div v-if="item.series_number" class="text-caption">
              #{{ item.series_number }}
            </div>
          </div>
          <span v-else class="text-grey">—</span>
        </template>

        <!-- Release Date column -->
        <template #[`item.release_date`]="{ item }">
          <div>
            <div>{{ formatDate(item.release_date) }}</div>
            <v-chip
              :color="isUpcoming(item.release_date) ? 'success' : 'grey'"
              size="small"
            >
              {{ isUpcoming(item.release_date) ? 'Upcoming' : 'Released' }}
            </v-chip>
          </div>
        </template>

        <!-- Notification Status column -->
        <template #[`item.notified_channels`]="{ item }">
          <div>
            <v-chip-group v-if="Object.keys(item.notified_channels || {}).length > 0">
              <v-chip
                v-for="(notified, channel) in item.notified_channels"
                :key="channel"
                :color="notified ? 'success' : 'warning'"
                size="small"
              >
                {{ channel }}
              </v-chip>
            </v-chip-group>
            <v-chip v-else color="warning" size="small">
              Not Notified
            </v-chip>
          </div>
        </template>

        <!-- Actions column -->
        <template #[`item.actions`]="{ item }">
          <v-menu>
            <template #activator="{ props }">
              <v-btn icon="mdi-dots-vertical" v-bind="props" size="small"></v-btn>
            </template>
            <v-list>
              <v-list-item @click="viewDetails(item)">
                <v-list-item-title>View Details</v-list-item-title>
              </v-list-item>
              <v-list-item @click="markAsNotified(item)" :disabled="Object.keys(item.notified_channels || {}).length > 0">
                <v-list-item-title>Mark as Notified</v-list-item-title>
              </v-list-item>
              <v-list-item @click="removeFromDatabase(item)" class="text-error">
                <v-list-item-title>Remove</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </template>
      </v-data-table>
    </v-card>

    <!-- Book Details Dialog -->
    <v-dialog v-model="detailsDialog" max-width="800px">
      <v-card v-if="selectedBook">
        <v-card-title>
          Book Details
          <v-spacer></v-spacer>
          <v-btn icon="mdi-close" @click="detailsDialog = false"></v-btn>
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12">
              <h3>{{ selectedBook.title }}</h3>
              <p class="text-subtitle-1">by {{ selectedBook.author }}</p>
            </v-col>
            <v-col cols="12" md="6">
              <v-list density="compact">
                <v-list-item>
                  <v-list-item-title>ASIN</v-list-item-title>
                  <v-list-item-subtitle>{{ selectedBook.asin }}</v-list-item-subtitle>
                </v-list-item>
                <v-list-item v-if="selectedBook.series">
                  <v-list-item-title>Series</v-list-item-title>
                  <v-list-item-subtitle>
                    {{ selectedBook.series }}
                    <span v-if="selectedBook.series_number">#{{ selectedBook.series_number }}</span>
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item v-if="selectedBook.publisher">
                  <v-list-item-title>Publisher</v-list-item-title>
                  <v-list-item-subtitle>{{ selectedBook.publisher }}</v-list-item-subtitle>
                </v-list-item>
                <v-list-item v-if="selectedBook.narrator">
                  <v-list-item-title>Narrator</v-list-item-title>
                  <v-list-item-subtitle>{{ selectedBook.narrator }}</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-col>
            <v-col cols="12" md="6">
              <v-list density="compact">
                <v-list-item>
                  <v-list-item-title>Release Date</v-list-item-title>
                  <v-list-item-subtitle>{{ formatDate(selectedBook.release_date) }}</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Last Checked</v-list-item-title>
                  <v-list-item-subtitle>{{ formatDate(selectedBook.last_checked) }}</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Notification Status</v-list-item-title>
                  <v-list-item-subtitle>
                    <v-chip-group v-if="Object.keys(selectedBook.notified_channels || {}).length > 0">
                      <v-chip
                        v-for="(notified, channel) in selectedBook.notified_channels"
                        :key="channel"
                        :color="notified ? 'success' : 'warning'"
                        size="small"
                      >
                        {{ channel }}: {{ notified ? 'Sent' : 'Pending' }}
                      </v-chip>
                    </v-chip-group>
                    <span v-else>No notifications sent</span>
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="detailsDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'DatabaseView',
  data() {
    return {
      books: [],
      filteredBooks: [],
      loading: false,
      selectedFilter: 'all',
      searchQuery: '',
      totalBooks: 0,
      detailsDialog: false,
      selectedBook: null,
      filterOptions: [
        { title: 'All Books', value: 'all' },
        { title: 'Upcoming Releases', value: 'upcoming' },
        { title: 'Notified', value: 'notified' },
        { title: 'Not Notified', value: 'unnotified' }
      ],
      headers: [
        { title: 'Title', value: 'title', sortable: true },
        { title: 'Author', value: 'author', sortable: true },
        { title: 'Series', value: 'series', sortable: true },
        { title: 'Release Date', value: 'release_date', sortable: true },
        { title: 'Notification Status', value: 'notified_channels', sortable: false },
        { title: 'Actions', value: 'actions', sortable: false, width: '100px' }
      ]
    };
  },
  computed: {
    upcomingCount() {
      return this.books.filter(book => this.isUpcoming(book.release_date)).length;
    },
    notifiedCount() {
      return this.books.filter(book => Object.keys(book.notified_channels || {}).length > 0).length;
    },
    pendingCount() {
      return this.books.filter(book => Object.keys(book.notified_channels || {}).length === 0).length;
    }
  },
  async mounted() {
    await this.loadBooks();
  },
  methods: {
    async loadBooks() {
      this.loading = true;
      try {
        const response = await axios.get(`http://localhost:5005/api/database?filter=${this.selectedFilter}&limit=1000`);
        this.books = response.data.books || [];
        this.totalBooks = response.data.total || 0;
        this.filterBooks();
      } catch (error) {
        console.error('Error loading books:', error);
        this.books = [];
        this.totalBooks = 0;
      } finally {
        this.loading = false;
      }
    },
    
    filterBooks() {
      if (!this.searchQuery) {
        this.filteredBooks = this.books;
        return;
      }
      
      const query = this.searchQuery.toLowerCase();
      this.filteredBooks = this.books.filter(book => 
        book.title.toLowerCase().includes(query) ||
        book.author.toLowerCase().includes(query) ||
        (book.series && book.series.toLowerCase().includes(query)) ||
        (book.narrator && book.narrator.toLowerCase().includes(query))
      );
    },
    
    debouncedSearch() {
      clearTimeout(this.searchTimeout);
      this.searchTimeout = setTimeout(() => {
        this.filterBooks();
      }, 300);
    },
    
    viewDetails(book) {
      this.selectedBook = book;
      this.detailsDialog = true;
    },
    
    async markAsNotified(book) {
      // This would typically update the database
      console.log('Mark as notified:', book.asin);
      // For now, just refresh the data
      await this.loadBooks();
    },
    
    async removeFromDatabase(book) {
      if (confirm(`Are you sure you want to remove "${book.title}" from the database?`)) {
        console.log('Remove from database:', book.asin);
        // For now, just refresh the data
        await this.loadBooks();
      }
    },
    
    formatDate(dateString) {
      if (!dateString) return 'Unknown';
      const date = new Date(dateString);
      return new Intl.DateTimeFormat('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
      }).format(date);
    },
    
    isUpcoming(dateString) {
      if (!dateString) return false;
      const releaseDate = new Date(dateString);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      return releaseDate >= today;
    }
  }
};
</script>

<style scoped>
.database-view {
  max-width: 1400px;
  margin: 0 auto;
}
</style>
