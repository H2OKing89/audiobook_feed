<template>
  <div class="watchlist-page">
    <h1 class="text-h4 mb-6">Watchlist Management</h1>
    
    <!-- Controls -->
    <div class="controls mb-4">
      <v-row>
        <v-col cols="12" sm="6" md="8">
          <v-text-field
            v-model="searchQuery"
            prepend-inner-icon="mdi-magnify"
            label="Search authors or criteria"
            hide-details
            variant="outlined"
            density="compact"
          ></v-text-field>
        </v-col>
        <v-col cols="12" sm="6" md="4" class="d-flex justify-end">
          <v-btn 
            color="primary" 
            prepend-icon="mdi-plus"
            @click="openAddDialog"
          >
            Add Author
          </v-btn>
        </v-col>
      </v-row>
    </div>
    
    <!-- Loading state -->
    <v-skeleton-loader v-if="loading" type="table" class="mt-4"></v-skeleton-loader>

    <!-- Empty state -->
    <v-card v-else-if="!watchlist || !watchlist.audiobooks || !watchlist.audiobooks.author || Object.keys(watchlist.audiobooks.author).length === 0">
      <v-card-text class="text-center py-8">
        <v-icon size="64" class="mb-4">mdi-playlist-plus</v-icon>
        <h3 class="text-h5 mb-2">No authors in your watchlist</h3>
        <p class="text-body-2 mb-4">Add authors to start tracking new audiobook releases</p>
        <v-btn color="primary" @click="openAddDialog">Add Your First Author</v-btn>
      </v-card-text>
    </v-card>
    
    <!-- Watchlist data -->
    <v-card v-else>
      <v-data-table
        :headers="headers"
        :items="watchlistItems"
        :search="searchQuery"
        class="watchlist-table"
      >
        <!-- Author name column -->
        <template #[`item.author`]="{ item }">
          <div class="font-weight-bold">{{ item.author }}</div>
        </template>
        
        <!-- Criteria column -->
        <template #[`item.criteria`]="{ item }">
          <div v-if="Object.keys(item.criteria).length === 0" class="text-caption text-medium-emphasis">
            No specific criteria - tracking all releases
          </div>
          <div v-else>
            <div v-for="(value, key) in item.criteria" :key="key" class="criteria-item">
              <v-chip size="small" class="mr-1">{{ key }}</v-chip>
              {{ Array.isArray(value) ? value.join(', ') : value }}
            </div>
          </div>
        </template>
        
        <!-- Actions column -->
        <template #[`item.actions`]="{ item }">
          <v-btn icon size="small" color="primary" @click="editAuthor(item)">
            <v-icon>mdi-pencil</v-icon>
          </v-btn>
          <v-btn icon size="small" color="error" class="ml-2" @click="confirmDelete(item)">
            <v-icon>mdi-delete</v-icon>
          </v-btn>
        </template>
      </v-data-table>
    </v-card>
    
    <!-- Add/Edit Dialog -->
    <v-dialog v-model="authorDialog" max-width="500px">
      <v-card>
        <v-card-title>
          <span>{{ isEditing ? 'Edit Author' : 'Add Author' }}</span>
        </v-card-title>
        
        <v-card-text>
          <v-form ref="form" v-model="valid">
            <v-text-field
              v-model="editedItem.author"
              label="Author Name"
              :rules="authorRules"
              required
              :disabled="isEditing"
            ></v-text-field>
            
            <p class="text-subtitle-2 mt-4">Criteria</p>
            
            <div v-for="(criteria, index) in editedCriteria" :key="index" class="d-flex align-center mb-2">
              <v-select
                v-model="criteria.key"
                label="Criteria Type"
                :items="criteriaTypes"
                style="min-width: 120px;"
                class="mr-2"
              ></v-select>
              
              <v-text-field
                v-model="criteria.value"
                :label="getCriteriaLabel(criteria.key)"
                class="flex-grow-1"
              ></v-text-field>
              
              <v-btn icon size="small" class="ml-2" @click="removeCriteria(index)" color="error">
                <v-icon>mdi-delete</v-icon>
              </v-btn>
            </div>
            
            <v-btn
              prepend-icon="mdi-plus"
              variant="text"
              class="mt-2"
              @click="addCriteria"
              color="primary"
              size="small"
            >
              Add Criteria
            </v-btn>
          </v-form>
        </v-card-text>
        
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="error" variant="text" @click="closeDialog">Cancel</v-btn>
          <v-btn color="primary" @click="saveAuthor" :disabled="!valid">Save</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="400px">
      <v-card>
        <v-card-title class="text-h5">Delete Author</v-card-title>
        <v-card-text>
          Are you sure you want to remove <strong>{{ deleteItem.author }}</strong> from your watchlist?
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" variant="text" @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" @click="deleteAuthor">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- Duplicate Author Dialog -->
    <v-dialog v-model="duplicateDialog" max-width="600px">
      <v-card>
        <v-card-title class="text-h5 d-flex align-center">
          <v-icon color="warning" class="mr-2">mdi-alert</v-icon>
          Author Already Exists
        </v-card-title>
        <v-card-text>
          <p class="mb-3">
            <strong>{{ duplicateAuthorName }}</strong> is already in your watchlist.
          </p>
          
          <div v-if="existingCriteria && Object.keys(existingCriteria).length > 0">
            <p class="text-subtitle-2 mb-2">Current criteria:</p>
            <div class="mb-3">
              <div v-for="(values, type) in existingCriteria" :key="type" class="mb-1">
                <v-chip size="small" class="mr-2">{{ type }}</v-chip>
                <span class="text-body-2">{{ Array.isArray(values) ? values.join(', ') : values }}</span>
              </div>
            </div>
          </div>
          <div v-else>
            <p class="text-body-2 mb-3">Currently tracking all releases (no specific criteria)</p>
          </div>
          
          <p class="text-body-2">
            Would you like to update the existing entry instead?
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" variant="text" @click="duplicateDialog = false">Cancel</v-btn>
          <v-btn color="warning" @click="editExistingAuthor">Update Existing</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- Success/Error Snackbar -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000">
      {{ snackbar.text }}
      <template v-slot:actions>
        <v-btn variant="text" @click="snackbar.show = false">Close</v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script>
