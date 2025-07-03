<template>
  <div class="dashboard">
    <h1 class="text-h4 mb-6">AudioStacker Dashboard</h1>
    
    <!-- System Status Card -->
    <v-row>
      <v-col cols="12" md="6">
        <v-card class="mb-4">
          <v-card-title>
            <v-icon class="mr-2">mdi-monitor-dashboard</v-icon>
            System Status
          </v-card-title>
          <v-card-text>
            <v-row v-if="systemStatus">
              <v-col cols="6">
                <div class="text-center">
                  <div class="text-h4 primary--text">{{ systemStatus.database.total_books }}</div>
                  <div class="text-caption">Total Books</div>
                </div>
              </v-col>
              <v-col cols="6">
                <div class="text-center">
                  <div class="text-h4 success--text">{{ systemStatus.database.upcoming_releases }}</div>
                  <div class="text-caption">Upcoming Releases</div>
                </div>
              </v-col>
              <v-col cols="12">
                <v-divider class="my-2"></v-divider>
                <div class="text-caption">
                  <strong>Last Check:</strong> 
                  {{ formatDate(systemStatus.database.last_check) }}
                </div>
                <div class="text-caption">
                  <strong>Database:</strong> 
                  <v-chip :color="systemStatus.system.database_exists ? 'success' : 'warning'" size="small">
                    {{ systemStatus.system.database_exists ? 'Connected' : 'Not Found' }}
                  </v-chip>
                </div>
              </v-col>
            </v-row>
            <v-skeleton-loader v-else type="article"></v-skeleton-loader>
          </v-card-text>
        </v-card>
      </v-col>
      
      <!-- Quick Actions Card -->
      <v-col cols="12" md="6">
        <v-card class="mb-4">
          <v-card-title>
            <v-icon class="mr-2">mdi-lightning-bolt</v-icon>
            Quick Actions
          </v-card-title>
          <v-card-text>
            <v-btn
              color="primary"
              block
              class="mb-2"
              @click="runAudioStacker(false)"
              :loading="runningAudioStacker"
            >
              <v-icon left>mdi-play</v-icon>
              Run AudioStacker Now
            </v-btn>
            
            <v-btn
              color="info"
              block
              class="mb-2"
              @click="runAudioStacker(true)"
              :loading="runningAudioStacker"
            >
              <v-icon left>mdi-eye</v-icon>
              Dry Run (Preview Only)
            </v-btn>
            
            <v-btn
              color="success"
              block
              @click="refreshStatus"
              :loading="loadingStatus"
            >
              <v-icon left>mdi-refresh</v-icon>
              Refresh Status
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Recent Discoveries -->
    <v-card class="mb-4">
      <v-card-title>
        <v-icon class="mr-2">mdi-new-box</v-icon>
        Recent Discoveries
        <v-spacer></v-spacer>
        <v-btn color="primary" variant="text" @click="$router.push('/database')">
          View All
        </v-btn>
      </v-card-title>
      <v-card-text>
        <div v-if="recentBooks.length === 0 && !loadingBooks" class="text-center text-grey">
          <v-icon size="64" class="mb-2">mdi-book-open-page-variant</v-icon>
          <div>No recent discoveries</div>
          <div class="text-caption">Run AudioStacker to find new releases</div>
        </div>
        
        <v-skeleton-loader v-if="loadingBooks" type="list-item@3"></v-skeleton-loader>
        
        <v-list v-if="recentBooks.length > 0">
          <v-list-item
            v-for="book in recentBooks.slice(0, 5)"
            :key="book.asin"
          >
            <template v-slot:prepend>
              <v-avatar color="primary">
                <v-icon>mdi-book</v-icon>
              </v-avatar>
            </template>
            
            <v-list-item-title>{{ book.title }}</v-list-item-title>
            <v-list-item-subtitle>
              by {{ book.author }}
              <span v-if="book.series"> • {{ book.series }}</span>
              <span v-if="book.release_date"> • {{ formatDate(book.release_date) }}</span>
            </v-list-item-subtitle>
            
            <template v-slot:append>
              <v-chip
                :color="Object.keys(book.notified_channels || {}).length > 0 ? 'success' : 'warning'"
                size="small"
              >
                {{ Object.keys(book.notified_channels || {}).length > 0 ? 'Notified' : 'Pending' }}
              </v-chip>
            </template>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>

    <!-- Watch-list Summary -->
    <v-card>
      <v-card-title>
        <v-icon class="mr-2">mdi-eye</v-icon>
        Watch-list Summary
        <v-spacer></v-spacer>
        <v-btn color="primary" variant="text" @click="$router.push('/watchlist')">
          Manage Watch-list
        </v-btn>
      </v-card-title>
      <v-card-text>
        <div v-if="!watchlist || !watchlist.audiobooks" class="text-center text-grey">
          <v-skeleton-loader v-if="loadingWatchlist" type="list-item@3"></v-skeleton-loader>
          <div v-else>
            <v-icon size="64" class="mb-2">mdi-account-multiple</v-icon>
            <div>No authors in watch-list</div>
            <div class="text-caption">Add authors to start tracking releases</div>
          </div>
        </div>
        
        <div v-else>
          <v-row>
            <v-col cols="12" md="4">
              <div class="text-center">
                <div class="text-h4 info--text">
                  {{ Object.keys(watchlist.audiobooks.author || {}).length }}
                </div>
                <div class="text-caption">Authors Tracked</div>
              </div>
            </v-col>
            <v-col cols="12" md="8">
              <div class="text-caption mb-2"><strong>Recent Authors:</strong></div>
              <v-chip-group>
                <v-chip
                  v-for="(criteria, author) in Object.entries(watchlist.audiobooks.author || {}).slice(0, 5)"
                  :key="author"
                  size="small"
                >
                  {{ author }}
                  <v-tooltip activator="parent" location="top">
                    {{ Array.isArray(criteria) ? criteria.length : Object.keys(criteria).length }} criteria
                  </v-tooltip>
                </v-chip>
                <v-chip v-if="Object.keys(watchlist.audiobooks.author || {}).length > 5" size="small" variant="outlined">
                  +{{ Object.keys(watchlist.audiobooks.author || {}).length - 5 }} more
                </v-chip>
              </v-chip-group>
            </v-col>
          </v-row>
        </div>
      </v-card-text>
    </v-card>

    <!-- Run Result Dialog -->
    <v-dialog v-model="runResultDialog" max-width="600px">
      <v-card>
        <v-card-title>
          <v-icon :color="runResult.error ? 'error' : 'success'" class="mr-2">
            {{ runResult.error ? 'mdi-alert-circle' : 'mdi-check-circle' }}
          </v-icon>
          AudioStacker Run {{ runResult.dry_run ? '(Dry Run)' : '' }}
        </v-card-title>
        <v-card-text>
          <div v-if="runResult.error" class="mb-4">
            <v-alert type="error" variant="tonal">
              <div class="font-weight-bold">Error:</div>
              <div>{{ runResult.error }}</div>
            </v-alert>
          </div>
          
          <div v-else>
            <v-alert type="success" variant="tonal" class="mb-4">
              Run completed successfully!
            </v-alert>
            
            <div v-if="runResult.dry_run && runResult.would_process_authors">
              <div class="font-weight-bold mb-2">Would process authors:</div>
              <v-chip-group>
                <v-chip v-for="author in runResult.would_process_authors" :key="author" size="small">
                  {{ author }}
                </v-chip>
              </v-chip-group>
            </div>
          </div>
          
          <v-divider class="my-4"></v-divider>
          
          <div class="text-caption">
            <div><strong>Start:</strong> {{ formatDate(runResult.start_time) }}</div>
            <div><strong>End:</strong> {{ formatDate(runResult.end_time) }}</div>
            <div><strong>Duration:</strong> {{ calculateDuration(runResult.start_time, runResult.end_time) }}</div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="runResultDialog = false">Close</v-btn>
          <v-btn color="primary" @click="refreshStatus">Refresh Status</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import apiService from '@/services/api';

