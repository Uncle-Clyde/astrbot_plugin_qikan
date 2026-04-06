<template>
  <div v-if="visible" class="equip-detail-overlay" @click.self="$emit('close')">
    <div class="equip-detail-panel">
      <div class="panel-header">
        <h3>{{ item.name }}</h3>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>
      <div class="panel-body">
        <div class="equip-icon-large">{{ icon }}</div>
        <div class="equip-quality">
          <span class="quality-tag" :class="getQualityClass(item.quality)">
            {{ getQualityName(item.quality) }}
          </span>
        </div>

        <div class="equip-stats">
          <div class="stat-row" v-if="item.attack_bonus">
            <span class="stat-label">攻击加成</span>
            <span class="stat-value atk">+{{ item.attack_bonus }}</span>
          </div>
          <div class="stat-row" v-if="item.defense_bonus">
            <span class="stat-label">防御加成</span>
            <span class="stat-value def">+{{ item.defense_bonus }}</span>
          </div>
          <div class="stat-row" v-if="item.hp_bonus">
            <span class="stat-label">生命加成</span>
            <span class="stat-value hp">+{{ item.hp_bonus }}</span>
          </div>
          <div class="stat-row" v-if="item.speed_bonus">
            <span class="stat-label">速度加成</span>
            <span class="stat-value spd">+{{ item.speed_bonus }}</span>
          </div>
          <div class="stat-row" v-if="item.tier">
            <span class="stat-label">品阶</span>
            <span class="stat-value">{{ item.tier_name || `T${item.tier}` }}</span>
          </div>
        </div>

        <div v-if="item.description" class="equip-desc">
          {{ item.description }}
        </div>

        <div v-if="item.special_effect" class="equip-special">
          <span class="special-label">特殊效果</span>
          <span class="special-value">{{ item.special_effect }}</span>
        </div>
      </div>
      <div class="panel-footer">
        <button class="action-btn unequip-btn" v-if="isEquipped" @click="$emit('unequip')">
          卸下
        </button>
        <button class="action-btn equip-btn" v-else @click="$emit('equip')">
          装备
        </button>
        <button class="action-btn close-action-btn" @click="$emit('close')">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  visible: { type: Boolean, default: false },
  item: { type: Object, default: null },
  icon: { type: String, default: '📦' },
  isEquipped: { type: Boolean, default: false },
})

defineEmits(['close', 'equip', 'unequip'])

const getQualityName = (quality) => {
  const names = ['', '普通', '良品', '精品', '极品']
  return names[quality] || '未知'
}

const getQualityClass = (quality) => {
  const classes = ['', 'q-common', 'q-fine', 'q-rare', 'q-epic']
  return classes[quality] || ''
}
</script>

<style scoped>
.equip-detail-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.equip-detail-panel {
  width: 360px;
  max-width: 90vw;
  background: rgba(25,25,40,0.98);
  border: 1px solid #2a2a3e;
  border-radius: 12px;
  overflow: hidden;
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from { transform: translateY(30px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: rgba(0,0,0,0.3);
  border-bottom: 1px solid #2a2a3e;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  color: #fff;
}

.close-btn {
  width: 28px; height: 28px;
  border: none; border-radius: 6px;
  background: rgba(255,255,255,0.1);
  color: #fff; cursor: pointer;
  font-size: 18px;
  display: flex; align-items: center; justify-content: center;
}

.close-btn:hover { background: rgba(255,255,255,0.2); }

.panel-body {
  padding: 20px;
  text-align: center;
}

.equip-icon-large {
  font-size: 48px;
  margin-bottom: 12px;
  filter: drop-shadow(0 4px 8px rgba(0,0,0,0.5));
}

.equip-quality {
  margin-bottom: 16px;
}

.quality-tag {
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.quality-tag.q-common { background: rgba(158,158,158,0.2); color: #9e9e9e; }
.quality-tag.q-fine { background: rgba(76,175,80,0.2); color: #4caf50; }
.quality-tag.q-rare { background: rgba(33,150,243,0.2); color: #2196f3; }
.quality-tag.q-epic { background: rgba(156,39,176,0.2); color: #9c27b0; }

.equip-stats {
  margin-bottom: 16px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  font-size: 13px;
}

.stat-label { color: #888; }
.stat-value { color: #fff; }
.stat-value.atk { color: #ff6b35; }
.stat-value.def { color: #4ecdc4; }
.stat-value.hp { color: #4caf50; }
.stat-value.spd { color: #fbbf24; }

.equip-desc {
  font-size: 12px;
  color: #aaa;
  line-height: 1.6;
  margin-bottom: 12px;
  font-style: italic;
}

.equip-special {
  padding: 10px;
  background: rgba(251,191,36,0.1);
  border: 1px solid rgba(251,191,36,0.2);
  border-radius: 6px;
  margin-bottom: 12px;
}

.special-label {
  font-size: 11px;
  color: #fbbf24;
  display: block;
  margin-bottom: 4px;
}

.special-value {
  font-size: 12px;
  color: #fbbf24;
}

.panel-footer {
  display: flex;
  gap: 8px;
  padding: 16px;
  border-top: 1px solid #2a2a3e;
}

.action-btn {
  flex: 1;
  padding: 10px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
}

.action-btn:hover { transform: translateY(-1px); }

.equip-btn {
  background: linear-gradient(135deg, #4a9eff, #3b82f6);
  color: #fff;
}

.unequip-btn {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: #fff;
}

.close-action-btn {
  background: rgba(255,255,255,0.1);
  color: #ccc;
}
</style>
