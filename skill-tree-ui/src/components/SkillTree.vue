<template>
  <div class="skill-tree-container">
    <div class="zoom-controls">
      <button @click="zoomIn" class="zoom-btn">+</button>
      <span class="zoom-level">{{ Math.round(scale * 100) }}%</span>
      <button @click="zoomOut" class="zoom-btn">−</button>
      <button @click="resetZoom" class="zoom-btn reset">重置</button>
      <button @click="fitToView" class="zoom-btn fit">适应窗口</button>
    </div>
    
    <div 
      class="skill-tree-viewport"
      ref="viewportRef"
      @wheel.prevent="handleWheel"
      @mousedown="startDrag"
      @mousemove="handleDrag"
      @mouseup="endDrag"
      @mouseleave="endDrag"
    >
      <div 
        class="skill-tree-content"
        :style="{
          transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
        }"
      >
        <div v-for="tree in skillTrees" :key="tree.tree_id" class="skill-tree">
          <div class="tree-header">
            <h3>{{ tree.name }}</h3>
            <span class="tree-name-en">{{ tree.name_en }}</span>
            <p class="tree-desc">{{ tree.desc }}</p>
            <span class="tree-stat">主属性: {{ tree.stat }}</span>
          </div>
          
          <div class="skill-chain">
            <svg class="connector-lines" :viewBox="`0 0 100 ${tree.skills.length * 120}`">
              <line 
                v-for="i in tree.skills.length - 1" 
                :key="i"
                x1="50" 
                :y1="i * 120 - 30" 
                x2="50" 
                :y2="i * 120 + 10"
                :class="{ 
                  'line-active': tree.skills[i - 1].is_equipped,
                  'line-available': tree.skills[i].can_learn && !tree.skills[i].is_equipped
                }"
              />
            </svg>
            
            <SkillNode
              v-for="skill in tree.skills"
              :key="skill.method_id"
              :skill="skill"
              @select="handleSkillSelect"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import SkillNode from './SkillNode.vue'
import type { Skill, SkillTree as SkillTreeType } from '../stores/skillStore'

defineProps<{
  skillTrees: SkillTreeType[]
}>()

const emit = defineEmits<{
  (e: 'select', skill: Skill): void
}>()

const viewportRef = ref<HTMLElement | null>(null)
const scale = ref(1)
const position = ref({ x: 0, y: 0 })
const isDragging = ref(false)
const lastMouse = ref({ x: 0, y: 0 })

const minScale = 0.3
const maxScale = 2
const zoomStep = 0.1

function zoomIn() {
  scale.value = Math.min(maxScale, scale.value + zoomStep)
}

function zoomOut() {
  scale.value = Math.max(minScale, scale.value - zoomStep)
}

function resetZoom() {
  scale.value = 1
  position.value = { x: 0, y: 0 }
}

function fitToView() {
  if (!viewportRef.value) return
  
  const viewport = viewportRef.value
  const contentWidth = viewport.scrollWidth
  const contentHeight = viewport.scrollHeight
  
  const scaleX = (viewport.clientWidth - 40) / contentWidth
  const scaleY = (viewport.clientHeight - 40) / contentHeight
  
  scale.value = Math.min(Math.max(minScale, Math.min(scaleX, scaleY)), maxScale)
  position.value = { x: 20, y: 20 }
}

function handleWheel(event: WheelEvent) {
  const delta = event.deltaY > 0 ? -zoomStep : zoomStep
  scale.value = Math.max(minScale, Math.min(maxScale, scale.value + delta))
}

function startDrag(event: MouseEvent) {
  isDragging.value = true
  lastMouse.value = { x: event.clientX, y: event.clientY }
}

function handleDrag(event: MouseEvent) {
  if (!isDragging.value) return
  
  const dx = event.clientX - lastMouse.value.x
  const dy = event.clientY - lastMouse.value.y
  
  position.value = {
    x: position.value.x + dx,
    y: position.value.y + dy
  }
  
  lastMouse.value = { x: event.clientX, y: event.clientY }
}

function endDrag() {
  isDragging.value = false
}

function handleSkillSelect(skill: Skill) {
  emit('select', skill)
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === '+' || event.key === '=') {
    zoomIn()
  } else if (event.key === '-') {
    zoomOut()
  } else if (event.key === '0') {
    resetZoom()
  } else if (event.key === 'f' || event.key === 'F') {
    fitToView()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.skill-tree-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  position: relative;
}

.zoom-controls {
  position: absolute;
  top: 16px;
  right: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(30, 30, 46, 0.95);
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid #3a3a4e;
  z-index: 100;
}

.zoom-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  background: #3a3a4e;
  color: #fff;
  font-size: 18px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.zoom-btn:hover {
  background: #4a4a5e;
}

.zoom-btn.reset,
.zoom-btn.fit {
  width: auto;
  padding: 0 12px;
  font-size: 12px;
}

.zoom-level {
  font-size: 12px;
  color: #888;
  min-width: 45px;
  text-align: center;
}

.skill-tree-viewport {
  flex: 1;
  overflow: hidden;
  position: relative;
  background: linear-gradient(135deg, #12121a 0%, #1a1a2e 100%);
  cursor: grab;
}

.skill-tree-viewport:active {
  cursor: grabbing;
}

.skill-tree-content {
  display: flex;
  gap: 60px;
  padding: 40px;
  transform-origin: 0 0;
  transition: transform 0.1s ease-out;
  min-height: 100%;
}

.skill-tree {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: rgba(30, 30, 46, 0.6);
  border-radius: 16px;
  padding: 24px;
  border: 1px solid #3a3a4e;
  min-width: 160px;
}

.tree-header {
  text-align: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #3a3a4e;
}

.tree-header h3 {
  margin: 0 0 4px 0;
  font-size: 16px;
  color: #fff;
}

.tree-name-en {
  font-size: 11px;
  color: #888;
  display: block;
  margin-bottom: 8px;
}

.tree-desc {
  font-size: 12px;
  color: #aaa;
  margin: 0 0 8px 0;
}

.tree-stat {
  font-size: 11px;
  color: #4a9eff;
  background: rgba(74, 158, 255, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

.skill-chain {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 70px;
  position: relative;
}

.connector-lines {
  position: absolute;
  top: 25px;
  left: 50%;
  transform: translateX(-50%);
  width: 4px;
  height: 100%;
  pointer-events: none;
}

.connector-lines line {
  stroke: #3a3a4e;
  stroke-width: 3;
  stroke-linecap: round;
}

.connector-lines .line-active {
  stroke: #4ade80;
}

.connector-lines .line-available {
  stroke: #4a9eff;
}
</style>
