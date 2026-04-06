<template>
  <div class="view-container">
    <div class="page-header">
      <el-button class="back-btn" @click="$router.push('/map')">← 返回</el-button>
      <h2>📦 贸易跑商</h2>
      <div class="player-stats">
        <span>💰 {{ player?.spirit_stones ?? 0 }} 第纳尔</span>
        <span>📍 {{ currentLocation }}</span>
      </div>
    </div>

    <div class="trade-content">
      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else-if="tradeGoods.length === 0" class="empty-state">
        <p>当前地点没有贸易货物。请前往城镇或村庄。</p>
      </div>
      <div v-else>
        <div class="trade-tabs">
          <button class="tab-btn" :class="{ active: activeTab === 'buy' }" @click="activeTab = 'buy'">
            🛒 买入
          </button>
          <button class="tab-btn" :class="{ active: activeTab === 'sell' }" @click="activeTab = 'sell'">
            💰 卖出
          </button>
        </div>

        <div v-if="activeTab === 'buy'" class="goods-grid">
          <div v-for="g in tradeGoods" :key="g.good_id" class="good-card">
            <div class="good-header">
              <div class="good-icon">{{ g.icon || '📦' }}</div>
              <div class="good-info">
                <h3>{{ g.name }}</h3>
                <span class="good-category">{{ g.category }}</span>
              </div>
            </div>
            <div class="good-prices">
              <div class="price-row">
                <span>本地买入:</span>
                <span class="buy-price">💰 {{ g.buy_price || g.price }}</span>
              </div>
              <div class="price-row" v-if="g.best_sell_location">
                <span>最佳卖出:</span>
                <span class="sell-price">💰 {{ g.best_sell_price }} ({{ g.best_sell_location }})</span>
              </div>
              <div class="profit-row" v-if="g.best_sell_price && g.buy_price">
                <span>利润:</span>
                <span class="profit" :class="{ 'profit-high': g.profit_margin > 50 }">
                  +{{ g.profit_margin || Math.round((g.best_sell_price - g.buy_price) / g.buy_price * 100) }}%
                </span>
              </div>
            </div>
            <div class="good-actions">
              <el-input-number v-model="buyCounts[g.good_id]" :min="1" :max="99" size="small" />
              <el-button type="primary" size="small" @click="buyGood(g)" :loading="buying === g.good_id">
                买入
              </el-button>
            </div>
          </div>
        </div>

        <div v-if="activeTab === 'sell'" class="goods-grid">
          <div v-if="myTradeGoods.length === 0" class="empty-state">
            <p>背包中没有贸易货物</p>
          </div>
          <div v-for="g in myTradeGoods" :key="g.good_id" class="good-card sell-card">
            <div class="good-header">
              <div class="good-icon">{{ g.icon || '📦' }}</div>
              <div class="good-info">
                <h3>{{ g.name }}</h3>
                <span class="good-count">数量: {{ g.count }}</span>
              </div>
            </div>
            <div class="good-prices">
              <div class="price-row">
                <span>本地卖出:</span>
                <span class="sell-price">💰 {{ g.sell_price || g.price }}</span>
              </div>
            </div>
            <div class="good-actions">
              <el-input-number v-model="sellCounts[g.good_id]" :min="1" :max="g.count" size="small" />
              <el-button type="warning" size="small" @click="sellGood(g)" :loading="selling === g.good_id">
                卖出
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { ElMessage } from 'element-plus'

const router = useRouter()
const gameStore = useGameStore()
const player = computed(() => gameStore.player)
const activeTab = ref('buy')
const tradeGoods = ref([])
const myTradeGoods = ref([])
const loading = ref(false)
const buying = ref(null)
const selling = ref(null)
const buyCounts = ref({})
const sellCounts = ref({})
const currentLocation = ref('未知')

const loadTradeGoods = async () => {
  loading.value = true
  const loc = player.value?.map_state?.current_location
  if (!loc) {
    ElMessage.warning('请先前往城镇或村庄')
    loading.value = false
    return
  }
  currentLocation.value = loc
  try {
    const goods = await gameStore.wsCall('get_trade_goods', { location_id: loc })
    if (goods?.goods) {
      tradeGoods.value = goods.goods.map(g => ({
        ...g,
        profit_margin: g.buy_price && g.best_sell_price
          ? Math.round((g.best_sell_price - g.buy_price) / g.buy_price * 100)
          : 0,
      }))
      buyCounts.value = {}
      tradeGoods.value.forEach(g => { buyCounts.value[g.good_id] = 1 })
    }
    if (goods?.my_goods) {
      myTradeGoods.value = goods.my_goods
      sellCounts.value = {}
      myTradeGoods.value.forEach(g => { sellCounts.value[g.good_id] = 1 })
    }
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const buyGood = async (good) => {
  const count = buyCounts.value[good.good_id] || 1
  buying.value = good.good_id
  try {
    const result = await gameStore.wsCall('trade_buy', { good_id: good.good_id, count })
    if (result?.success) {
      ElMessage.success(result.message || '购买成功')
      await loadTradeGoods()
    } else {
      ElMessage.error(result?.message || '购买失败')
    }
  } catch (e) {
    ElMessage.error('请求失败')
  } finally {
    buying.value = null
  }
}

const sellGood = async (good) => {
  const count = sellCounts.value[good.good_id] || 1
  selling.value = good.good_id
  try {
    const result = await gameStore.wsCall('trade_sell', { good_id: good.good_id, count })
    if (result?.success) {
      ElMessage.success(result.message || '卖出成功')
      await loadTradeGoods()
    } else {
      ElMessage.error(result?.message || '卖出失败')
    }
  } catch (e) {
    ElMessage.error('请求失败')
  } finally {
    selling.value = null
  }
}

onMounted(() => {
  loadTradeGoods()
})
</script>

<style scoped>
.view-container {
  padding: 16px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.page-header h2 { margin: 0; flex: 1; color: #d4a464; }

.player-stats {
  display: flex;
  gap: 16px;
  color: #aaa;
  font-size: 14px;
}

.loading-state, .empty-state {
  text-align: center;
  padding: 40px;
  color: #666;
}

.trade-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.tab-btn {
  padding: 8px 20px;
  background: rgba(20, 20, 35, 0.9);
  border: 1px solid #2a2a3e;
  border-radius: 6px;
  color: #888;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn.active {
  background: rgba(212, 164, 100, 0.2);
  border-color: #d4a464;
  color: #d4a464;
}

.goods-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.good-card {
  background: rgba(20, 20, 35, 0.9);
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 16px;
  transition: border-color 0.2s;
}

.good-card:hover { border-color: #d4a464; }

.good-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.good-icon { font-size: 32px; }

.good-info h3 { margin: 0; color: #e8e0d0; font-size: 15px; }

.good-category { font-size: 11px; color: #888; }

.good-count { font-size: 12px; color: #d4a464; }

.good-prices { margin: 8px 0; }

.price-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #888;
  margin: 4px 0;
}

.buy-price { color: #f44336; font-weight: bold; }
.sell-price { color: #4caf50; font-weight: bold; }

.profit-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px solid rgba(255,255,255,0.05);
}

.profit { font-weight: bold; }
.profit.profit-high { color: #4caf50; }

.good-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  align-items: center;
}
</style>
