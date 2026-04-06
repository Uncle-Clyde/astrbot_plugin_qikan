<template>
  <Teleport to="body">
    <div v-if="visible" class="gift-selector-overlay" @click.self="handleCancel">
      <div class="gift-selector-container">
        <div class="gift-selector-header">
          <h3 class="gift-title">🎁 选择礼物</h3>
          <p class="gift-subtitle" v-if="npc">
            赠送给 {{ npc.name }}
          </p>
          <button class="close-btn" @click="handleCancel">×</button>
        </div>

        <div class="gift-selector-body">
          <div class="gift-hint">
            <p>💡 好感度增益基于礼物价值，越贵重的礼物提升越多</p>
          </div>

          <div class="gift-categories">
            <div
              v-for="category in giftCategories"
              :key="category.key"
              class="gift-category-section"
            >
              <h4 class="category-title">{{ category.label }}</h4>
              <div class="gift-grid">
                <div
                  v-for="gift in getGiftsByCategory(category.key)"
                  :key="gift.id"
                  class="gift-item"
                  :class="{
                    selected: selectedGift?.id === gift.id,
                  }"
                  @click="selectGift(gift)"
                >
                  <div class="gift-icon">{{ getGiftIcon(gift.id) }}</div>
                  <div class="gift-info">
                    <span class="gift-name">{{ gift.name }}</span>
                    <span class="gift-value">{{ gift.value }} 第纳尔</span>
                    <span class="gift-favor-gain">+{{ Math.max(1, Math.floor(gift.value / 10)) }} 好感</span>
                  </div>
                  <div class="gift-check" v-if="selectedGift?.id === gift.id">✓</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="gift-selector-footer">
          <button class="cancel-btn" @click="handleCancel">取消</button>
          <button
            class="confirm-btn"
            :disabled="!selectedGift"
            @click="handleConfirm"
          >
            赠送选中的礼物
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import axios from 'axios'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  npc: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['update:visible', 'confirm'])

const gifts = ref([])
const selectedGift = ref(null)

const giftCategories = [
  { key: 'common', label: '🎁 普通礼物 (1-30第纳尔)' },
  { key: 'medium', label: '🎁 中级礼物 (31-80第纳尔)' },
  { key: 'advanced', label: '🎁 高级礼物 (81-150第纳尔)' },
  { key: 'rare', label: '🎁 稀有礼物 (151+第纳尔)' },
]

const categoryRanges = {
  common: [1, 30],
  medium: [31, 80],
  advanced: [81, 150],
  rare: [151, 9999],
}

watch(() => props.visible, async (newVal) => {
  if (newVal && gifts.value.length === 0) {
    await loadGifts()
  }
  if (!newVal) {
    selectedGift.value = null
  }
})

const loadGifts = async () => {
  try {
    const token = localStorage.getItem('qikan_token')
    const response = await axios.get('/api/gifts/list', {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (response.data.success) {
      gifts.value = response.data.gifts
    }
  } catch (error) {
    console.error('Failed to load gifts:', error)
  }
}

const getGiftsByCategory = (categoryKey) => {
  const [min, max] = categoryRanges[categoryKey]
  return gifts.value.filter(g => g.value >= min && g.value <= max)
}

const getGiftName = (giftId) => {
  const gift = gifts.value.find(g => g.id === giftId)
  return gift?.name || giftId
}

const getGiftIcon = (giftId) => {
  const iconMap = {
    bread: '🍞', dried_meat: '🥩', dried_fish: '🐟', grain: '🌾',
    vegetables: '🥬', eggs: '🥚', butter: '🧈', fresh_fish: '🐟',
    pickled_meat: '🥓', cheese: '🧀', honey: '🍯', poultry: '🍗',
    wine: '🍷', wool: '🧶', spices: '🌶️', silk: '🧵', furs: '🦊',
    dates: '🌴', horse: '🐎', iron_sword: '⚔️', leather_armor: '🛡️',
    silver_item: '🥈', war_horse: '🐴',
  }
  return iconMap[giftId] || '🎁'
}

const selectGift = (gift) => {
  selectedGift.value = gift
}

const handleConfirm = () => {
  if (selectedGift.value) {
    emit('confirm', selectedGift.value)
  }
}

const handleCancel = () => {
  emit('update:visible', false)
}

onMounted(() => {
  if (props.visible) {
    loadGifts()
  }
})
</script>

<style scoped>
.gift-selector-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.gift-selector-container {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  width: 100%;
  max-width: 700px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.gift-selector-header {
  padding: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  position: relative;
}

.gift-title {
  color: #fff;
  font-size: 20px;
  margin: 0 0 4px;
}

.gift-subtitle {
  color: rgba(255, 255, 255, 0.6);
  font-size: 14px;
  margin: 0;
}

.close-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.5);
  font-size: 24px;
  cursor: pointer;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.gift-selector-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.gift-hint {
  margin-bottom: 16px;
  padding: 10px 14px;
  background: rgba(74, 158, 255, 0.1);
  border: 1px solid rgba(74, 158, 255, 0.2);
  border-radius: 8px;
}

.gift-hint p {
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
  margin: 0;
}

.gift-categories {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.category-title {
  color: #fff;
  font-size: 15px;
  margin: 0 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.gift-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
}

.gift-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.gift-item:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
}

.gift-item.selected {
  background: rgba(74, 158, 255, 0.15);
  border-color: #4a9eff;
}

.gift-icon {
  font-size: 24px;
}

.gift-info {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.gift-name {
  color: #fff;
  font-size: 14px;
  font-weight: 500;
}

.gift-value {
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
}

.gift-favor-gain {
  color: #22c55e;
  font-size: 11px;
  font-weight: 600;
}

.gift-check {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 18px;
  height: 18px;
  background: #4a9eff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 12px;
  font-weight: bold;
}

.gift-selector-footer {
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.cancel-btn,
.confirm-btn {
  padding: 10px 24px;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.cancel-btn {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.cancel-btn:hover {
  background: rgba(255, 255, 255, 0.15);
}

.confirm-btn {
  background: linear-gradient(135deg, #4a9eff, #22c55e);
  color: #fff;
  font-weight: 600;
}

.confirm-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.confirm-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
