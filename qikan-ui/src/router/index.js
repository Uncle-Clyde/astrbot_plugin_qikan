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

// 全局路由守卫 - 处理页面刷新后的认证状态恢复
router.beforeEach(async (to, from, next) => {
  // 动态导入 store 避免循环依赖
  const { useGameStore } = await import('../stores/game')
  const gameStore = useGameStore()
  const token = localStorage.getItem('qikan_token')

  // 公开路由列表
  const publicRoutes = ['/', '/login', '/spawn']

  // 需要登录的路由
  if (!publicRoutes.includes(to.path)) {
    if (!token) {
      // 无 token，跳转到登录页
      next({ path: '/' })
      return
    }

    // 有 token 但未验证用户信息
    if (!gameStore.user && token) {
      // 自动验证 token 并恢复状态
      const valid = await gameStore.verifyToken()
      if (valid) {
        // 连接 WebSocket
        await gameStore.connectWs()
        
        // 等待 player 数据（通过 WebSocket 推送）
        // 发送获取面板请求触发数据推送
        gameStore.send({ type: 'get_panel' })
        gameStore.send({ type: 'get_inventory' })
        
        // 短暂延迟确保数据已更新
        await new Promise(resolve => setTimeout(resolve, 500))
      } else {
        // token 验证失败，清除并跳转登录
        localStorage.removeItem('qikan_token')
        gameStore.logout()
        next({ path: '/', query: { expired: '1' } })
        return
      }
    }
  }

  next()
})

export default router
