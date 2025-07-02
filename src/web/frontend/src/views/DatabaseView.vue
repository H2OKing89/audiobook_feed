<template>
  <v-container>
    <h1>Database</h1>
    
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <span>Tracked Audiobooks</span>
            <v-spacer></v-spacer>
            <v-text-field
              v-model="search"
              append-icon="mdi-magnify"
              label="Search"
              single-line
              hide-details
              @input="searchBooks"
            ></v-text-field>
          </v-card-title>
          
          <v-card-text>
            <v-data-table
              :headers="headers"
              :items="books"
              :loading="isLoading"
              :search="search"
              item-key="asin"
            >
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import axios from 'axios';

export default {
  name: 'DatabaseView',
  data() {
    return {
      books: [],
      search: '',
      isLoading: false,
      headers: [
        { title: 'Title', key: 'title' },
        { title: 'Author', key: 'author' },
        { 
          title: 'Series', 
          key: 'series',
          value: item => {
            if (item.series) {
              return item.series + (item.series_number ? ` #${item.series_number}` : '');
            }
            return '-';
          }
        },
        { 
          title: 'Release Date', 
          key: 'release_date',
          value: item => this.formatDate(item.release_date)
        },
        { title: 'Publisher', key: 'publisher' }
      ]
    };
  },
  mounted() {
    this.fetchBooks();
  },
  methods: {
    async fetchBooks() {
      this.isLoading = true;
      try {
        const response = await axios.get('/api/database?limit=1000');
        this.books = response.data.books || [];
      } catch (error) {
        console.error('Failed to fetch books:', error);
      } finally {
        this.isLoading = false;
      }
    },
    searchBooks() {
      // Vuetify data table handles search automatically
    },
    formatDate(dateString) {
      if (!dateString) return '-';
      try {
        return new Date(dateString).toLocaleDateString();
      } catch {
        return dateString;
      }
    }
  }
};
</script>
