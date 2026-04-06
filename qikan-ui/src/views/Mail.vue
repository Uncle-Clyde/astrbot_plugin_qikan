<template>
  <div class="view-container">
    <div class="nav-bar">
      <el-button @click="$router.push('/home')">← 返回</el-button>
      <h2>📧 邮件</h2>
      <el-button @click="loadMails">🔄 刷新</el-button>
    </div>
    
    <div class="mail-list">
      <el-empty v-if="mails.length === 0" description="暂无邮件" />
      
      <el-card 
        v-for="mail in mails" 
        :key="mail.mail_id" 
        class="mail-card"
        :class="{ 'unread': !mail.is_read }"
        @click="openMail(mail)"
      >
        <div class="mail-header">
          <span class="sender">{{ mail.sender_name }}</span>
          <span class="time">{{ formatTime(mail.created_at) }}</span>
        </div>
        <div class="mail-title">{{ mail.title }}</div>
        <div class="mail-preview">{{ mail.content?.substring(0, 50) }}...</div>
        <el-tag v-if="mail.attachments && Object.keys(mail.attachments).length > 0" type="warning" size="small">
          有附件
        </el-tag>
      </el-card>
    </div>

    <el-dialog v-model="showMailDetail" :title="currentMail?.title" width="500px">
      <div v-if="currentMail">
        <p><strong>发件人：</strong>{{ currentMail.sender_name }}</p>
        <p><strong>时间：</strong>{{ formatTime(currentMail.created_at) }}</p>
        <el-divider />
        <div class="mail-content">{{ currentMail.content }}</div>
        
        <div v-if="currentMail.attachments && Object.keys(currentMail.attachments).length > 0" class="attachments">
          <el-divider />
          <h4>附件：</h4>
          <div v-if="currentMail.attachments.stones">
            <el-tag type="warning">第纳尔 x{{ currentMail.attachments.stones }}</el-tag>
          </div>
          <div v-if="currentMail.attachments.items">
            <el-tag v-for="(item, idx) in currentMail.attachments.items" :key="idx" type="success" style="margin-right: 5px">
              {{ item.name || item }}
            </el-tag>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="claimAndDelete" type="primary" v-if="currentMail?.attachments && Object.keys(currentMail.attachments).length > 0">
          领取附件
        </el-button>
        <el-button @click="deleteMail">删除</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const gameStore = useGameStore()
const mails = ref([])
const showMailDetail = ref(false)
const currentMail = ref(null)

const loadMails = async () => {
  try {
    const res = await axios.get(`/api/mail/list?user_id=${gameStore.userId}`)
    if (res.data.success) {
      mails.value = res.data.mails || []
    }
  } catch (e) {
    ElMessage.error('加载邮件失败')
  }
}

const openMail = async (mail) => {
  currentMail.value = mail
  try {
    await axios.get(`/api/mail/${mail.mail_id}?user_id=${gameStore.userId}`)
    mail.is_read = true
  } catch (e) {}
  showMailDetail.value = true
}

const claimAndDelete = async () => {
  if (!currentMail.value) return
  try {
    const res = await axios.post(`/api/mail/${currentMail.value.mail_id}/claim?user_id=${gameStore.userId}`)
    if (res.data.success) {
      ElMessage.success('领取成功')
      showMailDetail.value = false
      loadMails()
    } else {
      ElMessage.error(res.data.message || '领取失败')
    }
  } catch (e) {
    ElMessage.error('领取失败')
  }
}

const deleteMail = async () => {
  if (!currentMail.value) return
  try {
    await axios.post(`/api/mail/${currentMail.value.mail_id}/delete?user_id=${gameStore.userId}`)
    showMailDetail.value = false
    loadMails()
    ElMessage.success('删除成功')
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN')
}

onMounted(async () => {
  if (!gameStore.token) {
    router.push('/')
    return
  }
  loadMails()
})
</script>

<style scoped>
.mail-list {
  padding: 10px;
  max-height: calc(100vh - 120px);
  overflow-y: auto;
}
.mail-card {
  margin-bottom: 10px;
  cursor: pointer;
}
.mail-card.unread {
  border-left: 3px solid #409eff;
}
.mail-header {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #666;
}
.mail-title {
  font-weight: bold;
  margin: 5px 0;
}
.mail-preview {
  font-size: 12px;
  color: #999;
}
.mail-content {
  white-space: pre-wrap;
  line-height: 1.6;
}
</style>
