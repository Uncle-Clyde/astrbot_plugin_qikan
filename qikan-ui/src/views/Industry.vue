<template>
  <div class="view-container industry-view">
    <div class="nav-bar">
      <button class="nav-btn" @click="handleBack">← 返回村庄</button>
      <h2 class="nav-title">{{ villageInfo?.icon || '🏘️' }} {{ villageInfo?.name || '村庄' }} · 产业管理</h2>
      <span class="village-type">{{ villageTypeText }}</span>
    </div>

    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
      <p>加载产业信息...</p>
    </div>

    <div v-else-if="villageInfo" class="industry-content">
      <!-- 村庄信息 -->
      <div class="village-info">
        <div class="info-row">
          <span>好感度: <strong>{{ playerFavor }}</strong></span>
          <span>繁荣度: <strong>{{ villageInfo.prosperity }}</strong></span>
          <span>产出: <strong>{{ villageInfo.production }}</strong></span>
        </div>
      </div>

      <!-- 已建造产业 -->
      <div class="section">
        <h3 class="section-title">
          📊 已建造产业 ({{ builtIndustries.total_count || 0 }}/{{ builtIndustries.max_count || 5 }})
        </h3>

        <div v-if="!builtIndustries.industries?.length" class="empty-msg">
          尚未建造任何产业
        </div>

        <div v-else class="industry-grid">
          <div
            v-for="ind in builtIndustries.industries"
            :key="ind.industry_id"
            class="industry-card"
            :class="{ damaged: ind.status !== 'intact' }"
          >
            <div class="ind-header">
              <span class="ind-icon">{{ ind.icon }}</span>
              <div class="ind-info">
                <span class="ind-name">{{ ind.name }} Lv.{{ ind.level }}</span>
                <span class="ind-status" :class="ind.status">{{ ind.status_name }}</span>
              </div>
            </div>

            <p class="ind-desc">{{ ind.description }}</p>

            <div class="ind-output" v-if="ind.pending_income > 0 || ind.pending_resource_amount > 0">
              <span v-if="ind.pending_income > 0">💰 +{{ ind.pending_income }}</span>
              <span v-if="ind.pending_resource_amount > 0">📦 {{ ind.pending_resource_type }}×{{ ind.pending_resource_amount }}</span>
              <span class="ind-hours">({{ ind.hours_since_collect }}小时前)</span>
            </div>
            <div v-else class="ind-output empty">暂无产出</div>

            <div class="ind-actions">
              <button
                v-if="ind.pending_income > 0 || ind.pending_resource_amount > 0"
                class="action-btn collect"
                @click="handleCollect(ind)"
                :disabled="collecting"
              >
                {{ collecting ? '收取中...' : '📥 收取' }}
              </button>
              <button
                v-if="ind.can_repair"
                class="action-btn repair"
                @click="handleRepair(ind)"
                :disabled="repairing"
              >
                🔧 修复 (💰{{ ind.repair_cost }})
              </button>
              <button
                v-if="ind.can_upgrade"
                class="action-btn upgrade"
                @click="handleUpgrade(ind)"
                :disabled="upgrading"
              >
                ⬆️ 升级 (💰{{ ind.upgrade_cost }})
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 可建造产业 -->
      <div class="section" v-if="availableIndustries.length > 0">
        <h3 class="section-title">🔨 可建造产业</h3>
        <div class="industry-grid">
          <div
            v-for="ind in availableIndustries"
            :key="ind.industry_id"
            class="industry-card buildable"
          >
            <div class="ind-header">
              <span class="ind-icon">{{ ind.icon }}</span>
              <div class="ind-info">
                <span class="ind-name">{{ ind.name }}</span>
                <span class="ind-type">{{ ind.industry_type }}</span>
              </div>
            </div>

            <p class="ind-desc">{{ ind.description }}</p>

            <div class="ind-requirements">
              <span>💰 费用: {{ ind.base_cost }}</span>
              <span v-if="ind.resource_type">📦 产出: {{ ind.resource_type }}×{{ ind.base_resource_amount }}/日</span>
              <span v-else>💰 收入: {{ ind.base_daily_income }}/日</span>
              <span>❤️ 好感: {{ ind.required_favor }}</span>
            </div>

            <button
              class="action-btn build"
              @click="handleBuild(ind)"
              :disabled="building"
            >
              {{ building ? '建造中...' : '🏗️ 建造' }}
            </button>
          </div>
        </div>
      </div>

      <div v-else class="empty-section">
        <p>没有可建造的产业（可能已达上限或条件不足）</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useGameStore } from '../stores/game'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const gameStore = useGameStore()

