<template>
  <div class="view-container">
    <div class="nav-bar">
      <el-button @click="$router.push('/home')">← 返回</el-button>
      <h2>🏆 成就</h2>
      <el-button @click="loadAchievements">🔄 刷新</el-button>
    </div>
    
    <div class="achievement-list">
      <el-card 
        v-for="achievement in achievements" 
        :key="achievement.achievement_id" 
        class="achievement-card"
        :class="{ 
          'completed': achievement.completed,
          'claimed': achievement.claimed 
        }"
      >
        <div class="achievement-icon">{{ achievement.icon }}</div>
        <div class="achievement-info">
          <h3>{{ achievement.name }}</h3>
          <p>{{ achievement.description }}</p>
          <div class="progress-bar">
            <el-progress 
              :percentage="getProgressPercent(achievement)" 
              :status="achievement.completed ? 'success' : ''"
            />
          </div>
          <div class="progress-text">
            {{ achievement.progress || 0 }} / {{ achievement.condition_value }}
          </div>
        </div>
        <div class="achievement-rewards">
          <el-tag v-if="achievement.reward_stones" type="warning">
            第纳尔 x{{ achievement.reward_stones }}
          </el-tag>
          <el-tag v-if="achievement.reward_title" type="success">
            称号: {{ achievement.reward_title }}
          </el-tag>
        </div>
        <div class="achievement-actions">
          <el-button 
            v-if="achievement.completed && !achievement.claimed" 
            type="primary" 
            size="small"
            @click="claimReward(achievement)"
          >
            领取奖励
          </el-button>
          <el-tag v-else-if="achievement.claimed" type="info" size="small">
            已领取
          </el-tag>
          <el-tag v-else-if="!achievement.completed" type="info" size="small">
            进行中
          </el-tag>
          <el-tag v-else type="success" size="small">
            完成
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
const achievements = ref([])

const loadAchievements = async () => {
  try {
    const res = await axios.get(`/api/achievements?user_id=${gameStore.userId}`)
    if (res.data.success) {
      achievements.value = res.data.achievements || []
    }
  } catch (e) {
    ElMessage.error('加载成就失败')
  }
}

const getProgressPercent = (achievement) => {
  const current = achievement.progress || 0
  const target = achievement.condition_value || 1
  return Math.min(100, Math.round((current / target) * 100))
}

const claimReward = async (achievement) => {
  try {
    const res = await axios.post(`/api/achievements/${achievement.achievement_id}/claim?user_id=${gameStore.userId}`)
    if (res.data.success) {
      ElMessage.success('领取成功')
      achievement.claimed = true
    } else {
      ElMessage.error(res.data.message || '领取失败')
    }
  } catch (e) {
    ElMessage.error('领取失败')
  }
}

onMounted(async () => {
  if (!gameStore.token) {
    router.push('/')
    return
  }
  loadAchievements()
})
</script>

<style scoped>
.achievement-list {
  padding: 10px;
  max-height: calc(100vh - 120px);
  overflow-y: auto;
}
.achievement-card {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 15px;
}
.achievement-card.completed {
  border-color: #67c23a;
}
.achievement-card.claimed {
  opacity: 0.7;
}
.achievement-icon {
  font-size: 32px;
  width: 50px;
  text-align: center;
}
.achievement-info {
  flex: 1;
}
.achievement-info h3 {
  margin: 0 0 5px 0;
}
.achievement-info p {
  margin: 0 0 10px 0;
  color: #666;
  font-size: 12px;
}
.progress-bar {
  width: 150px;
}
.progress-text {
  font-size: 12px;
  color: #999;
  margin-top: 5px;
}
.achievement-rewards {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.achievement-actions {
  min-width: 80px;
  text-align: center;
}
</style>
