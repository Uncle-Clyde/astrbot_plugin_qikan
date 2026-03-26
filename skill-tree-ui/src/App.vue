<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useSkillStore } from './stores/skillStore'
import { wsService, isConnected, connectionError } from './services/websocket'
import SkillTree from './components/SkillTree.vue'
import SkillDetail from './components/SkillDetail.vue'
import CombatSkills from './components/CombatSkills.vue'
import type { Skill } from './stores/skillStore'

const store = useSkillStore()
const wsUrl = ref('')
const showDetail = ref(false)

onMounted(async () => {
  store.setupMessageHandlers()
  
  const wsBase = (window as any).__XIUXIAN_WS_BASE__ || window.location.origin
  wsUrl.value = wsBase.replace(/^http/, 'ws') + '/ws'
  
  try {
    await wsService.connect(wsUrl.value)
    store.fetchPassiveSkills()
  } catch (e) {
    console.error('Failed to connect:', e)
  }
})

onUnmounted(() => {
  wsService.disconnect()
})

function handleSkillSelect(skill: Skill) {
  store.selectSkill(skill)
  showDetail.value = true
}

function handleCloseDetail() {
  showDetail.value = false
  store.selectSkill(null)
}

function handleLearn(skill: Skill) {
  store.learnSkill(skill.method_id)
}

function handleEquip(skill: Skill) {
  store.equipSkill(skill.method_id)
}

function handleUnequip() {
  store.unequipSkill()
}

function setActiveTab(tab: 'passive' | 'combat') {
  store.setActiveTab(tab)
}

function handleSearch(event: Event) {
  const target = event.target as HTMLInputElement
  store.setSearchQuery(target.value)
}

function setQualityFilter(quality: number | null) {
  store.setFilterQuality(quality)
}

function setRealmFilter(realm: number | null) {
  store.setFilterRealm(realm)
}
</script>

<template>
  <div class="app-container">
    <header class="app-header">
      <div class="header-left">
        <h1>🗡️ 骑砍英雄传 - 技能系统</h1>
        <div class="connection-status" :class="{ connected: isConnected }">
          {{ isConnected ? '已连接' : '未连接' }}
        </div>
      </div>
      
      <nav class="tab-nav">
        <button 
          class="tab-btn" 
          :class="{ active: store.activeTab === 'passive' }"
          @click="setActiveTab('passive')"
        >
          被动技能
          <span class="badge" v-if="store.equippedSkillsCount > 0">
            {{ store.equippedSkillsCount }}
          </span>
        </button>
        <button 
          class="tab-btn" 
          :class="{ active: store.activeTab === 'combat' }"
          @click="setActiveTab('combat')"
        >
          战斗技能
          <span class="badge" v-if="store.equippedCombatSkillsCount > 0">
            {{ store.equippedCombatSkillsCount }}
          </span>
        </button>
      </nav>
      
      <div class="header-right">
        <input 
          type="text" 
          class="search-input"
          placeholder="搜索技能..."
          :value="store.searchQuery"
          @input="handleSearch"
        />
      </div>
    </header>
    
    <div class="filter-bar" v-if="store.activeTab === 'passive'">
      <span class="filter-label">品质:</span>
      <button 
        class="filter-btn" 
        :class="{ active: store.filterQuality === null }"
        @click="setQualityFilter(null)"
      >全部</button>
      <button 
        class="filter-btn quality-0"
        :class="{ active: store.filterQuality === 0 }"
        @click="setQualityFilter(0)"
      >普通</button>
      <button 
        class="filter-btn quality-1"
        :class="{ active: store.filterQuality === 1 }"
        @click="setQualityFilter(1)"
      >稀有</button>
      <button 
        class="filter-btn quality-2"
        :class="{ active: store.filterQuality === 2 }"
        @click="setQualityFilter(2)"
      >传说</button>
      
      <span class="filter-label">爵位:</span>
      <button 
        class="filter-btn"
        :class="{ active: store.filterRealm === null }"
        @click="setRealmFilter(null)"
      >全部</button>
      <button 
        class="filter-btn"
        :class="{ active: store.filterRealm === 0 }"
        @click="setRealmFilter(0)"
      >平民</button>
      <button 
        class="filter-btn"
        :class="{ active: store.filterRealm === 1 }"
        @click="setRealmFilter(1)"
      >新兵</button>
      <button 
        class="filter-btn"
        :class="{ active: store.filterRealm === 2 }"
        @click="setRealmFilter(2)"
      >老兵</button>
    </div>
    
    <main class="app-main">
      <div v-if="store.loading" class="loading-overlay">
        <div class="spinner"></div>
        <p>加载中...</p>
      </div>
      
      <div v-if="connectionError" class="error-message">
        {{ connectionError }}
      </div>
      
      <SkillTree 
        v-if="store.activeTab === 'passive'"
        :skill-trees="store.filteredPassiveSkills"
        @select="handleSkillSelect"
      />
      
      <CombatSkills 
        v-if="store.activeTab === 'combat'"
        :combat-skills="store.filteredCombatSkills"
        @select="(skill) => store.selectCombatSkill(skill)"
      />
      
      <SkillDetail 
        v-if="showDetail && store.selectedSkill"
        :skill="store.selectedSkill"
        @close="handleCloseDetail"
        @learn="handleLearn"
        @equip="handleEquip"
        @unequip="handleUnequip"
      />
    </main>
    
    <footer class="app-footer">
      <div class="zoom-hint">
        <span>滚轮缩放</span>
        <span>拖拽平移</span>
        <span>+/- 键调节</span>
        <span>F 适应窗口</span>
      </div>
    </footer>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
  background: #0a0a12;
  color: #fff;
  overflow: hidden;
}

