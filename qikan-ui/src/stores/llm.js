import { defineStore } from 'pinia'
import api from './api'

export const useLLMStore = defineStore('llm', {
  state: () => ({
    chatting: false,
    response: '',
    error: ''
  }),

  actions: {
    async sendChat(message, gameContext = {}) {
      this.chatting = true
      this.error = ''
      try {
        const res = await api.post('/api/llm/chat', {
          message,
          context: {
            player: gameContext.player,
            location: gameContext.location,
            inventory: gameContext.inventory
          }
        })
        this.response = res.response || res.message
        return this.response
      } catch (e) {
        this.error = e.message || 'LLM请求失败'
        throw e
      } finally {
        this.chatting = false
      }
    }
  }
})
