<template>
  <div class="view-container">
    <div class="nav-bar">
      <el-button @click="$router.push('/home')">← 返回</el-button>
      <h2>📜 称号</h2>
      <el-button @click="loadTitles">🔄 刷新</el-button>
    </div>
    
    <div class="title-list">
      <el-card 
        v-for="title in titles" 
        :key="title.title_id" 
        class="title-card"
        :class="{ 'owned': title.owned, 'active': title.is_active }"
      >
        <div class="title-icon" :style="{ color: title.color }">{{ title.icon }}</div>
        <div class="title-info">
          <h3 :style="{ color: title.color }">{{ title.prefix || title.name }}</h3>
          <p>{{ title.description }}</p>
          <div class="title-bonus" v-if="title.bonus_attack || title.bonus_defense || title.bonus_hp">
            <el-tag size="small" v-if="title.bonus_attack">攻击+{{ title.bonus_attack }}</el-tag>
            <el-tag size="small" v-if="title.bonus_defense">防御+{{ title.bonus_defense }}</el-tag>
            <el-tag size="small" v-if="title.bonus_hp">生命+{{ title.bonus_hp }}</el-tag>
          </div>
        </div>
        <div class="title-actions">
          <el-button 
            v-if="title.owned && !title.is_active" 
            type="primary" 
            size="small"
            @click="activateTitle(title)"
          >
            佩戴
          </el-button>
          <el-button 
            v-if="title.is_active" 
            size="small"
            @click="deactivateTitle"
          >
            取下
          </el-button>
          <el-tag v-if="!title.owned" type="info" size="small">
            未获得
          </el-tag>
        </div>
      </el-card>
    </div>
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
const titles = ref([])

const loadTitles = async () => {
  try {
    const res = await axios.get(`/api/titles?user_id=${gameStore.userId}`)
    if (res.data.success) {
      titles.value = res.data.titles || []
    }
  } catch (e) {
    ElMessage.error('加载称号失败')
  }
}

const activateTitle = async (title) => {
  try {
    const res = await axios.post(`/api/titles/activate?user_id=${gameStore.userId}&title_id=${title.title_id}`)
    if (res.data.success) {
      titles.value.forEach(t => t.is_active = false)
      title.is_active = true
      ElMessage.success('佩戴成功')
    } else {
      ElMessage.error(res.data.message || '佩戴失败')
    }
  } catch (e) {
    ElMessage.error('佩戴失败')
  }
}

const deactivateTitle = async () => {
  try {
    const res = await axios.post(`/api/titles/deactivate?user_id=${gameStore.userId}`)
    if (res.data.success) {
      titles.value.forEach(t => t.is_active = false)
      ElMessage.success('取下成功')
    } else {
      ElMessage.error('取下失败')
    }
  } catch (e) {
    ElMessage.error('取下失败')
  }
}

onMounted(async () => {
  if (!gameStore.token) {
    router.push('/')
    return
  }
  loadTitles()
})
</script>

<style scoped>
.title-list {
  padding: 10px;
  max-height: calc(100vh - 120px);
  overflow-y: auto;
}
.title-card {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 15px;
}
.title-card.owned {
  border-color: #409eff;
}
.title-card.active {
  border-color: #67c23a;
  background: #f0f9ff;
}
.title-icon {
  font-size: 32px;
  width: 50px;
  text-align: center;
}
.title-info {
  flex: 1;
}
.title-info h3 {
  margin: 0 0 5px 0;
}
.title-info p {
  margin: 0 0 5px 0;
  color: #666;
  font-size: 12px;
}
.title-bonus {
  display: flex;
  gap: 5px;
}
.title-actions {
  min-width: 80px;
  text-align: center;
}
</style>
