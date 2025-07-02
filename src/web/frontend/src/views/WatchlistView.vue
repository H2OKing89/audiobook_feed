<template>
  <v-container>
    <h1>Watchlist</h1>

    <v-row>
      <v-col>
        <v-card>
          <v-card-title>
            <div class="d-flex align-center justify-space-between w-100">
              <span>Authors</span>
              <v-btn color="primary" @click="openAddAuthorDialog">Add Author</v-btn>
            </div>
          </v-card-title>
          <v-card-text>
            <v-list v-if="watchlist.length > 0">
              <v-list-item v-for="author in watchlist" :key="author.name">
                <template v-slot:prepend>
                  <v-icon>mdi-account</v-icon>
                </template>
                <v-list-item-title>{{ author.name }}</v-list-item-title>
                <v-list-item-subtitle v-if="author.criteria && author.criteria.length > 0">
                  Watching {{ author.criteria.length }} series/titles
                </v-list-item-subtitle>
                <template v-slot:append>
                  <v-btn icon="mdi-pencil" variant="text" size="small" 
                         @click="editAuthor(author)" />
                  <v-btn icon="mdi-delete" variant="text" size="small" color="error" 
                         @click="confirmDeleteAuthor(author)" />
                </template>
              </v-list-item>
            </v-list>
            <div v-else class="text-center pa-4">
              <v-icon size="large" color="grey">mdi-playlist-remove</v-icon>
              <p class="text-grey mt-2">No authors in watchlist</p>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Add/Edit Author Dialog -->
    <v-dialog v-model="authorDialog" max-width="600">
      <v-card>
        <v-card-title>
          {{ editingAuthor ? 'Edit Author' : 'Add Author' }}
        </v-card-title>
        <v-card-text>
          <v-form ref="authorForm" v-model="authorFormValid">
            <v-text-field
              v-model="authorForm.name"
              label="Author Name"
              required
              :rules="[(v) => !!v || 'Name is required']"
            />

            <div class="mt-4 mb-2">
              <div class="d-flex align-center justify-space-between">
                <h3>Titles/Series to Track</h3>
                <v-btn size="small" @click="addNewCriteria">
                  <v-icon>mdi-plus</v-icon> Add
                </v-btn>
              </div>
            </div>

            <v-card variant="outlined" class="mb-3" v-for="(criteria, idx) in authorForm.criteria" :key="idx">
              <v-card-text>
                <v-row>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model="criteria.title"
                      label="Title"
                      hint="Book title or partial match"
                    />
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model="criteria.series"
                      label="Series"
                      hint="Series name"
                    />
                  </v-col>
                </v-row>
                <v-row>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model="criteria.publisher"
                      label="Publisher"
                      hint="Optional publisher filter"
                    />
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model="criteria.narrator"
                      label="Narrator"
                      hint="Optional narrator filter"
                    />
                  </v-col>
                </v-row>
              </v-card-text>
              <v-card-actions>
                <v-spacer />
                <v-btn color="error" variant="text" size="small" @click="removeCriteria(idx)">
                  <v-icon>mdi-delete</v-icon> Remove
                </v-btn>
              </v-card-actions>
            </v-card>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" variant="text" @click="saveAuthor">Save</v-btn>
          <v-btn color="grey" variant="text" @click="authorDialog = false">Cancel</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title>Delete Author</v-card-title>
        <v-card-text>
          Are you sure you want to delete "{{ authorToDelete ? authorToDelete.name : '' }}" from your watchlist?
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" variant="text" @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" variant="text" @click="deleteAuthor">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Duplicate Author Dialog -->
    <v-dialog v-model="duplicateDialog" max-width="500">
      <v-card>
        <v-card-title>Author Already Exists</v-card-title>
        <v-card-text>
          <p>This author is already in your watchlist. Would you like to update their criteria instead?</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="grey" variant="text" @click="duplicateDialog = false">Cancel</v-btn>
          <v-btn color="primary" variant="text" @click="updateExistingAuthor">
            Update Existing
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script>
import axios from 'axios';

