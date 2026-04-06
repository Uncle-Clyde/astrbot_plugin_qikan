<template>
  <el-card class="game-card" :class="{ 'clickable': clickable }" @click="handleClick">
    <template #header v-if="title || $slots.header">
      <div class="card-header">
        <slot name="header">
          <span class="card-title">{{ title }}</span>
          <span v-if="subtitle" class="card-subtitle">{{ subtitle }}</span>
        </slot>
      </div>
    </template>
    <div class="card-body">
      <slot></slot>
    </div>
    <template #footer v-if="$slots.footer">
      <slot name="footer"></slot>
    </template>
  </el-card>
</template>

<script setup>
const props = defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  clickable: { type: Boolean, default: false }
})

const emit = defineEmits(['click'])

const handleClick = () => {
  if (props.clickable) {
    emit('click')
  }
}
</script>

<style scoped>
.game-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  transition: all var(--transition-normal);
}

.game-card:hover {
  border-color: var(--primary-color);
  box-shadow: var(--shadow-md);
}

.game-card.clickable {
  cursor: pointer;
}

.game-card.clickable:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.game-card :deep(.el-card__header) {
  background: rgba(74, 74, 138, 0.2);
  border-bottom: 1px solid var(--border-color);
  padding: 12px 16px;
}

.game-card :deep(.el-card__body) {
  padding: 16px;
  color: var(--text-primary);
}

.game-card :deep(.el-card__footer) {
  border-top: 1px solid var(--border-color);
  padding: 12px 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  color: var(--primary-color);
  font-weight: bold;
  font-size: 16px;
}

.card-subtitle {
  color: var(--text-muted);
  font-size: 12px;
  margin-left: 8px;
}

.card-body {
  color: var(--text-primary);
}
</style>
