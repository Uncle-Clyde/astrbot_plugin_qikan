<template>
  <div class="view-container location-view">
    <div class="nav-bar">
      <el-button class="nav-btn" @click="handleLeave">← 返回地图</el-button>
      <h2 class="nav-title">{{ locationInfo?.icon || '🏰' }} {{ locationInfo?.name || '据点' }}</h2>
      <span class="location-type-badge" :class="locationInfo?.type?.toLowerCase()">
        {{ locationTypeText }}
      </span>
      <button class="menu-btn" @click="openTownMenu">📜 据点菜单</button>
    </div>

    <div v-if="locationLoading" class="loading-overlay">
      <div class="loading-spinner">
        <div class="spinner"></div>
        <p>正在进入据点...</p>
      </div>
    </div>

    <div class="location-content" v-else-if="locationInfo">
      <p class="location-desc">{{ locationInfo.description }}</p>

      <div class="npc-section">
        <h3 class="section-title">👥 据点人物</h3>
        <div v-if="npcsLoading" class="npc-loading-placeholder">
          <div class="spinner small"></div>
          <p>加载人物信息...</p>
        </div>
        <div v-else class="npc-grid">
          <div
            v-for="npc in npcs"
            :key="npc.npc_id"
            class="npc-card"
            @click="openNPCDialog(npc)"
          >
            <div class="npc-header">
              <span class="npc-icon">{{ npc.icon }}</span>
              <div class="npc-info">
                <span class="npc-name">{{ npc.name }}</span>
                <span class="npc-title-text">{{ npc.title }}</span>
              </div>
            </div>
            <div class="npc-favor">
              <div class="favor-bar">
                <div class="favor-fill" :style="{ width: npc.favor + '%' }"></div>
              </div>
              <span class="favor-text">{{ npc.favor_level }} ({{ npc.favor }})</span>
            </div>
            <p class="npc-desc">{{ npc.description }}</p>
            <button class="npc-talk-btn">💬 对话</button>
          </div>
        </div>
      </div>

      <div class="rest-section" v-if="hasTavern">
        <h3 class="section-title">🍺 酒馆休息</h3>
        <div class="rest-card">
          <div class="rest-info">
            <p>费用: <strong>{{ restCost }} 第纳尔</strong></p>
            <p>效果: 恢复全部HP和体力</p>
            <p v-if="restCooldown > 0" class="cooldown-text">冷却中: {{ restCooldown }}秒</p>
            <p v-else class="ready-text">可以休息</p>
          </div>
          <button class="rest-btn" @click="handleRest" :disabled="restLoading || restCooldown > 0">
            {{ restLoading ? '休息中...' : '🍺 休息' }}
          </button>
        </div>
      </div>

      <div class="troop-heal-section" v-if="hasTroops">
        <h3 class="section-title">🏥 部队医疗</h3>
        <div class="heal-card">
          <div class="heal-info">
            <p v-if="troopHealInfo">
              统御: {{ troopHealInfo.leadership_level }}级 | 医疗速度: {{ troopHealInfo.medical_speed }}x | 可恢复: {{ troopHealInfo.heal_count }}人
            </p>
            <p v-else>点击查询部队医疗状态</p>
          </div>
          <button class="heal-btn" @click="handleHealTroops" :disabled="healTroopsLoading">
            {{ healTroopsLoading ? '医疗中...' : '🏥 医疗部队' }}
          </button>
        </div>
      </div>
    </div>

    <TownMenu
      :visible="townMenuVisible"
      :location-info="townMenuLocationInfo"
      :menu-items="townMenuItems"
      @close="townMenuVisible = false"
      @leave="handleLeave"
      @action="handleTownMenuAction"
    />

    <NPCDialog
      v-model:visible="dialogVisible"
      :npc="currentNPC"
      :dialog-data="currentDialogData"
      @action="handleDialogAction"
      @gift="openGiftSelector"
    />

    <GiftSelector
      v-model:visible="giftSelectorVisible"
      :npc="currentNPC"
      @confirm="handleGiftConfirm"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useGameStore } from '../stores/game'
