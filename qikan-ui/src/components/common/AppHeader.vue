<template>
  <div class="app-header" :style="headerStyle">
    <div class="header-left">
      <div class="logo" @click="goHome">
        <span class="logo-icon">{{ logoIcon }}</span>
        <span class="logo-text">{{ logoText }}</span>
      </div>
      <el-tag v-if="player" :type="realmTagType" size="small" class="realm-tag">
        {{ player.realm_name || '平民' }}
      </el-tag>
    </div>
    
    <nav class="header-nav">
      <slot name="nav"></slot>
    </nav>
    
    <div class="header-right">
      <slot name="right"></slot>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const goHome = () => {
  router.push('/home')
}

const props = defineProps({
  player: Object,
  logoIcon: { type: String, default: '⚔️' },
  logoText: { type: String, default: '骑砍英雄传' },
  customStyle: { type: Object, default: () => ({}) }
})

const headerStyle = computed(() => {
  const defaultStyle = {}
  if (props.customStyle.header_color) {
    defaultStyle.background = props.customStyle.header_color
  }
  if (props.customStyle.header_border_color) {
    defaultStyle.borderColor = props.customStyle.header_border_color
  }
  return { ...defaultStyle, ...props.customStyle }
})

const realmTagType = computed(() => {
  if (!props.player) return 'info'
  const realm = props.player.realm || 0
  if (realm >= 8) return 'danger'
  if (realm >= 6) return 'warning'
  if (realm >= 4) return 'success'
  if (realm >= 2) return 'primary'
  return 'info'
})
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 60px;
  background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-primary) 100%);
  border-bottom: 2px solid var(--border-color);
  box-shadow: var(--shadow-md);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: transform var(--transition-fast);
}

.logo:hover {
  transform: scale(1.05);
}

.logo-icon {
  font-size: 28px;
}

.logo-text {
  font-size: 18px;
  font-weight: bold;
  color: var(--primary-color);
  text-shadow: 0 0 10px rgba(212, 164, 100, 0.5);
}

.realm-tag {
  font-weight: bold;
}

.header-nav {
  display: flex;
  align-items: center;
  gap: 4px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
