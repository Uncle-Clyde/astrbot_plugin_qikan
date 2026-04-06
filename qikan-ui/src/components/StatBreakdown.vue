<template>
  <div class="stat-breakdown">
    <div class="breakdown-header" @click="expanded = !expanded">
      <h4>属性构成</h4>
      <span class="expand-icon">{{ expanded ? '▼' : '▶' }}</span>
    </div>
    <div v-show="expanded" class="breakdown-content">
      <div class="stat-group" v-for="sg in statGroups" :key="sg.label">
        <div class="stat-group-header">
          <span class="stat-group-label">{{ sg.label }}</span>
          <span class="stat-group-value" :style="{ color: sg.color }">{{ sg.total }}</span>
        </div>
        <div class="stat-group-bars">
          <div class="bar-row" v-for="bar in sg.bars" :key="bar.label">
            <span class="bar-label">{{ bar.label }}</span>
            <div class="bar-track">
              <div class="bar-fill" :style="{ width: bar.percent + '%', background: bar.color }"></div>
            </div>
            <span class="bar-value" :style="{ color: bar.color }">{{ bar.value >= 0 ? '+' : ''}}{{ bar.value }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  player: { type: Object, default: null },
})

const expanded = ref(true)

const statGroups = computed(() => {
  const p = props.player
  if (!p) return []

  const atk = p.total_attack || 0
  const def = p.total_defense || 0
  const hp = p.total_max_hp || p.max_hp || 0

  const equipBonus = p.equip_bonus || {}
  const prefixBonus = p.prefix_bonus || {}
  const gongfaBonus = p.gongfa_bonus || {}
  const mountBonus = p.mount_bonus || {}

  const maxVal = Math.max(atk, def, hp, 1)

  const makeBar = (label, value, color) => ({
    label,
    value: value || 0,
    color,
    percent: Math.min(100, Math.abs(value || 0) / maxVal * 100),
  })

  return [
    {
      label: '攻击力',
      total: atk,
      color: '#ff6b35',
      bars: [
        makeBar('基础', p.attack || 0, '#ff6b35'),
        makeBar('装备', equipBonus.attack || 0, '#4a9eff'),
        makeBar('前缀', prefixBonus.attack || 0, '#a78bfa'),
        makeBar('功法', gongfaBonus.attack_bonus || 0, '#22c55e'),
        makeBar('坐骑', mountBonus.attack || 0, '#fbbf24'),
      ],
    },
    {
      label: '防御力',
      total: def,
      color: '#4ecdc4',
      bars: [
        makeBar('基础', p.defense || 0, '#4ecdc4'),
        makeBar('装备', equipBonus.defense || 0, '#4a9eff'),
        makeBar('前缀', prefixBonus.defense || 0, '#a78bfa'),
        makeBar('功法', gongfaBonus.defense_bonus || 0, '#22c55e'),
        makeBar('坐骑', mountBonus.defense || 0, '#fbbf24'),
      ],
    },
    {
      label: '生命值',
      total: hp,
      color: '#4caf50',
      bars: [
        makeBar('基础', p.max_hp || 0, '#4caf50'),
        makeBar('装备', equipBonus.hp || 0, '#4a9eff'),
        makeBar('前缀', prefixBonus.hp || 0, '#a78bfa'),
      ],
    },
  ]
})
</script>

<style scoped>
.stat-breakdown {
  background: rgba(0,0,0,0.3);
  border: 1px solid #2d2d2d;
  border-radius: 8px;
  overflow: hidden;
}

.breakdown-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  cursor: pointer;
  background: rgba(0,0,0,0.2);
  transition: background 0.2s;
}

.breakdown-header:hover {
  background: rgba(0,0,0,0.3);
}

.breakdown-header h4 {
  margin: 0;
  font-size: 13px;
  color: var(--text-gold);
}

.expand-icon {
  color: #888;
  font-size: 12px;
}

.breakdown-content {
  padding: 12px 14px;
}

.stat-group {
  margin-bottom: 14px;
}

.stat-group:last-child {
  margin-bottom: 0;
}

.stat-group-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}

.stat-group-label {
  font-size: 12px;
  color: #888;
}

.stat-group-value {
  font-size: 13px;
  font-weight: 600;
}

.bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 3px;
  font-size: 11px;
}

.bar-label {
  width: 40px;
  color: #aaa;
  flex-shrink: 0;
}

.bar-track {
  flex: 1;
  height: 6px;
  background: rgba(255,255,255,0.05);
  border-radius: 3px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
}

.bar-value {
  width: 36px;
  text-align: right;
  flex-shrink: 0;
  font-weight: 500;
}
</style>