import { ElMessage } from 'element-plus'
import NPCDialog from '../components/NPCDialog.vue'
import GiftSelector from '../components/GiftSelector.vue'
import TownMenu from '../components/TownMenu.vue'

const router = useRouter()
const route = useRoute()
const gameStore = useGameStore()

const locationInfo = ref(null)
const npcs = ref([])
const dialogVisible = ref(false)
const currentNPC = ref(null)
const currentDialogData = ref(null)
const giftSelectorVisible = ref(false)
const locationLoading = ref(false)

const townMenuVisible = ref(false)
const townMenuLocationInfo = ref(null)
const townMenuItems = ref([])

const factionNames = {
  '0': '斯瓦迪亚王国',
  '1': '维吉亚王国',
  '2': '诺德王国',
  '3': '罗多克王国',
  '4': '库吉特汗国',
  '5': '萨兰德苏丹国',
}

const locationTypeText = computed(() => {
  const type = locationInfo.value?.type || ''
  const map = { TOWN: '城镇', VILLAGE: '村庄', CASTLE: '城堡', BANDIT_CAMP: '匪窝' }
  return map[type] || '据点'
})

const hasBlacksmith = computed(() => locationInfo.value?.has_blacksmith)
const hasMerchant = computed(() => npcs.value.some(n => n.npc_type === 'merchant'))
const hasTavern = computed(() => npcs.value.some(n => n.npc_type === 'tavern_keeper'))
const hasTroops = computed(() => {
  const p = gameStore.player
  return p && (p.map_state?.current_location)
})

const restCost = computed(() => {
  const type = locationInfo.value?.type || ''
  if (type === 'TOWN') return 20
  if (type === 'VILLAGE') return 10
  if (type === 'CASTLE') return 15
  return 10
})

const restCooldown = ref(0)
const restLoading = ref(false)
const healTroopsLoading = ref(false)
const troopHealInfo = ref(null)

const openTownMenu = async () => {
  const locId = locationInfo.value?.location_id || route.query.location_id
  if (!locId) {
    ElMessage.warning('无法获取据点信息，请返回后重新进入')
    return
  }
  gameStore.send({
    type: 'get_town_menu',
    data: { location_id: locId }
  })
}

const handleTownMenuAction = async (item) => {
  const locId = locationInfo.value?.location_id || route.query.location_id
  if (!locId) return

  if (item.action === 'navigate') {
    townMenuVisible.value = false
    const query = { ...(item.query || {}) }
    if (!query.location_id) query.location_id = locId
    if (!query.village_id) query.village_id = locId
    router.push({ path: item.route, query })
    return
  }

  if (item.action === 'open_npc_dialog' && item.npc_id) {
    townMenuVisible.value = false
    const npc = npcs.value.find(n => n.npc_id === item.npc_id)
    if (npc) {
      openNPCDialog(npc)
    } else {
      currentNPC.value = { npc_id: item.npc_id, name: item.npc_name, icon: item.icon || '👤', title: '', description: '', favor: 0, favor_level: '陌生' }
      gameStore.send({
        type: 'start_npc_dialog',
        data: { npc_id: item.npc_id }
      })
    }
    return
  }

  if (item.action === 'rest') {
    townMenuVisible.value = false
    await handleRest()
    return
  }

  if (item.action === 'show_message') {
    townMenuVisible.value = false
    ElMessage.info(item.message || '功能开发中...')
    return
  }

  gameStore.send({
    type: 'town_menu_action',
    data: {
      action_id: item.id,
      location_id: locId,
      npc_id: item.npc_id || '',
    }
  })
}

const handleLeave = () => {
  townMenuVisible.value = false
  gameStore.send({ type: 'leave_location' })
  router.push('/map')
}

const openNPCDialog = async (npc) => {
  currentNPC.value = npc
  gameStore.send({
    type: 'start_npc_dialog',
    data: { npc_id: npc.npc_id }
  })
}

const handleDialogAction = (action, data) => {
  switch (action) {
    case 'open_shop':
      router.push({ path: '/trade', query: { location_id: locationInfo.value?.location_id } })
      break
    case 'open_blacksmith':
      router.push({ path: '/blacksmith', query: { location_id: locationInfo.value?.location_id } })
      break
    case 'show_quests':
      ElMessage.info('任务系统开发中...')
      break
    case 'rest':
      handleRest()
      break
    case 'close':
      dialogVisible.value = false
      break
  }
}

