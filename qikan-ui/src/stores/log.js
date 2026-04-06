import { defineStore } from 'pinia'

const STORAGE_KEY = 'qikan_player_logs'
const MAX_LOGS = 200

const LOG_TYPE_MAP = {
  cultivate: { type: 'cultivate', icon: '🧘' },
  adventure: { type: 'combat', icon: '⚔️' },
  checkin: { type: 'system', icon: '📅' },
  heal: { type: 'system', icon: '💊' },
  start_afk: { type: 'system', icon: '💤' },
  cancel_afk: { type: 'system', icon: '⏹️' },
  collect_afk: { type: 'reward', icon: '🎁' },
  equip: { type: 'equip', icon: '🛡️' },
  unequip: { type: 'equip', icon: '📦' },
  use_item: { type: 'item', icon: '💊' },
  shop_buy: { type: 'trade', icon: '🛒' },
  market_buy: { type: 'trade', icon: '🏪' },
  recycle: { type: 'trade', icon: '♻️' },
  enter_location: { type: 'travel', icon: '🏰' },
  leave_location: { type: 'travel', icon: '🚶' },
  rest_at_settlement: { type: 'travel', icon: '🍺' },
  start_npc_dialog: { type: 'npc', icon: '💬' },
  give_gift_to_npc: { type: 'npc', icon: '🎁' },
  allocate_attribute_points: { type: 'cultivate', icon: '⭐' },
  allocate_skill_points: { type: 'cultivate', icon: '📜' },
  breakthrough: { type: 'cultivate', icon: '🔥' },
  sect_accept_task: { type: 'system', icon: '📋' },
  sect_create_task: { type: 'system', icon: '📋' },
  travel: { type: 'travel', icon: '🗺️' },
  combat: { type: 'combat', icon: '⚔️' },
  gathering: { type: 'system', icon: '🌿' },
  hunting: { type: 'combat', icon: '🏹' },
  crafting: { type: 'system', icon: '🔨' },
  forging: { type: 'system', icon: '⚒️' },
  reset_player: { type: 'system', icon: '🔄' },
  set_spawn_origin: { type: 'system', icon: '🎭' },
}

const DEFAULT_LOG_TYPE = { type: 'system', icon: '🔧' }

export const useLogStore = defineStore('log', {
  state: () => ({
    logs: [],
    filter: 'all',
  }),

  getters: {
    filteredLogs: (state) => {
      if (state.filter === 'all') return state.logs
      return state.logs.filter(l => l.type === state.filter)
    },
  },

  actions: {
    init() {
      try {
        const stored = localStorage.getItem(STORAGE_KEY)
        if (stored) {
          this.logs = JSON.parse(stored)
        }
      } catch (e) {
        console.error('Failed to load logs:', e)
        this.logs = []
      }
    },

    getActionLogType(action) {
      return LOG_TYPE_MAP[action]?.type || DEFAULT_LOG_TYPE.type
    },

    getActionLogIcon(action) {
      return LOG_TYPE_MAP[action]?.icon || DEFAULT_LOG_TYPE.icon
    },

    addLog(entry) {
      const log = {
        id: Date.now() + '_' + Math.random().toString(36).substr(2, 5),
        timestamp: new Date().toISOString(),
        type: entry.type || 'system',
        icon: entry.icon || '🔧',
        title: entry.title || '',
        content: entry.content || '',
        ...entry,
      }

      this.logs.unshift(log)
      if (this.logs.length > MAX_LOGS) {
        this.logs = this.logs.slice(0, MAX_LOGS)
      }

      this._save()
    },

    clearLogs() {
      this.logs = []
      this._save()
    },

    setFilter(filter) {
      this.filter = filter
    },

    _save() {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(this.logs))
      } catch (e) {
        console.error('Failed to save logs:', e)
      }
    },
  },
})
