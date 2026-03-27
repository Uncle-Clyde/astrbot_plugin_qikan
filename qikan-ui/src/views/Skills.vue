<template>
  <div class="view-container">
    <div class="nav-bar">
      <el-button @click="$router.push('/home')">← 返回</el-button>
      <h2>⚔️ 技能系统</h2>
    </div>
    
    <el-card class="skills-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="被动技能" name="heart">
          <div class="skills-grid">
            <div v-for="skill in heartMethods" :key="skill.method_id" class="skill-card">
              <h4>{{ skill.name }}</h4>
              <p>{{ skill.description }}</p>
              <el-tag v-if="skill.equipped" type="success">已装备</el-tag>
              <el-button v-else size="small" @click="equipSkill(skill)">装备</el-button>
            </div>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="战斗技能" name="combat">
          <div class="skills-grid">
            <div v-for="skill in combatSkills" :key="skill.gongfa_id" class="skill-card">
              <h4>{{ skill.name }}</h4>
              <p>{{ skill.description }}</p>
              <p>攻击: +{{ skill.attack_bonus }} 防御: +{{ skill.defense_bonus }}</p>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useGameStore } from '../stores/game'

const gameStore = useGameStore()
const activeTab = ref('heart')
const heartMethods = ref([])
const combatSkills = ref([])

const equipSkill = (skill) => {
  gameStore.send({ type: 'equip_skill', data: { skill_id: skill.method_id } })
}

onMounted(() => {
  gameStore.send({ type: 'get_skills' })
})
</script>

<style scoped>
.view-container { min-height: 100vh; background: #1a1a2e; padding: 20px; }
.nav-bar { display: flex; align-items: center; gap: 20px; margin-bottom: 20px; }
.nav-bar h2 { color: #ffd700; margin: 0; }
.skills-card { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: #e0e0e0; }
.skills-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; }
.skill-card { padding: 15px; background: rgba(0,0,0,0.3); border-radius: 8px; }
.skill-card h4 { margin: 0 0 10px; color: #ffd700; }
.skill-card p { margin: 5px 0; color: #aaa; font-size: 12px; }
</style>
