<template>
  <div class="view-container">
    <div class="nav-bar">
      <el-button @click="$router.push('/home')">← 返回</el-button>
      <h2>⚔️ 技能与属性</h2>
    </div>
    
    <el-card class="skills-card">
      <div class="unified-panel">
        <div class="points-header">
          <div class="points-row">
            <div class="point-box">
              <span class="point-label">可分配属性点</span>
              <span class="point-value">{{ player?.attribute_points || 0 }}</span>
            </div>
            <div class="point-box">
              <span class="point-label">可用技能点</span>
              <span class="point-value skill">{{ availableSkillPoints }}</span>
            </div>
            <div class="point-actions">
              <el-button type="warning" size="small" @click="resetAllPoints" :disabled="!hasPendingChanges">
                🔄 重置
              </el-button>
              <el-button type="success" size="small" @click="commitAllPoints" :disabled="!hasPendingChanges" :loading="committing">
                ✓ 确认加点
              </el-button>
            </div>
          </div>
        </div>

        <el-tabs v-model="activeTab">
          <el-tab-pane label="全部技能" name="all">
            <div class="skills-unified">
              <div class="skill-category">
                <div class="category-title">💪 力量系技能</div>
                <div class="skills-grid">
                  <div v-for="skill in strengthSkills" :key="skill.skill_id" class="skill-card-full">
                    <div class="skill-icon-area">{{ skill.icon }}</div>
                    <div class="skill-info">
                      <div class="skill-name-row">
                        <span class="skill-name">{{ skill.name }}</span>
                        <el-tag size="small" type="danger">力量</el-tag>
                      </div>
                      <div class="skill-desc">{{ skill.description }}</div>
                      <div class="skill-effect" v-if="skill.effect_text">{{ skill.effect_text }}</div>
                      <div class="skill-level-row">
                        <span class="current-level">等级: {{ skill.current_level || 0 }}</span>
                        <span class="max-level">/ {{ skill.max_level }}</span>
                      </div>
                      <div class="skill-progress-bar">
                        <div class="progress-fill" :style="{ width: (skill.current_level / skill.max_level * 100) + '%' }"></div>
                      </div>
                    </div>
                    <div class="skill-controls">
                      <el-button size="small" circle type="danger" @click="removeSkillPoint(skill.skill_id)" :disabled="!canRemoveSkillPoint(skill.skill_id)">-</el-button>
                      <span class="pending-points">{{ pendingSkills[skill.skill_id] || 0 }}</span>
                      <el-button size="small" circle type="success" @click="addSkillPoint(skill.skill_id)" :disabled="!canAddSkillPoint()">+</el-button>
                    </div>
                  </div>
                </div>
              </div>

              <div class="skill-category">
                <div class="category-title">⚡ 敏捷系技能</div>
                <div class="skills-grid">
                  <div v-for="skill in agilitySkills" :key="skill.skill_id" class="skill-card-full">
                    <div class="skill-icon-area">{{ skill.icon }}</div>
                    <div class="skill-info">
                      <div class="skill-name-row">
                        <span class="skill-name">{{ skill.name }}</span>
                        <el-tag size="small" type="success">敏捷</el-tag>
                      </div>
                      <div class="skill-desc">{{ skill.description }}</div>
                      <div class="skill-effect" v-if="skill.effect_text">{{ skill.effect_text }}</div>
                      <div class="skill-level-row">
                        <span class="current-level">等级: {{ skill.current_level || 0 }}</span>
                        <span class="max-level">/ {{ skill.max_level }}</span>
                      </div>
                      <div class="skill-progress-bar">
                        <div class="progress-fill agility" :style="{ width: (skill.current_level / skill.max_level * 100) + '%' }"></div>
                      </div>
                    </div>
                    <div class="skill-controls">
                      <el-button size="small" circle type="danger" @click="removeSkillPoint(skill.skill_id)" :disabled="!canRemoveSkillPoint(skill.skill_id)">-</el-button>
                      <span class="pending-points">{{ pendingSkills[skill.skill_id] || 0 }}</span>
                      <el-button size="small" circle type="success" @click="addSkillPoint(skill.skill_id)" :disabled="!canAddSkillPoint()">+</el-button>
                    </div>
                  </div>
                </div>
              </div>

              <div class="skill-category">
                <div class="category-title">🧠 智力系技能</div>
                <div class="skills-grid">
                  <div v-for="skill in intelligenceSkills" :key="skill.skill_id" class="skill-card-full">
                    <div class="skill-icon-area">{{ skill.icon }}</div>
                    <div class="skill-info">
                      <div class="skill-name-row">
                        <span class="skill-name">{{ skill.name }}</span>
                        <el-tag size="small" type="primary">智力</el-tag>
                      </div>
                      <div class="skill-desc">{{ skill.description }}</div>
                      <div class="skill-effect" v-if="skill.effect_text">{{ skill.effect_text }}</div>
                      <div class="skill-level-row">
                        <span class="current-level">等级: {{ skill.current_level || 0 }}</span>
                        <span class="max-level">/ {{ skill.max_level }}</span>
                      </div>
                      <div class="skill-progress-bar">
                        <div class="progress-fill intelligence" :style="{ width: (skill.current_level / skill.max_level * 100) + '%' }"></div>
                      </div>
                    </div>
                    <div class="skill-controls">
                      <el-button size="small" circle type="danger" @click="removeSkillPoint(skill.skill_id)" :disabled="!canRemoveSkillPoint(skill.skill_id)">-</el-button>
                      <span class="pending-points">{{ pendingSkills[skill.skill_id] || 0 }}</span>
                      <el-button size="small" circle type="success" @click="addSkillPoint(skill.skill_id)" :disabled="!canAddSkillPoint()">+</el-button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="属性分配" name="attributes">
            <div class="attributes-panel">
              <div class="attr-cards">
                <div class="attr-card-full strength">
                  <div class="attr-header">
                    <span class="attr-icon">💪</span>
                    <span class="attr-name">力量</span>
                    <span class="attr-base">{{ player?.strength || 5 }}</span>
                  </div>
                  <div class="attr-desc">增加物理攻击和生命值</div>
                  <div class="attr-controls">
                    <el-button size="small" circle type="danger" @click="decrementAttr('strength')" :disabled="!canDecrementAttr('strength')">-</el-button>
                    <span class="pending-count">{{ pendingAttributes.strength }}</span>
                    <el-button size="small" circle type="success" @click="incrementAttr('strength')" :disabled="!canIncrementAttr()">+</el-button>
                  </div>
                </div>

                <div class="attr-card-full intelligence">
                  <div class="attr-header">
                    <span class="attr-icon">🧠</span>
                    <span class="attr-name">智力</span>
                    <span class="attr-base">{{ player?.intelligence || 5 }}</span>
                  </div>
                  <div class="attr-desc">增加法术攻击和法力上限</div>
                  <div class="attr-controls">
                    <el-button size="small" circle type="danger" @click="decrementAttr('intelligence')" :disabled="!canDecrementAttr('intelligence')">-</el-button>
                    <span class="pending-count">{{ pendingAttributes.intelligence }}</span>
                    <el-button size="small" circle type="success" @click="incrementAttr('intelligence')" :disabled="!canIncrementAttr()">+</el-button>
                  </div>
                </div>

                <div class="attr-card-full agility">
                  <div class="attr-header">
                    <span class="attr-icon">⚡</span>
                    <span class="attr-name">敏捷</span>
                    <span class="attr-base">{{ player?.agility || 5 }}</span>
                  </div>
                  <div class="attr-desc">增加攻击速度和闪避</div>
                  <div class="attr-controls">
                    <el-button size="small" circle type="danger" @click="decrementAttr('agility')" :disabled="!canDecrementAttr('agility')">-</el-button>
                    <span class="pending-count">{{ pendingAttributes.agility }}</span>
                    <el-button size="small" circle type="success" @click="incrementAttr('agility')" :disabled="!canIncrementAttr()">+</el-button>
                  </div>
                </div>
              </div>

              <div class="attr-summary" v-if="pendingAttributePoints > 0">
                <span>待确认分配: 力量{{ pendingAttributes.strength > 0 ? '+' + pendingAttributes.strength : '' }} 
                智力{{ pendingAttributes.intelligence > 0 ? '+' + pendingAttributes.intelligence : '' }} 
                敏捷{{ pendingAttributes.agility > 0 ? '+' + pendingAttributes.agility : '' }}</span>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="战斗技能" name="combat">
            <div class="skills-grid">
              <div v-for="skill in heartMethods" :key="skill.method_id" class="skill-card">
                <div class="skill-header">
                  <span class="skill-icon">{{ skill.icon || '⚔️' }}</span>
                  <span class="skill-name">{{ skill.name }}</span>
                </div>
                <div class="skill-desc">{{ skill.description }}</div>
                <el-tag v-if="skill.equipped" type="success" size="small">已装备</el-tag>
                <el-button v-else size="small" @click="equipSkill(skill)">装备</el-button>
              </div>
            </div>
            <el-empty v-if="heartMethods.length === 0" description="暂无战斗技能" />
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useGameStore } from '../stores/game'

