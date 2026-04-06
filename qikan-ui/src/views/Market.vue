<template>
  <div class="view-container">
    <div class="nav-bar">
      <el-button @click="$router.push('/home')">← 返回</el-button>
      <h2>💰 集市</h2>
      <el-button @click="loadMarket">🔄 刷新</el-button>
    </div>
    <el-card class="market-card">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="🛒 浏览市场" name="browse">
          <div class="browse-section">
            <div class="search-bar">
              <el-input v-model="searchKeyword" placeholder="搜索物品..." prefix-icon="Search" @input="filterListings" />
            </div>
            <el-table :data="filtered" style="width: 100%" stripe>
              <el-table-column prop="item_name" label="物品" />
              <el-table-column prop="seller_name" label="卖家" width="100" />
              <el-table-column prop="quantity" label="数量" width="80" />
              <el-table-column prop="unit_price" label="单价" width="100" />
              <el-table-column prop="total_price" label="总价" width="100" />
              <el-table-column label="操作" width="200">
                <template #default="{ row }">
                  <el-input-number v-model="buyCounts[row.listing_id]" :min="1" :max="row.quantity" size="small" style="width: 80px" />
                  <el-button size="small" type="primary" @click="buy(row)" :disabled="gameStore.isActionLocked('market_buy')">购买</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="📦 我的上架" name="my">
          <div class="my-listings-section">
            <div class="listing-form">
              <h4>上架新物品</h4>
              <el-form inline>
                <el-form-item label="物品">
                  <el-select v-model="listItem" placeholder="选择物品" style="width: 200px">
                    <el-option v-for="item in myInventory" :key="item.item_id" :label="`${item.name} x${item.count}`" :value="item.item_id" />
                  </el-select>
                </el-form-item>
                <el-form-item label="数量">
                  <el-input-number v-model="listCount" :min="1" :max="99" />
                </el-form-item>
                <el-form-item label="单价">
                  <el-input-number v-model="listPrice" :min="1" :step="10" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="listItemToMarket" :loading="listingLoading">上架</el-button>
                </el-form-item>
              </el-form>
            </div>
            
            <h4>已上架物品</h4>
            <el-table :data="myListings" style="width: 100%" stripe>
              <el-table-column prop="item_name" label="物品" />
              <el-table-column prop="quantity" label="剩余数量" width="100" />
              <el-table-column prop="unit_price" label="单价" width="100" />
              <el-table-column prop="status" label="状态" width="80">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'active' ? 'success' : row.status === 'sold' ? 'warning' : 'info'" size="small">
                    {{ row.status === 'active' ? '在售' : row.status === 'sold' ? '已售' : '已取消' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button v-if="row.status === 'active'" size="small" type="danger" @click="cancelListing(row.listing_id)">下架</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="📊 统计" name="stats">
          <div class="stats-section">
            <h4>手续费预览</h4>
            <el-form inline>
              <el-form-item label="单价">
                <el-input-number v-model="feePreview.price" :min="1" />
              </el-form-item>
              <el-form-item label="数量">
                <el-input-number v-model="feePreview.count" :min="1" />
              </el-form-item>
              <el-form-item>
                <el-button @click="calcFee">计算</el-button>
              </el-form-item>
            </el-form>
            <div v-if="feeResult" class="fee-result">
              <p>总价: {{ feeResult.total_price }} 第纳尔</p>
              <p>手续费: {{ feeResult.fee }} 第纳尔</p>
              <p>实际收入: {{ feeResult.total_price - feeResult.fee }} 第纳尔</p>
            </div>
            
            <h4 style="margin-top: 20px">交易历史</h4>
            <el-button size="small" type="danger" @click="clearHistory">清理历史记录</el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const gameStore = useGameStore()
const activeTab = ref('browse')
const listings = ref([])
const myListings = ref([])
const myInventory = ref([])
const searchKeyword = ref('')
const filtered = computed(() => {
  if (!searchKeyword.value) return listings.value
  const kw = searchKeyword.value.toLowerCase()
  return listings.value.filter(l => l.item_name?.toLowerCase().includes(kw))
})
const buyCounts = ref({})
const listItem = ref('')
const listCount = ref(1)
const listPrice = ref(100)
const listingLoading = ref(false)
const feePreview = ref({ price: 100, count: 1 })
const feeResult = ref(null)

const loadMarket = () => {
  if (activeTab.value === 'browse') {
    gameStore.send({ type: 'get_market', data: { page: 1 } })
  } else if (activeTab.value === 'my') {
    gameStore.send({ type: 'get_my_listings' })
    gameStore.send({ type: 'get_inventory' })
  }
}

const handleTabChange = (tab) => {
  activeTab.value = tab
  loadMarket()
}

const filterListings = () => {}

const buy = (item) => {
  const count = buyCounts.value[item.listing_id] || 1
  if (!gameStore.lockAction('market_buy')) {
    ElMessage.warning('购买太频繁，请稍后再试')
    return
  }
  gameStore.send({ type: 'market_buy', data: { listing_id: item.listing_id, count } })
  setTimeout(() => gameStore.unlockAction('market_buy'), 500)
}

const listItemToMarket = async () => {
  if (!listItem.value) {
    ElMessage.warning('请选择物品')
    return
  }
  listingLoading.value = true
  try {
    const result = await gameStore.wsCall('market_list', {
      item_id: listItem.value,
      quantity: listCount.value,
      unit_price: listPrice.value,
    })
    if (result?.success) {
      ElMessage.success('上架成功')
      loadMarket()
    } else {
      ElMessage.error(result?.message || '上架失败')
    }
  } catch (e) {
    ElMessage.error('请求失败')
  } finally {
    listingLoading.value = false
  }
}

const cancelListing = async (listingId) => {
  try {
    const result = await gameStore.wsCall('market_cancel', { listing_id: listingId })
    if (result?.success) {
      ElMessage.success('已下架')
      loadMarket()
    }
  } catch (e) {}
}

const calcFee = async () => {
  try {
    const result = await gameStore.wsCall('market_fee_preview', {
      unit_price: feePreview.value.price,
      quantity: feePreview.value.count,
    })
    if (result) {
      feeResult.value = result
    }
  } catch (e) {}
}

const clearHistory = async () => {
  try {
    await ElMessageBox.confirm('确定要清理交易历史吗？', '确认')
    const result = await gameStore.wsCall('market_clear_history')
    if (result?.success) {
      ElMessage.success('已清理')
    }
  } catch (e) {}
}

onMounted(async () => {
  if (!gameStore.token) {
    router.push('/')
    return
  }
  if (!gameStore.connected) {
    await gameStore.connectWs()
  }
  gameStore.wsMessageHandlers = gameStore.wsMessageHandlers || {}
  gameStore.wsMessageHandlers['market'] = (msg) => {
    if (msg.type === 'market_data') {
      listings.value = msg.data?.listings || []
      listings.value.forEach(l => { buyCounts.value[l.listing_id] = 1 })
    } else if (msg.type === 'my_listings') {
      myListings.value = msg.data?.listings || []
    } else if (msg.type === 'inventory_data') {
      myInventory.value = msg.data?.items || []
    } else if (msg.type === 'action_result') {
      if (msg.data?.success) {
        ElMessage.success(msg.data.message)
        loadMarket()
      } else {
        ElMessage.error(msg.data?.message)
      }
    }
  }
  loadMarket()
})
</script>

<style scoped>
.view-container { min-height: 100vh; background: #1a1a2e; padding: 20px; }
.nav-bar { display: flex; align-items: center; gap: 20px; margin-bottom: 20px; }
.nav-bar h2 { color: #ffd700; margin: 0; }
.market-card { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: #e0e0e0; }
.search-bar { margin-bottom: 12px; }
.listing-form { margin-bottom: 20px; padding: 12px; background: rgba(0,0,0,0.2); border-radius: 8px; }
.listing-form h4 { color: #d4a464; margin: 0 0 12px; }
.stats-section h4 { color: #d4a464; margin: 12px 0 8px; }
.fee-result { padding: 12px; background: rgba(0,0,0,0.2); border-radius: 8px; margin-top: 8px; }
.fee-result p { margin: 4px 0; color: #aaa; }
.fee-result p:last-child { color: #4caf50; font-weight: bold; }
</style>
