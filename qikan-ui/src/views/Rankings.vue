<template>
  <div class="view-container">
    <div class="page-header">
      <el-button class="back-btn" @click="$router.push('/home')">← 返回</el-button>
      <h2>📊 排行榜</h2>
    </div>

    <div class="rankings-content">
      <div class="rank-tabs">
        <button class="tab-btn" :class="{ active: activeTab === 'level' }" @click="activeTab = 'level'">
          📈 等级
        </button>
        <button class="tab-btn" :class="{ active: activeTab === 'dao_yun' }" @click="activeTab = 'dao_yun'">
          ⭐ 声望
        </button>
        <button class="tab-btn" :class="{ active: activeTab === 'gold' }" @click="activeTab = 'gold'">
          💰 财富
        </button>
        <button class="tab-btn" :class="{ active: activeTab === 'combat' }" @click="activeTab = 'combat'">
          ⚔️ 战斗力
        </button>
      </div>

      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else-if="rankings.length === 0" class="empty-state">
        <p>暂无排行数据</p>
      </div>
      <div v-else class="rankings-table">
        <div v-for="(r, idx) in rankings" :key="r.user_id" class="rank-row" :class="{ 'is-me': r.is_me }">
          <div class="rank-number">
            <span v-if="idx === 0" class="rank-medal gold">🥇</span>
            <span v-else-if="idx === 1" class="rank-medal silver">🥈</span>
            <span v-else-if="idx === 2" class="rank-medal bronze">🥉</span>
            <span v-else class="rank-num">{{ idx + 1 }}</span>
          </div>
          <div class="rank-name">{{ r.name }}</div>
          <div class="rank-realm">{{ r.realm_name || '平民' }}</div>
          <div class="rank-value">
            <template v-if="activeTab === 'level'">{{ r.level }}级</template>
            <template v-else-if="activeTab === 'dao_yun'">{{ r.dao_yun }}</template>
            <template v-else-if="activeTab === 'gold'">{{ r.spirit_stones }}</template>
            <template v-else>{{ r.total_attack + r.total_defense }}</template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'

const router = useRouter()
const gameStore = useGameStore()
const activeTab = ref('level')
const rankings = ref([])
const loading = ref(false)

const loadRankings = async () => {
  loading.value = true
  try {
    const result = await gameStore.wsCall('get_rankings', { type: activeTab.value })
    if (result?.rankings) {
      const currentUserId = gameStore.player?.user_id
      rankings.value = result.rankings.map(r => ({
        ...r,
        is_me: r.user_id === currentUserId,
      }))
    }
  } catch (e) {
    console.error('加载排行失败', e)
  } finally {
    loading.value = false
  }
}

watch(activeTab, () => {
  loadRankings()
})

onMounted(() => {
  loadRankings()
})
</script>

<style scoped>
.view-container {
  padding: 16px;
  max-width: 800px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.page-header h2 { margin: 0; flex: 1; color: #d4a464; }

.rank-tabs {
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

.rankings-table {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rank-row {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: rgba(20, 20, 35, 0.9);
  border: 1px solid #2a2a3e;
  border-radius: 6px;
  transition: all 0.2s;
}

.rank-row.is-me {
  border-color: #d4a464;
  background: rgba(212, 164, 100, 0.1);
}

.rank-number {
  width: 50px;
  text-align: center;
  font-size: 18px;
}

.rank-medal { font-size: 24px; }
.rank-num { color: #888; }

.rank-name {
  flex: 1;
  color: #e8e0d0;
  font-size: 14px;
  font-weight: bold;
}

.rank-realm {
  color: #888;
  font-size: 12px;
  width: 80px;
  text-align: center;
}

.rank-value {
  color: #d4a464;
  font-size: 16px;
  font-weight: bold;
  width: 100px;
  text-align: right;
}
</style>