const router = useRouter()
const gameStore = useGameStore()
const activeTab = ref('all')

const committing = ref(false)
const pendingAttributes = ref({ strength: 0, intelligence: 0, agility: 0 })
const pendingSkills = ref({})

const heartMethods = ref([])

const player = computed(() => gameStore.player)

const pendingAttributePoints = computed(() => {
  return pendingAttributes.value.strength + pendingAttributes.value.intelligence + pendingAttributes.value.agility
})

const availableSkillPoints = computed(() => {
  if (!player.value) return 0
  const basePoints = Math.floor((player.value.strength || 5) / 3) + 
                    Math.floor((player.value.intelligence || 5) / 3) + 
                    Math.floor((player.value.agility || 5) / 3)
  const used = usedSkillPoints.value
  const pending = Object.values(pendingSkills.value).reduce((a, b) => a + b, 0)
  return basePoints - used - pending
})

const usedSkillPoints = computed(() => {
  if (!player.value?.skills) return 0
  return Object.values(player.value.skills).reduce((a, b) => a + b, 0)
})

const hasPendingChanges = computed(() => {
  return pendingAttributePoints.value > 0 || Object.values(pendingSkills.value).some(v => v > 0)
})

const allSkills = computed(() => {
  const skills = [
    { skill_id: 1, name: '铁骨', description: '增加生命值上限', icon: '🛡️', attribute: 'strength', max_level: 10, current_level: player.value?.skills?.[1] || 0, effect_text: '每级+10生命值' },
    { skill_id: 2, name: '强击', description: '增加物理攻击伤害', icon: '⚔️', attribute: 'strength', max_level: 10, current_level: player.value?.skills?.[2] || 0, effect_text: '每级+2攻击' },
    { skill_id: 3, name: '武器专精', description: '各类武器伤害加成', icon: '🗡️', attribute: 'strength', max_level: 10, current_level: player.value?.skills?.[3] || 0, effect_text: '每级+1%武器伤害' },
    { skill_id: 10, name: '跑动', description: '增加闪避率', icon: '🏃', attribute: 'agility', max_level: 10, current_level: player.value?.skills?.[10] || 0, effect_text: '每级+1%闪避' },
    { skill_id: 11, name: '盾防', description: '增加防御力', icon: '🛡️', attribute: 'agility', max_level: 10, current_level: player.value?.skills?.[11] || 0, effect_text: '每级+2防御' },
    { skill_id: 12, name: '骑术', description: '骑乘能力', icon: '🐎', attribute: 'agility', max_level: 10, current_level: player.value?.skills?.[12] || 0, effect_text: '每级+2骑术' },
    { skill_id: 13, name: '弓术', description: '弓箭伤害', icon: '🏹', attribute: 'agility', max_level: 10, current_level: player.value?.skills?.[13] || 0, effect_text: '每级+2弓术' },
    { skill_id: 14, name: '投掷', description: '投掷武器伤害', icon: '🎯', attribute: 'agility', max_level: 10, current_level: player.value?.skills?.[14] || 0, effect_text: '每级+2投掷' },
    { skill_id: 20, name: '战术', description: '战斗策略', icon: '📜', attribute: 'intelligence', max_level: 10, current_level: player.value?.skills?.[20] || 0, effect_text: '每级+1战术' },
    { skill_id: 21, name: '教练', description: '训练士兵', icon: '👥', attribute: 'intelligence', max_level: 10, current_level: player.value?.skills?.[21] || 0, effect_text: '每级+1教练经验' },
    { skill_id: 22, name: '交易', description: '买卖折扣', icon: '💰', attribute: 'intelligence', max_level: 10, current_level: player.value?.skills?.[22] || 0, effect_text: '每级-1%交易税' },
    { skill_id: 23, name: '俘虏管理', description: '俘虏容量', icon: '⛓️', attribute: 'intelligence', max_level: 10, current_level: player.value?.skills?.[23] || 0, effect_text: '每级+1俘虏容量' },
    { skill_id: 30, name: '急救', description: '战场包扎', icon: '🩹', attribute: 'intelligence', max_level: 10, current_level: player.value?.skills?.[30] || 0, effect_text: '每级+5治疗效果' },
    { skill_id: 31, name: '草药学', description: '采集与制药', icon: '🌿', attribute: 'intelligence', max_level: 10, current_level: player.value?.skills?.[31] || 0, effect_text: '每级+1采集效率' },
    { skill_id: 32, name: '外科手术', description: '高级治疗', icon: '🔪', attribute: 'intelligence', max_level: 10, current_level: player.value?.skills?.[32] || 0, effect_text: '每级+3手术效果' },
  ]
  return skills
})

