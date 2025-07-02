import { createRouter, createWebHistory } from 'vue-router';
// Remove unused import
// import HomeView from '@/views/HomeView.vue';

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import(/* webpackChunkName: "dashboard" */ '@/views/DashboardView.vue')
  },
  {
    path: '/database',
    name: 'Database',
    component: () => import(/* webpackChunkName: "database" */ '@/views/DatabaseView.vue')
  },


  {
    path: '/watchlist',
    name: 'Watchlist',
    component: () => import(/* webpackChunkName: "watchlist" */ '@/views/WatchlistView.vue')
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import(/* webpackChunkName: "settings" */ '@/views/SettingsView.vue')
  }
];

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
});

export default router;
