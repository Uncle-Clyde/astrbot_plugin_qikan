<template>
  <div class="nav-item" :class="{ active }" @click="handleClick">
    <span class="nav-icon">{{ icon }}</span>
    <span class="nav-text">{{ text }}</span>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({
  icon: { type: String, default: '📌' },
  text: { type: String, default: '' },
  active: { type: Boolean, default: false },
  to: { type: String, default: '' }
})

const emit = defineEmits(['click'])
const router = useRouter()

const handleClick = () => {
  emit('click')
  if (props.to) {
    router.push(props.to)
  }
}
</script>

<style scoped>
.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 16px;
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  color: var(--text-secondary);
  min-width: 60px;
}

.nav-item:hover {
  background: rgba(212, 164, 100, 0.1);
  color: var(--primary-color);
}

.nav-item.active {
  background: rgba(212, 164, 100, 0.2);
  color: var(--primary-color);
}

.nav-icon {
  font-size: 20px;
  margin-bottom: 2px;
}

.nav-text {
  font-size: 12px;
  white-space: nowrap;
}
</style>
