<template>
  <div class="message-panel">
    <div class="panel-header">
      <h3>Game Messages</h3>
      <span class="message-count">{{ messages.length }}</span>
    </div>
    <div class="message-list">
      <div
        v-for="(message, index) in messages"
        :key="index"
        :class="['message-item', message.type]"
      >
        <div class="message-header">
          <span class="message-type">{{ message.type }}</span>
          <span class="message-timestamp">{{ message.timestamp }}</span>
        </div>
        <div class="message-content">
          {{ message.content }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { GameEvent, getGameState } from '@/game/game-state';

const messages = ref<Array<{
  type: string;
  content: string;
  timestamp: string;
}>>([]);

const gameState = getGameState();

const eventHandlers = {
  [GameEvent.TOWN_ENTER]: (payload: { townName: string }) => {
    addMessage(` Entered ${payload.townName}`, 'success');
  },
  [GameEvent.TOWN_LEAVE]: (payload: { townName: string }) => {
    addMessage(` Left ${payload.townName}`, 'warning');
  },
  [GameEvent.ITEM_ACQUIRE]: (payload: { item: { name: string; quantity?: number } }) => {
    const itemName = payload.item.name;
    const quantity = payload.item.quantity ? `${payload.item.quantity}x ` : '';
    addMessage(` Acquired ${quantity}${itemName}`, 'success');
  }
};

function addMessage(content: string, type: string) {
  const message = {
    type,
    content,
    timestamp: new Date().toLocaleTimeString()
  };
  messages.value = [message, ...messages.value];
}

onMounted(() => {
  gameState.subscribe((event) => {
    const handler = eventHandlers[event.type as GameEvent];
    if (handler) {
      handler(event.payload);
    }
  });
});

onBeforeUnmount(() => {
  gameState.unsubscribeAll();
});
</script>

<style scoped>
.message-panel {
  position: fixed;
  right: 20px;
  bottom: 20px;
  width: 300px;
  background: #fff;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  padding: 10px;
  z-index: 1000;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.message-count {
  font-size: 0.8em;
  color: #666;
}

.message-list {
  max-height: 400px;
  overflow-y: auto;
}

.message-item {
  padding: 8px 12px;
  margin-bottom: 8px;
  border-radius: 4px;
  font-size: 0.9em;
}

.message-item.success {
  background-color: #f0f9eb;
  border-left: 4px solid #67c23a;
}

.message-item.warning {
  background-color: #fdf6ec;
  border-left: 4px solid #e6a23d;
}

.message-header {
  display: flex;
  justify-content: space-between;
  font-weight: bold;
  margin-bottom: 4px;
}

.message-type {
  text-transform: uppercase;
  font-size: 0.7em;
  color: #666;
}

.message-timestamp {
  font-size: 0.7em;
  color: #999;
}
</style>