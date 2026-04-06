<template>
  <div class="world-chat-inline">
    <div class="chat-header" @click="collapsed = !collapsed">
      <h3>💬 世界频道</h3>
      <div class="header-actions">
        <span class="online-count" v-if="onlineCount > 0">{{ onlineCount }} 人在线</span>
        <router-link to="/chat" class="more-link" @click.stop>更多</router-link>
        <span class="collapse-icon">{{ collapsed ? '▲' : '▼' }}</span>
      </div>
    </div>
    <div v-show="!collapsed" class="chat-body">
      <div class="messages" ref="chatRef">
        <div v-for="(msg, i) in gameStore.worldChat" :key="i" class="message">
          <span class="name" :style="{ color: getNameColor(msg.realm) }">{{ msg.name }}</span>
          <span class="role" v-if="msg.sect_name">[{{ msg.sect_name }}]</span>
          <span class="content">: {{ msg.content }}</span>
        </div>
        <div v-if="gameStore.worldChat.length === 0" class="no-messages">
          暂无消息，快来聊聊吧
        </div>
      </div>
      <div class="input-bar">
        <input
          v-model="inputMsg"
          @keyup.enter="sendMessage"
          placeholder="输入消息..."
          class="chat-input"
        />
        <button class="send-btn" @click="sendMessage" :disabled="gameStore.isButtonLoading('world_chat')">发送</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { ElMessage } from 'element-plus'

const router = useRouter()
const gameStore = useGameStore()
const chatRef = ref(null)
const inputMsg = ref('')
const collapsed = ref(false)
const onlineCount = ref(0)

const getNameColor = (realm) => {
  const colors = ['', '#4CAF50', '#2196F3', '#9C27B0', '#FF9800', '#f44336']
  return colors[realm] || '#ffd700'
}

const sendMessage = () => {
  if (!inputMsg.value.trim()) return
  if (!gameStore.connected) {
    ElMessage.warning('未连接到服务器，请刷新页面')
    return
  }
  if (!gameStore.lockAction('chat')) {
    ElMessage.warning('发送太频繁，请稍后再发')
    return
  }
  gameStore.setButtonLoading('world_chat', true)
  gameStore.sendWorldChat(inputMsg.value.trim())
  inputMsg.value = ''
  setTimeout(() => {
    gameStore.unlockAction('chat')
    gameStore.setButtonLoading('world_chat', false)
  }, 300)
}

const scrollToBottom = () => {
  nextTick(() => {
    if (chatRef.value) {
      chatRef.value.scrollTop = chatRef.value.scrollHeight
    }
  })
}

watch(() => gameStore.worldChat.length, () => {
  if (!collapsed.value) {
    scrollToBottom()
  }
})

onMounted(async () => {
  if (gameStore.connected) {
    gameStore.getWorldChatHistory()
    scrollToBottom()
  }
})
</script>

<style scoped>
.world-chat-inline {
  background: rgba(15,15,25,0.98);
  border-top: 2px solid #2a2a3e;
  flex-shrink: 0;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 20px;
  cursor: pointer;
  transition: background 0.2s;
  user-select: none;
}

.chat-header:hover {
  background: rgba(255,255,255,0.03);
}

.chat-header h3 {
  margin: 0;
  font-size: 14px;
  color: var(--text-gold);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.online-count {
  font-size: 11px;
  color: #4caf50;
}

.more-link {
  font-size: 12px;
  color: #888;
  text-decoration: none;
  transition: color 0.2s;
}

.more-link:hover {
  color: var(--text-gold);
}

.collapse-icon {
  color: #666;
  font-size: 11px;
}

.chat-body {
  padding: 0 20px 12px;
}

.messages {
  height: 160px;
  overflow-y: auto;
  padding: 8px 0;
  margin-bottom: 8px;
  border-bottom: 1px solid #2a2a3e;
}

.no-messages {
  text-align: center;
  color: #555;
  padding: 30px;
  font-size: 13px;
}

.message {
  margin-bottom: 4px;
  color: #ccc;
  font-size: 13px;
  line-height: 1.5;
}

.name {
  font-weight: bold;
  margin-right: 4px;
}

.role {
  color: #888;
  margin-right: 4px;
  font-size: 11px;
}

.content {
  color: #bbb;
}

.input-bar {
  display: flex;
  gap: 8px;
}

.chat-input {
  flex: 1;
  background: rgba(0,0,0,0.3);
  border: 1px solid #3d3d3d;
  border-radius: 6px;
  padding: 8px 12px;
  color: #f5deb3;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
}

.chat-input:focus {
  border-color: #d4af37;
}

.chat-input::placeholder {
  color: #555;
}

.send-btn {
  padding: 8px 20px;
  background: linear-gradient(145deg, #8B0000 0%, #5C0000 100%);
  border: 1px solid #B22222;
  border-radius: 6px;
  color: #ffd700;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.send-btn:hover:not(:disabled) {
  background: linear-gradient(145deg, #B22222 0%, #8B0000 100%);
  box-shadow: 0 2px 8px rgba(139, 0, 0, 0.4);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .messages {
    height: 120px;
  }
  .chat-header {
    padding: 8px 12px;
  }
  .chat-body {
    padding: 0 12px 10px;
  }
}
</style>
