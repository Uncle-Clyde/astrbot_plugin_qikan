import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import Home from '../views/Home.vue'
import Spawn from '../views/Spawn.vue'

const routes = [
  { path: '/', name: 'Login', component: Login },
  { path: '/spawn', name: 'Spawn', component: Spawn },
  { path: '/home', name: 'Home', component: Home },
  { path: '/skills', name: 'Skills', component: () => import('../views/Skills.vue') },
  { path: '/map', name: 'Map', component: () => import('../views/Map.vue') },
  { path: '/location', name: 'Location', component: () => import('../views/LocationView.vue') },
  { path: '/family', name: 'Family', component: () => import('../views/Family.vue') },
  { path: '/market', name: 'Market', component: () => import('../views/Market.vue') },
  { path: '/chat', name: 'Chat', component: () => import('../views/WorldChat.vue') },
  { path: '/mail', name: 'Mail', component: () => import('../views/Mail.vue') },
  { path: '/achievements', name: 'Achievements', component: () => import('../views/Achievements.vue') },
  { path: '/titles', name: 'Titles', component: () => import('../views/Titles.vue') },
  { path: '/blacksmith', name: 'Blacksmith', component: () => import('../views/Blacksmith.vue') },
  { path: '/companions', name: 'Companions', component: () => import('../views/Companions.vue') },
  { path: '/troops', name: 'Troops', component: () => import('../views/Troops.vue') },
  { path: '/tournament', name: 'Tournament', component: () => import('../views/Tournament.vue') },
  { path: '/dungeon', name: 'Dungeon', component: () => import('../views/Dungeon.vue') },
  { path: '/bandits', name: 'Bandits', component: () => import('../views/Bandits.vue') },
  { path: '/trade', name: 'Trade', component: () => import('../views/Trade.vue') },
  { path: '/industry', name: 'Industry', component: () => import('../views/Industry.vue') },
  { path: '/rankings', name: 'Rankings', component: () => import('../views/Rankings.vue') },
  { path: '/icons', name: 'Icons', component: () => import('../views/Icons.vue') },
  { path: '/admin', name: 'Admin', component: () => import('../views/Admin.vue') },
  { path: '/about', name: 'About', component: () => import('../views/About.vue') }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
