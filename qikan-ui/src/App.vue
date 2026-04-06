<template>
  <div id="app" :class="themeClass" :style="customStyles" @click="handleGlobalClick">
    <router-view />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import { useGameStore } from './stores/game'

const gameStore = useGameStore()

let audioStore = null
const getAudioStore = () => {
  if (!audioStore) {
    try {
      audioStore = require('./stores/audio').useAudioStore
    } catch (e) {
      console.warn('Audio store not available')
    }
  }
  return audioStore
}

const handleGlobalClick = (e) => {
  const target = e.target
  if (target.tagName === 'BUTTON' || target.closest('button')) {
    const audio = getAudioStore()
    if (audio) {
      audio.playSound('button')
    }
  }
}

const uiConfig = ref({
  enabled: false,
  background_gradient_start: '#1a1a2e',
  background_gradient_end: '#16213e',
  header_color: 'linear-gradient(135deg, #16213e 0%, #1a1a2e 100%)',
  header_border_color: '#4a4a8a',
  accent_color: '#d4a464',
  text_color: '#e8e0d0',
  button_color: '#d4a464'
})

const themeClass = computed(() => {
  if (uiConfig.value.enabled) {
    return 'custom-theme'
  }
  return 'default-theme'
})

const customStyles = computed(() => {
  if (!uiConfig.value.enabled) {
    return {}
  }
  return {
    '--primary-color': uiConfig.value.accent_color || '#d4a464',
    '--text-primary': uiConfig.value.text_color || '#e8e0d0',
    '--bg-primary': uiConfig.value.background_gradient_start || '#1a1a2e',
    '--bg-secondary': uiConfig.value.background_gradient_end || '#16213e',
    '--header-bg': uiConfig.value.header_color,
    '--header-border': uiConfig.value.header_border_color,
    '--button-bg': uiConfig.value.button_color || '#d4a464',
    background: `linear-gradient(135deg, ${uiConfig.value.background_gradient_start} 0%, ${uiConfig.value.background_gradient_end} 100%)`,
    'min-height': '100vh'
  }
})

const loadUiConfig = async () => {
  try {
    const resp = await fetch('/api/icons/config')
    const data = await resp.json()
    if (data.success && data.config) {
      uiConfig.value = { ...uiConfig.value, ...data.config }
    }
  } catch (e) {
    console.error('加载UI配置失败', e)
  }
}

onMounted(() => {
  loadUiConfig()
})

watch(() => gameStore.uiConfig, (newConfig) => {
  if (newConfig) {
    uiConfig.value = { ...uiConfig.value, ...newConfig }
  }
}, { deep: true })
</script>

<style>
@import './styles/variables.css';

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: linear-gradient(135deg, var(--bg-primary, #1a1a2e) 0%, var(--bg-secondary, #16213e) 100%);
  color: var(--text-primary, #e8e0d0);
}

#app {
  min-height: 100vh;
  transition: all 0.3s ease;
}

.default-theme {
  --primary-color: #d4a464;
  --bg-primary: #1a1a2e;
  --bg-secondary: #16213e;
}

.custom-theme {
  --primary-color: var(--primary-color);
  --bg-primary: var(--bg-primary);
  --bg-secondary: var(--bg-secondary);
}

.el-button--primary {
  --el-button-bg-color: var(--primary-color);
  --el-button-border-color: var(--primary-color);
  --el-button-hover-bg-color: var(--primary-color);
  --el-button-hover-border-color: var(--primary-color);
}

.el-input__wrapper {
  background: rgba(18, 18, 42, 0.8) !important;
  border: 1px solid var(--border-color, #4a4a8a) !important;
  box-shadow: none !important;
}

.el-input__inner {
  color: var(--text-primary, #e8e0d0) !important;
}

.el-textarea__inner {
  background: rgba(18, 18, 42, 0.8) !important;
  border: 1px solid var(--border-color, #4a4a8a) !important;
  color: var(--text-primary, #e8e0d0) !important;
}

.el-card {
  --el-card-bg-color: rgba(18, 18, 42, 0.8);
  --el-card-border-color: var(--border-color, #4a4a8a);
}

.el-dialog {
  --el-dialog-bg-color: #16213e;
  border: 1px solid var(--border-color, #4a4a8a);
}

.el-dialog__title {
  color: var(--primary-color, #d4a464) !important;
}

.el-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(74, 74, 138, 0.3);
  --el-table-row-hover-bg-color: rgba(212, 164, 100, 0.1);
  --el-table-border-color: var(--border-color, #4a4a8a);
  --el-table-text-color: var(--text-primary, #e8e0d0);
  --el-table-header-text-color: var(--primary-color, #d4a464);
}

.el-tabs__item {
  color: var(--text-secondary, #b8b8c8) !important;
}

.el-tabs__item.is-active {
  color: var(--primary-color, #d4a464) !important;
}

.el-message {
  --el-message-bg-color: rgba(18, 18, 42, 0.9);
  --el-message-border-color: var(--border-color, #4a4a8a);
}

.el-message__content {
  color: var(--text-primary, #e8e0d0) !important;
}

::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
}

::-webkit-scrollbar-thumb {
  background: var(--border-color, #4a4a8a);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--primary-color, #d4a464);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { 
    opacity: 0;
    transform: translateY(20px);
  }
  to { 
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.fade-enter-active {
  animation: fadeIn 0.3s ease;
}

.slide-enter-active {
  animation: slideUp 0.3s ease;
}
</style>