const loading = ref(false)
const villageInfo = ref(null)
const playerFavor = ref(0)
const builtIndustries = ref({ industries: [], total_count: 0, max_count: 5 })
const availableIndustries = ref([])
const collecting = ref(false)
const building = ref(false)
const upgrading = ref(false)
const repairing = ref(false)

const villageTypeText = computed(() => {
  const type = villageInfo.value?.type || ''
  const map = { 农业: '农业村', 渔业: '渔业村', 畜牧: '畜牧村', 矿业: '矿业村' }
  return map[type] || '村庄'
})

const loadIndustries = async () => {
  const villageId = route.query.village_id
  if (!villageId) {
    ElMessage.warning('缺少村庄ID')
    router.push('/map')
    return
  }

  loading.value = true
  try {
    const result = await gameStore.wsCall('get_village_industries', { village_id: villageId })
    if (result?.success) {
      villageInfo.value = result.village
      playerFavor.value = result.player_favor || 0
      builtIndustries.value = result.built_industries || { industries: [], total_count: 0, max_count: 5 }
      availableIndustries.value = result.available_industries || []
    } else {
      ElMessage.error(result?.message || '加载失败')
    }
  } catch (e) {
    ElMessage.error('请求失败')
  } finally {
    loading.value = false
  }
}

const handleCollect = async (ind) => {
  const villageId = route.query.village_id
  collecting.value = true
  try {
    const result = await gameStore.wsCall('collect_industry_income', { village_id: villageId })
    if (result?.success) {
      let msg = result.message
      if (result.total_income > 0) msg += ` (+${result.total_income}💰)`
      if (result.total_resources) {
        const res = Object.entries(result.total_resources).map(([k, v]) => `${k}×${v}`).join(', ')
        if (res) msg += ` (${res})`
      }
      ElMessage.success(msg)
      await gameStore.getPanel()
      await loadIndustries()
    } else {
      ElMessage.error(result?.message || '收取失败')
    }
  } catch (e) {
    ElMessage.error('请求失败')
  } finally {
    collecting.value = false
  }
}

const handleBuild = async (ind) => {
  const villageId = route.query.village_id
  building.value = true
  try {
    const result = await gameStore.wsCall('build_industry', {
      village_id: villageId,
      industry_id: ind.industry_id,
    })
    if (result?.success) {
      ElMessage.success(result.message)
      await gameStore.getPanel()
      await loadIndustries()
    } else {
      ElMessage.error(result?.message || '建造失败')
    }
  } catch (e) {
    ElMessage.error('请求失败')
  } finally {
    building.value = false
  }
}

const handleUpgrade = async (ind) => {
  const villageId = route.query.village_id
  upgrading.value = true
  try {
    const result = await gameStore.wsCall('upgrade_industry', {
      village_id: villageId,
      industry_id: ind.industry_id,
    })
    if (result?.success) {
      ElMessage.success(result.message)
      await gameStore.getPanel()
      await loadIndustries()
    } else {
      ElMessage.error(result?.message || '升级失败')
    }
  } catch (e) {
    ElMessage.error('请求失败')
  } finally {
    upgrading.value = false
  }
}

