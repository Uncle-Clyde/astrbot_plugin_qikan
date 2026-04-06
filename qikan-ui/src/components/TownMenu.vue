<template>
  <Teleport to="body">
    <Transition name="town-menu">
      <div v-if="visible" class="town-menu-overlay" @click.self="handleClose">
        <div class="town-menu">
          <!-- 顶部标题区 -->
          <div class="town-menu-header">
            <div class="town-menu-icon">{{ locationInfo?.icon || '🏰' }}</div>
            <div class="town-menu-title">
              <h2 class="town-name">{{ locationInfo?.name || '据点' }}</h2>
              <p class="town-subtitle">
                <span v-if="locationInfo?.faction_name" class="faction-text">{{ locationInfo.faction_name }}</span>
                <span class="type-badge" :class="typeClass">{{ typeText }}</span>
              </p>
            </div>
          </div>

          <!-- 描述 -->
          <p v-if="locationInfo?.description" class="town-desc">{{ locationInfo.description }}</p>

          <!-- 分隔线 -->
          <div class="divider"></div>

          <!-- 菜单项列表 -->
          <div class="menu-list">
            <button
              v-for="item in menuItems"
              :key="item.id"
              class="menu-item"
              :class="{ disabled: !item.available }"
              :disabled="!item.available"
              @click="handleMenuClick(item)"
            >
              <span class="menu-icon">{{ item.icon }}</span>
              <div class="menu-content">
                <span class="menu-name">{{ item.name }}</span>
                <span v-if="item.description" class="menu-desc">{{ item.description }}</span>
                <span v-if="item.npc_name" class="menu-npc">— {{ item.npc_name }}</span>
              </div>
              <span v-if="!item.available" class="menu-unavailable">不可用</span>
            </button>
          </div>

          <!-- 底部分隔线 -->
          <div class="divider"></div>

          <!-- 离开按钮 -->
          <button class="menu-item leave-btn" @click="handleLeave">
            <span class="menu-icon">🚪</span>
            <div class="menu-content">
              <span class="menu-name">离开据点</span>
              <span class="menu-desc">返回大地图</span>
            </div>
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  locationInfo: { type: Object, default: null },
  menuItems: { type: Array, default: () => [] },
})

const emit = defineEmits(['close', 'leave', 'action'])

const typeText = computed(() => {
  const type = props.locationInfo?.type || ''
  const map = { TOWN: '城镇', VILLAGE: '村庄', CASTLE: '城堡', BANDIT_CAMP: '匪窝' }
  return map[type] || '据点'
})

const typeClass = computed(() => {
  return (props.locationInfo?.type || '').toLowerCase()
})

const handleClose = () => emit('close')
const handleLeave = () => emit('leave')

const handleMenuClick = (item) => {
  if (!item.available) return
  emit('action', item)
}
</script>

<style scoped>
/* 骑砍风格城镇菜单 */
.town-menu-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.town-menu {
  width: 420px;
  max-width: 90vw;
  max-height: 85vh;
  background: linear-gradient(180deg, #2a1f14 0%, #1a120b 100%);
  border: 2px solid #8b6914;
  border-radius: 4px;
  box-shadow:
    0 0 0 1px #5a4510,
    0 0 30px rgba(0, 0, 0, 0.8),
    inset 0 1px 0 rgba(255, 215, 0, 0.1);
  overflow-y: auto;
  position: relative;
}

/* 顶部装饰边框 */
.town-menu::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, transparent, #d4a464, #ffd700, #d4a464, transparent);
}

.town-menu-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px 12px;
}

.town-menu-icon {
  font-size: 48px;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.5));
}

.town-menu-title {
  flex: 1;
}

.town-name {
  margin: 0;
  font-size: 26px;
  font-weight: bold;
  color: #d4a464;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
  font-family: 'Georgia', serif;
  letter-spacing: 1px;
}

.town-subtitle {
  margin: 4px 0 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.faction-text {
  color: #a08060;
  font-size: 13px;
  font-style: italic;
}

.type-badge {
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.type-badge.town {
  background: rgba(74, 158, 255, 0.2);
  color: #4a9eff;
  border: 1px solid rgba(74, 158, 255, 0.4);
}

.type-badge.village {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
  border: 1px solid rgba(34, 197, 94, 0.4);
}

.type-badge.castle {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.4);
}

.type-badge.bandit_camp {
  background: rgba(168, 85, 247, 0.2);
  color: #a855f7;
  border: 1px solid rgba(168, 85, 247, 0.4);
}

.town-desc {
  margin: 0 24px 12px;
  color: #8b7355;
  font-size: 13px;
  line-height: 1.5;
  font-style: italic;
}

.divider {
  height: 1px;
  margin: 0 20px;
  background: linear-gradient(90deg, transparent, #5a4510, #8b6914, #5a4510, transparent);
}

/* 菜单列表 */
.menu-list {
  padding: 8px 12px;
}

.menu-item {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 12px 16px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: left;
  gap: 12px;
}

.menu-item:hover:not(.disabled) {
  background: rgba(212, 164, 100, 0.1);
  border-color: rgba(139, 105, 20, 0.3);
}

.menu-item:active:not(.disabled) {
  background: rgba(212, 164, 100, 0.2);
}

.menu-item.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.menu-icon {
  font-size: 24px;
  width: 36px;
  text-align: center;
  flex-shrink: 0;
}

.menu-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.menu-name {
  color: #d4a464;
  font-size: 15px;
  font-weight: 600;
  font-family: 'Georgia', serif;
}

.menu-desc {
  color: #8b7355;
  font-size: 12px;
}

.menu-npc {
  color: #a08060;
  font-size: 12px;
  font-style: italic;
}

.menu-unavailable {
  color: #666;
  font-size: 11px;
  font-style: italic;
}

/* 离开按钮 */
.leave-btn {
  margin: 8px 12px 16px;
  border-color: rgba(139, 105, 20, 0.2);
}

.leave-btn:hover {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
}

.leave-btn .menu-name {
  color: #c0a080;
}

/* 过渡动画 */
.town-menu-enter-active,
.town-menu-leave-active {
  transition: all 0.25s ease;
}

.town-menu-enter-from,
.town-menu-leave-to {
  opacity: 0;
  transform: scale(0.95) translateY(-10px);
}
</style>
