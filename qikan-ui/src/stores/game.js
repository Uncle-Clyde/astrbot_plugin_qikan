import { defineStore } from 'pinia'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '',
  timeout: 10000
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('qikan_token')
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  res => res.data,
  err => {
    if (err.response?.status === 401) {
      ElMessage.error('登录已过期，请重新登录')
      localStorage.removeItem('qikan_token')
      window.location.href = '/'
    } else {
      ElMessage.error(err.response?.data?.message || err.message || '请求失败')
    }
    return Promise.reject(err)
  }
)

export const useGameStore = defineStore('game', {
  state: () => ({
    token: localStorage.getItem('qikan_token') || '',
    user: null,
    player: null,
    inventory: [],
    ws: null,
    connected: false,
    worldChat: [],
    rankings: null,
    family: null,
    market: [],
    currentLocation: null,
    locations: []
  }),

  actions: {
    async login(name, password, adminKey = '') {
      const res = await api.post('/api/login', { name, password, admin_key: adminKey })
      if (res.success) {
        this.token = res.token
        localStorage.setItem('qikan_token', res.token)
        await this.connectWs()
        return true
      }
      ElMessage.error(res.message)
      return false
    },

    async register(name, password, accessPassword = '') {
      const res = await api.post('/api/register', { name, password, access_password: accessPassword })
      if (res.success) {
        ElMessage.success('注册成功，请登录')
        return true
      }
      ElMessage.error(res.message)
      return false
    },

    connectWs() {
      if (this.ws) return
      
      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${location.host}/ws`
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        this.connected = true
        this.send({ type: 'auth', token: this.token })
      }

      this.ws.onmessage = (e) => {
        const msg = JSON.parse(e.data)
        this.handleWsMessage(msg)
      }

      this.ws.onclose = () => {
        this.connected = false
        this.ws = null
        setTimeout(() => this.connectWs(), 3000)
      }
    },

    send(data) {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify(data))
      }
    },

    handleWsMessage(msg) {
      switch (msg.type) {
        case 'state_update':
          this.player = msg
          break
        case 'inventory':
          this.inventory = msg.items || []
          break
        case 'world_chat_msg':
          this.worldChat.push(msg)
          if (this.worldChat.length > 100) this.worldChat.shift()
          break
        case 'rankings_data':
          this.rankings = msg.data
          break
      }
    },

    async getPanel() {
      this.send({ type: 'get_panel' })
    },

    async getInventory() {
      this.send({ type: 'get_inventory' })
    },

    async useItem(itemId) {
      this.send({ type: 'use_item', data: { item_id: itemId } })
    },

    async equipItem(itemId) {
      this.send({ type: 'equip_item', data: { item_id: itemId } })
    },

    async unequip(slot) {
      this.send({ type: 'unequip', data: { slot } })
    },

    async startAfk() {
      const res = await api.post('/api/start-afk')
      ElMessage.info(res.message)
    },

    async collectAfk() {
      const res = await api.post('/api/collect-afk')
      ElMessage.info(res.message)
      this.getPanel()
    },

    async checkin() {
      const res = await api.post('/api/checkin')
      ElMessage.info(res.message)
    },

    async adventure() {
      const res = await api.post('/api/adventure')
      ElMessage.info(res.message)
    },

    async getRankings() {
      this.send({ type: 'get_rankings' })
    },

    async getWorldChatHistory() {
      this.send({ type: 'get_world_chat_history' })
    },

    async sendWorldChat(content) {
      this.send({ type: 'world_chat_send', data: { content } })
    },

    logout() {
      this.token = ''
      this.user = null
      this.player = null
      localStorage.removeItem('qikan_token')
      if (this.ws) {
        this.ws.close()
        this.ws = null
      }
    }
  }
})

export default api