const handleRepair = async (ind) => {
  const villageId = route.query.village_id
  repairing.value = true
  try {
    const result = await gameStore.wsCall('repair_industry', {
      village_id: villageId,
      industry_id: ind.industry_id,
    })
    if (result?.success) {
      ElMessage.success(result.message)
      await gameStore.getPanel()
      await loadIndustries()
    } else {
      ElMessage.error(result?.message || '修复失败')
    }
  } catch (e) {
    ElMessage.error('请求失败')
  } finally {
    repairing.value = false
  }
}

const handleBack = () => {
  const locId = route.query.location_id || route.query.village_id
  if (locId) {
    router.push({ path: '/location', query: { location_id: locId } })
  } else {
    router.push('/map')
  }
}

onMounted(() => {
  loadIndustries()
})
</script>

<style scoped>
.industry-view {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  min-height: 100vh;
}

.nav-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 20px;
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  flex-wrap: wrap;
}

.nav-btn {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
  padding: 6px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.nav-title {
  color: #fff;
  font-size: 18px;
  margin: 0;
}

.village-type {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
  border: 1px solid rgba(34, 197, 94, 0.4);
}

.industry-content {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.village-info {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 24px;
}

.info-row {
  display: flex;
  gap: 24px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
}

.info-row strong {
  color: #d4a464;
}

.section {
  margin-bottom: 32px;
}

.section-title {
  color: #fff;
  font-size: 18px;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.empty-msg, .empty-section {
  text-align: center;
  color: rgba(255, 255, 255, 0.4);
  padding: 40px;
  font-size: 14px;
}

.industry-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.industry-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.2s;
}

.industry-card:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.2);
}

.industry-card.damaged {
  border-color: rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.05);
}

.industry-card.buildable {
  border-color: rgba(74, 158, 255, 0.2);
}

.ind-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.ind-icon {
  font-size: 28px;
}

.ind-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.ind-name {
  color: #fff;
  font-size: 15px;
  font-weight: 600;
}

.ind-status {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 3px;
}

.ind-status.intact {
  color: #4caf50;
  background: rgba(76, 175, 80, 0.15);
}

.ind-status.light_damage {
  color: #ff9800;
  background: rgba(255, 152, 0, 0.15);
}

.ind-status.heavy_damage {
  color: #f44336;
  background: rgba(244, 67, 54, 0.15);
}

.ind-status.destroyed {
  color: #9e9e9e;
  background: rgba(158, 158, 158, 0.15);
}

.ind-type {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
}

.ind-desc {
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
  line-height: 1.4;
  margin: 0 0 12px;
}

.ind-output {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
  font-size: 13px;
  color: #d4a464;
  margin-bottom: 12px;
}

.ind-output.empty {
  color: rgba(255, 255, 255, 0.3);
}

.ind-hours {
  color: rgba(255, 255, 255, 0.4);
  font-size: 11px;
}

.ind-requirements {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 12px;
}

.ind-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.action-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-btn.collect {
  background: linear-gradient(135deg, #4caf50, #2e7d32);
  color: #fff;
}

.action-btn.collect:hover:not(:disabled) {
  opacity: 0.85;
}

.action-btn.repair {
  background: linear-gradient(135deg, #ff9800, #e65100);
  color: #fff;
}

.action-btn.repair:hover:not(:disabled) {
  opacity: 0.85;
}

.action-btn.upgrade {
  background: linear-gradient(135deg, #2196f3, #0d47a1);
  color: #fff;
}

.action-btn.upgrade:hover:not(:disabled) {
  opacity: 0.85;
}

.action-btn.build {
  width: 100%;
  background: linear-gradient(135deg, #d4a464, #b8860b);
  color: #1a1a2e;
}

.action-btn.build:hover:not(:disabled) {
  opacity: 0.85;
}

.loading-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  color: rgba(255, 255, 255, 0.6);
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: #d4a464;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 12px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
