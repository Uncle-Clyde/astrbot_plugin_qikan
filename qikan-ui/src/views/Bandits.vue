<template>
  <div class="view-container">
    <div class="page-header">
      <el-button class="back-btn" @click="$router.push('/home')">← 返回</el-button>
      <h2>⚔️ 山贼讨伐</h2>
      <div class="player-stats">
        <span>❤️ {{ player?.hp ?? 0 }}/{{ player?.max_hp ?? 100 }}</span>
        <span>💰 {{ player?.spirit_stones ?? 0 }} 第纳尔</span>
      </div>
    </div>

    <div class="bandits-content">
      <div class="section-tabs">
        <button class="tab-btn" :class="{ active: activeTab === 'nearby' }" @click="activeTab = 'nearby'">
          🗺️ 附近山贼
        </button>
        <button class="tab-btn" :class="{ active: activeTab === 'all' }" @click="activeTab = 'all'">
          📋 全部山贼
        </button>
      </div>

      <div v-if="loading" class="loading-state">加载中...</div>

      <div v-else-if="bandits.length === 0" class="empty-state">
        <p>{{ activeTab === 'nearby' ? '附近没有山贼' : '暂无山贼数据' }}</p>
      </div>

      <div v-else class="bandits-grid">
        <div v-for="b in bandits" :key="b.id" class="bandit-card">
          <div class="bandit-header">
            <div class="bandit-icon">{{ b.icon || '👹' }}</div>
            <div class="bandit-info">
              <h3>{{ b.name }}</h3>
              <span class="bandit-type">{{ b.type_name || b.type }}</span>
            </div>
          </div>
          <div class="bandit-stats">
            <div class="stat"><span>❤️ 生命</span><span>{{ b.hp || '?' }}</span></div>
            <div class="stat"><span>⚔️ 攻击</span><span>{{ b.attack || '?' }}</span></div>
            <div class="stat"><span>🛡️ 防御</span><span>{{ b.defense || '?' }}</span></div>
          </div>
          <div class="bandit-rewards" v-if="b.rewards">
            <span>掉落: {{ b.rewards }}</span>
          </div>
          <div class="bandit-actions">
            <el-button size="small" @click="viewBanditInfo(b)">查看</el-button>
            <el-button type="danger" size="small" @click="attackBandit(b)" :loading="attacking === b.id">
              ⚔️ 攻击
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="infoDialogVisible" title="山贼详情" width="500px">
      <div v-if="selectedBandit" class="bandit-detail">
        <h3>{{ selectedBandit.icon || '👹' }} {{ selectedBandit.name }}</h3>
        <p>{{ selectedBandit.description || '暂无描述' }}</p>
        <div class="detail-stats">
          <p>生命: {{ selectedBandit.hp || '?' }}</p>
          <p>攻击: {{ selectedBandit.attack || '?' }}</p>
          <p>防御: {{ selectedBandit.defense || '?' }}</p>
          <p>类型: {{ selectedBandit.type_name || selectedBandit.type }}</p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { ElMessage } from 'element-plus'

const router = useRouter()
const gameStore = useGameStore()
const player = computed(() => gameStore.player)
const activeTab = ref('nearby')
const bandits = ref([])
const loading = ref(false)
const attacking = ref(null)
const infoDialogVisible = ref(false)
const selectedBandit = ref(null)

const loadBandits = async () => {
  loading.value = true
  try {
    if (activeTab.value === 'nearby') {
      const resp = await fetch('/api/bandits/nearby')
      const data = await resp.json()
      bandits.value = data.bandits || []
    } else {
      const resp = await fetch('/api/bandits')
      const data = await resp.json()
      bandits.value = data.bandits || []
    }
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const viewBanditInfo = async (bandit) => {
  selectedBandit.value = bandit
  infoDialogVisible.value = true
}

const attackBandit = async (bandit) => {
  attacking.value = bandit.id
  try {
    const result = await gameStore.wsCall('attack_bandit', { bandit_id: bandit.id })
    if (result?.success) {
      ElMessage.success(result.message || '攻击成功')
      await loadBandits()
    } else {
      ElMessage.error(result?.message || '攻击失败')
    }
  } catch (e) {
    ElMessage.error('请求失败')
  } finally {
    attacking.value = null
  }
}

onMounted(() => {
  loadBandits()
})
</script>

<style scoped>
.view-container {
  padding: 16px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  flex: 1;
  color: #d4a464;
}

.player-stats {
  display: flex;
  gap: 16px;
  color: #aaa;
  font-size: 14px;
}

.section-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.tab-btn {
  padding: 8px 20px;
  background: rgba(20, 20, 35, 0.9);
  border: 1px solid #2a2a3e;
  border-radius: 6px;
  color: #888;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}

.tab-btn:hover {
  border-color: #d4a464;
  color: #e8e0d0;
}

.tab-btn.active {
  background: rgba(212, 164, 100, 0.2);
  border-color: #d4a464;
  color: #d4a464;
}

.loading-state, .empty-state {
  text-align: center;
  padding: 40px;
  color: #666;
}

.bandits-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.bandit-card {
  background: rgba(20, 20, 35, 0.9);
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 16px;
  transition: border-color 0.2s;
}

.bandit-card:hover {
  border-color: #d4a464;
}

.bandit-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.bandit-icon {
  font-size: 36px;
}

.bandit-info h3 {
  margin: 0;
  color: #e8e0d0;
  font-size: 16px;
}

.bandit-type {
  font-size: 12px;
  color: #888;
}

.bandit-stats {
  display: flex;
  gap: 12px;
  margin: 8px 0;
}

.stat {
  display: flex;
  gap: 4px;
  font-size: 13px;
  color: #888;
}

.stat span:last-child {
  color: #e8e0d0;
  font-weight: bold;
}

.bandit-rewards {
  font-size: 12px;
  color: #d4a464;
  margin: 8px 0;
}

.bandit-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.bandit-detail h3 {
  color: #e8e0d0;
  margin: 0 0 8px;
}

.bandit-detail p {
  color: #aaa;
  margin: 4px 0;
}

.detail-stats {
  margin-top: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
}

.detail-stats p {
  margin: 4px 0;
}
</style>
