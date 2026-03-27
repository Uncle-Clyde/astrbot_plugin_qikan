<template>
  <div class="home-container">
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <h2>⚔️ 骑砍英雄传</h2>
        </div>
        <div class="header-center">
          <el-button-group>
            <el-button @click="currentView = 'panel'" :type="currentView === 'panel' ? 'danger' : ''">⚔️ 角色</el-button>
            <el-button @click="currentView = 'inventory'" :type="currentView === 'inventory' ? 'danger' : ''">🎒 背包</el-button>
            <el-button @click="$router.push('/skills')">📜 技能</el-button>
            <el-button @click="$router.push('/map')">🗺️ 地图</el-button>
            <el-button @click="$router.push('/family')">🏰 家族</el-button>
            <el-button @click="$router.push('/market')">🏛️ 集市</el-button>
            <el-button @click="$router.push('/chat')">💬 世界</el-button>
            <el-button @click="$router.push('/icons')">⚙️ 图标</el-button>
          </el-button-group>
        </div>
        <div class="header-right">
          <el-button @click="handleLogout" type="danger" size="small">🚪 退出</el-button>
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
  background: linear-gradient(180deg, #0D0D0D 0%, #1A1A1A 50%, #151515 100%);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(180deg, #1A1A1A 0%, #0D0D0D 100%);
  border-bottom: 3px solid #8B0000;
  padding: 0 24px;
  height: 60px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
}

.header-left h2 {
  color: #FFD700;
  margin: 0;
  font-size: 22px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.8), 0 0 10px rgba(255, 215, 0, 0.3);
  letter-spacing: 3px;
  font-family: 'Microsoft YaHei', serif;
}

.header-center .el-button {
  background: linear-gradient(145deg, #252525 0%, #1A1A1A 100%);
  border: 1px solid #3D3D3D;
  color: #C4B59D;
  font-weight: 500;
  transition: all 0.3s ease;
}

.header-center .el-button:hover {
  background: linear-gradient(145deg, #8B0000 0%, #5C0000 100%);
  border-color: #B22222;
  color: #FFD700;
  box-shadow: 0 0 12px rgba(139, 0, 0, 0.5);
}

.player-card, .equipment-card, .info-card, .status-card {
  background: linear-gradient(145deg, #252525 0%, #1E1E1E 100%);
  border: 1px solid #3D3D3D;
  color: #F5DEB3;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

.player-card:hover, .equipment-card:hover {
  border-color: #8B7355;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.6);
}

:deep(.el-card__header) {
  background: linear-gradient(90deg, #1A1A1A 0%, #252525 100%);
  border-bottom: 2px solid #8B0000;
  padding: 14px 16px;
}

:deep(.el-card__body) {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header span {
  color: #FFD700;
  font-size: 18px;
  font-weight: bold;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
  padding: 16px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  border: 1px solid #2D2D2D;
}

.stat-item {
  text-align: center;
  padding: 8px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
}

.stat-item .label {
  display: block;
  color: #888;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 4px;
}

.stat-item .value {
  display: block;
  color: #FFD700;
  font-size: 18px;
  font-weight: bold;
  text-shadow: 0 0 8px rgba(255, 215, 0, 0.3);
}

.action-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 20px;
  padding: 16px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  border: 1px solid #2D2D2D;
}

.action-buttons .el-button {
  background: linear-gradient(145deg, #8B0000 0%, #5C0000 100%);
  border: 1px solid #B22222;
  color: #FFD700;
  font-weight: bold;
  transition: all 0.3s ease;
}

.action-buttons .el-button:hover {
  background: linear-gradient(145deg, #B22222 0%, #8B0000 100%);
  box-shadow: 0 4px 12px rgba(139, 0, 0, 0.5);
  transform: translateY(-2px);
}

.equipment-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.equip-slot {
  text-align: center;
  padding: 16px 12px;
  background: linear-gradient(145deg, #1A1A1A 0%, #0F0F0F 100%);
  border: 2px solid #5C4033;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.equip-slot::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(139, 115, 85, 0.1), transparent);
  transition: left 0.5s ease;
}

.equip-slot:hover::before {
  left: 100%;
}

.equip-slot:hover {
  background: linear-gradient(145deg, #3D2B1F 0%, #2D1F15 100%);
  border-color: #D4AF37;
  transform: translateY(-3px);
  box-shadow: 0 6px 16px rgba(212, 175, 55, 0.2);
}

.equip-slot.empty {
  opacity: 0.7;
}

.equip-slot.equipped {
  background: linear-gradient(145deg, #2D2416 0%, #1F1510 100%);
  border-color: #D4AF37;
}

.slot-icon {
  font-size: 28px;
  display: block;
  margin-bottom: 6px;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.6));
}

.slot-name {
  font-size: 12px;
  color: #C4B59D;
  font-weight: 500;
  margin-top: 4px;
}

.slot-item {
  font-size: 11px;
  color: #FFD700;
  margin-top: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 80px;
}

.slot-empty {
  font-size: 10px;
  color: #555;
  margin-top: 6px;
}

.equip-section {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #3D3D3D;
}

.equip-section h4 {
  color: #D4AF37;
  margin: 12px 0 16px;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 2px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
}

.location-info p, .status-info {
  margin: 8px 0;
  color: #C4B59D;
  padding: 8px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
  border-left: 3px solid #8B0000;
}

/* 标签样式 */
:deep(.el-tag) {
  border-color: #8B0000;
  background: linear-gradient(145deg, #5C0000 0%, #3D0000 100%);
  color: #FFD700;
}

/* 输入框样式 */
:deep(.el-input__wrapper) {
  background: #0D0D0D;
  border: 1px solid #3D3D3D;
  box-shadow: none;
}

:deep(.el-input__wrapper:hover) {
  border-color: #8B7355;
}

:deep(.el-input__wrapper.is-focus) {
  border-color: #D4AF37;
  box-shadow: 0 0 8px rgba(212, 175, 55, 0.2);
}

:deep(.el-input__inner) {
  color: #F5DEB3;
}

/* 对话框样式 */
:deep(.el-dialog) {
  background: #1E1E1E;
  border: 2px solid #3D3D3D;
  border-radius: 8px;
}

:deep(.el-dialog__header) {
  background: linear-gradient(90deg, #1A1A1A 0%, #252525 100%);
  border-bottom: 2px solid #8B0000;
}

:deep(.el-dialog__title) {
  color: #FFD700;
}

:deep(.el-dialog__body) {
  color: #F5DEB3;
}
</style>