const strengthSkills = computed(() => allSkills.value.filter(s => s.attribute === 'strength'))
const agilitySkills = computed(() => allSkills.value.filter(s => s.attribute === 'agility'))
const intelligenceSkills = computed(() => allSkills.value.filter(s => s.attribute === 'intelligence'))

const canIncrementAttr = () => (player.value?.attribute_points || 0) > pendingAttributePoints.value

const canDecrementAttr = (attr) => {
  const baseAttr = attr === 'strength' ? player.value?.strength : 
                   attr === 'intelligence' ? player.value?.intelligence : 
                   player.value?.agility
  const pending = pendingAttributes.value[attr]
  return (baseAttr || 5) + pending > 5
}

const incrementAttr = (attr) => {
  if (!canIncrementAttr()) return
  pendingAttributes.value[attr]++
}

const decrementAttr = (attr) => {
  if (!canDecrementAttr(attr)) return
  pendingAttributes.value[attr]--
}

const canAddSkillPoint = () => availableSkillPoints.value > 0

const canRemoveSkillPoint = (skillId) => {
  const skill = player.value?.skills?.[skillId] || 0
  const pending = pendingSkills.value[skillId] || 0
  return skill + pending > 0
}

const addSkillPoint = (skillId) => {
  if (!canAddSkillPoint()) return
  pendingSkills.value[skillId] = (pendingSkills.value[skillId] || 0) + 1
}

