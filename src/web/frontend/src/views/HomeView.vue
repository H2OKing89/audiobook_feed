<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <h1>Welcome to AudioStacker</h1>
        <p>Manage your audiobook watchlist and track upcoming releases.</p>
      </v-col>
    </v-row>
    
    <v-row>
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-playlist-check</v-icon>
            Watchlist
          </v-card-title>
          <v-card-text>
            Manage authors and series you want to track for new releases.
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" to="/watchlist">Manage Watchlist</v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
      
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-view-dashboard</v-icon>
            Dashboard
          </v-card-title>
          <v-card-text>
            View upcoming releases and system status.
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" to="/dashboard">View Dashboard</v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
      
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-database</v-icon>
            Database
          </v-card-title>
          <v-card-text>
            Browse tracked audiobooks and release information.
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" to="/database">Browse Database</v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
export default {
  name: 'HomeView'
};
</script>
