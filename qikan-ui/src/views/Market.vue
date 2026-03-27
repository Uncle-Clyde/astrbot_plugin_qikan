<template>
  <div class="view-container">
    <div class="nav-bar">
      <el-button @click="$router.push('/home')">← 返回</el-button>
      <h2>💰 集市</h2>
    </div>
    <el-card class="market-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="市场" name="browse">
          <el-table :data="listings" style="width: 100%">
            <el-table-column prop="item_name" label="物品" />
            <el-table-column prop="quantity" label="数量" />
            <el-table-column prop="unit_price" label="单价" />
            <el-table-column label="操作">
              <template #default="{ row }">
                <el-button size="small" @click="buy(row)">购买</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="我的上架" name="my">
          <el-table :data="myListings" style="width: 100%">
            <el-table-column prop="item_name" label="物品" />
            <el-table-column prop="quantity" label="数量" />
            <el-table-column prop="unit_price" label="单价" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>
<script setup>
import { ref } from 'vue'
const activeTab = ref('browse')
const listings = ref([])
const myListings = ref([])
const buy = (item) => {}
</script>
<style scoped>
.view-container { min-height: 100vh; background: #1a1a2e; padding: 20px; }
.nav-bar { display: flex; align-items: center; gap: 20px; margin-bottom: 20px; }
.nav-bar h2 { color: #ffd700; margin: 0; }
.market-card { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: #e0e0e0; }
</style>
