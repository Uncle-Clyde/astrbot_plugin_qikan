<template>
  <div class="view-container">
    <div class="page-header">
      <el-button class="back-btn" @click="$router.push('/home')">← 返回</el-button>
      <h2>🏚️ 地牢历练</h2>
      <div class="player-stats">
        <span>❤️ {{ player?.hp ?? 0 }}/{{ player?.max_hp ?? 100 }}</span>
        <span>⚡ {{ player?.lingqi ?? 0 }}/{{ player?.max_lingqi ?? 50 }}</span>
      </div>
    </div>

    <div class="dungeon-content">
      <div v-if="!dungeonState" class="dungeon-entrance">
        <div class="entrance-card">
          <div class="entrance-icon">🏚️</div>
          <h3>进入地牢</h3>
          <p>地牢中充满了危险的怪物和珍贵的宝藏。每次进入都会消耗体力。</p>
          <div class="entrance-info">
            <p>消耗: 20 体力</p>
            <p>奖励: 经验、第纳尔、装备</p>
          </div>
          <el-button type="primary" size="large" @click="enterDungeon" :loading="isLoading">
            ⚔️ 进入地牢
          </el-button>
        </div>
      </div>

      <div v-else class="dungeon-active">
        <div class="dungeon-header">
          <div class="floor-info">
            <span class="floor-label">当前层数</span>
            <span class="floor-number">{{ dungeonState.current_floor || 1 }}</span>
          </div>
          <div class="dungeon-status">
            <el-tag :type="dungeonState.in_combat ? 'danger' : 'success'">
              {{ dungeonState.in_combat ? '战斗中' : '探索中' }}
            </el-tag>
          </div>
        </div>

        <div v-if="dungeonState.in_combat && dungeonState.combat" class="combat-area">
          <div class="combat-display">
            <div class="combatant player-side">
              <div class="name">你</div>
              <div class="hp-bar">
                <div class="hp-fill player-hp" :style="{ width: playerHpPercent + '%' }"></div>
                <span class="hp-text">{{ dungeonState.combat.player_hp }}/{{ dungeonState.combat.player_max_hp }}</span>
              </div>
              <div class="status-effects">
                <span v-if="dungeonState.combat.player_defending" class="status-icon" title="防御中">🛡️</span>
                <span v-if="dungeonState.combat.player_berserk > 0" class="status-icon" title="狂暴">🔥×{{ dungeonState.combat.player_berserk }}</span>
                <span v-if="dungeonState.combat.player_combo > 1" class="status-icon combo" title="连击">💥×{{ dungeonState.combat.player_combo }}</span>
                <span v-if="dungeonState.combat.player_shield_stun > 0" class="status-icon" title="眩晕">⚡×{{ dungeonState.combat.player_shield_stun }}</span>
              </div>
            </div>
            <div class="vs">VS</div>
            <div class="combatant enemy-side">
              <div class="name">{{ dungeonState.combat.enemy_name || '怪物' }}</div>
              <div class="hp-bar">
                <div class="hp-fill enemy-hp" :style="{ width: enemyHpPercent + '%' }"></div>
                <span class="hp-text">{{ dungeonState.combat.enemy_hp }}/{{ dungeonState.combat.enemy_max_hp }}</span>
              </div>
              <div class="status-effects">
                <span v-if="dungeonState.combat.enemy_stunned > 0" class="status-icon" title="眩晕">⚡×{{ dungeonState.combat.enemy_stunned }}</span>
                <span v-if="dungeonState.combat.enemy_weakened > 0" class="status-icon" title="虚弱">💀×{{ dungeonState.combat.enemy_weakened }}</span>
              </div>
              <div class="enemy-intent" v-if="dungeonState.combat.enemy_intent">
                <span v-if="dungeonState.combat.enemy_intent === 'attack'">⚔️ 准备攻击</span>
                <span v-else-if="dungeonState.combat.enemy_intent === 'defend'">🛡️ 准备防御</span>
                <span v-else-if="dungeonState.combat.enemy_intent === 'special'">💥 准备强力攻击</span>
              </div>
            </div>
          </div>

          <div class="combat-log">
            <div v-for="(log, i) in (dungeonState.combat.combat_log || [])" :key="i" class="log-entry">{{ log }}</div>
          </div>

          <div class="combat-info-bar">
            <span class="info-item">⚡ 体力: {{ dungeonState.combat.player_lingqi }}/{{ dungeonState.combat.player_max_lingqi }}</span>
            <span class="info-item">🔄 回合: {{ dungeonState.combat.round_number }}/{{ dungeonState.combat.max_rounds }}</span>
          </div>

          <div class="combat-actions">
            <el-button type="primary" @click="combatAction('attack')" :loading="isLoading">⚔️ 攻击</el-button>
            <el-button @click="combatAction('defend')" :loading="isLoading">🛡️ 防御</el-button>
            <el-button type="warning" @click="combatAction('charge')" :loading="isLoading" :disabled="isOnCooldown('charge')">
              🐎 冲锋 <span class="cooldown-badge" v-if="isOnCooldown('charge')">(CD:{{ getCooldown('charge') }})</span>
            </el-button>
            <el-button type="info" @click="combatAction('shield_bash')" :loading="isLoading" :disabled="isOnCooldown('shield_bash')">
              💥 盾击 <span class="cooldown-badge" v-if="isOnCooldown('shield_bash')">(CD:{{ getCooldown('shield_bash') }})</span>
            </el-button>
            <el-button type="danger" @click="combatAction('berserk')" :loading="isLoading" :disabled="isOnCooldown('berserk')">
              🔥 狂暴 <span class="cooldown-badge" v-if="isOnCooldown('berserk')">(CD:{{ getCooldown('berserk') }})</span>
            </el-button>
            <el-button type="success" @click="combatAction('skill')" :loading="isLoading">✨ 技能</el-button>
            <el-button @click="combatAction('flee')" :loading="isLoading">🏃 逃跑</el-button>
          </div>
        </div>

        <div v-else class="explore-area">
          <div class="explore-info">
            <p>📍 你正在探索地牢第 {{ dungeonState.current_floor || 1 }} 层</p>
            <p v-if="dungeonState.loot && dungeonState.loot.length > 0">
              🎁 已获得战利品: {{ dungeonState.loot.map(l => l.name).join(', ') }}
            </p>
          </div>
          <div class="explore-actions">
            <el-button type="primary" size="large" @click="advanceFloor" :loading="isLoading">
              ⬇️ 推进下一层
            </el-button>
            <el-button type="info" size="large" @click="exitDungeon" :loading="isLoading">
              🚪 退出地牢
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { ElMessage } from 'element-plus'

