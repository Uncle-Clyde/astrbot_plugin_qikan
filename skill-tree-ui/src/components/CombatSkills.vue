<template>
  <div class="combat-skills-container">
    <div class="combat-groups">
      <div 
        v-for="(group, key) in combatSkills" 
        :key="key" 
        class="combat-group"
      >
        <div class="group-header">
          <h3>{{ group.name }}</h3>
          <span class="group-name-en">{{ group.name_en }}</span>
        </div>
        
        <div class="group-skills">
          <div 
            v-for="skill in group.skills" 
            :key="skill.gongfa_id"
            class="combat-skill-card"
            :class="{ 
              'is-equipped': skill.equipped_slot !== null,
              [`tier-${skill.tier}`]: true
            }"
            @click="$emit('select', skill)"
          >
            <div class="skill-header">
              <span class="skill-name">{{ skill.name }}</span>
              <span class="skill-tier">{{ skill.tier_name }}</span>
            </div>
            <p class="skill-desc">{{ skill.description }}</p>
            <div class="skill-stats">
              <span class="stat" v-if="skill.attack_bonus > 0">
                ⚔️ +{{ skill.attack_bonus }}%
              </span>
              <span class="stat" v-if="skill.defense_bonus > 0">
                🛡️ +{{ skill.defense_bonus }}%
              </span>
              <span class="stat" v-if="skill.hp_regen > 0">
                ❤️ +{{ skill.hp_regen }}
              </span>
              <span class="stat" v-if="skill.lingqi_cost > 0">
                💧 -{{ skill.lingqi_cost }}
              </span>
            </div>
            <div v-if="skill.equipped_slot" class="equipped-slot">
              装备位: {{ skill.equipped_slot }}
            </div>
            <div v-if="skill.equipped_slot" class="mastery-bar">
              <div class="mastery-fill" :style="{ width: `${getMasteryProgress(skill)}%` }"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { CombatSkill, CombatSkillGroup } from '../stores/skillStore'

defineProps<{
  combatSkills: Record<string, CombatSkillGroup>
}>()

defineEmits<{
  (e: 'select', skill: CombatSkill): void
}>()

function getMasteryProgress(skill: CombatSkill): number {
  if (!skill.equipped_slot) return 0
  return Math.min(100, (skill.current_exp / skill.mastery_exp) * 100)
}
</script>

<style scoped>
.combat-skills-container {
  height: 100%;
  overflow-y: auto;
  padding: 20px;
}

.combat-groups {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 24px;
}

.combat-group {
  background: rgba(30, 30, 46, 0.6);
  border-radius: 16px;
  padding: 20px;
  border: 1px solid #3a3a4e;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #3a3a4e;
}

.group-header h3 {
  margin: 0;
  font-size: 16px;
  color: #fff;
}

.group-name-en {
  font-size: 12px;
  color: #888;
}

.group-skills {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.combat-skill-card {
  background: rgba(20, 20, 30, 0.8);
  border-radius: 12px;
  padding: 16px;
  border: 2px solid #3a3a4e;
  cursor: pointer;
  transition: all 0.2s;
}

.combat-skill-card:hover {
  transform: translateX(4px);
  border-color: #4a9eff;
}

.combat-skill-card.is-equipped {
  border-color: #4ade80;
  background: rgba(74, 222, 128, 0.05);
}

/* Tier colors */
.tier-0 {
  --tier-color: #9ca3af;
}

.tier-1 {
  --tier-color: #60a5fa;
}

.tier-2 {
  --tier-color: #a855f7;
}

.tier-3 {
  --tier-color: #f59e0b;
}

.skill-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.skill-name {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.skill-tier {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.1);
  color: var(--tier-color);
  border: 1px solid var(--tier-color);
}

.skill-desc {
  font-size: 12px;
  color: #888;
  margin: 0 0 12px 0;
  line-height: 1.4;
}

.skill-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.stat {
  font-size: 11px;
  padding: 2px 6px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  color: #aaa;
}

.equipped-slot {
  margin-top: 8px;
  font-size: 11px;
  color: #4ade80;
}

.mastery-bar {
  margin-top: 6px;
  height: 4px;
  background: #2a2a3e;
  border-radius: 2px;
  overflow: hidden;
}

.mastery-fill {
  height: 100%;
  background: linear-gradient(90deg, #4ade80, #22c55e);
  transition: width 0.3s;
}
</style>
