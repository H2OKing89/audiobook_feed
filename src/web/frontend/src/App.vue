<template>
  <v-app>
    <v-app-bar app color="primary" dark>
      <v-app-bar-title>Audiobook Feed Generator</v-app-bar-title>
      <v-spacer></v-spacer>
      <v-btn to="/" text>Home</v-btn>
      <v-btn to="/search" text>Search</v-btn>
      <v-btn to="/feeds" text>My Feeds</v-btn>
      <v-btn to="/settings" text>Settings</v-btn>
    </v-app-bar>

    <v-main>
      <v-container fluid>
        <router-view></router-view>
      </v-container>
    </v-main>

    <v-footer app color="primary" dark padless>
      <v-col class="text-center" cols="12">
        {{ new Date().getFullYear() }} — <strong>Audiobook Feed Generator</strong>
      </v-col>
    </v-footer>
  </v-app>
</template>

<script>
export default {
  name: 'App'
}
</script>
