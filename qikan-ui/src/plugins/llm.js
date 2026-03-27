export default {
  install(app) {
    app.config.globalProperties.$llm = {
      send: async (message, context = {}) => {
        const response = await fetch('/api/llm/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message, context })
        })
        return response.json()
      }
    }
  }
}