import apiService from '@/services/api';

export default {
  name: 'WatchlistView',
  data() {
    return {
      // Watchlist data
      watchlist: null,
      loading: false,
      
      // Table config
      searchQuery: '',
      headers: [
        { title: 'Author', key: 'author', sortable: true },
        { title: 'Criteria', key: 'criteria', sortable: false },
        { title: 'Actions', key: 'actions', sortable: false, align: 'end' }
      ],
      
      // Dialog states
      authorDialog: false,
      deleteDialog: false,
      duplicateDialog: false,
      isEditing: false,
      valid: true,
      
      // Form data
      editedItem: {
        author: '',
        criteria: {}
      },
      editedCriteria: [],
      deleteItem: {},
      
      // Duplicate author data
      duplicateAuthorName: '',
      existingCriteria: {},
      
      // Criteria types
      criteriaTypes: [
        { title: 'Series', value: 'series' },
        { title: 'Narrator', value: 'narrator' },
        { title: 'Include Keywords', value: 'include' },
        { title: 'Exclude Keywords', value: 'exclude' }
      ],
      
      // Form validation
      authorRules: [
        v => !!v || 'Author name is required',
        v => v.length >= 2 || 'Author name must be at least 2 characters'
      ],
      
      // Snackbar
      snackbar: {
        show: false,
        text: '',
        color: 'success'
      }
    };
  },
  
  computed: {
    watchlistItems() {
      if (!this.watchlist || !this.watchlist.audiobooks || !this.watchlist.audiobooks.author) {
        return [];
      }
      
      return Object.entries(this.watchlist.audiobooks.author).map(([author, criteria]) => {
        return {
          author,
          criteria: this.formatCriteria(criteria),
          raw_criteria: criteria
        };
      });
    }
  },
  
  async mounted() {
    await this.loadWatchlist();
  },
  
  methods: {
    async loadWatchlist() {
      this.loading = true;
      try {
        const response = await apiService.getWatchlist();
        this.watchlist = response.data;
      } catch (error) {
        console.error('Error loading watchlist:', error);
        this.showSnackbar('Failed to load watchlist', 'error');
        this.watchlist = null;
      } finally {
        this.loading = false;
      }
    },
    
    formatCriteria(criteria) {
      // Process criteria based on the structure in the watchlist
      const formatted = {};
      
      if (typeof criteria === 'object' && !Array.isArray(criteria)) {
        if (criteria.series) formatted.series = criteria.series;
        if (criteria.narrator) formatted.narrator = criteria.narrator;
        if (criteria.include) formatted.include = criteria.include;
        if (criteria.exclude) formatted.exclude = criteria.exclude;
      }
      
      return formatted;
    },
    
    getCriteriaLabel(criteriaType) {
      switch (criteriaType) {
        case 'series': return 'Series Name';
        case 'narrator': return 'Narrator Name';
        case 'include': return 'Include Keywords';
        case 'exclude': return 'Exclude Keywords';
        default: return 'Value';
      }
    },
    
    openAddDialog() {
      this.isEditing = false;
      this.editedItem = {
        author: '',
        criteria: {}
      };
      this.editedCriteria = [];
      this.authorDialog = true;
    },
    
    editAuthor(item) {
      this.isEditing = true;
      this.editedItem = {
        author: item.author,
        criteria: { ...item.raw_criteria }
      };
      
      // Convert criteria to array format for editing
      this.editedCriteria = [];
      Object.entries(item.criteria).forEach(([key, value]) => {
        if (Array.isArray(value)) {
          value.forEach(val => {
            this.editedCriteria.push({ key, value: val });
          });
        } else {
          this.editedCriteria.push({ key, value });
        }
      });
      
      // Ensure we have at least one criteria row
      if (this.editedCriteria.length === 0) {
        this.addCriteria();
      }
      
      this.authorDialog = true;
    },
    
    addCriteria() {
      this.editedCriteria.push({ key: 'series', value: '' });
    },
    
    removeCriteria(index) {
      this.editedCriteria.splice(index, 1);
    },
    
    closeDialog() {
      this.authorDialog = false;
      this.$nextTick(() => {
        this.editedItem = {
          author: '',
          criteria: {}
        };
        this.editedCriteria = [];
      });
    },
    
    async saveAuthor() {
      if (!this.$refs.form.validate()) return;
      
      // Convert editedCriteria array back to object format
      const criteria = {};
      this.editedCriteria.forEach(({ key, value }) => {
        if (!value.trim()) return; // Skip empty values
        
        if (!criteria[key]) {
          criteria[key] = [];
        }
        
        if (!criteria[key].includes(value)) {
          criteria[key].push(value);
        }
      });
      
      // Removing unused variable
      // const authorEntry = {
      //   [this.editedItem.author]: criteria
      // };
      
      try {
        if (this.isEditing) {
          // Update existing entry
          await apiService.updateWatchlist({
            author: this.editedItem.author,
            criteria
          });
          this.showSnackbar(`Updated ${this.editedItem.author} in watchlist`);
        } else {
          // Add new entry
          const response = await apiService.addToWatchlist({
            author: this.editedItem.author,
            criteria
          });
          
          // Check if the author already exists
          if (response.data.author_exists) {
            this.duplicateAuthorName = response.data.author_name;
            this.existingCriteria = response.data.existing_criteria;
            this.duplicateDialog = true;
            return; // Don't close the dialog or reload, let user decide
          }
          
          this.showSnackbar(`Added ${this.editedItem.author} to watchlist`);
        }
        
        // Reload the watchlist
        await this.loadWatchlist();
        this.closeDialog();
      } catch (error) {
        console.error('Error saving author:', error);
        this.showSnackbar(`Failed to save author: ${error.response?.data?.message || error.message}`, 'error');
      }
    },
    
    confirmDelete(item) {
      this.deleteItem = item;
      this.deleteDialog = true;
    },
    
    async deleteAuthor() {
      try {
        await apiService.removeFromWatchlist(this.deleteItem.author);
        this.showSnackbar(`Removed ${this.deleteItem.author} from watchlist`);
        await this.loadWatchlist();
        this.deleteDialog = false;
      } catch (error) {
        console.error('Error deleting author:', error);
        this.showSnackbar(`Failed to delete author: ${error.response?.data?.message || error.message}`, 'error');
      }
    },
    
    editExistingAuthor() {
      // Close the duplicate dialog
      this.duplicateDialog = false;
      
      // Find the existing author in the watchlist
      const existingAuthor = this.watchlistItems.find(item => 
        item.author === this.duplicateAuthorName
      );
      
      if (existingAuthor) {
        // Switch to edit mode with the existing author's data
        this.editAuthor(existingAuthor);
      } else {
        // Fallback: just close the add dialog and show a message
        this.closeDialog();
        this.showSnackbar(`Please find ${this.duplicateAuthorName} in the list and click Edit`, 'info');
      }
    },
    
    showSnackbar(text, color = 'success') {
      this.snackbar = {
        show: true,
        text,
        color
      };
    }
  }
};
</script>

<style scoped>
.watchlist-page {
  max-width: 1200px;
  margin: 0 auto;
}

.criteria-item {
  margin-bottom: 4px;
}
</style>
