<template>
  <div class="home-container">
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <h2>⚔️ 骑砍英雄传</h2>
        </div>
        <div class="header-center">
          <el-button-group>
            <el-button @click="currentView = 'panel'">角色</el-button>
            <el-button @click="currentView = 'inventory'">背包</el-button>
            <el-button @click="$router.push('/skills')">技能</el-button>
            <el-button @click="$router.push('/map')">地图</el-button>
            <el-button @click="$router.push('/family')">家族</el-button>
            <el-button @click="$router.push('/market')">集市</el-button>
            <el-button @click="$router.push('/chat')">世界</el-button>
            <el-button @click="$router.push('/icons')">图标</el-button>
          </el-button-group>
        </div>
        <div class="header-right">
          <el-button @click="handleLogout" type="danger" size="small">退出</el-button>
        </div>
      </el-header>
      
      <el-main>
        <div v-if="currentView === 'panel'" class="panel-view">
          <el-row :gutter="20">
            <el-col :span="16">
              <el-card class="player-card">
                <template #header>
                  <div class="card-header">
                    <span>{{ player?.name || '未知' }}</span>
                    <el-tag :type="realmTagType">{{ player?.realm_name || '平民' }}</el-tag>
                  </div>
                </template>
                
                <div class="stats-grid">
                  <div class="stat-item">
                    <span class="label">等级</span>
                    <span class="value">{{ player?.level || 1 }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="label">经验</span>
                    <span class="value">{{ player?.exp || 0 }}/{{ player?.exp_next || 100 }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="label">生命</span>
                    <span class="value">{{ player?.hp || 0 }}/{{ player?.max_hp || 100 }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="label">攻击</span>
                    <span class="value">{{ player?.total_attack || 0 }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="label">防御</span>
                    <span class="value">{{ player?.total_defense || 0 }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="label">第纳尔</span>
                    <span class="value">{{ player?.spirit_stones || 0 }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="label">体力</span>
                    <span class="value">{{ player?.lingqi || 0 }}/{{ player?.max_lingqi || 50 }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="label">声望</span>
                    <span class="value">{{ player?.dao_yun || 0 }}</span>
                  </div>
                </div>

                <div class="action-buttons">
                  <el-button type="success" @click="handleCheckin">签到</el-button>
                  <el-button type="primary" @click="handleStartAfk">挂机</el-button>
                  <el-button type="warning" @click="handleAdventure">征战</el-button>
                  <el-button type="info" @click="handleBandits">讨伐</el-button>
                </div>
              </el-card>

              <el-card class="equipment-card" style="margin-top: 20px;">
                <template #header>
                  <span>装备栏</span>
                </template>
                <div class="equipment-grid">
                  <div 
                    v-for="slot in equipmentSlots" 
                    :key="slot.key"
                    class="equip-slot"
                    :class="{ empty: !player?.equipment?.[slot.key] }"
                    @click="handleEquipClick(slot.key)"
                  >
                    <div class="slot-icon">{{ slot.icon }}</div>
                    <div class="slot-name">{{ slot.name }}</div>
                    <div class="slot-item" v-if="player?.equipment?.[slot.key]">
                      {{ player.equipment[slot.key].name }}
                    </div>
                    <div class="slot-empty" v-else>未装备</div>
                  </div>
                </div>

                <div class="equip-section" v-if="player?.mounted">
                  <h4>🐎 坐骑装备</h4>
                  <div class="equip-grid">
                    <div 
                      v-for="slot in mountSlots" 
                      :key="slot.key"
                      class="equip-slot"
                      :class="{ empty: !player?.equipped_mount_items?.[slot.key] }"
                      @click="handleMountEquipClick(slot.key)"
                    >
                      <div class="slot-icon">{{ slot.icon }}</div>
                      <div class="slot-name">{{ slot.name }}</div>
                      <div class="slot-item" v-if="player?.equipped_mount_items?.[slot.key]">
                        {{ player.equipped_mount_items[slot.key].name }}
                      </div>
                      <div class="slot-empty" v-else>未装备</div>
                    </div>
                  </div>
                </div>
              </el-card>
            </el-col>
            
            <el-col :span="8">
              <el-card class="info-card">
                <template #header>
                  <span>当前位置</span>
                </template>
                <div class="location-info">
                  <p>{{ player?.location || '流浪中' }}</p>
                  <p v-if="player?.faction">阵营: {{ player.faction }}</p>
                </div>
              </el-card>
              
              <el-card class="status-card" style="margin-top: 20px;">
                <template #header>
                  <span>状态</span>
                </template>
                <div class="status-info">
                  <el-tag v-if="player?.afk" type="success">挂机中</el-tag>
                  <el-tag v-if="player?.pending_death_items" type="danger">待确认死亡</el-tag>
                  <el-tag v-else type="info">正常</el-tag>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </div>

        <div v-else-if="currentView === 'inventory'" class="inventory-view">
          <el-card>
            <template #header>
              <div class="card-header">
                <span>背包物品</span>
                <el-button size="small" @click="gameStore.getInventory()">刷新</el-button>
              </div>
            </template>
            <el-table :data="gameStore.inventory" style="width: 100%">
              <el-table-column prop="name" label="名称" />
              <el-table-column prop="count" label="数量" width="80" />
              <el-table-column prop="quality" label="品质" width="80">
                <template #default="{ row }">
                  <el-tag :type="getQualityType(row.quality)">{{ getQualityName(row.quality) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="180">
                <template #default="{ row }">
                  <el-button size="small" @click="handleUseItem(row)">使用</el-button>
                  <el-button size="small" @click="handleEquipItem(row)">装备</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-main>
    </el-container>

    <el-dialog v-model="equipDialogVisible" title="装备详情" width="400px">
      <div v-if="selectedEquip" class="equip-detail">
        <h3>{{ selectedEquip.name }}</h3>
        <p>品质: {{ getQualityName(selectedEquip.quality) }}</p>
        <p>攻击: {{ selectedEquip.attack_bonus || 0 }}</p>
        <p>防御: {{ selectedEquip.defense_bonus || 0 }}</p>
        <p>描述: {{ selectedEquip.description }}</p>
      </div>
      <template #footer>
        <el-button @click="equipDialogVisible = false">关闭</el-button>
        <el-button v-if="selectedEquip" type="primary" @click="handleEquipAction">装备</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { useIconStore } from '../stores/icons'
import { ElMessage } from 'element-plus'

const gameStore = useGameStore()
const iconStore = useIconStore()

const currentView = ref('panel')
const equipDialogVisible = ref(false)
const selectedEquip = ref(null)
const selectedSlot = ref('')

const equipmentSlots = computed(() => {
  const slots = [
    { key: 'weapon', name: '武器' },
    { key: 'armor', name: '护甲' },
    { key: 'helmet', name: '头盔' },
    { key: 'gloves', name: '手部' },
    { key: 'boots', name: '腿部' },
    { key: 'shoulder', name: '肩甲' },
    { key: 'accessory1', name: '饰品1' },
    { key: 'accessory2', name: '饰品2' }
  ]
  return slots.map(slot => ({
    ...slot,
    icon: iconStore.getIconContent(slot.key) || getDefaultIcon(slot.key)
  }))
})

const mountSlots = computed(() => {
  const slots = [
    { key: 'mount', name: '坐骑' },
    { key: 'mount_armor', name: '马甲' },
    { key: 'mount_weapon', name: '马战武器' },
    { key: 'horse_armament', name: '马具' }
  ]
  return slots.map(slot => ({
    ...slot,
    icon: iconStore.getIconContent(slot.key) || getDefaultIcon(slot.key)
  }))
})

const getDefaultIcon = (key) => {
  const defaults = {
    weapon: '⚔️', armor: '🛡️', helmet: '⛑️', gloves: '🧤',
    boots: '👢', shoulder: '🦺', accessory1: '💍', accessory2: '📿',
    mount: '🐎', mount_armor: '🎽', mount_weapon: '🔱', horse_armament: '🪢'
  }
  return defaults[key] || '📦'
}

const player = computed(() => gameStore.player)

const realmTagType = computed(() => {
  const realm = player.value?.realm || 0
  if (realm >= 6) return 'danger'
  if (realm >= 3) return 'warning'
  return 'success'
})

const getQualityType = (quality) => {
  const types = ['', 'info', 'success', 'warning', 'danger']
  return types[quality] || 'info'
}

const getQualityName = (quality) => {
  const names = ['', '普通', '良品', '精品', '极品']
  return names[quality] || '未知'
}

const handleEquipClick = (slot) => {
  if (player.value?.equipment?.[slot]) {
    selectedEquip.value = player.value.equipment[slot]
    selectedSlot.value = slot
    equipDialogVisible.value = true
  }
}

const handleMountEquipClick = (slot) => {
  if (player.value?.equipped_mount_items?.[slot]) {
    selectedEquip.value = player.value.equipped_mount_items[slot]
    selectedSlot.value = slot
    equipDialogVisible.value = true
  }
}

const handleEquipAction = async () => {
  if (selectedEquip.value) {
    await gameStore.equipItem(selectedEquip.value.item_id)
    equipDialogVisible.value = false
  }
}

const handleUseItem = async (item) => {
  await gameStore.useItem(item.item_id)
}

const handleEquipItem = async (item) => {
  await gameStore.equipItem(item.item_id)
}

const handleCheckin = async () => {
  await gameStore.checkin()
}

const handleStartAfk = async () => {
  await gameStore.startAfk()
}

const handleAdventure = async () => {
  await gameStore.adventure()
}

const handleBandits = () => {
  ElMessage.info('讨伐功能开发中...')
}

const handleLogout = () => {
  gameStore.logout()
  router.push('/')
}

onMounted(() => {
  if (!gameStore.token) {
    router.push('/')
    return
  }
  iconStore.loadConfig()
  gameStore.getPanel()
  gameStore.getInventory()
})
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  background: #1a1a2e;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #16213e;
  border-bottom: 1px solid #0f3460;
}

.header-left h2 {
  color: #ffd700;
  margin: 0;
}

.header-center .el-button {
  background: transparent;
  border-color: #0f3460;
  color: #e0e0e0;
}

.header-center .el-button:hover {
  background: #0f3460;
}

.player-card, .equipment-card, .info-card, .status-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #e0e0e0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 15px;
  margin-bottom: 20px;
}

.stat-item {
  text-align: center;
}

.stat-item .label {
  display: block;
  color: #888;
  font-size: 12px;
}

.stat-item .value {
  display: block;
  color: #ffd700;
  font-size: 16px;
  font-weight: bold;
}

.action-buttons {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.equipment-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 15px;
}

.equip-slot {
  text-align: center;
  padding: 15px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid #0f3460;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.equip-slot:hover {
  border-color: #ffd700;
}

.equip-slot.empty {
  opacity: 0.6;
}

.slot-icon {
  font-size: 24px;
}

.slot-name {
  font-size: 12px;
  color: #888;
  margin-top: 5px;
}

.slot-item {
  font-size: 12px;
  color: #ffd700;
  margin-top: 5px;
}

.slot-empty {
  font-size: 11px;
  color: #555;
  margin-top: 5px;
}

.equip-section {
  margin-top: 20px;
}

.equip-section h4 {
  color: #ffd700;
  margin: 10px 0;
}

.location-info p, .status-info {
  margin: 5px 0;
  color: #e0e0e0;
}
</style>