export default {
  name: 'DashboardView',
  data() {
    return {
      systemStatus: null,
      recentBooks: [],
      watchlist: null,
      loadingStatus: false,
      loadingBooks: false,
      loadingWatchlist: false,
      runningAudioStacker: false,
      runResult: {},
      runResultDialog: false
    };
  },
  async mounted() {
    await this.loadDashboardData();
  },
  methods: {
    async loadDashboardData() {
      await Promise.all([
        this.loadSystemStatus(),
        this.loadRecentBooks(),
        this.loadWatchlist()
      ]);
    },
    
    async loadSystemStatus() {
      this.loadingStatus = true;
      try {
        const response = await apiService.getStatus();
        this.systemStatus = {
          system: response.data,
          database: {
            total_books: 0,
            upcoming_releases: 0,
            last_check: 'Never'
          }
        };
        
        // Load database info
        try {
          const dbResponse = await apiService.getDatabaseBooks();
          this.systemStatus.database = {
            total_books: dbResponse.data.total || 0,
            upcoming_releases: dbResponse.data.cache_info?.upcoming_releases || 0,
            last_check: dbResponse.data.cache_info?.last_updated || 'Never'
          };
        } catch (dbError) {
          console.warn('Could not load database info:', dbError);
        }
      } catch (error) {
        console.error('Error loading system status:', error);
      } finally {
        this.loadingStatus = false;
      }
    },
    
    async loadRecentBooks() {
      this.loadingBooks = true;
      try {
        const response = await apiService.getDatabaseBooks();
        this.recentBooks = response.data.books || [];
      } catch (error) {
        console.error('Error loading recent books:', error);
        this.recentBooks = [];
      } finally {
        this.loadingBooks = false;
      }
    },
    
    async loadWatchlist() {
      this.loadingWatchlist = true;
      try {
        const response = await apiService.getWatchlist();
        this.watchlist = response.data;
      } catch (error) {
        console.error('Error loading watchlist:', error);
        this.watchlist = null;
      } finally {
        this.loadingWatchlist = false;
      }
    },
    
    async refreshStatus() {
      await this.loadDashboardData();
    },
    
    async runAudioStacker(dryRun = false) {
      this.runningAudioStacker = true;
      try {
        const response = await apiService.runAudiostacker(dryRun);
        this.runResult = response.data;
        this.runResult.start_time = new Date().toISOString();
        this.runResult.end_time = new Date().toISOString();
        this.runResult.dry_run = dryRun;
        this.runResultDialog = true;
        
        // If successful, refresh the dashboard data
        if (!this.runResult.error && this.runResult.success) {
          setTimeout(() => {
            this.loadDashboardData();
          }, 1000);
        }
      } catch (error) {
        console.error('Error running AudioStacker:', error);
        this.runResult = {
          error: 'Failed to run AudioStacker',
          details: error.response?.data || error.message,
          start_time: new Date().toISOString(),
          end_time: new Date().toISOString(),
          dry_run: dryRun
        };
        this.runResultDialog = true;
      } finally {
        this.runningAudioStacker = false;
      }
    },
    
    formatDate(dateString) {
      if (!dateString || dateString === 'Never') return dateString;
      const date = new Date(dateString);
      return new Intl.DateTimeFormat('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      }).format(date);
    },
    
    calculateDuration(start, end) {
      if (!start || !end) return 'Unknown';
      const startTime = new Date(start);
      const endTime = new Date(end);
      const duration = Math.round((endTime - startTime) / 1000);
      return `${duration}s`;
    }
  }
};
</script>

<style scoped>
.dashboard {
  max-width: 1200px;
  margin: 0 auto;
}
</style>
