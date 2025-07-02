<template>
  <v-app>
    <v-app-bar app color="primary" dark>
      <v-app-bar-title>AudioStacker</v-app-bar-title>
      <v-spacer></v-spacer>
      <v-btn to="/" text>Dashboard</v-btn>
      <v-btn to="/database" text>Database</v-btn>

      <v-btn to="/watchlist" text>Watch-list</v-btn>

      <v-btn to="/settings" text>Settings</v-btn>
    </v-app-bar>

    <v-main>
      <v-container fluid>
        <router-view></router-view>
      </v-container>
    </v-main>

    <v-footer app color="primary" dark padless>
      <v-col class="text-center" cols="12">
        {{ new Date().getFullYear() }} — <strong>AudioStacker</strong> - Audiobook Release Tracking
      </v-col>
    </v-footer>
  </v-app>
</template>

<script>
export default {
  name: 'App'
}
</script>
