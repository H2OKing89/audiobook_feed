<template>
  <v-container>
    <h1>Feeds</h1>
    
    <v-row>
      <v-col cols="12">
        <v-alert
          type="warning"
          variant="outlined"
          prominent
          icon="mdi-alert"
        >
          <v-alert-title>Feeds Functionality Deprecated</v-alert-title>
          <div>
            The feeds functionality has been removed and replaced with the new 
            watchlist-based tracking system. This provides better accuracy and 
            automatic monitoring of your favorite authors.
          </div>
          <template v-slot:append>
            <v-btn color="primary" to="/watchlist">
              Use Watchlist Instead
            </v-btn>
          </template>
        </v-alert>
      </v-col>
    </v-row>
    
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon left color="info">mdi-information</v-icon>
            What Changed?
          </v-card-title>
          <v-card-text>
            <v-timeline density="compact">
              <v-timeline-item
                dot-color="red"
                size="small"
              >
                <template v-slot:opposite>
                  <span class="text-caption">Old System</span>
                </template>
                <div>
                  <strong>Manual Feed Management</strong>
                  <div class="text-caption">Required manual configuration of RSS feeds and search parameters</div>
                </div>
              </v-timeline-item>
              
              <v-timeline-item
                dot-color="green"
                size="small"
              >
                <template v-slot:opposite>
                  <span class="text-caption">New System</span>
                </template>
                <div>
                  <strong>Automatic Watchlist Tracking</strong>
                  <div class="text-caption">Simply add authors to your watchlist and get automatic notifications</div>
                </div>
              </v-timeline-item>
            </v-timeline>
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" to="/dashboard">
              View Dashboard
            </v-btn>
            <v-btn color="secondary" to="/database">
              Browse Database
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
export default {
  name: 'FeedsView'
};
</script>
