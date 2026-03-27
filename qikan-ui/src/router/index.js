import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import Home from '../views/Home.vue'

const routes = [
  { path: '/', name: 'Login', component: Login },
  { path: '/home', name: 'Home', component: Home },
  { path: '/skills', name: 'Skills', component: () => import('../views/Skills.vue') },
  { path: '/map', name: 'Map', component: () => import('../views/Map.vue') },
  { path: '/family', name: 'Family', component: () => import('../views/Family.vue') },
  { path: '/market', name: 'Market', component: () => import('../views/Market.vue') },
  { path: '/chat', name: 'Chat', component: () => import('../views/WorldChat.vue') }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
