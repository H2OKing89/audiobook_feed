<template>
  <v-container>
    <h1>Search</h1>
    
    <v-row>
      <v-col cols="12">
        <v-alert
          type="info"
          variant="outlined"
          prominent
          icon="mdi-information"
        >
          <v-alert-title>Search Functionality Deprecated</v-alert-title>
          <div>
            The search functionality has been replaced with the new watchlist system. 
            Instead of manually searching, add authors to your watchlist and the system 
            will automatically track new releases.
          </div>
          <template v-slot:append>
            <v-btn color="primary" to="/watchlist">
              Go to Watchlist
            </v-btn>
          </template>
        </v-alert>
      </v-col>
    </v-row>
    
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>Migration Guide</v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon color="primary">mdi-numeric-1-circle</v-icon>
                </template>
                <v-list-item-title>Add Authors to Watchlist</v-list-item-title>
                <v-list-item-subtitle>
                  Go to the Watchlist page and add the authors you want to track
                </v-list-item-subtitle>
              </v-list-item>
              
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon color="primary">mdi-numeric-2-circle</v-icon>
                </template>
                <v-list-item-title>Specify Criteria (Optional)</v-list-item-title>
                <v-list-item-subtitle>
                  Add specific titles, series, or publishers to track
                </v-list-item-subtitle>
              </v-list-item>
              
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon color="primary">mdi-numeric-3-circle</v-icon>
                </template>
                <v-list-item-title>Automatic Tracking</v-list-item-title>
                <v-list-item-subtitle>
                  The system will automatically find and track new releases
                </v-list-item-subtitle>
              </v-list-item>
              
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon color="primary">mdi-numeric-4-circle</v-icon>
                </template>
                <v-list-item-title>View Results</v-list-item-title>
                <v-list-item-subtitle>
                  Check the Dashboard and Database pages for upcoming releases
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
export default {
  name: 'SearchView'
};
</script>