const router = useRouter()
const gameStore = useGameStore()
const player = computed(() => gameStore.player)
const dungeonState = ref(null)
const isLoading = ref(false)

const playerHpPercent = computed(() => {
  if (!dungeonState.value?.combat?.player_max_hp) return 100
  return Math.max(0, (dungeonState.value.combat.player_hp / dungeonState.value.combat.player_max_hp) * 100)
})

const enemyHpPercent = computed(() => {
  if (!dungeonState.value?.combat?.enemy_max_hp) return 100
  return Math.max(0, (dungeonState.value.combat.enemy_hp / dungeonState.value.combat.enemy_max_hp) * 100)
})

const enterDungeon = async () => {
  isLoading.value = true
  try {
    const result = await gameStore.wsCall('dungeon_start')
    if (result?.success) {
      ElMessage.success('进入地牢')
      dungeonState.value = result.state || result.data || {}
    } else {
      ElMessage.error(result?.message || '进入失败')
    }
  } catch (e) {
    ElMessage.error('请求失败')
  } finally {
    isLoading.value = false
  }
}

const advanceFloor = async () => {
  isLoading.value = true
  try {
    const result = await gameStore.wsCall('dungeon_advance')
    if (result?.success) {
      ElMessage.success(result.message || '推进成功')
      dungeonState.value = result.state || result.data || dungeonState.value
    } else {
      ElMessage.error(result?.message || '推进失败')
    }
  } catch (e) {
    ElMessage.error('请求失败')
  } finally {
    isLoading.value = false
  }
}

const exitDungeon = async () => {
  isLoading.value = true
  try {
    const result = await gameStore.wsCall('dungeon_exit')
    if (result?.success) {
      ElMessage.success(result.message || '退出成功')
      dungeonState.value = null
    }
  } catch (e) {
    ElMessage.error('请求失败')
  } finally {
    isLoading.value = false
  }
}