const openGiftSelector = (npc) => {
  currentNPC.value = npc
  giftSelectorVisible.value = true
}

const handleGiftConfirm = async (gift) => {
  giftSelectorVisible.value = false
  if (!gameStore.lockAction('gift')) {
    ElMessage.warning('请勿频繁操作')
    return
  }
  gameStore.setButtonLoading('gift', true)
  gameStore.send({
    type: 'give_gift_to_npc',
    data: {
      npc_id: currentNPC.value.npc_id,
      gift_id: gift.id,
    }
  })
  setTimeout(() => {
    gameStore.unlockAction('gift')
    gameStore.setButtonLoading('gift', false)
  }, 500)
}

const handleRest = async () => {
  restLoading.value = true
  try {
    const result = await gameStore.wsCall('rest_at_settlement')
    if (result?.success) {
      ElMessage.success(result.message)
      await gameStore.getPanel()
    } else {
      ElMessage.error(result?.message || '休息失败')
    }
  } catch (e) {
    ElMessage.error('请求失败')
  } finally {
    restLoading.value = false
  }
}

const handleHealTroops = async () => {
  healTroopsLoading.value = true
  try {
    const result = await gameStore.wsCall('heal_troops')
    if (result?.success) {
      ElMessage.success(result.message)
      troopHealInfo.value = result
      await gameStore.getPanel()
    } else {
      ElMessage.error(result?.message || '医疗失败')
    }
  } catch (e) {
    ElMessage.error('请求失败')
  } finally {
    healTroopsLoading.value = false
  }
}

const handleWsMessage = (msg) => {
  if (msg.type === 'action_result') {
    if (msg.action === 'enter_location' && msg.data?.success) {
      locationInfo.value = msg.data.location
      npcs.value = msg.data.npcs || []
      setTimeout(() => openTownMenu(), 500)
    } else if (msg.action === 'leave_location' && msg.data?.success) {
      ElMessage.success(msg.data.message)
    } else if (msg.action === 'start_npc_dialog' && msg.data?.success) {
      currentDialogData.value = msg.data.all_dialogs || {}
      dialogVisible.value = true
    } else if (msg.action === 'give_gift_to_npc' && msg.data?.success) {
      ElMessage.success(msg.data.message)
      if (currentNPC.value) {
        currentNPC.value.favor = msg.data.new_favor
        currentNPC.value.favor_level = msg.data.favor_level
        const idx = npcs.value.findIndex(n => n.npc_id === currentNPC.value.npc_id)
        if (idx >= 0) {
          npcs.value[idx].favor = msg.data.new_favor
          npcs.value[idx].favor_level = msg.data.favor_level
        }
      }
    } else if (msg.action === 'town_menu_action' && msg.data?.success) {
      if (msg.data.action === 'navigate') {
        townMenuVisible.value = false
        const query = { location_id: locationInfo.value?.location_id, ...(msg.data.query || {}) }
        router.push({ path: msg.data.route, query })
      } else if (msg.data.action === 'open_npc_dialog') {
        townMenuVisible.value = false
        const npc = npcs.value.find(n => n.npc_id === msg.data.npc_id)
        if (npc) {
          openNPCDialog(npc)
        }
      } else if (msg.data.action === 'rest') {
        townMenuVisible.value = false
        handleRest()
      } else if (msg.data.action === 'show_message') {
        townMenuVisible.value = false
        ElMessage.info(msg.data.message)
      } else {
        ElMessage.success(msg.data.message)
      }
    } else if (msg.action === 'get_village_industries' && msg.data?.success) {
    } else if (msg.action === 'build_industry' && msg.data?.success) {
      ElMessage.success(msg.data.message)
    } else if (msg.action === 'upgrade_industry' && msg.data?.success) {
      ElMessage.success(msg.data.message)
    } else if (msg.action === 'collect_industry_income' && msg.data?.success) {
      ElMessage.success(msg.data.message)
    } else if (msg.action === 'repair_industry' && msg.data?.success) {
      ElMessage.success(msg.data.message)
    } else if (msg.data?.success) {
      ElMessage.success(msg.data.message)
    } else if (msg.data?.message) {
      ElMessage.error(msg.data.message)
    }
  } else if (msg.type === 'town_menu' && msg.data?.success) {
    townMenuLocationInfo.value = msg.data.location
    townMenuItems.value = msg.data.menu_items || []
    townMenuVisible.value = true
  }
}

