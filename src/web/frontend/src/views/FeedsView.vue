<template>
  <div class="feeds-view">
    <h1 class="text-h4 mb-6">My Audiobook Feeds</h1>
    
    <v-row>
      <v-col cols="12" md="8">
        <v-btn
          color="primary"
          class="mb-4"
          prepend-icon="mdi-plus"
          @click="createFeedDialog = true"
        >
          Create New Feed
        </v-btn>
        
        <!-- Feeds List -->
        <v-card v-if="feeds.length > 0">
          <v-list>
            <v-list-item
              v-for="(feed, index) in feeds"
              :key="index"
              :value="feed"
            >
              <template v-slot:prepend>
                <v-avatar color="grey-lighten-1">
                  <v-icon icon="mdi-rss"></v-icon>
                </v-avatar>
              </template>
              
              <v-list-item-title>{{ feed.name }}</v-list-item-title>
              <v-list-item-subtitle>
                {{ feed.description || 'No description' }}
              </v-list-item-subtitle>
              <v-list-item-subtitle>
                Contains: {{ formatFeedContent(feed) }}
              </v-list-item-subtitle>
              
              <template v-slot:append>
                <v-btn
                  icon
                  variant="text"
                  color="primary"
                  @click="editFeed(feed)"
                >
                  <v-icon>mdi-pencil</v-icon>
                </v-btn>
                <v-btn
                  icon
                  variant="text"
                  color="info"
                  @click="exportFeed(feed)"
                >
                  <v-icon>mdi-calendar-export</v-icon>
                </v-btn>
                <v-btn
                  icon
                  variant="text"
                  color="error"
                  @click="confirmDeleteFeed(feed)"
                >
                  <v-icon>mdi-delete</v-icon>
                </v-btn>
              </template>
            </v-list-item>
          </v-list>
        </v-card>
        
        <!-- No Feeds Message -->
        <v-alert
          v-else
          type="info"
          class="mt-4"
        >
          You don't have any feeds yet. Create one to get started!
        </v-alert>
      </v-col>
      
      <v-col cols="12" md="4">
        <v-card title="Feed Statistics">
          <v-card-text>
            <p>Total Feeds: {{ feeds.length }}</p>
            <p>Authors Tracked: {{ totalAuthors }}</p>
            <p>Series Tracked: {{ totalSeries }}</p>
            <p>Last Updated: {{ lastUpdated }}</p>
          </v-card-text>
          <v-card-actions>
            <v-btn
              color="primary"
              variant="text"
              @click="refreshFeeds"
              :loading="loading"
            >
              Refresh Feeds
            </v-btn>
          </v-card-actions>
        </v-card>
        
        <v-card title="Export Options" class="mt-4">
          <v-card-text>
            <p>Export all your feeds to calendar format or JSON.</p>
          </v-card-text>
          <v-card-actions>
            <v-btn
              color="primary"
              variant="text"
              @click="exportAllFeeds('ical')"
            >
              Export All (iCal)
            </v-btn>
            <v-btn
              color="primary"
              variant="text"
              @click="exportAllFeeds('json')"
            >
              Export All (JSON)
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
    
    <!-- Create/Edit Feed Dialog -->
    <v-dialog v-model="createFeedDialog" max-width="600px">
      <v-card>
        <v-card-title>{{ editingFeed ? 'Edit Feed' : 'Create New Feed' }}</v-card-title>
        
        <v-card-text>
          <v-form>
            <v-text-field
              v-model="feedForm.name"
              label="Feed Name"
              required
              outlined
            ></v-text-field>
            
            <v-textarea
              v-model="feedForm.description"
              label="Description (optional)"
              outlined
              rows="2"
            ></v-textarea>
            
            <v-file-input
              v-model="feedForm.coverImage"
              label="Cover Image (optional)"
              accept="image/*"
              outlined
              prepend-icon="mdi-camera"
            ></v-file-input>
            
            <div class="my-4">
              <h3 class="text-h6 mb-2">Feed Content</h3>
              
              <div v-if="feedForm.content.length > 0">
                <v-list>
                  <v-list-item
                    v-for="(item, i) in feedForm.content"
                    :key="i"
                  >
                    <v-list-item-title>
                      {{ item.name }}
                      <v-chip
                        size="small"
                        class="ml-2"
                        :color="getTypeColor(item.type)"
                      >
                        {{ item.type }}
                      </v-chip>
                    </v-list-item-title>
                    
                    <template v-slot:append>
                      <v-btn
                        icon
                        variant="text"
                        size="small"
                        color="error"
                        @click="removeContentItem(i)"
                      >
                        <v-icon>mdi-close</v-icon>
                      </v-btn>
                    </template>
                  </v-list-item>
                </v-list>
              </div>
              <div v-else>
                <p class="text-subtitle-2 text-grey">No content added yet</p>
              </div>
              
              <v-btn
                color="primary"
                class="mt-2"
                prepend-icon="mdi-plus"
                @click="addContentDialog = true"
              >
                Add Content
              </v-btn>
            </div>
          </v-form>
        </v-card-text>
        
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            color="primary"
            @click="saveFeed"
          >
            Save
          </v-btn>
          <v-btn
            color="grey darken-1"
            @click="createFeedDialog = false"
          >
            Cancel
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- Add Content Dialog -->
    <v-dialog v-model="addContentDialog" max-width="500px">
      <v-card>
        <v-card-title>Add Content to Feed</v-card-title>
        
        <v-card-text>
          <v-tabs v-model="contentTab">
            <v-tab value="author">Author</v-tab>
            <v-tab value="series">Series</v-tab>
            <v-tab value="book">Book</v-tab>
          </v-tabs>
          
          <v-window v-model="contentTab">
            <v-window-item value="author">
              <v-text-field
                v-model="contentForm.author"
                label="Author Name"
                class="mt-4"
                outlined
              ></v-text-field>
            </v-window-item>
            
            <v-window-item value="series">
              <v-text-field
                v-model="contentForm.series"
                label="Series Name"
                class="mt-4"
                outlined
              ></v-text-field>
              <v-text-field
                v-model="contentForm.seriesAuthor"
                label="Author (optional)"
                outlined
              ></v-text-field>
            </v-window-item>
            
            <v-window-item value="book">
              <v-text-field
                v-model="contentForm.bookTitle"
                label="Book Title"
                class="mt-4"
                outlined
              ></v-text-field>
              <v-text-field
                v-model="contentForm.bookAuthor"
                label="Author"
                outlined
              ></v-text-field>
            </v-window-item>
          </v-window>
        </v-card-text>
        
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            color="primary"
            @click="addContent"
          >
            Add
          </v-btn>
          <v-btn
            color="grey darken-1"
            @click="addContentDialog = false"
          >
            Cancel
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="400px">
      <v-card>
        <v-card-title>Delete Feed</v-card-title>
        
        <v-card-text>
          Are you sure you want to delete "{{ feedToDelete?.name }}"? This action cannot be undone.
        </v-card-text>
        
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            color="error"
            @click="deleteFeed"
          >
            Delete
          </v-btn>
          <v-btn
            color="grey darken-1"
            @click="deleteDialog = false"
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
  name: 'FeedsView',
  data() {
    return {
      feeds: [],
      loading: false,
      createFeedDialog: false,
      addContentDialog: false,
      deleteDialog: false,
      editingFeed: false,
      feedToDelete: null,
      contentTab: 'author',
      feedForm: {
        name: '',
        description: '',
        coverImage: null,
        content: []
      },
      contentForm: {
        author: '',
        series: '',
        seriesAuthor: '',
        bookTitle: '',
        bookAuthor: ''
      }
    };
  },
  async mounted() {
    await this.loadFeeds();
  },
  computed: {
    totalAuthors() {
      return this.feeds.reduce((count, feed) => {
        return count + feed.content.filter(item => item.type === 'author').length;
      }, 0);
    },
    totalSeries() {
      return this.feeds.reduce((count, feed) => {
        return count + feed.content.filter(item => item.type === 'series').length;
      }, 0);
    },
    lastUpdated() {
      return new Date().toLocaleDateString();
    }
  },
  methods: {
    async loadFeeds() {
      this.loading = true;
      try {
        const response = await axios.get('http://localhost:5005/api/feeds');
        this.feeds = response.data;
      } catch (error) {
        console.error('Error loading feeds:', error);
      } finally {
        this.loading = false;
      }
    },
    
    formatFeedContent(feed) {
      const authors = feed.content.filter(item => item.type === 'author').length;
      const series = feed.content.filter(item => item.type === 'series').length;
      const books = feed.content.filter(item => item.type === 'book').length;
      
      const parts = [];
      if (authors) parts.push(`${authors} author${authors > 1 ? 's' : ''}`);
      if (series) parts.push(`${series} series`);
      if (books) parts.push(`${books} book${books > 1 ? 's' : ''}`);
      
      return parts.join(', ') || 'Empty feed';
    },
    
    getTypeColor(type) {
      const colors = {
        author: 'blue',
        series: 'purple',
        book: 'green'
      };
      return colors[type] || 'grey';
    },
    
    refreshFeeds() {
      this.loadFeeds();
    },
    
    editFeed(feed) {
      this.editingFeed = true;
      this.feedForm = {
        id: feed.id,
        name: feed.name,
        description: feed.description || '',
        coverImage: null,
        content: [...feed.content]
      };
      this.createFeedDialog = true;
    },
    
    exportFeed(feed) {
      // In a real app, this would trigger a download
      console.log('Exporting feed:', feed);
      // this.$toast.info(`Exporting ${feed.name} to iCal format`);
    },
    
    exportAllFeeds(format) {
      console.log(`Exporting all feeds in ${format} format`);
      // this.$toast.info(`Exporting all feeds to ${format.toUpperCase()} format`);
    },
    
    confirmDeleteFeed(feed) {
      this.feedToDelete = feed;
      this.deleteDialog = true;
    },
    
    async deleteFeed() {
      try {
        await axios.delete(`http://localhost:5005/api/feeds/${this.feedToDelete.id}`);
        await this.loadFeeds(); // Reload feeds from backend
      } catch (error) {
        console.error('Error deleting feed:', error);
      }
      
      this.deleteDialog = false;
      this.feedToDelete = null;
    },
    
    async saveFeed() {
      if (!this.feedForm.name) {
        // this.$toast.error('Feed name is required');
        return;
      }
      
      try {
        if (this.editingFeed) {
          // Update existing feed
          await axios.post('http://localhost:5005/api/feeds', {
            id: this.feedForm.id,
            name: this.feedForm.name,
            description: this.feedForm.description,
            content: this.feedForm.content
          });
        } else {
          // Create new feed
          await axios.post('http://localhost:5005/api/feeds', {
            name: this.feedForm.name,
            description: this.feedForm.description,
            content: this.feedForm.content
          });
        }
        
        // Reload feeds from backend
        await this.loadFeeds();
        
        // Reset form and close dialog
        this.resetFeedForm();
        this.createFeedDialog = false;
        this.editingFeed = false;
      } catch (error) {
        console.error('Error saving feed:', error);
      }
    },
    
    resetFeedForm() {
      this.feedForm = {
        name: '',
        description: '',
        coverImage: null,
        content: []
      };
    },
    
    addContent() {
      let contentItem = null;
      
      if (this.contentTab === 'author' && this.contentForm.author) {
        contentItem = {
          type: 'author',
          name: this.contentForm.author
        };
      } else if (this.contentTab === 'series' && this.contentForm.series) {
        contentItem = {
          type: 'series',
          name: this.contentForm.series
        };
        
        if (this.contentForm.seriesAuthor) {
          contentItem.author = this.contentForm.seriesAuthor;
        }
      } else if (this.contentTab === 'book' && this.contentForm.bookTitle) {
        contentItem = {
          type: 'book',
          name: this.contentForm.bookTitle
        };
        
        if (this.contentForm.bookAuthor) {
          contentItem.author = this.contentForm.bookAuthor;
        }
      } else {
        // this.$toast.error('Please fill in the required fields');
        return;
      }
      
      if (contentItem) {
        this.feedForm.content.push(contentItem);
        this.resetContentForm();
        this.addContentDialog = false;
      }
    },
    
    resetContentForm() {
      this.contentForm = {
        author: '',
        series: '',
        seriesAuthor: '',
        bookTitle: '',
        bookAuthor: ''
      };
    },
    
    removeContentItem(index) {
      this.feedForm.content.splice(index, 1);
    }
  }
};
</script>
