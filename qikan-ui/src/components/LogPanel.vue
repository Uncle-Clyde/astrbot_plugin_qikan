<template>
  <div class="log-panel" :class="{ collapsed: collapsed }">
    <div class="log-header" @click="collapsed = !collapsed">
      <h3>📋 个人日志</h3>
      <div class="log-header-actions">
        <button class="log-clear-btn" @click.stop="clearLogs" title="清空日志">🗑️</button>
        <span class="collapse-icon">{{ collapsed ? '▶' : '▼' }}</span>
      </div>
    </div>
    <div v-show="!collapsed" class="log-body">
      <div class="log-filters">
        <button
          v-for="f in filters"
          :key="f.key"
          class="filter-btn"
          :class="{ active: logStore.filter === f.key }"
          @click="logStore.setFilter(f.key)"
        >
          {{ f.icon }} {{ f.label }}
        </button>
      </div>
      <div class="log-list">
        <div v-if="logStore.filteredLogs.length === 0" class="no-logs">
          暂无日志记录
        </div>
        <div
          v-for="log in logStore.filteredLogs"
          :key="log.id"
          class="log-entry"
        >
          <div class="log-entry-header">
            <span class="log-icon">{{ log.icon }}</span>
            <span class="log-title">{{ log.title }}</span>
            <span class="log-time">{{ formatTime(log.timestamp) }}</span>
          </div>
          <div v-if="log.content" class="log-content">{{ log.content }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useLogStore } from '../stores/log'

const logStore = useLogStore()
const collapsed = ref(false)

const filters = [
  { key: 'all', icon: '📋', label: '全部' },
  { key: 'combat', icon: '⚔️', label: '战斗' },
  { key: 'trade', icon: '💰', label: '交易' },
  { key: 'gather', icon: '🌿', label: '采集' },
  { key: 'system', icon: '🔧', label: '系统' },
  { key: 'social', icon: '💬', label: '社交' },
  { key: 'travel', icon: '🗺️', label: '移动' },
]

const clearLogs = () => {
  if (confirm('确定清空所有日志吗？')) {
    logStore.clearLogs()
  }
}

const formatTime = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${h}:${m}`
}

onMounted(() => {
  logStore.init()
})
</script>

<style scoped>
.log-panel {
  background: rgba(20,20,30,0.95);
  border: 1px solid #2a2a3e;
  border-radius: 10px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.log-panel.collapsed {
  max-height: 44px;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: rgba(0,0,0,0.3);
  cursor: pointer;
  transition: background 0.2s;
}

.log-header:hover {
  background: rgba(0,0,0,0.4);
}

.log-header h3 {
  margin: 0;
  font-size: 14px;
  color: var(--text-gold);
}

.log-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.log-clear-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.log-clear-btn:hover {
  opacity: 1;
}

.collapse-icon {
  color: #888;
  font-size: 12px;
}

.log-body {
  padding: 10px 14px;
}

.log-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 10px;
}

.filter-btn {
  padding: 4px 8px;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 4px;
  background: rgba(255,255,255,0.05);
  color: #aaa;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-btn:hover {
  background: rgba(255,255,255,0.1);
  color: #fff;
}

.filter-btn.active {
  background: rgba(212,175,55,0.2);
  border-color: rgba(212,175,55,0.4);
  color: var(--text-gold);
}

.log-list {
  max-height: 450px;
  overflow-y: auto;
}

.no-logs {
  text-align: center;
  color: #555;
  padding: 20px;
  font-size: 13px;
}

.log-entry {
  padding: 8px 0;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}

.log-entry:last-child {
  border-bottom: none;
}

.log-entry-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.log-icon {
  font-size: 14px;
  flex-shrink: 0;
}

.log-title {
  font-size: 12px;
  color: #ddd;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.log-time {
  font-size: 10px;
  color: #666;
  flex-shrink: 0;
}

.log-content {
  font-size: 11px;
  color: #999;
  margin-top: 3px;
  padding-left: 20px;
  line-height: 1.4;
}
</style>
