import { defineStore } from 'pinia'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useLogStore } from './log'
import { getGameState, GameEvent } from '@/game/game-state'
import { GameNotificationService } from '@/services/game-notification-service'

let audioStore = null
const getAudioStore = () => {
  if (!audioStore) {
    try {
      audioStore = require('./audio').useAudioStore
    } catch (e) {
      console.warn('Audio store not available')
    }
  }
  return audioStore
}

const api = axios.create({
  baseURL: '',
  timeout: 30000
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
    connecting: false,
    worldChat: [],
    rankings: null,
    family: null,
    market: [],
    currentLocation: null,
    locations: [],
    wsReconnectTimer: null,
    pendingRequests: new Map(),
    requestTimeout: 30000,
    loading: false,
    actionLocks: new Map(),
    buttonLoading: {},
    actionTimestamps: [],
    rateLimitWarned: false,
    rateLimitBlocked: false,
    currentDialog: null,
    currentNPC: null,
  }),

  actions: {
    checkRateLimit() {
      const now = Date.now()
      const halfSecond = 500
      const twoSeconds = 2000
      const maxActionsInWindow = 10
      
      this.actionTimestamps = this.actionTimestamps.filter(ts => now - ts < twoSeconds)
      
      const recentActions = this.actionTimestamps.filter(ts => now - ts < halfSecond)
      
      if (recentActions.length >= 1) {
        if (!this.rateLimitWarned) {
          this.rateLimitWarned = true
          setTimeout(() => { this.rateLimitWarned = false }, 3000)
          return { blocked: true, warning: true, message: '操作太频繁，请稍后再试' }
        }
      }
      
      this.actionTimestamps.push(now)
      
      if (this.actionTimestamps.length >= maxActionsInWindow) {
        this.rateLimitBlocked = true
        setTimeout(() => { 
          this.rateLimitBlocked = false
          this.actionTimestamps = []
        }, 5000)
        return { blocked: true, warning: false, message: '操作过于频繁，已临时封禁5秒' }
      }
      
      return { blocked: false }
    },

    isActionLocked(action) {
      return this.actionLocks.get(action) === true
    },

    lockAction(action = 'default') {
      if (this.actionLocks.get(action) === true) return false
      this.actionLocks.set(action, true)
      return true
    },

    unlockAction(action = 'default') {
      this.actionLocks.delete(action)
    },

    setButtonLoading(key, value) {
      this.buttonLoading = { ...this.buttonLoading, [key]: value }
    },

    isButtonLoading(key) {
      return !!this.buttonLoading[key]
    },

    async login(name, password, accessPassword = '') {
      try {
        const res = await api.post('/api/login', { 
          name, 
          password, 
          access_password: accessPassword 
        })
        if (res.success) {
          this.token = res.token
          localStorage.setItem('qikan_token', res.token)
          await this.connectWs()
          return { success: true, needsSpawn: res.needs_spawn_selection }
        }
        ElMessage.error(res.message)
        return { success: false, needsSpawn: false }
      } catch (err) {
        ElMessage.error('登录失败: ' + (err.message || '网络错误'))
        return { success: false, needsSpawn: false }
      }
    },

    async register(name, password, accessPassword = '', spawnOrigin = '', spawnLocation = '') {
      const res = await api.post('/api/register', { 
        name, 
        password, 
        access_password: accessPassword,
        spawn_origin: spawnOrigin,
        spawn_location: spawnLocation
      })
      if (res.success) {
        ElMessage.success('注册成功，请登录')
        return { success: true, needsSpawn: res.needs_spawn_selection }
      }
      ElMessage.error(res.message)
      return { success: false, needsSpawn: false }
    },

    async verifyToken() {
      if (!this.token) return false
      try {
        const res = await api.post('/api/verify-token', { token: this.token })
        if (res.success) {
          this.user = { user_id: res.user_id, name: res.name }
          return true
        }
        return false
      } catch (err) {
        return false
      }
    },

    async reconnectWs() {
      if (this.ws && (this.ws.readyState === WebSocket.CONNECTING || this.ws.readyState === WebSocket.OPEN)) {
        return
      }
      await this.connectWs()
    },

    connectWs() {
      if (this.connecting) return Promise.resolve()
      if (this.ws && (this.ws.readyState === WebSocket.CONNECTING || this.ws.readyState === WebSocket.OPEN)) {
        return Promise.resolve()
      }
      
      if (this.wsReconnectTimer) {
        clearTimeout(this.wsReconnectTimer)
        this.wsReconnectTimer = null
      }

      this.connecting = true
      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${location.host}/ws`
      this.ws = new WebSocket(wsUrl)

      return new Promise((resolve) => {
        this.ws.onopen = () => {
          this.connected = true
          this.connecting = false
          if (this.token) {
            const pageGuard = window.__XIUXIAN_PAGE_GUARD__ || { enabled: false, page_id: '', issued_at: 0, signature: '' }
            setTimeout(() => {
              this.send({
                type: 'login',
                data: {
                  token: this.token,
                  page_id: pageGuard.page_id || '',
                  issued_at: pageGuard.issued_at || 0,
                  signature: pageGuard.signature || ''
                }
              })
              resolve()
            }, 100)
          } else {
            resolve()
          }
        }

        this.ws.onmessage = (e) => {
          try {
            const msg = JSON.parse(e.data)
            console.log('[WS] Raw message received:', JSON.stringify(msg).substring(0, 200))
            this.handleWsMessage(msg)
          } catch (err) {
            console.error('WebSocket消息解析失败:', err)
          }
        }

        this.ws.onerror = (err) => {
          console.error('WebSocket错误:', err)
          this.connecting = false
          resolve()
        }

        this.ws.onclose = () => {
          this.connected = false
          this.connecting = false
        }
      })
    },

    async sendWithTimeout(data, requestId = null) {
      const id = requestId || `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      
      return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          this.pendingRequests.delete(id)
          ElMessage.warning('请求超时，请检查网络连接')
          reject(new Error('Request timeout'))
        }, this.requestTimeout)

        this.pendingRequests.set(id, { resolve, reject, timeout })

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ ...data, requestId: id }))
        } else {
          clearTimeout(timeout)
          this.pendingRequests.delete(id)
          ElMessage.warning('未连接到服务器，正在重连...')
          this.connectWs()
          reject(new Error('Not connected'))
        }
      })
    },

    async wsCall(type, data = {}) {
      try {
        const msg = await this.sendWithTimeout({ type, data })
        return msg.data || msg
      } catch (e) {
        console.error('wsCall error:', e)
        return null
      }
    },

    send(data, expectResponse = false) {
      console.log('[WS] Sending:', data.type)
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify(data))
      } else {
        ElMessage.warning('未连接到服务器')
      }
    },

    wsMessageHandlers: {},

    handleWsMessage(msg) {
      console.log('[WS] Received message:', msg.type, msg.requestId ? '(has requestId)' : '')
      if (this.wsMessageHandlers) {
        for (const key in this.wsMessageHandlers) {
          console.log('[WS] Calling handler:', key)
          this.wsMessageHandlers[key](msg)
        }
      }

      if (msg.requestId) {
        console.log('[WS] Handling requestId:', msg.requestId)
        const pending = this.pendingRequests.get(msg.requestId)
        if (pending) {
          clearTimeout(pending.timeout)
          this.pendingRequests.delete(msg.requestId)
          pending.resolve(msg)
          return
        }
      }

       switch (msg.type) {
        case 'state_update': {
          const oldTown = this.player?.currentLocation || null
          this.player = msg.data || msg
          const newTown = this.player?.currentLocation || null
          
          // Handle town entry/exit notifications
          if (newTown && newTown !== oldTown) {
            getGameState().enterTown(newTown)
            // Dispatch WebSocket event for town entry
            this.dispatchWebSocketEvent({
              type: GameEvent.TOWN_ENTER,
              payload: { townName: newTown }
            })
          } else if (!newTown && oldTown) {
            getGameState().leaveTown()
            // Dispatch WebSocket event for town exit
            this.dispatchWebSocketEvent({
              type: GameEvent.TOWN_LEAVE,
              payload: { townName: oldTown }
            })
          }

          // 自动获取背包数据
          if (this.inventory.length === 0) {
            setTimeout(() => {
              this.getInventory()
            }, 500)
          }
          break
        }
        case 'inventory': {
          const oldItems = this.inventory
          // 兼容两种格式：data 是数组 或 data 是对象 {items: [...]}
          let invData = msg.data
          if (Array.isArray(invData)) {
            this.inventory = invData
          } else if (invData?.items) {
            this.inventory = invData.items
          } else if (msg.items) {
            this.inventory = msg.items
          } else {
            this.inventory = []
          }

          // Find new items and trigger acquisition notifications
          const newItems = this.inventory.filter(
            item => !oldItems.some(oldItem => oldItem.id === item.id)
          )

          newItems.forEach(item => {
            getGameState().addItem(item)
            // Dispatch WebSocket event for item acquisition
            this.dispatchWebSocketEvent({
              type: GameEvent.ITEM_ACQUIRE,
              payload: { item }
            })
            // 添加：记录到个人日志
            const logStore = useLogStore()
            const quantity = item.count > 1 ? ` x${item.count}` : ''
            logStore.addLog({
              type: 'item',
              icon: '💎',
              title: '获得物品',
              content: `${item.name}${quantity}`
            })
          })
          break
        }
        case 'world_chat_msg':
          this.worldChat.push(msg.data || msg)
          if (this.worldChat.length > 100) this.worldChat.shift()
          break
        case 'world_chat_history':
          this.worldChat = msg.data || []
          break
        case 'rankings_data':
          this.rankings = msg.data
          break
        case 'map_player':
        case 'map_locations':
          break
        case 'town_menu':
        case 'town_menu_action':
        case 'location_update':
          break
        case 'action_result':
          // Handle action results for town entry/exit
          if (msg.data?.success) {
            const action = msg.action
            if (action === 'enter_location' && msg.data?.town_name) {
              getGameState().enterTown(msg.data.town_name)
              // Dispatch WebSocket event for town entry
              this.dispatchWebSocketEvent({
                type: GameEvent.TOWN_ENTER,
                payload: { townName: msg.data.town_name }
              })
            } else if (action === 'leave_location') {
              const oldTown = this.player?.currentLocation
              getGameState().leaveTown()
              // Dispatch WebSocket event for town exit
              this.dispatchWebSocketEvent({
                type: GameEvent.TOWN_LEAVE,
                payload: { townName: oldTown }
              })
            }
          }
          break
        case 'town_update':
          // Handle explicit town updates from server
          if (msg.data?.town_name) {
            getGameState().enterTown(msg.data.town_name)
            this.dispatchWebSocketEvent({
              type: GameEvent.TOWN_ENTER,
              payload: { townName: msg.data.town_name }
            })
          } else if (msg.data?.left_town) {
            const oldTown = this.player?.currentLocation
            getGameState().leaveTown()
            this.dispatchWebSocketEvent({
              type: GameEvent.TOWN_LEAVE,
              payload: { townName: oldTown }
            })
          }
          break
        case 'custom_notification':
          // Handle custom notifications from server
          if (msg.data?.type === 'town_enter' && msg.data?.town_name) {
            getGameState().enterTown(msg.data.town_name)
            this.dispatchWebSocketEvent({
              type: GameEvent.TOWN_ENTER,
              payload: { townName: msg.data.town_name }
            })
          } else if (msg.data?.type === 'town_leave') {
            const oldTown = this.player?.currentLocation
            getGameState().leaveTown()
            this.dispatchWebSocketEvent({
              type: GameEvent.TOWN_LEAVE,
              payload: { townName: oldTown }
            })
          } else if (msg.data?.type === 'item_acquire' && msg.data?.item) {
            getGameState().addItem(msg.data.item)
            this.dispatchWebSocketEvent({
              type: GameEvent.ITEM_ACQUIRE,
              payload: { item: msg.data.item }
            })
          }
          break
        case 'server_notification':
          // Handle server-side notifications
          if (msg.data?.event_type && msg.data?.payload) {
            const eventMap = {
              [GameEvent.TOWN_ENTER]: () => {
                getGameState().enterTown(msg.data.payload.townName)
                this.dispatchWebSocketEvent({
                  type: GameEvent.TOWN_ENTER,
                  payload: { townName: msg.data.payload.townName }
                })
              },
              [GameEvent.TOWN_LEAVE]: () => {
                const oldTown = this.player?.currentLocation
                getGameState().leaveTown()
                this.dispatchWebSocketEvent({
                  type: GameEvent.TOWN_LEAVE,
                  payload: { townName: oldTown }
                })
              },
              [GameEvent.ITEM_ACQUIRE]: () => {
                getGameState().addItem(msg.data.payload.item)
                this.dispatchWebSocketEvent({
                  type: GameEvent.ITEM_ACQUIRE,
                  payload: { item: msg.data.payload.item }
                })
              }
            }
            
            const handler = eventMap[msg.data.event_type]
            if (handler) {
              handler()
            }
          }
          break
        case 'location_update':
          // Handle explicit location updates from server
          if (msg.data?.town_name) {
            getGameState().enterTown(msg.data.town_name)
            this.dispatchWebSocketEvent({
              type: GameEvent.TOWN_ENTER,
              payload: { townName: msg.data.town_name }
            })
          } else if (msg.data?.left_town) {
            const oldTown = this.player?.currentLocation
            getGameState().leaveTown()
            this.dispatchWebSocketEvent({
              type: GameEvent.TOWN_LEAVE,
              payload: { townName: oldTown }
            })
          }
          break
        case 'item_update':
          // Handle explicit item updates from server
          if (msg.data?.item) {
            getGameState().addItem(msg.data.item)
            this.dispatchWebSocketEvent({
              type: GameEvent.ITEM_ACQUIRE,
              payload: { item: msg.data.item }
            })
            const logStore = useLogStore()
            const item = msg.data.item
            const quantity = item.count > 1 ? ` x${item.count}` : ''
            logStore.addLog({
              type: 'item',
              icon: '💎',
              title: '获得物品',
              content: `${item.name}${quantity}`
            })
          }
          break
        case 'town_event':
          // Handle town-specific events from server
          if (msg.data?.event_type && msg.data?.payload) {
            const townEventMap = {
              'town_enter': () => {
                getGameState().enterTown(msg.data.payload.townName)
                this.dispatchWebSocketEvent({
                  type: GameEvent.TOWN_ENTER,
                  payload: { townName: msg.data.payload.townName }
                })
              },
              'town_leave': () => {
                const oldTown = this.player?.currentLocation
                getGameState().leaveTown()
                this.dispatchWebSocketEvent({
                  type: GameEvent.TOWN_LEAVE,
                  payload: { townName: oldTown }
                })
              }
            }
            
            const handler = townEventMap[msg.data.event_type]
            if (handler) {
              handler()
            }
          }
          break
        case 'item_event':
          // Handle item-specific events from server
          if (msg.data?.event_type && msg.data?.item) {
            const item = msg.data.item
            const itemEventMap = {
              'item_acquire': () => {
                getGameState().addItem(item)
                this.dispatchWebSocketEvent({
                  type: GameEvent.ITEM_ACQUIRE,
                  payload: { item }
                })
                const logStore = useLogStore()
                const quantity = item.count > 1 ? ` x${item.count}` : ''
                logStore.addLog({
                  type: 'item',
                  icon: '💎',
                  title: '获得物品',
                  content: `${item.name}${quantity}`
                })
              }
            }
            
            const handler = itemEventMap[msg.data.event_type]
            if (handler) {
              handler()
            }
          }
          break
        case 'location_change':
          // Handle location changes from server
          if (msg.data?.new_location) {
            getGameState().enterTown(msg.data.new_location)
            this.dispatchWebSocketEvent({
              type: GameEvent.TOWN_ENTER,
              payload: { townName: msg.data.new_location }
            })
          } else if (msg.data?.left_location) {
            const oldTown = this.player?.currentLocation
            getGameState().leaveTown()
            this.dispatchWebSocketEvent({
              type: GameEvent.TOWN_LEAVE,
              payload: { townName: oldTown }
            })
          }
          break
        case 'item_change':
          // Handle item changes from server
          if (msg.data?.item) {
            getGameState().addItem(msg.data.item)
            this.dispatchWebSocketEvent({
              type: GameEvent.ITEM_ACQUIRE,
              payload: { item: msg.data.item }
            })
            const logStore = useLogStore()
            const item = msg.data.item
            const quantity = item.count > 1 ? ` x${item.count}` : ''
            logStore.addLog({
              type: 'item',
              icon: '💎',
              title: '获得物品',
              content: `${item.name}${quantity}`
            })
          }
          break
        case 'world_chat_msg':
          this.worldChat.push(msg.data || msg)
          if (this.worldChat.length > 100) this.worldChat.shift()
          break
        case 'world_chat_history':
          this.worldChat = msg.data || []
          break
        case 'rankings_data':
          this.rankings = msg.data
          break
        case 'map_player':
        case 'map_locations':
          break
        case 'town_menu':
          break
        case 'town_menu_action':
          break
        case 'location_update':
          break
        case 'action_result':
          if (msg.data?.success) {
            const action = msg.action
            const audio = getAudioStore()
            if (audio) {
              if (action === 'shop_buy' || action === 'market_buy' || action === 'recycle') {
                audio.playSound('coins')
              } else if (action === 'sect_accept_task' || action === 'sect_create_task') {
                audio.playSound('task')
              } else if (action === 'equip' || action === 'unequip') {
                audio.playSound('equip')
              } else if (action === 'cultivate' || action === 'adventure' || action?.includes('combat')) {
                audio.playSound('cultivate')
              } else if (action === 'allocate_attribute_points' || action === 'allocate_skill_points') {
                audio.playSound('levelup')
              }
            }
            ElMessage.success(msg.data.message || '操作成功')
            const logStore = useLogStore()
            logStore.addLog({
              type: logStore.getActionLogType(action),
              icon: logStore.getActionLogIcon(action),
              title: action || '操作',
              content: msg.data.message || '操作成功',
              action: action,
            }, msg.data)
            if (action === 'start_afk' || action === 'cancel_afk' || action === 'collect_afk') {
              setTimeout(() => this.getPanel(), 100)
            }
          } else if (msg.data?.success === false) {
            ElMessage.error(msg.data?.message || '操作失败')
            const logStore = useLogStore()
            logStore.addLog({
              type: 'system',
              icon: '❌',
              title: logStore.getActionLogTitle(action) || action || '操作',
              content: msg.data?.message || '操作失败',
              action: action,
            }, msg.data)
          }
          break
        case 'error':
          ElMessage.error(msg.message || '发生错误')
          break
        case 'announcements':
          break
        case 'market_data':
        case 'my_listings':
        case 'shop_data':
        case 'sect_list_data':
        case 'sect_my_data':
        case 'sect_detail_data':
        case 'scenes':
        case 'map_locations':
        case 'map_player':
          break
        case 'dungeon_state':
        case 'dungeon_update':
        case 'pvp_state':
        case 'pvp_update':
        case 'pvp_challenge_notice':
        case 'pvp_start':
        case 'pvp_result':
          break
        case 'heart_methods':
        case 'bind_key':
        case 'fee_preview':
        case 'market_blocked':
        case 'noop':
          break
        default:
          console.log('未处理的WebSocket消息类型:', msg.type, msg)
      }
    },

    dispatchWebSocketEvent(event) {
      const logStore = useLogStore()
      
      switch (event.type) {
        case GameEvent.TOWN_ENTER:
          getGameState().enterTown(event.payload.townName)
          logStore.addLog({
            type: 'travel',
            icon: '🏰',
            title: '进入城镇',
            content: `进入了 ${event.payload.townName}`,
            action: 'enter_location',
          })
          break
        case GameEvent.TOWN_LEAVE:
          getGameState().leaveTown()
          logStore.addLog({
            type: 'travel',
            icon: '🚶',
            title: '离开城镇',
            content: `离开了 ${event.payload.townName}`,
            action: 'leave_location',
          })
          break
        case GameEvent.ITEM_ACQUIRE:
          getGameState().addItem(event.payload.item)
          const item = event.payload.item
          const itemName = item?.name || '未知物品'
          const quantity = item?.quantity || 1
          logStore.addLog({
            type: 'reward',
            icon: '🎁',
            title: '获得物品',
            content: `获得了 ${quantity > 1 ? `${quantity}x ` : ''}${itemName}`,
            action: 'item_acquire',
          })
          break
        default:
          console.log('未知的WebSocket事件类型:', event.type)
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
      this.send({ type: 'equip', data: { equip_id: itemId } })
    },

    async unequipItem(slot) {
      this.send({ type: 'unequip', data: { slot } })
    },

    async equipMount(mountId) {
      this.send({ type: 'equip_mount', data: { mount_id: mountId } })
    },

    async unequipMount() {
      this.send({ type: 'unequip_mount' })
    },

    async equipMountItem(equipId, slot) {
      this.send({ type: 'equip_mount_item', data: { equip_id: equipId } })
    },

    async unequipMountItem(slot) {
      this.send({ type: 'unequip_mount_item', data: { slot } })
    },

    async startAfk(minutes = 60) {
      this.send({ type: 'start_afk', data: { minutes } })
    },

    async cancelAfk() {
      this.send({ type: 'cancel_afk' })
    },

    async collectAfk() {
      this.send({ type: 'collect_afk' })
    },

    async checkin() {
      this.send({ type: 'checkin' })
    },

    async adventure() {
      this.send({ type: 'adventure' })
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
      this.actionLocks.clear()
      this.buttonLoading = {}
      localStorage.removeItem('qikan_token')
      if (this.wsReconnectTimer) {
        clearTimeout(this.wsReconnectTimer)
        this.wsReconnectTimer = null
      }
      this.pendingRequests.forEach(pending => {
        clearTimeout(pending.timeout)
      })
      this.pendingRequests.clear()
      if (this.ws) {
        this.ws.close()
        this.ws = null
      }
    },

    cleanup() {
      if (this.wsReconnectTimer) {
        clearTimeout(this.wsReconnectTimer)
        this.wsReconnectTimer = null
      }
      this.pendingRequests.forEach(pending => {
        clearTimeout(pending.timeout)
      })
      this.pendingRequests.clear()
      if (this.ws) {
        this.ws.close()
        this.ws = null
      }
    }
  }
})

export default api
