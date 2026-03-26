<template>
  <div class="skill-detail-panel" v-if="skill">
    <div class="panel-header">
      <h2>{{ skill.name }}</h2>
      <button class="close-btn" @click="$emit('close')">×</button>
    </div>
    
    <div class="panel-content">
      <div class="skill-quality" :class="`quality-${skill.quality}`">
        {{ skill.quality_name }}
      </div>
      
      <div class="skill-description">
        {{ skill.description }}
      </div>
      
      <div class="skill-stats">
        <div class="stat-row">
          <span class="stat-label">需求爵位</span>
          <span class="stat-value">{{ skill.realm_name }}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">攻击加成</span>
          <span class="stat-value attack">+{{ skill.attack_bonus }}%</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">防御加成</span>
          <span class="stat-value defense">+{{ skill.defense_bonus }}%</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">经验倍率</span>
          <span class="stat-value exp">{{ skill.exp_multiplier * 100 }}%</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">道韵概率</span>
          <span class="stat-value daoyun">{{ skill.dao_yun_rate * 100 }}%</span>
        </div>
      </div>
      
      <div class="skill-progress" v-if="skill.is_equipped">
        <h4>当前熟练度</h4>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: `${masteryProgress}%` }"></div>
        </div>
        <div class="progress-info">
          <span>等级 {{ skill.current_mastery }}</span>
          <span>{{ skill.current_exp }} / {{ skill.mastery_exp }}</span>
        </div>
      </div>
      
      <div class="skill-status">
        <div v-if="skill.is_equipped" class="status equipped">
          ✓ 已装备
        </div>
        <div v-else-if="skill.can_learn" class="status available">
          可学习
        </div>
        <div v-else class="status locked">
          🔒 需要 {{ skill.realm_name }} 爵位
        </div>
      </div>
      
      <div class="skill-actions">
        <button 
          v-if="skill.can_learn && !skill.is_equipped"
          class="action-btn learn"
          @click="$emit('learn', skill)"
        >
          学习技能
        </button>
        <button 
          v-if="!skill.is_equipped && skill.can_learn"
          class="action-btn equip"
          @click="$emit('equip', skill)"
        >
          装备技能
        </button>
        <button 
          v-if="skill.is_equipped"
          class="action-btn unequip"
          @click="$emit('unequip')"
        >
          卸下技能
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Skill } from '../stores/skillStore'

const props = defineProps<{
  skill: Skill | null
}>()

defineEmits<{
  (e: 'close'): void
  (e: 'learn', skill: Skill): void
  (e: 'equip', skill: Skill): void
  (e: 'unequip'): void
}>()

const masteryProgress = computed(() => {
  if (!props.skill || !props.skill.is_equipped) return 0
  return (props.skill.current_exp / props.skill.mastery_exp) * 100
})
</script>

<style scoped>
.skill-detail-panel {
  width: 320px;
  background: rgba(30, 30, 46, 0.98);
  border-left: 1px solid #3a3a4e;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #3a3a4e;
}

.panel-header h2 {
  margin: 0;
  font-size: 18px;
  color: #fff;
}

.close-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: #3a3a4e;
  color: #fff;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background: #4a4a5e;
}

.panel-content {
  padding: 20px;
  overflow-y: auto;
}

.skill-quality {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
  margin-bottom: 16px;
}

.quality-0 {
  background: rgba(156, 163, 175, 0.2);
  color: #9ca3af;
  border: 1px solid #9ca3af;
}

.quality-1 {
  background: rgba(96, 165, 250, 0.2);
  color: #60a5fa;
  border: 1px solid #60a5fa;
}

.quality-2 {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
  border: 1px solid #f59e0b;
}

.skill-description {
  color: #aaa;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 20px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.skill-stats {
  margin-bottom: 20px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #2a2a3e;
}

.stat-label {
  color: #888;
  font-size: 13px;
}

.stat-value {
  color: #fff;
  font-size: 13px;
  font-weight: 500;
}

.stat-value.attack {
  color: #ef4444;
}

.stat-value.defense {
  color: #3b82f6;
}

.stat-value.exp {
  color: #22c55e;
}

.stat-value.daoyun {
  color: #a855f7;
}

.skill-progress {
  margin-bottom: 20px;
}

.skill-progress h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #fff;
}

.progress-bar {
  height: 8px;
  background: #2a2a3e;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4ade80, #22c55e);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #888;
}

.skill-status {
  margin-bottom: 20px;
}

.status {
  padding: 12px;
  border-radius: 8px;
  text-align: center;
  font-size: 14px;
  font-weight: 500;
}

.status.equipped {
  background: rgba(74, 222, 128, 0.1);
  color: #4ade80;
  border: 1px solid #4ade80;
}

.status.available {
  background: rgba(74, 158, 255, 0.1);
  color: #4a9eff;
  border: 1px solid #4a9eff;
}

.status.locked {
  background: rgba(255, 255, 255, 0.05);
  color: #888;
  border: 1px solid #3a3a4e;
}

.skill-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.action-btn {
  padding: 12px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn.learn {
  background: linear-gradient(135deg, #4ade80, #22c55e);
  color: #000;
}

.action-btn.equip {
  background: linear-gradient(135deg, #4a9eff, #3b82f6);
  color: #fff;
}

.action-btn.unequip {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  border: 1px solid #3a3a4e;
}

.action-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}
</style>
