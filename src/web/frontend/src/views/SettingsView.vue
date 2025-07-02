<template>
  <v-container>
    <h1>Settings</h1>
    
    <v-row>
      <v-col cols="12" md="8">
        <v-card>
          <v-card-title>Application Settings</v-card-title>
          <v-card-text>
            <v-form>
              <v-text-field
                label="API Rate Limit (calls per minute)"
                type="number"
                v-model="settings.rateLimit"
                hint="Number of Audible API calls allowed per minute"
              ></v-text-field>
              
              <v-select
                label="Language Filter"
                v-model="settings.language"
                :items="languageOptions"
                hint="Filter audiobooks by language"
              ></v-select>
              
              <v-text-field
                label="Cleanup Grace Period (days)"
                type="number"
                v-model="settings.cleanupGracePeriod"
                hint="Days to keep audiobooks after release date"
              ></v-text-field>
            </v-form>
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" @click="saveSettings">
              Save Settings
            </v-btn>
            <v-btn color="grey" @click="resetSettings">
              Reset to Defaults
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
      
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>Database Actions</v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item>
                <v-btn color="primary" block @click="runMaintenance">
                  <v-icon left>mdi-database-refresh</v-icon>
                  Run Maintenance
                </v-btn>
              </v-list-item>
              <v-list-item>
                <v-btn color="warning" block @click="pruneDatabase">
                  <v-icon left>mdi-delete-sweep</v-icon>
                  Prune Released Books
                </v-btn>
              </v-list-item>
              <v-list-item>
                <v-btn color="info" block @click="exportData">
                  <v-icon left>mdi-export</v-icon>
                  Export Data
                </v-btn>
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
  name: 'SettingsView',
  data() {
    return {
      settings: {
        rateLimit: 10,
        language: 'english',
        cleanupGracePeriod: 0
      },
      languageOptions: [
        { title: 'English', value: 'english' },
        { title: 'Spanish', value: 'spanish' },
        { title: 'French', value: 'french' },
        { title: 'German', value: 'german' }
      ]
    };
  },
  mounted() {
    this.loadSettings();
  },
  methods: {
    loadSettings() {
      // Load settings from localStorage or API
      const saved = localStorage.getItem('audiostacker-settings');
      if (saved) {
        this.settings = { ...this.settings, ...JSON.parse(saved) };
      }
    },
    saveSettings() {
      localStorage.setItem('audiostacker-settings', JSON.stringify(this.settings));
      console.log('Settings saved:', this.settings);
    },
    resetSettings() {
      this.settings = {
        rateLimit: 10,
        language: 'english',
        cleanupGracePeriod: 0
      };
    },
    async runMaintenance() {
      try {
        const response = await axios.post('/api/maintenance');
        console.log('Maintenance completed:', response.data);
      } catch (error) {
        console.error('Maintenance failed:', error);
      }
    },
    async pruneDatabase() {
      try {
        const response = await axios.post('/api/prune');
        console.log('Database pruned:', response.data);
      } catch (error) {
        console.error('Prune failed:', error);
      }
    },
    async exportData() {
      try {
        const response = await axios.get('/api/export');
        // Handle file download
        console.log('Data exported:', response.data);
      } catch (error) {
        console.error('Export failed:', error);
      }
    }
  }
};
</script>
