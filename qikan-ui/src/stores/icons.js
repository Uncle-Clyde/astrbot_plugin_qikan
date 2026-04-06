import { defineStore } from 'pinia'
import axios from 'axios'

const api = axios.create({
  baseURL: '',
  timeout: 10000
})

export const useIconStore = defineStore('icons', {
  state: () => ({
    config: null,
    loaded: false
  }),

  getters: {
    icons() {
      return this.config?.icons || {}
    }
  },

  actions: {
    async loadConfig() {
      if (this.loaded && this.config) return this.config
      
      try {
        const res = await api.get('/api/icons/config')
        if (res.success) {
          this.config = res.config
          this.loaded = true
        }
      } catch (e) {
        console.error('加载图标配置失败:', e)
      }
      return this.config
    },

    getIcon(key) {
      if (!this.config?.icons?.[key]) {
        return { emoji: '❓', image: '' }
      }
      return this.config.icons[key]
    },

    getIconContent(key) {
      const icon = this.getIcon(key)
      return icon.image || icon.emoji
    }
  }
})
