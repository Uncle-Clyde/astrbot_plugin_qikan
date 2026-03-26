<template>
  <div 
    class="skill-node"
    :class="{
      'skill-locked': isLocked,
      'skill-available': isAvailable,
      'skill-learned': isLearned,
      'skill-equipped': skill.is_equipped,
      [`quality-${skill.quality}`]: true
    }"
    @click="handleClick"
  >
    <div class="skill-icon">
      <span class="skill-level">{{ skillLevel }}</span>
    </div>
    <div class="skill-info">
      <h4 class="skill-name">{{ skill.name }}</h4>
      <p class="skill-realm">{{ skill.realm_name }}</p>
    </div>
    <div v-if="skill.is_equipped" class="equipped-badge">已装备</div>
    <div v-if="isLocked" class="locked-overlay">
      <span class="lock-icon">🔒</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Skill } from '../stores/skillStore'

const props = defineProps<{
  skill: Skill
  previousSkillLevel?: number
}>()

const emit = defineEmits<{
  (e: 'select', skill: Skill): void
  (e: 'learn', skill: Skill): void
  (e: 'equip', skill: Skill): void
}>()

const isLocked = computed(() => !props.skill.can_learn)
const isAvailable = computed(() => props.skill.can_learn && !props.skill.is_equipped)
const isLearned = computed(() => props.skill.is_equipped)

const skillLevel = computed(() => {
  const match = props.skill.name.match(/·(.+)$/)
  return match ? match[1] : '?'
})

function handleClick() {
  emit('select', props.skill)
}
</script>

<style scoped>
.skill-node {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px;
  border-radius: 12px;
  background: linear-gradient(145deg, #2a2a3e, #1e1e2f);
  border: 2px solid #3a3a4e;
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 100px;
}

.skill-node:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4);
}

.skill-locked {
  opacity: 0.5;
  filter: grayscale(0.7);
}

.skill-available {
  border-color: #4a9eff;
  box-shadow: 0 0 15px rgba(74, 158, 255, 0.3);
}

.skill-learned {
  border-color: #4ade80;
  background: linear-gradient(145deg, #1a3a2e, #0e2a1e);
}

.skill-equipped {
  border-color: #fbbf24;
  box-shadow: 0 0 20px rgba(251, 191, 36, 0.4);
}

/* Quality colors */
.quality-0 {
  --quality-color: #9ca3af;
}

.quality-1 {
  --quality-color: #60a5fa;
}

.quality-2 {
  --quality-color: #f59e0b;
}

.skill-icon {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--quality-color), transparent);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
  border: 2px solid var(--quality-color);
}

.skill-level {
  font-size: 14px;
  font-weight: bold;
  color: white;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
}

.skill-info {
  text-align: center;
}

.skill-name {
  font-size: 12px;
  margin: 0 0 4px 0;
  color: #fff;
  white-space: nowrap;
}

.skill-realm {
  font-size: 10px;
  margin: 0;
  color: #888;
}

.equipped-badge {
  position: absolute;
  top: -8px;
  right: -8px;
  background: #fbbf24;
  color: #000;
  font-size: 9px;
  font-weight: bold;
  padding: 2px 6px;
  border-radius: 8px;
}

.locked-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 12px;
}

.lock-icon {
  font-size: 24px;
}
</style>