const removeSkillPoint = (skillId) => {
  if (!canRemoveSkillPoint(skillId)) return
  pendingSkills.value[skillId] = Math.max(0, (pendingSkills.value[skillId] || 0) - 1)
}

const resetAllPoints = () => {
  pendingAttributes.value = { strength: 0, intelligence: 0, agility: 0 }
  pendingSkills.value = {}
}

const commitAllPoints = async () => {
  if (!hasPendingChanges.value) return
  committing.value = true

  try {
    if (pendingAttributePoints.value > 0) {
      gameStore.send({
        type: 'allocate_attribute_points',
        data: {
          strength: pendingAttributes.value.strength,
          intelligence: pendingAttributes.value.intelligence,
          agility: pendingAttributes.value.agility
        }
      })
    }

    const totalSkillPending = Object.values(pendingSkills.value).reduce((a, b) => a + b, 0)
    if (totalSkillPending > 0) {
      gameStore.send({
        type: 'allocate_skill_points',
        data: pendingSkills.value
      })
    }

    setTimeout(() => {
      pendingAttributes.value = { strength: 0, intelligence: 0, agility: 0 }
      pendingSkills.value = {}
      gameStore.getPanel()
      committing.value = false
      ElMessage.success('加点成功！')
    }, 500)
  } catch (e) {
    ElMessage.error('分配失败')
    committing.value = false
  }
}

const equipSkill = (skill) => {
  gameStore.send({ type: 'learn_heart_method', data: { method_id: skill.method_id || skill.skill_id } })
}

const handleWsMessage = (msg) => {
  if (msg.type === 'heart_methods_data') {
    heartMethods.value = msg.data?.methods || []
  } else if (msg.type === 'action_result') {
    const action = msg.action
    if (msg.data?.success) {
      if (action === 'allocate_attribute_points' || action === 'allocate_skill_points') {
        ElMessage.success(msg.data.message || '加点成功')
      } else {
        ElMessage.success(msg.data.message)
      }
      gameStore.getPanel()
    } else {
      ElMessage.error(msg.data?.message || '操作失败')
    }
  }
}