export default {
  name: 'WatchlistView',
  data() {
    return {
      watchlist: [],
      isLoading: false,
      authorDialog: false,
      deleteDialog: false,
      duplicateDialog: false,
      authorFormValid: false,
      authorForm: {
        name: '',
        criteria: []
      },
      editingAuthor: null,
      authorToDelete: null,
      duplicateAuthorIdx: -1
    };
  },
  mounted() {
    this.fetchWatchlist();
  },
  methods: {
    async fetchWatchlist() {
      this.isLoading = true;
      try {
        const response = await axios.get('/api/watchlist');
        this.watchlist = response.data;
      } catch (error) {
        console.error('Failed to fetch watchlist:', error);
      } finally {
        this.isLoading = false;
      }
    },
    openAddAuthorDialog() {
      this.editingAuthor = null;
      this.authorForm = {
        name: '',
        criteria: [{ title: '', series: '', publisher: '', narrator: '' }]
      };
      this.authorDialog = true;
    },
    editAuthor(author) {
      this.editingAuthor = author;
      this.authorForm = JSON.parse(JSON.stringify(author)); // Deep clone
      
      // Ensure at least one criteria
      if (!this.authorForm.criteria || this.authorForm.criteria.length === 0) {
        this.authorForm.criteria = [{ title: '', series: '', publisher: '', narrator: '' }];
      }
      
      this.authorDialog = true;
    },
    addNewCriteria() {
      this.authorForm.criteria.push({
        title: '',
        series: '',
        publisher: '',
        narrator: ''
      });
    },
    removeCriteria(index) {
      this.authorForm.criteria.splice(index, 1);
      
      // Make sure we have at least one criteria
      if (this.authorForm.criteria.length === 0) {
        this.addNewCriteria();
      }
    },
    async saveAuthor() {
      if (!this.$refs.authorForm.validate()) return;

      // Filter out empty criteria
      const formData = {
        ...this.authorForm,
        criteria: this.authorForm.criteria.filter(c => 
          c.title || c.series || c.publisher || c.narrator
        )
      };
      
      // Check for duplicates if adding a new author
      if (!this.editingAuthor) {
        const duplicateIdx = this.watchlist.findIndex(a => 
          a.name.toLowerCase() === formData.name.toLowerCase()
        );
        
        if (duplicateIdx >= 0) {
          this.duplicateAuthorIdx = duplicateIdx;
          this.duplicateDialog = true;
          this.authorDialog = false;
          return;
        }
      }

      try {
        if (this.editingAuthor) {
          await axios.put(`/api/watchlist/${encodeURIComponent(this.editingAuthor.name)}`, formData);
        } else {
          await axios.post('/api/watchlist', formData);
        }
        
        this.authorDialog = false;
        this.fetchWatchlist();
      } catch (error) {
        console.error('Failed to save author:', error);
      }
    },
    confirmDeleteAuthor(author) {
      this.authorToDelete = author;
      this.deleteDialog = true;
    },
    async deleteAuthor() {
      if (!this.authorToDelete) return;
      
      try {
        await axios.delete(`/api/watchlist/${encodeURIComponent(this.authorToDelete.name)}`);
        this.deleteDialog = false;
        this.fetchWatchlist();
      } catch (error) {
        console.error('Failed to delete author:', error);
      }
    },
    async updateExistingAuthor() {
      if (this.duplicateAuthorIdx < 0) return;
      
      const existingAuthor = this.watchlist[this.duplicateAuthorIdx];
      
      try {
        await axios.put(
          `/api/watchlist/${encodeURIComponent(existingAuthor.name)}`, 
          this.authorForm
        );
        
        this.duplicateDialog = false;
        this.fetchWatchlist();
      } catch (error) {
        console.error('Failed to update existing author:', error);
      }
    }
  }
};
</script>
