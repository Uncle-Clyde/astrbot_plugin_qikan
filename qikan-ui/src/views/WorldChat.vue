<template>
  <div class="view-container">
    <div class="nav-bar">
      <el-button @click="$router.push('/home')">← 返回</el-button>
      <h2>💬 世界频道</h2>
    </div>
    <el-card class="chat-card">
      <div class="chat-messages" ref="chatRef">
        <div v-for="(msg, i) in gameStore.worldChat" :key="i" class="chat-message">
          <span class="msg-name" :style="{ color: getNameColor(msg.realm) }">
            {{ msg.name }}
          </span>
          <span class="msg-role" v-if="msg.sect_name">[{{ msg.sect_name }}]</span>
          <span class="msg-content">: {{ msg.content }}</span>
        </div>
      </div>
      <div class="chat-input">
        <el-input v-model="inputMsg" placeholder="发送消息..." @keyup.enter="sendMessage" />
        <el-button type="primary" @click="sendMessage">发送</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useGameStore } from '../stores/game'

const gameStore = useGameStore()
const chatRef = ref(null)
const inputMsg = ref('')

const getNameColor = (realm) => {
  const colors = ['', '#4CAF50', '#2196F3', '#9C27B0', '#FF9800', '#f44336']
  return colors[realm] || '#ffd700'
}

const sendMessage = () => {
  if (inputMsg.value.trim()) {
    gameStore.sendWorldChat(inputMsg.value.trim())
    inputMsg.value = ''
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (chatRef.value) {
      chatRef.value.scrollTop = chatRef.value.scrollHeight
    }
  })
}

onMounted(() => {
  gameStore.getWorldChatHistory()
  scrollToBottom()
})
</script>

<style scoped>
.view-container { min-height: 100vh; background: #1a1a2e; padding: 20px; }
.nav-bar { display: flex; align-items: center; gap: 20px; margin-bottom: 20px; }
.nav-bar h2 { color: #ffd700; margin: 0; }
.chat-card { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); }
.chat-messages { height: 400px; overflow-y: auto; padding: 10px; }
.chat-message { margin-bottom: 8px; color: #e0e0e0; }
.msg-name { font-weight: bold; margin-right: 5px; }
.msg-role { color: #888; margin-right: 5px; font-size: 12px; }
.chat-input { display: flex; gap: 10px; margin-top: 10px; }
</style>
