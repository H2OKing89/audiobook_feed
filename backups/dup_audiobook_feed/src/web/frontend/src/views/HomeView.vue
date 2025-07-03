<template>
  <div class="home">
    <v-row>
      <v-col cols="12" class="text-center">
        <h1 class="text-h3 mb-5">Welcome to Audiobook Feed Generator</h1>
        <p class="text-body-1 mb-10">
          Track and manage your favorite audiobooks all in one place. Create custom feeds based on 
          authors, series, or individual books.
        </p>
      </v-col>
    </v-row>
    
    <v-row>
      <v-col cols="12" md="4">
        <v-card class="mx-auto" max-width="400">
          <v-card-title>
            <v-icon left size="large" class="mr-2">mdi-magnify</v-icon>
            Search
          </v-card-title>
          <v-card-text>
            Search for your favorite authors, series, or books and add them to your feeds.
          </v-card-text>
          <v-card-actions>
            <v-btn to="/search" color="primary" variant="text">
              Start Searching
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
      
      <v-col cols="12" md="4">
        <v-card class="mx-auto" max-width="400">
          <v-card-title>
            <v-icon left size="large" class="mr-2">mdi-rss</v-icon>
            Manage Feeds
          </v-card-title>
          <v-card-text>
            View and manage your existing feeds. Edit preferences and export to calendar.
          </v-card-text>
          <v-card-actions>
            <v-btn to="/feeds" color="primary" variant="text">
              My Feeds
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
      
      <v-col cols="12" md="4">
        <v-card class="mx-auto" max-width="400">
          <v-card-title>
            <v-icon left size="large" class="mr-2">mdi-cog</v-icon>
            Settings
          </v-card-title>
          <v-card-text>
            Configure notification preferences, API keys, and other application settings.
          </v-card-text>
          <v-card-actions>
            <v-btn to="/settings" color="primary" variant="text">
              Configure
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script>
export default {
  name: 'HomeView'
}
</script>
