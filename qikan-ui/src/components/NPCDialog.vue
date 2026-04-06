<template>
  <Teleport to="body">
    <div v-if="visible" class="npc-dialog-overlay" @click.self="handleClose">
      <div class="npc-dialog-container">
        <div class="npc-dialog-header">
          <div class="npc-header-info">
            <span class="npc-icon-large">{{ npc?.icon || '👤' }}</span>
            <div class="npc-title-info">
              <h3 class="npc-name">{{ npc?.name || '未知NPC' }}</h3>
              <span class="npc-title-text">{{ npc?.title || '' }}</span>
            </div>
          </div>
          <div class="npc-favor-display">
            <div class="favor-bar-large">
              <div class="favor-fill-large" :style="{ width: (npc?.favor || 0) + '%' }"></div>
            </div>
            <span class="favor-text-large">{{ npc?.favor_level || '陌生人' }} ({{ npc?.favor || 0 }}/100)</span>
          </div>
          <button class="close-btn" @click="handleClose">×</button>
        </div>

        <div class="npc-dialog-body">
          <div class="dialog-text">
            <p>{{ dialogText }}</p>
          </div>

          <div class="dialog-options">
            <button
              v-for="option in dialogOptions"
              :key="option.option_id"
              class="dialog-option-btn"
              :class="{ disabled: !option.available }"
              :disabled="!option.available"
              @click="handleOptionClick(option)"
            >
              <span class="option-icon" v-if="option.action === 'show_gift_selector'">🎁</span>
              <span class="option-text">{{ option.text }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  npc: {
    type: Object,
    default: null,
  },
  dialogData: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['update:visible', 'action', 'gift'])

const currentNode = ref('greeting')
const dialogText = ref('')
const dialogOptions = ref([])

watch(() => props.dialogData, (newData) => {
  if (newData && props.visible) {
    const node = newData[currentNode.value]
    if (node) {
      dialogText.value = node.text
      dialogOptions.value = node.options || []
    }
  }
}, { immediate: true })

watch(() => props.visible, (newVal) => {
  if (newVal) {
    currentNode.value = 'greeting'
    if (props.dialogData?.greeting) {
      dialogText.value = props.dialogData.greeting.text
      dialogOptions.value = props.dialogData.greeting.options || []
    }
  }
})

const handleOptionClick = (option) => {
  if (!option.available) return

  if (option.action === 'show_gift_selector' || option.action === 'open_gift_selector') {
    emit('gift', props.npc)
    return
  }

  if (option.action === 'close') {
    handleClose()
    return
  }

  if (option.action) {
    emit('action', option.action, option.action_data)
  }

  if (option.next_node && props.dialogData?.[option.next_node]) {
    currentNode.value = option.next_node
    const node = props.dialogData[option.next_node]
    dialogText.value = node.text
    dialogOptions.value = node.options || []
  }
}

const handleClose = () => {
  emit('update:visible', false)
}
</script>

<style scoped>
.npc-dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.npc-dialog-container {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  width: 100%;
  max-width: 600px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.npc-dialog-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  position: relative;
}

.npc-header-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.npc-icon-large {
  font-size: 48px;
}

.npc-title-info {
  display: flex;
  flex-direction: column;
}

.npc-name {
  color: #fff;
  font-size: 20px;
  margin: 0;
  font-weight: 600;
}

.npc-title-text {
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
}

.npc-favor-display {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.favor-bar-large {
  width: 120px;
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.favor-fill-large {
  height: 100%;
  background: linear-gradient(90deg, #4a9eff, #22c55e);
  border-radius: 4px;
  transition: width 0.3s;
}

.favor-text-large {
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
}

.close-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.5);
  font-size: 24px;
  cursor: pointer;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.npc-dialog-body {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  overflow-y: auto;
}

.dialog-text {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 16px;
  min-height: 80px;
}

.dialog-text p {
  color: #fff;
  font-size: 15px;
  line-height: 1.6;
  margin: 0;
}

.dialog-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dialog-option-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.dialog-option-btn:hover:not(.disabled) {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
}

.dialog-option-btn.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.option-icon {
  font-size: 16px;
}
</style>
