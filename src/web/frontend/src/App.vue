<template>
  <v-app>
    <v-app-bar app color="primary" dark>
      <v-app-bar-nav-icon @click="drawer = !drawer"></v-app-bar-nav-icon>
      <v-toolbar-title>AudioStacker</v-toolbar-title>
      <v-spacer></v-spacer>
      <v-btn icon @click="refreshData">
        <v-icon>mdi-refresh</v-icon>
      </v-btn>
    </v-app-bar>
    
    <v-navigation-drawer v-model="drawer" app>
      <v-list>
        <v-list-item to="/" link>
          <template v-slot:prepend>
            <v-icon>mdi-home</v-icon>
          </template>
          <v-list-item-title>Home</v-list-item-title>
        </v-list-item>
        
        <v-list-item to="/dashboard" link>
          <template v-slot:prepend>
            <v-icon>mdi-view-dashboard</v-icon>
          </template>
          <v-list-item-title>Dashboard</v-list-item-title>
        </v-list-item>
        
        <v-list-item to="/watchlist" link>
          <template v-slot:prepend>
            <v-icon>mdi-playlist-check</v-icon>
          </template>
          <v-list-item-title>Watchlist</v-list-item-title>
        </v-list-item>
        
        <v-list-item to="/database" link>
          <template v-slot:prepend>
            <v-icon>mdi-database</v-icon>
          </template>
          <v-list-item-title>Database</v-list-item-title>
        </v-list-item>
        
        <v-divider></v-divider>
        
        <v-list-item to="/settings" link>
          <template v-slot:prepend>
            <v-icon>mdi-cog</v-icon>
          </template>
          <v-list-item-title>Settings</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-navigation-drawer>
    
    <v-main>
      <v-container fluid>
        <router-view />
      </v-container>
    </v-main>
    
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="snackbar.timeout"
    >
      {{ snackbar.text }}
      <template v-slot:actions>
        <v-btn
          variant="text"
          @click="snackbar.show = false"
        >
          Close
        </v-btn>
      </template>
    </v-snackbar>
  </v-app>
</template>

<script>
export default {
  name: 'App',
  data() {
    return {
      drawer: true,
      snackbar: {
        show: false,
        text: '',
        color: 'info',
        timeout: 3000
      }
    };
  },
  methods: {
    showMessage(text, color = 'info', timeout = 3000) {
      this.snackbar.text = text;
      this.snackbar.color = color;
      this.snackbar.timeout = timeout;
      this.snackbar.show = true;
    },
    refreshData() {
      // Send a refresh event that child components can listen for
      this.$root.$emit('refresh-data');
      this.showMessage('Refreshing data...');
    }
  }
};
</script>
