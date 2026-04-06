<template>
  <nav class="side-nav" :class="{ collapsed: isCollapsed }">
    <button class="nav-toggle" @click="isCollapsed = !isCollapsed">
      {{ isCollapsed ? '☰' : '✕' }}
    </button>
    <div v-show="!isCollapsed" class="nav-items">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ active: isActive(item.path) }"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span class="nav-label">{{ item.label }}</span>
      </router-link>
    </div>
  </nav>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const isCollapsed = ref(false)

const navItems = [
  { path: '/home', icon: '⚔️', label: '角色' },
  { path: '/skills', icon: '📜', label: '技能' },
  { path: '/map', icon: '🗺️', label: '地图' },
  { path: '/hunting', icon: '🏹', label: '狩猎' },
  { path: '/gathering', icon: '🌿', label: '采集' },
  { path: '/family', icon: '🏰', label: '家族' },
  { path: '/market', icon: '🏛️', label: '集市' },
  { path: '/blacksmith', icon: '🔨', label: '铁匠' },
  { path: '/companions', icon: '🤝', label: '同伴' },
  { path: '/troops', icon: '🛡️', label: '部队' },
  { path: '/tournament', icon: '🏟️', label: '竞技场' },
  { path: '/chat', icon: '💬', label: '世界' },
  { path: '/mail', icon: '📮', label: '邮件' },
  { path: '/achievements', icon: '🏆', label: '成就' },
  { path: '/titles', icon: '👑', label: '称号' },
  { path: '/icons', icon: '⚙️', label: '设置' },
]

const isActive = (path) => route.path === path
</script>

<style scoped>
.side-nav {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: 64px;
  background: rgba(15,15,25,0.98);
  border-right: 1px solid #2a2a3e;
  z-index: 50;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  overflow: hidden;
}

.side-nav.collapsed {
  width: 40px;
}

.nav-toggle {
  width: 100%;
  height: 40px;
  background: rgba(0,0,0,0.3);
  border: none;
  border-bottom: 1px solid #2a2a3e;
  color: #888;
  cursor: pointer;
  font-size: 16px;
  transition: background 0.2s;
}

.nav-toggle:hover {
  background: rgba(0,0,0,0.5);
  color: #fff;
}

.nav-items {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 8px 4px;
  text-decoration: none;
  color: #888;
  transition: all 0.2s;
  border-left: 3px solid transparent;
  gap: 2px;
}

.nav-item:hover {
  background: rgba(255,255,255,0.05);
  color: #ccc;
}

.nav-item.active {
  background: rgba(212,175,55,0.1);
  border-left-color: var(--gold);
  color: var(--text-gold);
}

.nav-icon {
  font-size: 18px;
}

.nav-label {
  font-size: 9px;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .side-nav {
    width: 48px;
  }
  .side-nav.collapsed {
    width: 32px;
  }
  .nav-icon {
    font-size: 16px;
  }
  .nav-label {
    font-size: 8px;
  }
}
</style>