const combatAction = async (action) => {
  isLoading.value = true
  try {
    const result = await gameStore.wsCall('dungeon_combat', { action })
    if (result?.success) {
      dungeonState.value = result.state || result.data || dungeonState.value
      if (result.combat_end) {
        if (result.outcome === 'win') {
          ElMessage.success('战斗胜利')
        } else if (result.outcome === 'flee') {
          ElMessage.info('成功逃离')
        }
      }
    } else {
      ElMessage.error(result?.message || '战斗失败')
      if (result?.fled || result?.died) {
        dungeonState.value = null
      }
    }
  } catch (e) {
    ElMessage.error('请求失败')
  } finally {
    isLoading.value = false
  }
}

const isOnCooldown = (action) => {
  const cooldowns = dungeonState.value?.combat?.skill_cooldowns || {}
  return (cooldowns[action] || 0) > 0
}

const getCooldown = (action) => {
  const cooldowns = dungeonState.value?.combat?.skill_cooldowns || {}
  return cooldowns[action] || 0
}

onMounted(async () => {
  try {
    const state = await gameStore.wsCall('dungeon_state')
    if (state?.active) {
      dungeonState.value = state
    }
  } catch (e) {}
})
</script>

<style scoped>
.view-container {
  padding: 16px;
  max-width: 900px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  flex: 1;
  color: #d4a464;
}

.player-stats {
  display: flex;
  gap: 16px;
  color: #aaa;
  font-size: 14px;
}

.entrance-card {
  text-align: center;
  padding: 40px;
  background: rgba(20, 20, 35, 0.9);
  border: 2px solid #2a2a3e;
  border-radius: 12px;
}

.entrance-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.entrance-card h3 {
  color: #e8e0d0;
  font-size: 24px;
  margin: 0 0 12px;
}

.entrance-card p {
  color: #888;
  margin: 4px 0;
}

.entrance-info {
  margin: 16px 0;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.dungeon-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: rgba(20, 20, 35, 0.9);
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  margin-bottom: 16px;
}

.floor-label {
  display: block;
  font-size: 12px;
  color: #888;
}

.floor-number {
  display: block;
  font-size: 32px;
  font-weight: bold;
  color: #d4a464;
}

.combat-area, .explore-area {
  padding: 16px;
  background: rgba(20, 20, 35, 0.9);
  border: 1px solid #2a2a3e;
  border-radius: 8px;
}

.combat-display {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 16px;
}

.combatant {
  flex: 1;
  text-align: center;
}

.status-effects {
  display: flex;
  gap: 4px;
  justify-content: center;
  margin-top: 4px;
}

.status-icon {
  font-size: 14px;
}

.status-icon.combo {
  color: #ff9800;
}

.enemy-intent {
  font-size: 11px;
  color: #f44336;
  margin-top: 4px;
}

.combat-info-bar {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-bottom: 12px;
  font-size: 12px;
  color: #888;
}

.cooldown-badge {
  font-size: 10px;
  color: #f44336;
}

.combatant .name {
  font-size: 16px;
  font-weight: bold;
  color: #e8e0d0;
  margin-bottom: 8px;
}

.hp-bar {
  position: relative;
  height: 24px;
  background: #1a1a2e;
  border-radius: 12px;
  overflow: hidden;
}

.hp-fill {
  height: 100%;
  border-radius: 12px;
  transition: width 0.3s;
}

.player-hp { background: linear-gradient(90deg, #4caf50, #8bc34a); }
.enemy-hp { background: linear-gradient(90deg, #f44336, #ff5722); }

.hp-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 12px;
  color: #fff;
  text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
}

.vs {
  font-size: 24px;
  font-weight: bold;
  color: #d4a464;
}

.combat-log {
  max-height: 150px;
  overflow-y: auto;
  padding: 12px;
  background: rgba(10, 10, 20, 0.8);
  border-radius: 6px;
  margin-bottom: 16px;
}

.log-entry {
  font-size: 13px;
  color: #aaa;
  padding: 2px 0;
}

.combat-actions, .explore-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
}

.explore-info {
  margin-bottom: 16px;
}

.explore-info p {
  color: #aaa;
  margin: 4px 0;
}
</style>
