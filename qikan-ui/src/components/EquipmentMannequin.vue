<template>
  <div class="equipment-mannequin">
    <div class="mannequin-layout">
      <div class="mannequin-row mannequin-head">
        <div class="equip-slot" :class="{ empty: !equipped.helmet }" @click="$emit('slot-click', 'helmet')">
          <div class="slot-icon">{{ getIcon('helmet') }}</div>
          <div class="slot-name">头盔</div>
          <div class="slot-item-name" v-if="equipped.helmet">{{ equipped.helmet.name }}</div>
          <div class="slot-empty-text" v-else>未装备</div>
          <div class="quality-border" v-if="equipped.helmet" :class="getQualityClass(equipped.helmet.quality)"></div>
        </div>
      </div>

      <div class="mannequin-row mannequin-shoulders">
        <div class="equip-slot" :class="{ empty: !equipped.shoulder }" @click="$emit('slot-click', 'shoulder')">
          <div class="slot-icon">{{ getIcon('shoulder') }}</div>
          <div class="slot-name">肩甲</div>
          <div class="slot-item-name" v-if="equipped.shoulder">{{ equipped.shoulder.name }}</div>
          <div class="slot-empty-text" v-else>未装备</div>
          <div class="quality-border" v-if="equipped.shoulder" :class="getQualityClass(equipped.shoulder.quality)"></div>
        </div>
      </div>

      <div class="mannequin-row mannequin-torso">
        <div class="equip-slot" :class="{ empty: !equipped.weapon }" @click="$emit('slot-click', 'weapon')">
          <div class="slot-icon">{{ getIcon('weapon') }}</div>
          <div class="slot-name">武器</div>
          <div class="slot-item-name" v-if="equipped.weapon">{{ equipped.weapon.name }}</div>
          <div class="slot-empty-text" v-else>未装备</div>
          <div class="quality-border" v-if="equipped.weapon" :class="getQualityClass(equipped.weapon.quality)"></div>
        </div>
        <div class="equip-slot" :class="{ empty: !equipped.armor }" @click="$emit('slot-click', 'armor')">
          <div class="slot-icon">{{ getIcon('armor') }}</div>
          <div class="slot-name">护甲</div>
          <div class="slot-item-name" v-if="equipped.armor">{{ equipped.armor.name }}</div>
          <div class="slot-empty-text" v-else>未装备</div>
          <div class="quality-border" v-if="equipped.armor" :class="getQualityClass(equipped.armor.quality)"></div>
        </div>
        <div class="equip-slot" :class="{ empty: !equipped.accessory1 }" @click="$emit('slot-click', 'accessory1')">
          <div class="slot-icon">{{ getIcon('accessory1') }}</div>
          <div class="slot-name">饰品1</div>
          <div class="slot-item-name" v-if="equipped.accessory1">{{ equipped.accessory1.name }}</div>
          <div class="slot-empty-text" v-else>未装备</div>
          <div class="quality-border" v-if="equipped.accessory1" :class="getQualityClass(equipped.accessory1.quality)"></div>
        </div>
      </div>

      <div class="mannequin-row mannequin-hands">
        <div class="equip-slot" :class="{ empty: !equipped.gloves }" @click="$emit('slot-click', 'gloves')">
          <div class="slot-icon">{{ getIcon('gloves') }}</div>
          <div class="slot-name">手套</div>
          <div class="slot-item-name" v-if="equipped.gloves">{{ equipped.gloves.name }}</div>
          <div class="slot-empty-text" v-else>未装备</div>
          <div class="quality-border" v-if="equipped.gloves" :class="getQualityClass(equipped.gloves.quality)"></div>
        </div>
        <div class="equip-slot" :class="{ empty: !equipped.accessory2 }" @click="$emit('slot-click', 'accessory2')">
          <div class="slot-icon">{{ getIcon('accessory2') }}</div>
          <div class="slot-name">饰品2</div>
          <div class="slot-item-name" v-if="equipped.accessory2">{{ equipped.accessory2.name }}</div>
          <div class="slot-empty-text" v-else>未装备</div>
          <div class="quality-border" v-if="equipped.accessory2" :class="getQualityClass(equipped.accessory2.quality)"></div>
        </div>
      </div>

      <div class="mannequin-row mannequin-legs">
        <div class="equip-slot" :class="{ empty: !equipped.boots }" @click="$emit('slot-click', 'boots')">
          <div class="slot-icon">{{ getIcon('boots') }}</div>
          <div class="slot-name">靴子</div>
          <div class="slot-item-name" v-if="equipped.boots">{{ equipped.boots.name }}</div>
          <div class="slot-empty-text" v-else>未装备</div>
          <div class="quality-border" v-if="equipped.boots" :class="getQualityClass(equipped.boots.quality)"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useIconStore } from '../stores/icons'

const props = defineProps({
  player: { type: Object, default: null },
})

defineEmits(['slot-click'])

const iconStore = useIconStore()

const equipped = computed(() => props.player?.equipment || {})

const getIcon = (slot) => {
  const cfg = iconStore.icons?.[slot]
  if (cfg?.emoji) return cfg.emoji
  const defaults = {
    weapon: '⚔️', armor: '🛡️', helmet: '⛑️', gloves: '🧤',
    boots: '👢', shoulder: '🦺', accessory1: '💍', accessory2: '📿',
  }
  return defaults[slot] || '📦'
}

const getQualityClass = (quality) => {
  const classes = ['', 'quality-common', 'quality-fine', 'quality-rare', 'quality-epic']
  return classes[quality] || ''
}
</script>

<style scoped>
.equipment-mannequin {
  padding: 8px;
}

.mannequin-layout {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}

.mannequin-row {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.equip-slot {
  position: relative;
  width: 80px;
  height: 80px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(145deg, #1a1a1a 0%, #0f0f0f 100%);
  border: 2px solid #3d2b1f;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.25s ease;
  overflow: hidden;
}

.equip-slot:hover {
  background: linear-gradient(145deg, #3d2b1f 0%, #2d1f15 100%);
  border-color: #d4af37;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(212, 175, 55, 0.2);
}

.equip-slot.empty {
  opacity: 0.6;
}

.quality-border {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
}

.quality-common { background: #9e9e9e; }
.quality-fine { background: #4caf50; }
.quality-rare { background: #2196f3; }
.quality-epic { background: #9c27b0; }

.slot-icon {
  font-size: 24px;
  margin-bottom: 2px;
  filter: drop-shadow(0 2px 3px rgba(0,0,0,0.5));
}

.slot-name {
  font-size: 10px;
  color: #888;
}

.slot-item-name {
  font-size: 9px;
  color: #ffd700;
  max-width: 70px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 2px;
}

.slot-empty-text {
  font-size: 9px;
  color: #555;
  margin-top: 2px;
}

@media (max-width: 768px) {
  .equip-slot {
    width: 64px;
    height: 64px;
  }
  .slot-icon {
    font-size: 20px;
  }
  .slot-name {
    font-size: 9px;
  }
}
</style>