onMounted(async () => {
  if (!gameStore.token) {
    router.push('/')
    return
  }
  if (!gameStore.connected) {
    await gameStore.connectWs()
  }
  gameStore.wsMessageHandlers = gameStore.wsMessageHandlers || {}
  gameStore.wsMessageHandlers['skills'] = handleWsMessage
  await gameStore.getPanel()
  gameStore.send({ type: 'get_heart_methods' })
})
</script>

<style scoped>
.view-container {
  min-height: 100vh;
  background: linear-gradient(180deg, #0D0D0D 0%, #1A1A1A 100%);
  padding: 20px;
}

.nav-bar {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 20px;
}

.nav-bar h2 {
  color: #ffd700;
  margin: 0;
}

.skills-card {
  background: linear-gradient(145deg, #252525 0%, #1E1E1E 100%);
  border: 1px solid #3D3D3D;
  color: #F5DEB3;
}

.points-header {
  margin-bottom: 20px;
  padding: 15px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
}

.points-row {
  display: flex;
  align-items: center;
  gap: 20px;
}

.point-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 20px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.point-label {
  color: #888;
  font-size: 12px;
}

.point-value {
  color: #ffd700;
  font-size: 24px;
  font-weight: bold;
}

.point-value.skill {
  color: #4FC3F7;
}

.point-actions {
  margin-left: auto;
  display: flex;
  gap: 10px;
}

.skills-unified {
  padding: 10px;
}

.skill-category {
  margin-bottom: 25px;
}

.category-title {
  color: #ffd700;
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 15px;
  padding-bottom: 8px;
  border-bottom: 1px solid #3D3D3D;
}

.skills-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 15px;
}

.skill-card-full {
  display: flex;
  gap: 12px;
  padding: 15px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid #3D3D3D;
  border-radius: 10px;
  transition: all 0.2s;
}

.skill-card-full:hover {
  border-color: #ffd700;
  transform: translateY(-2px);
}

.skill-icon-area {
  font-size: 32px;
  width: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.skill-info {
  flex: 1;
}

.skill-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 5px;
}

.skill-name {
  color: #ffd700;
  font-weight: bold;
  font-size: 15px;
}

.skill-desc {
  color: #aaa;
  font-size: 12px;
  margin-bottom: 4px;
}

.skill-effect {
  color: #4FC3F7;
  font-size: 11px;
  margin-bottom: 6px;
}

.skill-level-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 6px;
}

.current-level {
  color: #fff;
  font-size: 14px;
}

.max-level {
  color: #666;
  font-size: 12px;
}

.skill-progress-bar {
  height: 6px;
  background: #333;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #ffd700, #ff9800);
  transition: width 0.3s;
}

.progress-fill.agility {
  background: linear-gradient(90deg, #4CAF50, #8BC34A);
}

.progress-fill.intelligence {
  background: linear-gradient(90deg, #2196F3, #03A9F4);
}

.skill-controls {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.pending-points {
  color: #81C784;
  font-weight: bold;
}

.attributes-panel {
  padding: 20px;
}

.attr-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.attr-card-full {
  padding: 20px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
  border: 2px solid #3D3D3D;
  text-align: center;
}

.attr-card-full.strength {
  border-color: #ff7043;
}

.attr-card-full.intelligence {
  border-color: #7e57c2;
}

.attr-card-full.agility {
  border-color: #26a69a;
}

.attr-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 10px;
}

.attr-icon {
  font-size: 28px;
}

.attr-name {
  font-size: 18px;
  font-weight: bold;
  color: #ffd700;
}

.attr-base {
  font-size: 24px;
  color: #fff;
  font-weight: bold;
}

.attr-desc {
  color: #888;
  font-size: 12px;
  margin-bottom: 15px;
}

.attr-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
}

.pending-count {
  color: #81C784;
  font-size: 18px;
  font-weight: bold;
  min-width: 30px;
}

.attr-summary {
  margin-top: 20px;
  padding: 15px;
  background: rgba(255, 215, 0, 0.1);
  border-radius: 8px;
  text-align: center;
  color: #ffd700;
}

:deep(.el-tabs__item) {
  color: #aaa;
}

:deep(.el-tabs__item.is-active) {
  color: #ffd700;
}

:deep(.el-tabs__active-bar) {
  background-color: #ffd700;
}
</style>