.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: rgba(20, 20, 30, 0.95);
  border-bottom: 1px solid #2a2a3e;
  z-index: 50;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h1 {
  font-size: 20px;
  font-weight: 600;
}

.connection-status {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  background: rgba(255, 100, 100, 0.2);
  color: #ef4444;
}

.connection-status.connected {
  background: rgba(74, 222, 128, 0.2);
  color: #4ade80;
}

.tab-nav {
  display: flex;
  gap: 8px;
}

.tab-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  color: #888;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.tab-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.tab-btn.active {
  background: linear-gradient(135deg, #4a9eff, #3b82f6);
  color: #fff;
}

.tab-btn .badge {
  position: absolute;
  top: -6px;
  right: -6px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: #ef4444;
  color: #fff;
  font-size: 10px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.search-input {
  padding: 10px 16px;
  border: 1px solid #3a3a4e;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.3);
  color: #fff;
  font-size: 14px;
  width: 200px;
  outline: none;
  transition: border-color 0.2s;
}

.search-input:focus {
  border-color: #4a9eff;
}

.search-input::placeholder {
  color: #666;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: rgba(20, 20, 30, 0.8);
  border-bottom: 1px solid #2a2a3e;
}

.filter-label {
  font-size: 12px;
  color: #888;
  margin-right: 4px;
}

.filter-btn {
  padding: 6px 12px;
  border: 1px solid #3a3a4e;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  color: #888;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.filter-btn.active {
  background: rgba(74, 158, 255, 0.2);
  border-color: #4a9eff;
  color: #4a9eff;
}

.filter-btn.quality-0.active {
  background: rgba(156, 163, 175, 0.2);
  border-color: #9ca3af;
  color: #9ca3af;
}

.filter-btn.quality-1.active {
  background: rgba(96, 165, 250, 0.2);
  border-color: #60a5fa;
  color: #60a5fa;
}

.filter-btn.quality-2.active {
  background: rgba(245, 158, 11, 0.2);
  border-color: #f59e0b;
  color: #f59e0b;
}

.app-main {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
}

.loading-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(10, 10, 18, 0.9);
  z-index: 100;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #3a3a4e;
  border-top-color: #4a9eff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-overlay p {
  margin-top: 16px;
  color: #888;
}

.error-message {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 24px;
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid #ef4444;
  border-radius: 8px;
  color: #ef4444;
  z-index: 100;
}

.app-footer {
  padding: 8px 24px;
  background: rgba(20, 20, 30, 0.95);
  border-top: 1px solid #2a2a3e;
}

.zoom-hint {
  display: flex;
  gap: 24px;
  justify-content: center;
}

.zoom-hint span {
  font-size: 11px;
  color: #666;
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 4px;
}
</style>