onMounted(async () => {
  if (!gameStore.token) {
    router.push('/')
    return
  }
  if (!gameStore.connected) {
    await gameStore.connectWs()
  }

  gameStore.wsMessageHandlers = gameStore.wsMessageHandlers || {}
  gameStore.wsMessageHandlers['location'] = handleWsMessage

  const locationId = route.query.location_id
  if (locationId) {
    gameStore.send({
      type: 'enter_location',
      data: { location_id: locationId }
    })
  }
})

onUnmounted(() => {
  if (gameStore.wsMessageHandlers && gameStore.wsMessageHandlers['location']) {
    delete gameStore.wsMessageHandlers['location']
  }
})
</script>

<style scoped>
.location-view {
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

.menu-btn {
  background: linear-gradient(135deg, rgba(212, 164, 100, 0.2), rgba(184, 134, 11, 0.2));
  border: 1px solid rgba(212, 164, 100, 0.4);
  color: #d4a464;
  padding: 6px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s;
  margin-left: auto;
}

.menu-btn:hover {
  background: linear-gradient(135deg, rgba(212, 164, 100, 0.3), rgba(184, 134, 11, 0.3));
  border-color: rgba(212, 164, 100, 0.6);
}

.nav-title {
  color: #fff;
  font-size: 20px;
  margin: 0;
}

.location-type-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.location-type-badge.town {
  background: rgba(74, 158, 255, 0.2);
  color: #4a9eff;
  border: 1px solid #4a9eff;
}

.location-type-badge.village {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
  border: 1px solid #22c55e;
}

.location-type-badge.castle {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  border: 1px solid #ef4444;
}

.location-content {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.location-desc {
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 24px;
}

.section-title {
  color: #fff;
  font-size: 18px;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.npc-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

.npc-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.npc-card:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
  transform: translateY(-2px);
}

.npc-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.npc-icon {
  font-size: 32px;
}

.npc-info {
  display: flex;
  flex-direction: column;
}

.npc-name {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
}

.npc-title-text {
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
}

.npc-favor {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.favor-bar {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
}

.favor-fill {
  height: 100%;
  background: linear-gradient(90deg, #4a9eff, #22c55e);
  border-radius: 3px;
  transition: width 0.3s;
}

.favor-text {
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
  white-space: nowrap;
}

.npc-desc {
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  line-height: 1.4;
  margin: 0 0 12px;
}

.npc-talk-btn {
  width: 100%;
  padding: 8px;
  background: rgba(74, 158, 255, 0.2);
  border: 1px solid rgba(74, 158, 255, 0.3);
  color: #4a9eff;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.npc-talk-btn:hover {
  background: rgba(74, 158, 255, 0.3);
}

.rest-section, .troop-heal-section {
  margin-top: 24px;
}

.rest-card, .heal-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
}

.rest-info, .heal-info {
  flex: 1;
}

.rest-info p, .heal-info p {
  margin: 4px 0;
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
}

.rest-info strong {
  color: #d4a464;
}

.cooldown-text {
  color: #f44336 !important;
}

.ready-text {
  color: #4caf50 !important;
}

.rest-btn, .heal-btn {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.rest-btn {
  background: linear-gradient(135deg, #d4a464, #b8860b);
  color: #1a1a2e;
}

.rest-btn:hover:not(:disabled) {
  opacity: 0.85;
  transform: translateY(-1px);
}

.rest-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.heal-btn {
  background: linear-gradient(135deg, #4caf50, #2e7d32);
  color: #fff;
}

.heal-btn:hover:not(:disabled) {
  opacity: 0.85;
  transform: translateY(-1px);
}

.heal-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
