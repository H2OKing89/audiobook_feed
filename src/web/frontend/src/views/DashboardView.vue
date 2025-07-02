<template>
  <v-container>
    <h1>Dashboard</h1>
    
    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-clock-outline</v-icon>
            Upcoming Releases
          </v-card-title>
          <v-card-text>
            <div v-if="upcomingReleases.length > 0">
              <v-list>
                <v-list-item v-for="book in upcomingReleases" :key="book.asin">
                  <v-list-item-title>{{ book.title }}</v-list-item-title>
                  <v-list-item-subtitle>{{ book.author }} - {{ book.release_date }}</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </div>
            <div v-else class="text-center pa-4">
              <v-icon size="large" color="grey">mdi-calendar-blank</v-icon>
              <p class="text-grey mt-2">No upcoming releases</p>
            </div>
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" @click="runAudioStacker">
              <v-icon left>mdi-play</v-icon>
              Check for Updates
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
      
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-chart-line</v-icon>
            System Status
          </v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item>
                <v-list-item-title>Last Check</v-list-item-title>
                <v-list-item-subtitle>{{ lastCheck || 'Never' }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Total Books Tracked</v-list-item-title>
                <v-list-item-subtitle>{{ totalBooks }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Watchlist Authors</v-list-item-title>
                <v-list-item-subtitle>{{ watchlistCount }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import axios from 'axios';

export default {
  name: 'DashboardView',
  data() {
    return {
      upcomingReleases: [],
      lastCheck: null,
      totalBooks: 0,
      watchlistCount: 0,
      isLoading: false
    };
  },
  mounted() {
    this.fetchDashboardData();
  },
  methods: {
    async fetchDashboardData() {
      this.isLoading = true;
      try {
        // Fetch upcoming releases
        const dbResponse = await axios.get('/api/database?filter=upcoming&limit=10');
        this.upcomingReleases = dbResponse.data.books || [];
        this.totalBooks = dbResponse.data.total || 0;

        // Fetch watchlist count
        const watchlistResponse = await axios.get('/api/watchlist');
        this.watchlistCount = watchlistResponse.data.length || 0;
        
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        this.isLoading = false;
      }
    },
    async runAudioStacker() {
      this.isLoading = true;
      try {
        const response = await axios.post('/api/run');
        console.log('AudioStacker run result:', response.data);
        // Refresh data after run
        this.fetchDashboardData();
      } catch (error) {
        console.error('Failed to run AudioStacker:', error);
      } finally {
        this.isLoading = false;
      }
    }
  }
};
</script>
