<template>
  <div class="home-container">
    <!-- 出身选择强制弹窗 -->
    <div v-if="showSpawnModal" class="spawn-modal-overlay">
      <div class="spawn-modal">
        <div class="spawn-modal-header">
          <h2>⚔️ 选择你的出身 ⚔️</h2>
          <p>卡拉迪亚大陆欢迎你！请选择你的出身背景</p>
        </div>
        
        <div class="spawn-modal-content">
          <!-- 加载状态/重试按钮 -->
          <div v-if="spawnLoading" class="loading-state">
            <el-icon class="loading-icon"><Loading /></el-icon>
            <span>正在加载出身数据...</span>
            <el-button type="primary" style="margin-top: 15px" @click="forceShowSpawnModal">点击重试</el-button>
          </div>
          
          <!-- 出身选项 -->
          <div v-else-if="spawnOrigins.length === 0" class="loading-state">
            <span>无法加载出身数据</span>
            <el-button type="primary" style="margin-top: 15px" @click="forceShowSpawnModal">点击重试</el-button>
          </div>
          <div v-else class="origin-section">
            <h3>📜 选择出身背景</h3>
            <div class="origin-grid">
              <div 
                v-for="origin in spawnOrigins" 
                :key="origin.origin_id"
                class="origin-card"
                :class="{ selected: selectedOrigin === origin.origin_id }"
                @click="selectOrigin(origin.origin_id)"
              >
                <span class="origin-icon">{{ origin.icon }}</span>
                <span class="origin-name">{{ origin.name }}</span>
                <span class="origin-desc">{{ origin.description }}</span>
                <span class="origin-bonus">{{ origin.specialty }}</span>
              </div>
            </div>
          </div>
          
          <!-- 地点选项 -->
          <div v-if="selectedOrigin" class="location-section">
            <h3>🏰 选择出生地点</h3>
            <div v-if="spawnLocationsLoading" class="loading-state">
              <el-icon class="loading-icon"><Loading /></el-icon>
              <span>加载中...</span>
            </div>
            <div v-else-if="filteredSpawnLocations.length === 0" class="loading-state">
              <span>暂无可用地点</span>
            </div>
            <div v-else class="location-grid">
              <div 
                v-for="loc in filteredSpawnLocations" 
                :key="loc.location_id"
                class="location-card"
                :class="{ selected: selectedLocation === loc.location_id }"
                @click="selectLocation(loc.location_id)"
              >
                <span class="loc-icon">{{ loc.icon }}</span>
                <span class="loc-name">{{ loc.name }}</span>
                <span class="loc-faction">{{ loc.faction_name }}</span>
              </div>
            </div>
          </div>
        </div>
        
        <div class="spawn-modal-footer">
          <el-button 
            type="primary" 
            size="large" 
            :loading="confirmLoading"
            :disabled="!selectedOrigin"
            @click="confirmSpawnSelection"
          >
            {{ selectedLocation ? '🎮 进入游戏' : '请选择出身' }}
          </el-button>
        </div>
      </div>
    </div>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <span class="logo-icon">⚔️</span>
          <h2>骑砍英雄传</h2>
          <el-tag v-if="player" :type="realmTagType" size="small" class="realm-tag">{{ player.realm_name || '平民' }}</el-tag>
        </div>
        <nav class="header-nav">
          <a class="nav-item" :class="{ active: currentView === 'panel' }" @click="currentView = 'panel'">
            <span class="nav-icon">⚔️</span>
            <span class="nav-text">角色</span>
          </a>
          <a class="nav-item" :class="{ active: currentView === 'inventory' }" @click="currentView = 'inventory'">
            <span class="nav-icon">🎒</span>
            <span class="nav-text">背包</span>
          </a>
          <a class="nav-item" :class="{ active: currentView === 'crafting' }" @click="currentView = 'crafting'">
            <span class="nav-icon">🔨</span>
            <span class="nav-text">制作</span>
          </a>
          <a class="nav-item" :class="{ active: currentView === 'forging' }" @click="currentView = 'forging'">
            <span class="nav-icon">⚒️</span>
            <span class="nav-text">锻造</span>
          </a>
          <a class="nav-item" @click="$router.push('/skills')">
            <span class="nav-icon">📜</span>
            <span class="nav-text">技能</span>
          </a>
          <a class="nav-item" @click="$router.push('/map')">
            <span class="nav-icon">🗺️</span>
            <span class="nav-text">地图</span>
          </a>
          <a class="nav-item" @click="$router.push('/family')">
            <span class="nav-icon">🏰</span>
            <span class="nav-text">家族</span>
          </a>
          <a class="nav-item" @click="$router.push('/market')">
            <span class="nav-icon">🏛️</span>
            <span class="nav-text">集市</span>
          </a>
          <a class="nav-item" v-if="isAdmin" @click="$router.push('/admin')">
            <span class="nav-icon">🔧</span>
            <span class="nav-text">管理</span>
          </a>
          <a class="nav-item" @click="$router.push('/icons')">
            <span class="nav-icon">⚙️</span>
            <span class="nav-text">设置</span>
          </a>
          <a class="nav-item" @click="$router.push('/about')">
            <span class="nav-icon">📖</span>
            <span class="nav-text">关于</span>
          </a>
        </nav>
        <div class="header-right">
          <span class="player-name">{{ player?.name || '游客' }}</span>
          <el-button @click="handleLogout" type="danger" size="small" text>退出</el-button>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <div v-if="currentView === 'panel'" class="panel-view">
          <el-row :gutter="16">
            <!-- 左侧: 玩家信息和装备栏 -->
            <el-col :span="8">
              <el-card class="player-card">
                <div class="player-header">
                    <div class="player-info">
                      <div class="player-avatar">
                        <img v-if="player?.avatar_url" :src="player.avatar_url" :alt="player?.name" class="avatar-img" />
                        <span v-else>{{ player?.name?.slice(0, 1) || '?' }}</span>
                      </div>
                      <div class="player-details">
                      <h3>{{ player?.name || '未知' }}</h3>
                      <div class="player-badges">
                        <el-tag :type="realmTagType" size="small">{{ player?.realm_name || '平民' }}</el-tag>
                        <el-tag v-if="player?.afk" type="success" size="small">挂机中</el-tag>
                        <el-tag v-else type="info" size="small">在线</el-tag>
                      </div>
                    </div>
                  </div>
                  <div class="player-location">
                    <span class="location-icon">📍</span>
                    <span>{{ getLocationDisplay() }}</span>
                  </div>
                </div>
                
                <div class="stats-grid">
                  <div class="stat-item">
                    <span class="label">等级</span>
                    <span class="value">{{ player?.level || 1 }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="label">经验</span>
                    <span class="value">{{ player?.exp || 0 }}/{{ player?.exp_next || 100 }}</span>
                  </div>
                  <div v-if="player && player.realm === 0" class="exp-tip">
                    💡 签到或挂机可获得经验，升级后开启更多功能
                  </div>
                  <div class="stat-item hp">
                    <span class="label">生命</span>
                    <span class="value">{{ player?.hp || 0 }}/{{ player?.max_hp || 100 }}</span>
                    <div class="stat-bar"><div class="stat-bar-fill" :style="{ width: ((player?.hp || 0) / (player?.max_hp || 100) * 100) + '%' }"></div></div>
                  </div>
                  <div class="stat-item">
                    <span class="label">攻击</span>
                    <span class="value attack">{{ player?.total_attack || 0 }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="label">防御</span>
                    <span class="value defense">{{ player?.total_defense || 0 }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="label">第纳尔</span>
                    <span class="value gold">{{ player?.spirit_stones || 0 }}</span>
                  </div>
                </div>

                <div class="action-buttons">
                  <el-button type="success" @click="handleCheckin" :loading="gameStore.isButtonLoading('checkin')">📅 签到</el-button>
                  <el-button type="info" @click="handleHeal" :loading="gameStore.isButtonLoading('heal')">💊 治疗</el-button>
                  <el-button v-if="player?.afk" type="danger" @click="handleCancelAfk" :loading="gameStore.isButtonLoading('cancel_afk')">⏹️ 取消挂机</el-button>
                  <el-button v-else type="primary" @click="handleStartAfk" :loading="gameStore.isButtonLoading('afk')">💤 挂机</el-button>
                  <el-button v-if="canCollectAfk" type="warning" @click="handleCollectAfk" :loading="gameStore.isButtonLoading('collect_afk')">🎁 领取</el-button>
                  <el-button type="warning" @click="$router.push('/dungeon')">⚔️ 地牢</el-button>
                  <el-button type="danger" @click="$router.push('/bandits')">👹 山贼</el-button>
                </div>
              </el-card>

              <el-card class="equipment-card">
                <template #header>
                  <div class="card-header">
                    <span>装备栏</span>
                    <el-switch v-model="showVisualEquipment" active-text="可视化" inactive-text="列表" />
                  </div>
                </template>
                
                <div v-if="showVisualEquipment" class="visual-equipment">
                  <div class="humanoid-figure">
                    <div class="equip-slot-visual head" :class="{ equipped: player?.equipment?.helmet }" @click="handleEquipClick('helmet')">
                      <span class="slot-emoji">{{ getSlotIcon('helmet') }}</span>
                      <span class="slot-label">头盔</span>
                      <span class="item-name" v-if="player?.equipment?.helmet">{{ player.equipment.helmet.name }}</span>
                      <span class="empty-tip" v-else>点击装备</span>
                    </div>
                    <div class="equip-slot-visual shoulder-l" :class="{ equipped: player?.equipment?.shoulder }" @click="handleEquipClick('shoulder')">
                      <span class="slot-emoji">{{ getSlotIcon('shoulder') }}</span>
                      <span class="slot-label">肩</span>
                      <span class="item-name" v-if="player?.equipment?.shoulder">{{ player.equipment.shoulder.name }}</span>
                    </div>
                    <div class="equip-slot-visual weapon-hand" :class="{ equipped: player?.equipment?.weapon }" @click="handleEquipClick('weapon')">
                      <span class="slot-emoji">{{ getSlotIcon('weapon') }}</span>
                      <span class="slot-label">武器</span>
                      <span class="item-name" v-if="player?.equipment?.weapon">{{ player.equipment.weapon.name }}</span>
                    </div>
                    <div class="equip-slot-visual body" :class="{ equipped: player?.equipment?.armor }" @click="handleEquipClick('armor')">
                      <span class="slot-emoji">{{ getSlotIcon('armor') }}</span>
                      <span class="slot-label">护甲</span>
                      <span class="item-name" v-if="player?.equipment?.armor">{{ player.equipment.armor.name }}</span>
                      <span class="empty-tip" v-else>点击装备</span>
                    </div>
                    <div class="equip-slot-visual accessory-l" :class="{ equipped: player?.equipment?.accessory1 }" @click="handleEquipClick('accessory1')">
                      <span class="slot-emoji">{{ getSlotIcon('accessory1') }}</span>
                      <span class="slot-label">饰品</span>
                      <span class="item-name" v-if="player?.equipment?.accessory1">{{ player.equipment.accessory1.name }}</span>
                    </div>
                    <div class="equip-slot-visual accessory-r" :class="{ equipped: player?.equipment?.accessory2 }" @click="handleEquipClick('accessory2')">
                      <span class="slot-emoji">{{ getSlotIcon('accessory2') }}</span>
                      <span class="slot-label">饰品</span>
                      <span class="item-name" v-if="player?.equipment?.accessory2">{{ player.equipment.accessory2.name }}</span>
                    </div>
                    <div class="equip-slot-visual hand-l" :class="{ equipped: player?.equipment?.gloves }" @click="handleEquipClick('gloves')">
                      <span class="slot-emoji">{{ getSlotIcon('gloves') }}</span>
                      <span class="slot-label">手套</span>
                      <span class="item-name" v-if="player?.equipment?.gloves">{{ player.equipment.gloves.name }}</span>
                    </div>
                    <div class="equip-slot-visual feet" :class="{ equipped: player?.equipment?.boots }" @click="handleEquipClick('boots')">
                      <span class="slot-emoji">{{ getSlotIcon('boots') }}</span>
                      <span class="slot-label">靴子</span>
                      <span class="item-name" v-if="player?.equipment?.boots">{{ player.equipment.boots.name }}</span>
                      <span class="empty-tip" v-else>点击装备</span>
                    </div>
                  </div>
                  <div class="equip-stats-panel">
                    <div class="stat-title">角色属性</div>
                    <div class="stat-row">
                      <span class="stat-label">⚔️ 攻击</span>
                      <span class="stat-value attack">{{ player?.total_attack || 0 }}</span>
                    </div>
                    <div class="stat-row">
                      <span class="stat-label">🛡️ 防御</span>
                      <span class="stat-value defense">{{ player?.total_defense || 0 }}</span>
                    </div>
                    <div class="stat-row">
                      <span class="stat-label">❤️ 生命</span>
                      <span class="stat-value">{{ player?.hp || 0 }}/{{ player?.max_hp || 100 }}</span>
                    </div>
                    <div class="stat-row">
                      <span class="stat-label">💰 第纳尔</span>
                      <span class="stat-value gold">{{ player?.spirit_stones || 0 }}</span>
                    </div>
                    <el-divider style="margin: 10px 0" />
                    <div class="stat-row attr-row">
                      <span class="stat-label">💪 力量</span>
                      <span class="stat-value strength">{{ player?.strength || 5 }}</span>
                    </div>
                    <div class="stat-row attr-row">
                      <span class="stat-label">🧠 智力</span>
                      <span class="stat-value intelligence">{{ player?.intelligence || 5 }}</span>
                    </div>
                    <div class="stat-row attr-row">
                      <span class="stat-label">⚡ 敏捷</span>
                      <span class="stat-value agility">{{ player?.agility || 5 }}</span>
                    </div>
                    <div class="stat-row attr-row" v-if="player?.attribute_points > 0">
                      <span class="stat-label">⭐ 可分配</span>
                      <span class="stat-value points">{{ player?.attribute_points || 0 }}</span>
                    </div>
                  </div>
                </div>

                <div v-show="!showVisualEquipment" class="equipment-section">
                  <h4 class="section-title">角色装备</h4>
                  <div class="equipment-grid">
                    <div v-for="slot in equipmentSlots" :key="slot.key" class="equip-slot" :class="{ empty: !player?.equipment?.[slot.key], equipped: player?.equipment?.[slot.key] }" @click="handleEquipClick(slot.key)">
                      <div class="slot-icon">{{ slot.icon }}</div>
                      <div class="slot-name">{{ slot.name }}</div>
                      <div class="slot-item" v-if="player?.equipment?.[slot.key]">{{ player.equipment[slot.key].name }}</div>
                      <div class="slot-empty" v-else>未装备</div>
                    </div>
                  </div>
                </div>

                <el-divider />
                
                <div class="equipment-section">
                  <div class="mount-header">
                    <h4 class="section-title">🐎 坐骑装备</h4>
                    <div class="mount-actions">
                      <el-tag v-if="player?.mounted" type="success" size="small">已骑乘</el-tag>
                      <el-button v-if="player?.mounted" size="small" type="danger" text @click="handleUnequipMount" :disabled="gameStore.isActionLocked('unequip_mount')">收回</el-button>
                      <el-button v-else size="small" type="warning" text @click="handleSummonMount">召唤坐骑</el-button>
                    </div>
                  </div>
                  <div class="equipment-grid mount-grid">
                    <div v-for="slot in mountSlots" :key="slot.key" class="equip-slot" :class="{ empty: !player?.equipped_mount_items?.[slot.key], equipped: player?.equipped_mount_items?.[slot.key] }" @click="handleMountEquipClick(slot.key)">
                      <div class="slot-icon">{{ slot.icon }}</div>
                      <div class="slot-name">{{ slot.name }}</div>
                      <div class="slot-item" v-if="player?.equipped_mount_items?.[slot.key]">{{ player.equipped_mount_items[slot.key].name }}</div>
                      <div class="slot-empty" v-else>未装备</div>
                    </div>
                  </div>
                </div>
              </el-card>
            </el-col>
            
            <!-- 中间: 个人日志 (与装备栏平分面积) -->
            <el-col :span="8">
              <el-card class="log-card">
                <template #header>
                  <div class="card-header">
                    <span>📜 个人日志</span>
                    <div class="log-header-controls">
                      <el-button size="small" text @click="toggleLogMinimize">{{ logMinimized ? '⬆️' : '⬇️' }}</el-button>
                      <el-button size="small" text @click="clearPersonalLog" v-if="personalLog.length > 0 && !logMinimized">清空</el-button>
                    </div>
                  </div>
                </template>
                <div class="log-messages" ref="logRef" v-show="!logMinimized">
                  <div v-for="(log, i) in personalLog" :key="i" class="log-message" :class="log.type">
                    <span class="log-time">{{ log.time }}</span>
                    <span class="log-content">{{ log.content }}</span>
                  </div>
                  <div v-if="personalLog.length === 0" class="log-empty">暂无记录</div>
                </div>
                <div class="log-resize-handle" @mousedown="startResize" v-show="!logMinimized"></div>
              </el-card>

              <el-card v-if="player?.active_buffs && player.active_buffs.length > 0" class="buff-card">
                <template #header>
                  <span>🧪 药水BUFF ({{ player.active_buffs.length }})</span>
                </template>
                <div class="buff-grid">
                  <div v-for="(buff, idx) in player.active_buffs" :key="idx" class="buff-item" :class="buff.is_side_effect ? 'buff-debuff' : 'buff-positive'">
                    <div class="buff-name">{{ buff.name }}</div>
                    <div class="buff-effects">
                      <span v-if="buff.attack_boost" :class="buff.is_side_effect ? 'debuff' : 'buff'">{{ buff.is_side_effect ? '⚔️' : '⚔️+' }}{{ Math.abs(buff.attack_boost) }}</span>
                      <span v-if="buff.defense_boost" :class="buff.is_side_effect ? 'debuff' : 'buff'">{{ buff.is_side_effect ? '🛡️' : '🛡️+' }}{{ Math.abs(buff.defense_boost) }}</span>
                      <span v-if="buff.hp_boost" :class="buff.is_side_effect ? 'debuff' : 'buff'">{{ buff.is_side_effect ? '❤️' : '❤️+' }}{{ Math.abs(buff.hp_boost) }}</span>
                      <span v-if="buff.lingqi_boost" :class="buff.is_side_effect ? 'debuff' : 'buff'">{{ buff.is_side_effect ? '⚡' : '⚡+' }}{{ Math.abs(buff.lingqi_boost) }}</span>
                    </div>
                    <div class="buff-timer">{{ formatBuffTime(buff.remaining_seconds) }}</div>
                  </div>
                </div>
              </el-card>
            </el-col>
            
            <!-- 右侧: 资产、位置、快捷操作 -->
            <el-col :span="8">
              <el-card class="info-card">
                <template #header>
                  <span>💰 资产</span>
                </template>
                <div class="asset-grid">
                  <div class="asset-item">
                    <span class="asset-icon">💵</span>
                    <span class="asset-value">{{ player?.spirit_stones || 0 }}</span>
                    <span class="asset-label">第纳尔</span>
                  </div>
                  <div class="asset-item">
                    <span class="asset-icon">⭐</span>
                    <span class="asset-value">{{ player?.dao_yun || 0 }}</span>
                    <span class="asset-label">声望</span>
                  </div>
                  <div class="asset-item">
                    <span class="asset-icon">⚡</span>
                    <span class="asset-value">{{ player?.lingqi || 0 }}/{{ player?.max_lingqi || 50 }}</span>
                    <span class="asset-label">体力</span>
                  </div>
                </div>
              </el-card>
              
              <el-card class="info-card" style="margin-top: 12px;">
                <template #header>
                  <span>📍 位置</span>
                </template>
                <div class="location-info">
                  <p><strong>{{ getLocationDisplay() }}</strong></p>
                  <p v-if="player?.faction">阵营: {{ player.faction }}</p>
                </div>
              </el-card>

              <el-card class="quick-actions" style="margin-top: 12px;">
                <template #header>
                  <span>⚡ 快捷操作</span>
                </template>
                <div class="quick-btns">
                  <el-button size="small" @click="currentView = 'inventory'">📦 背包</el-button>
                  <el-button size="small" @click="$router.push('/skills')">📜 技能</el-button>
                  <el-button size="small" @click="$router.push('/map')">🗺️ 地图</el-button>
                  <el-button v-if="player?.map_state?.current_location" size="small" type="warning" @click="$router.push('/location')">🏘️ 访问</el-button>
                  <el-button size="small" @click="$router.push('/chat')">💬 聊天</el-button>
                  <el-button size="small" @click="$router.push('/mail')">📧 邮件</el-button>
                  <el-button size="small" @click="$router.push('/achievements')">🏆 成就</el-button>
                  <el-button size="small" @click="$router.push('/titles')">📜 称号</el-button>
                  <el-button size="small" @click="$router.push('/companions')">🤝 同伴</el-button>
                  <el-button size="small" @click="$router.push('/troops')">🛡️ 部队</el-button>
                  <el-button size="small" @click="$router.push('/tournament')">🏟️ 竞技场</el-button>
                  <el-button size="small" @click="$router.push('/bandits')">⚔️ 山贼</el-button>
                  <el-button size="small" @click="$router.push('/dungeon')">🏚️ 地牢</el-button>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </div>

        <div v-else-if="currentView === 'inventory'" class="inventory-view">
          <el-card>
            <template #header>
              <div class="card-header">
                <span>🎒 背包物品 ({{ gameStore.inventory.length }})</span>
                <el-button size="small" @click="gameStore.getInventory()">🔄 刷新</el-button>
              </div>
            </template>
            <el-table :data="gameStore.inventory" style="width: 100%" stripe>
              <el-table-column prop="name" label="名称" />
              <el-table-column prop="count" label="数量" width="80" align="center" />
              <el-table-column prop="quality" label="品质" width="80" align="center">
                <template #default="{ row }">
                  <el-tag :type="getQualityType(row.quality)" size="small">{{ getQualityName(row.quality) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="200" align="center">
                <template #default="{ row }">
                  <el-button size="small" type="primary" @click="handleUseItem(row)" :loading="gameStore.isButtonLoading('use_' + row.item_id)">使用</el-button>
                  <el-button size="small" type="warning" @click="handleEquipItem(row)" :loading="gameStore.isButtonLoading('equip_' + row.item_id)">装备</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>

        <div v-else-if="currentView === 'crafting'" class="crafting-view">
          <el-card>
            <template #header>
              <div class="card-header">
                <span>🔨 制作台</span>
                <el-button size="small" @click="loadAllCraftingData">🔄 刷新</el-button>
              </div>
            </template>
            
            <el-tabs v-model="craftingSubTab">
              <el-tab-pane label="🏹 狩猎" name="hunting">
                <div class="crafting-subtab">
                  <el-alert title="狩猎说明" type="info" :closable="false" style="margin-bottom: 15px">
                    狩猎野生动物获取材料，消耗体力。
                  </el-alert>
                  <div class="hunting-grid">
                    <div v-for="w in wildlifeList" :key="w.id" class="wildlife-card" :class="{ 'can-hunt': canHunt && !huntingLoading }">
                      <div class="wildlife-info">
                        <div class="wildlife-icon">{{ w.icon }}</div>
                        <div class="wildlife-details">
                          <h3>{{ w.name }} <span class="tier-badge" :class="tierClass(w.tier)">{{ tierName(w.tier) }}</span></h3>
                          <p class="wildlife-desc">{{ w.description }}</p>
                          <div class="wildlife-drops">
                            <span v-for="(chance, itemId) in w.drops" :key="itemId" class="drop-item">
                              {{ dropName(itemId) }} ({{ Math.round(chance * 100) }}%)
                            </span>
                          </div>
                          <div class="wildlife-rewards">
                            <span class="reward exp">✨ +{{ w.exp }} 经验</span>
                            <span class="reward gold">💰 +{{ w.gold }} 第纳尔</span>
                          </div>
                        </div>
                      </div>
                      <el-button type="primary" :disabled="!canHunt || huntingLoading" @click="doHunt(w.id)">
                        {{ huntingLoading ? '狩猎中...' : canHunt ? '🏹 狩猎' : '体力不足' }}
                      </el-button>
                    </div>
                  </div>
                </div>
              </el-tab-pane>
              
              <el-tab-pane label="🌿 采集" name="gathering">
                <div class="crafting-subtab">
                  <el-alert title="采集说明" type="info" :closable="false" style="margin-bottom: 15px">
                    采集草药用于制作医疗物品，消耗体力。需要学习草药学技能。
                  </el-alert>
                  <div class="gathering-info">
                    <p>草药学等级: {{ gatheringInfo.herbalism_level || 0 }}</p>
                    <p>预计采集: {{ gatheringInfo.estimated_herbs || '未知' }} 株</p>
                    <p>体力消耗: {{ gatheringInfo.lingqi_cost || 10 }} 点</p>
                    <p v-if="gatheringInfo.cooldown_remaining > 0">冷却中: {{ gatheringInfo.cooldown_remaining }} 秒</p>
                    <p v-else style="color: #4caf50">✅ 可以采集</p>
                  </div>
                  <el-button type="success" size="large" :disabled="!gatheringInfo.can_gather || gatheringLoading" @click="doGather">
                    {{ gatheringLoading ? '采集中...' : '🌿 采集草药' }}
                  </el-button>
                </div>
              </el-tab-pane>
              
              <el-tab-pane label="💊 医疗制作" name="medical">
                <el-table :data="craftingRecipes" style="width: 100%">
                  <el-table-column prop="name" label="名称" />
                  <el-table-column prop="description" label="描述" />
                  <el-table-column prop="materials" label="材料">
                    <template #default="{ row }">
                      <span v-for="(mat, idx) in row.materials" :key="idx">
                        {{ mat.name }}x{{ mat.count }}{{ idx < row.materials.length - 1 ? '、' : '' }}
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="120" align="center">
                    <template #default="{ row }">
                      <el-button size="small" type="primary" @click="doCraft(row.recipe_id)" :loading="craftingLoading">制作</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>
              
              <el-tab-pane label="🔧 饰品制作" name="accessories">
                <div class="crafting-subtab">
                  <el-alert title="饰品制作" type="info" :closable="false" style="margin-bottom: 15px">
                    使用锻造材料制作饰品。
                  </el-alert>
                  <div class="accessory-crafting">
                    <el-form label-width="100px">
                      <el-form-item label="选择饰品">
                        <el-select v-model="selectedAccessory" placeholder="选择要制作的饰品">
                          <el-option v-for="acc in accessoryRecipes" :key="acc.id" :label="acc.name" :value="acc.id" />
                        </el-select>
                      </el-form-item>
                      <el-form-item>
                        <el-button type="primary" @click="doCraftAccessory" :loading="craftingLoading">制作饰品</el-button>
                      </el-form-item>
                    </el-form>
                  </div>
                </div>
              </el-tab-pane>
              
              <el-tab-pane label="我的材料" name="materials">
                <el-table :data="craftingMaterials" style="width: 100%">
                  <el-table-column prop="name" label="名称" />
                  <el-table-column prop="count" label="数量" width="100" align="center" />
                  <el-table-column prop="category" label="类型" width="100" />
                </el-table>
              </el-tab-pane>
            </el-tabs>
          </el-card>
        </div>

        <div v-else-if="currentView === 'forging'" class="forging-view">
          <el-card>
            <template #header>
              <div class="card-header">
                <span>⚒️ 锻造台</span>
                <el-button size="small" @click="loadForgingData">🔄 刷新</el-button>
              </div>
            </template>
            <el-alert
              v-if="!canForge"
              title="锻造限制"
              type="warning"
              :closable="false"
              style="margin-bottom: 15px"
            >
              锻造需要在城镇铁匠铺或控制的村庄进行。你当前位于: {{ currentLocationName }}
            </el-alert>
            <el-alert
              v-else
              title="锻造说明"
              type="info"
              :closable="false"
              style="margin-bottom: 15px"
            >
              使用锻造材料制作武器和盔甲。
            </el-alert>
            
            <el-tabs v-model="forgingTab">
              <el-tab-pane label="锻造配方" name="recipes" :disabled="!canForge">
                <el-table :data="forgingRecipes" style="width: 100%">
                  <el-table-column prop="name" label="名称" />
                  <el-table-column prop="fuel" label="燃料" />
                  <el-table-column prop="metal" label="金属" />
                  <el-table-column prop="accessory" label="辅料" />
                  <el-table-column prop="skill_req" label="技能要求" width="100" />
                  <el-table-column label="操作" width="120" align="center">
                    <template #default="{ row }">
                      <el-button size="small" type="primary" @click="doForge(row.recipe_id)" :loading="forgingLoading" :disabled="!canForge">锻造</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>
              <el-tab-pane label="锻造材料" name="materials" :disabled="!canForge">
                <div class="forging-materials-section">
                  <h4>购买材料</h4>
                  <el-table :data="shopMaterials" style="width: 100%" max-height="200">
                    <el-table-column prop="name" label="名称" />
                    <el-table-column prop="category" label="类型" />
                    <el-table-column prop="price" label="单价" width="80" />
                    <el-table-column label="操作" width="150" align="center">
                      <template #default="{ row }">
                        <el-input-number v-model="buyMaterialCounts[row.material_id]" :min="1" :max="99" size="small" />
                        <el-button size="small" type="warning" @click="buyMaterial(row.material_id, buyMaterialCounts[row.material_id])">购买</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
                <div class="forging-materials-section" style="margin-top: 20px">
                  <h4>已有材料</h4>
                  <el-table :data="playerForgingMaterials" style="width: 100%">
                    <el-table-column prop="name" label="名称" />
                    <el-table-column prop="count" label="数量" width="100" align="center" />
                  </el-table>
                </div>
              </el-tab-pane>
            </el-tabs>
          </el-card>
        </div>
      </el-main>
    </el-container>

    <div class="world-chat-panel" :style="{ transform: 'scale(' + chatZoom + ')', transformOrigin: 'bottom right' }">
      <div class="chat-header">
        <span>💬 世界频道</span>
        <div class="chat-controls">
          <el-button size="small" text @click="chatZoom = Math.min(1.5, chatZoom + 0.1)">🔍+</el-button>
          <el-button size="small" text @click="chatZoom = Math.max(0.5, chatZoom - 0.1)">🔍-</el-button>
          <el-button size="small" text @click="chatExpanded = !chatExpanded">
            {{ chatExpanded ? '▼' : '▲' }}
          </el-button>
        </div>
      </div>
      <div class="chat-messages" ref="chatRef" v-show="chatExpanded">
        <div v-for="(msg, i) in gameStore.worldChat" :key="i" class="chat-message">
          <span class="msg-name" :style="{ color: getNameColor(msg.realm) }">{{ msg.name }}</span>
          <span class="msg-role" v-if="msg.sect_name">[{{ msg.sect_name }}]</span>
          <span class="msg-content">: {{ msg.content }}</span>
        </div>
      </div>
      <div class="chat-input" v-show="chatExpanded">
        <el-input 
          v-model="chatInputMsg" 
          placeholder="发送消息..." 
          size="small"
          @keyup.enter="sendChatMessage" 
        />
        <el-button size="small" type="primary" @click="sendChatMessage">发送</el-button>
      </div>
    </div>

    <el-dialog v-model="equipDialogVisible" title="装备详情" width="450px">
      <div v-if="selectedEquip && !equipDialogType" class="equip-detail">
        <h3>{{ selectedEquip.name }}</h3>
        <p>品质: {{ getQualityName(selectedEquip.quality) }}</p>
        <p>攻击: {{ selectedEquip.attack_bonus || 0 }}</p>
        <p>防御: {{ selectedEquip.defense_bonus || 0 }}</p>
        <p>描述: {{ selectedEquip.description }}</p>
      </div>
      <div v-else-if="selectedEquip && equipDialogType === 'mounted_unequip'" class="equip-detail">
        <h3>{{ selectedEquip.name }}</h3>
        <p>品质: {{ getQualityName(selectedEquip.quality) }}</p>
        <p>攻击: {{ selectedEquip.attack_bonus || 0 }}</p>
        <p>防御: {{ selectedEquip.defense_bonus || 0 }}</p>
        <p>描述: {{ selectedEquip.description }}</p>
      </div>
      <div v-else-if="equipDialogType === 'mount'" class="equip-list">
        <p>选择背包中的坐骑：</p>
        <el-table :data="mountableItems" style="width: 100%" @row-click="selectMountItem">
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="count" label="数量" width="80" />
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button size="small" type="primary">装备</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="mountableItems.length === 0" description="背包中没有可召唤的坐骑" />
      </div>
      <div v-else-if="equipDialogType === 'mount_equip'" class="equip-list">
        <p>选择背包中的{{ getSlotName(selectedSlot) }}：</p>
        <el-table :data="mountEquipableItems" style="width: 100%" @row-click="selectMountEquipItem">
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="count" label="数量" width="80" />
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button size="small" type="primary">装备</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="mountEquipableItems.length === 0" :description="'背包中没有可装备的' + getSlotName(selectedSlot)" />
      </div>
      <div v-else-if="equipDialogType === 'quick_equip'" class="equip-list">
        <p>选择可装备的物品（{{ getSlotName(selectedSlot) }}）：</p>
        <el-table :data="quickEquipItems" style="width: 100%" @row-click="doQuickEquip(row.item_id)">
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="tier_name" label="品质" width="80" />
          <el-table-column prop="attack" label="攻击" width="80" />
          <el-table-column prop="defense" label="防御" width="80" />
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button size="small" type="primary" @click.stop="doQuickEquip(row.item_id)">装备</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="quickEquipItems.length === 0" description="背包中没有可装备的物品" />
      </div>
      <template #footer>
        <el-button @click="equipDialogVisible = false">关闭</el-button>
        <el-button v-if="selectedEquip && !equipDialogType" type="primary" @click="handleEquipAction" :loading="gameStore.isButtonLoading('equip_' + selectedEquip?.item_id)">装备</el-button>
        <el-button v-if="selectedEquip && equipDialogType === 'mounted_unequip'" type="danger" @click="handleUnequipMountEquip" :loading="gameStore.isButtonLoading('unequip_mount_' + selectedSlot)">卸下</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { useIconStore } from '../stores/icons'
import { useLogStore } from '../stores/log'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'

const gameStore = useGameStore()
const iconStore = useIconStore()
const logStore = useLogStore()

const currentView = ref('panel')
const isAdmin = ref(false)
const adminLevel = ref(0)
const equipDialogVisible = ref(false)
const selectedEquip = ref(null)
const selectedSlot = ref('')
const equipDialogType = ref('')
const showVisualEquipment = ref(true)

const getSlotIcon = (slotKey) => {
  const icons = {
    helmet: '⛑️',
    shoulder: '🦺',
    weapon: '⚔️',
    armor: '🛡️',
    accessory1: '💍',
    accessory2: '📿',
    gloves: '🧤',
    boots: '👢'
  }
  return icons[slotKey] || '📦'
}

const chatExpanded = ref(true)
const chatZoom = ref(1)
const chatInputMsg = ref('')
const chatRef = ref(null)

const getNameColor = (realm) => {
  const colors = ['', '#4CAF50', '#2196F3', '#9C27B0', '#FF9800', '#f44336']
  return colors[realm] || '#ffd700'
}

const checkRateLimit = () => {
  const result = gameStore.checkRateLimit()
  if (result.blocked) {
    if (result.warning) {
      ElMessage.warning(result.message)
    } else {
      ElMessage.error(result.message)
    }
    return false
  }
  return true
}

const sendChatMessage = () => {
  if (chatInputMsg.value.trim()) {
    gameStore.sendWorldChat(chatInputMsg.value.trim())
    chatInputMsg.value = ''
  }
}

const scrollChatToBottom = () => {
  nextTick(() => {
    if (chatRef.value) {
      chatRef.value.scrollTop = chatRef.value.scrollHeight
    }
  })
}

const personalLog = computed(() => {
  return logStore.logs.map(log => ({
    ...log,
    time: new Date(log.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
  }))
})

const logRef = ref(null)
const logMinimized = ref(false)

const toggleLogMinimize = () => {
  logMinimized.value = !logMinimized.value
}

const startResize = (e) => {
  e.preventDefault()
}

const addPersonalLog = (content, type = 'info') => {
  const iconMap = {
    gold: '💰', exp: '✨', levelup: '🎉', point: '⭐',
    combat: '⚔️', trade: '🛒', travel: '🗺️', npc: '💬',
    equip: '🛡️', cultivate: '🧘', item: '💊', system: '🔧',
    reward: '🎁',
  }
  logStore.addLog({
    type,
    icon: iconMap[type] || '🔧',
    title: type,
    content,
  })
}

const clearPersonalLog = () => {
  logStore.clearLogs()
}

watch(() => gameStore.player, (newPlayer, oldPlayer) => {
  if (newPlayer && oldPlayer) {
    if (newPlayer.spirit_stones !== oldPlayer.spirit_stones) {
      const diff = newPlayer.spirit_stones - oldPlayer.spirit_stones
      if (diff > 0) {
        addPersonalLog(`获得第纳尔 +${diff}`, 'gold')
      }
    }
    if (newPlayer.exp !== oldPlayer.exp) {
      const diff = newPlayer.exp - oldPlayer.exp
      if (diff > 0) {
        addPersonalLog(`获得经验 +${diff}`, 'exp')
      }
    }
    if (newPlayer.level !== oldPlayer.level) {
      addPersonalLog(`🎉 升级了！当前等级 ${newPlayer.level}级`, 'levelup')
      addPersonalLog(`获得属性点 +1`, 'point')
      const audio = getAudioStore()
      if (audio) audio.playSound('levelup')
    }
    if (newPlayer.unallocated_points !== oldPlayer.unallocated_points) {
      const diff = newPlayer.unallocated_points - oldPlayer.unallocated_points
      if (diff > 0) {
        addPersonalLog(`获得可分配属性点 +${diff}`, 'point')
      }
    }
    if (newPlayer.attribute_points !== oldPlayer.attribute_points) {
      const diff = newPlayer.attribute_points - oldPlayer.attribute_points
      if (diff > 0) {
        addPersonalLog(`获得属性点 +${diff}`, 'point')
      }
    }
    if (newPlayer.skill_points !== oldPlayer.skill_points) {
      const diff = newPlayer.skill_points - oldPlayer.skill_points
      if (diff > 0) {
        addPersonalLog(`获得技能点 +${diff}`, 'point')
      }
    }
    if (newPlayer.realm !== oldPlayer.realm) {
      addPersonalLog(`🏆 爵位提升！当前爵位 ${newPlayer.realm}阶`, 'levelup')
      addPersonalLog(`🎉 恭喜获得爵位提升！`, 'levelup')
      const audio = getAudioStore()
      if (audio) audio.playSound('levelup')
    }
  }
}, { deep: true })

watch(() => gameStore.worldChat.length, () => {
  scrollChatToBottom()
})

const mountableItems = computed(() => {
  return gameStore.inventory.filter(item => item.type === 'mount' || item.item_id?.startsWith('mount_'))
})

const mountEquipableItems = computed(() => {
  const slotToType = {
    'mount_armor': 'mount_armor',
    'mount_weapon': 'mount_weapon',
    'horse_armament': 'horse_armament'
  }
  const targetType = slotToType[selectedSlot.value]
  if (!targetType) return []
  return gameStore.inventory.filter(item => item.type === targetType || item.item_id?.startsWith(targetType + '_'))
})

const getSlotName = (slot) => {
  const names = {
    'mount_armor': '马甲',
    'mount_weapon': '马战武器',
    'horse_armament': '马具'
  }
  return names[slot] || slot
}

const equipmentSlots = computed(() => {
  const slots = [
    { key: 'weapon', name: '武器' },
    { key: 'armor', name: '护甲' },
    { key: 'helmet', name: '头盔' },
    { key: 'gloves', name: '手部' },
    { key: 'boots', name: '腿部' },
    { key: 'shoulder', name: '肩甲' },
    { key: 'accessory1', name: '饰品1' },
    { key: 'accessory2', name: '饰品2' }
  ]
  return slots.map(slot => ({
    ...slot,
    icon: iconStore.getIconContent(slot.key) || getDefaultIcon(slot.key)
  }))
})

const mountSlots = computed(() => {
  const slots = [
    { key: 'mount', name: '坐骑' },
    { key: 'mount_armor', name: '马甲' },
    { key: 'mount_weapon', name: '马战武器' },
    { key: 'horse_armament', name: '马具' }
  ]
  return slots.map(slot => ({
    ...slot,
    icon: iconStore.getIconContent(slot.key) || getDefaultIcon(slot.key)
  }))
})

const getDefaultIcon = (key) => {
  const defaults = {
    weapon: '⚔️', armor: '🛡️', helmet: '⛑️', gloves: '🧤',
    boots: '👢', shoulder: '🦺', accessory1: '💍', accessory2: '📿',
    mount: '🐎', mount_armor: '🎽', mount_weapon: '🔱', horse_armament: '🪢'
  }
  return defaults[key] || '📦'
}

const player = computed(() => gameStore.player)

// 出身选择弹窗相关
const showSpawnModal = ref(false)
const spawnLoading = ref(true)
const spawnLocationsLoading = ref(true)
const confirmLoading = ref(false)
const spawnOrigins = ref([])
const spawnLocations = ref([])
const selectedOrigin = ref('')
const selectedLocation = ref('')
let spawnTimeoutTimer = null

const filteredSpawnLocations = computed(() => {
  if (!selectedOrigin.value) return []
  return spawnLocations.value.filter(loc => 
    loc.available_origins && loc.available_origins.includes(selectedOrigin.value)
  )
})

const checkAndShowSpawnModal = async () => {
  console.log('[Spawn] Checking spawn status, player:', gameStore.player)
   
  // 强制显示弹窗，不管有没有数据
  if (!showSpawnModal.value) {
    showSpawnModal.value = true
    spawnLoading.value = true
    spawnLocationsLoading.value = true
    
    // 注册消息处理器
    gameStore.wsMessageHandlers = gameStore.wsMessageHandlers || {}
    gameStore.wsMessageHandlers['spawn_select'] = handleSpawnWsMessage
    
    // 等待连接
    if (!gameStore.connected) {
      console.log('[Spawn] Connecting to WebSocket...')
      await gameStore.connectWs()
    }
    
    // 等待一下让连接稳定
    await new Promise(resolve => setTimeout(resolve, 300))
    
    // 发送请求
    console.log('[Spawn] Sending requests...')
    gameStore.send({ type: 'get_spawn_origins' })
    gameStore.send({ type: 'get_spawn_locations' })
    
    // 设置获取数据的超时
    setTimeout(() => {
      if (spawnLoading.value && spawnOrigins.value.length === 0) {
        spawnLoading.value = false
        ElMessage.warning('获取出身数据超时')
      }
      if (spawnLocationsLoading.value && spawnLocations.value.length === 0) {
        spawnLocationsLoading.value = false
        ElMessage.warning('获取地点数据超时')
      }
    }, 10000)
  }
}

const handleSpawnWsMessage = (msg) => {
  console.log('[Spawn] Received message:', msg.type)
  if (msg.type === 'spawn_origins') {
    spawnOrigins.value = msg.data || []
    console.log('[Spawn] Loaded origins:', spawnOrigins.value.length)
    spawnLoading.value = false
  } else if (msg.type === 'spawn_locations') {
    spawnLocations.value = msg.data || []
    console.log('[Spawn] Loaded locations:', spawnLocations.value.length)
    spawnLocationsLoading.value = false
  } else if (msg.type === 'action_result' && msg.action === 'set_spawn_origin') {
    if (spawnTimeoutTimer) {
      clearTimeout(spawnTimeoutTimer)
      spawnTimeoutTimer = null
    }
    confirmLoading.value = false
    if (msg.data?.success) {
      ElMessage.success('选择成功！欢迎来到卡拉迪亚大陆！')
      showSpawnModal.value = false
      sessionStorage.removeItem('needsSpawn')
      sessionStorage.setItem('spawn_completed', '1')
      gameStore.getPanel()
      gameStore.getInventory()
    } else {
      ElMessage.error(msg.data?.message || '选择失败')
    }
  } else if (msg.type === 'error') {
    if (spawnTimeoutTimer) {
      clearTimeout(spawnTimeoutTimer)
      spawnTimeoutTimer = null
    }
    confirmLoading.value = false
    ElMessage.error(msg.message || '服务器发生错误')
  }
}

const selectOrigin = (originId) => {
  selectedOrigin.value = originId
  selectedLocation.value = ''
}

const selectLocation = (locationId) => {
  selectedLocation.value = locationId
}

const confirmSpawnSelection = async () => {
  if (!selectedOrigin.value) {
    ElMessage.warning('请选择出身背景')
    return
  }
  
  if (!gameStore.connected) {
    ElMessage.warning('未连接到服务器，请刷新页面重试')
    return
  }
  
  confirmLoading.value = true
  
  if (spawnTimeoutTimer) {
    clearTimeout(spawnTimeoutTimer)
  }
  spawnTimeoutTimer = setTimeout(() => {
    spawnTimeoutTimer = null
    confirmLoading.value = false
    ElMessage.error('操作超时，请检查网络连接后重试')
  }, 15000)
  
  gameStore.send({ 
    type: 'set_spawn_origin',
    data: {
      origin: selectedOrigin.value,
      location: selectedLocation.value
    }
  })
}

onUnmounted(() => {
  if (spawnTimeoutTimer) {
    clearTimeout(spawnTimeoutTimer)
    spawnTimeoutTimer = null
  }
  if (gameStore.wsMessageHandlers && gameStore.wsMessageHandlers['spawn_select']) {
    delete gameStore.wsMessageHandlers['spawn_select']
  }
})

const canCollectAfk = computed(() => {
  if (!player.value?.afk_cultivate_end) return false
  const now = Date.now() / 1000
  return player.value.afk_cultivate_end <= now
})

const realmTagType = computed(() => {
  const realm = player.value?.realm || 0
  if (realm >= 6) return 'danger'
  if (realm >= 3) return 'warning'
  return 'success'
})

const getQualityType = (quality) => {
  const types = ['', 'info', 'success', 'warning', 'danger']
  return types[quality] || 'info'
}

const getQualityName = (quality) => {
  const names = ['', '普通', '良品', '精品', '极品']
  return names[quality] || '未知'
}

const getLocationDisplay = () => {
  const mapState = player.value?.map_state
  if (mapState?.current_location) {
    return mapState.current_location
  }
  if (mapState?.travel_destination) {
    return '旅行中...'
  }
  return '流浪中'
}

const handleEquipClick = async (slot) => {
  if (player.value?.equipment?.[slot]) {
    selectedEquip.value = player.value.equipment[slot]
    selectedSlot.value = slot
    equipDialogVisible.value = true
  } else {
    selectedSlot.value = slot
    equipDialogType.value = 'quick_equip'
    await gameStore.getInventory()
    equipDialogVisible.value = true
  }
}

// 快捷装备：槽位到后端槽位的映射
const slotMap = {
  weapon: 'weapon',
  helmet: 'head',
  armor: 'body',
  gloves: 'hands',
  boots: 'legs',
  shoulder: 'shoulders',
  accessory1: 'accessory1',
  accessory2: 'accessory2',
}

const quickEquipItems = computed(() => {
  const targetSlot = slotMap[selectedSlot.value]
  if (!targetSlot || !gameStore.inventory) return []
  return gameStore.inventory.filter(item => item.slot === targetSlot)
})

const doQuickEquip = async (equipId) => {
  try {
    const result = await gameStore.wsCall('equip_item', { equip_id: equipId })
    if (result?.success) {
      ElMessage.success(result.message || '装备成功')
      equipDialogVisible.value = false
      await gameStore.getPanel()
      await gameStore.getInventory()
    } else {
      ElMessage.error(result?.message || '装备失败')
    }
  } catch (e) {
    ElMessage.error('请求失败')
  }
}

const handleMountEquipClick = (slot) => {
  if (player.value?.equipped_mount_items?.[slot]) {
    selectedEquip.value = player.value.equipped_mount_items[slot]
    selectedSlot.value = slot
    equipDialogType.value = 'mounted_unequip'
    equipDialogVisible.value = true
  } else {
    selectedEquip.value = null
    selectedSlot.value = slot
    equipDialogType.value = 'mount_equip'
    gameStore.getInventory()
    equipDialogVisible.value = true
  }
}

const handleSummonMount = () => {
  selectedEquip.value = null
  selectedSlot.value = ''
  equipDialogType.value = 'mount'
  gameStore.getInventory()
  equipDialogVisible.value = true
}

const handleUnequipMount = () => {
  gameStore.unequipMount()
}

const handleEquipAction = async () => {
  if (selectedEquip.value) {
    const key = 'equip_' + selectedEquip.value.item_id
    gameStore.setButtonLoading(key, true)
    await gameStore.equipItem(selectedEquip.value.item_id)
    equipDialogVisible.value = false
    setTimeout(() => {
      gameStore.setButtonLoading(key, false)
      gameStore.getPanel()
    }, 100)
  }
}

const selectMountItem = (row) => {
  const key = 'equip_mount_' + row.item_id
  gameStore.setButtonLoading(key, true)
  gameStore.equipMount(row.item_id)
  equipDialogVisible.value = false
  setTimeout(() => {
    gameStore.setButtonLoading(key, false)
    gameStore.getPanel()
  }, 100)
}

const selectMountEquipItem = (row) => {
  const key = 'equip_mount_item_' + row.item_id
  gameStore.setButtonLoading(key, true)
  gameStore.equipMountItem(row.item_id)
  equipDialogVisible.value = false
  setTimeout(() => {
    gameStore.setButtonLoading(key, false)
    gameStore.getPanel()
  }, 100)
}

const handleUnequipMountEquip = () => {
  if (selectedSlot.value) {
    const key = 'unequip_mount_' + selectedSlot.value
    gameStore.setButtonLoading(key, true)
    gameStore.unequipMountItem(selectedSlot.value)
    equipDialogVisible.value = false
    setTimeout(() => {
      gameStore.setButtonLoading(key, false)
      gameStore.getPanel()
    }, 100)
  }
}

const handleUseItem = async (item) => {
  const key = 'use_' + item.item_id
  gameStore.setButtonLoading(key, true)
  await gameStore.useItem(item.item_id)
  setTimeout(() => {
    gameStore.setButtonLoading(key, false)
  }, 300)
}

const handleEquipItem = async (item) => {
  const key = 'equip_' + item.item_id
  gameStore.setButtonLoading(key, true)
  await gameStore.equipItem(item.item_id)
  setTimeout(() => {
    gameStore.setButtonLoading(key, false)
  }, 300)
}

const handleCheckin = async () => {
  if (!checkRateLimit()) return
  gameStore.setButtonLoading('checkin', true)
  await gameStore.checkin()
  setTimeout(() => {
    gameStore.setButtonLoading('checkin', false)
  }, 500)
}

const handleHunt = async () => {
  if (!checkRateLimit()) return
  gameStore.setButtonLoading('hunt', true)
  gameStore.send({ type: 'hunt_wildlife' })
  setTimeout(() => {
    gameStore.setButtonLoading('hunt', false)
  }, 500)
}

const handleGather = async () => {
  if (!checkRateLimit()) return
  gameStore.setButtonLoading('gather', true)
  gameStore.send({ type: 'gather_herbs' })
  setTimeout(() => {
    gameStore.setButtonLoading('gather', false)
  }, 500)
}

const handleHeal = async () => {
  if (!checkRateLimit()) return
  gameStore.setButtonLoading('heal', true)
  gameStore.send({ type: 'use_heal_skill', data: { skill_id: 'bandage' } })
  setTimeout(() => {
    gameStore.setButtonLoading('heal', false)
  }, 500)
}

// 制作tab子tab
const craftingSubTab = ref('medical')
const craftingRecipes = ref([])
const craftingMaterials = ref([])
const craftingLoading = ref(false)
const accessoryRecipes = ref([])
const selectedAccessory = ref('')
const huntingLoading = ref(false)
const gatheringLoading = ref(false)
const gatheringInfo = ref({})

const wildlifeList = [
  { id: 'deer', name: '鹿', icon: '🦌', tier: 0, description: '森林中常见的温顺动物', exp: 15, gold: 10, drops: { hunt_deer_skin: 0.8, hunt_deer_meat: 0.9, hunt_deer_antler: 0.3 } },
  { id: 'rabbit', name: '野兔', icon: '🐇', tier: 0, description: '草地常见的小动物', exp: 8, gold: 5, drops: { hunt_rabbit_skin: 0.7, hunt_rabbit_meat: 0.9 } },
  { id: 'chicken', name: '野鸡', icon: '🐔', tier: 0, description: '村庄附近的野生禽类', exp: 5, gold: 3, drops: { hunt_feather: 0.8, hunt_chicken_meat: 0.9 } },
  { id: 'boar', name: '野猪', icon: '🐗', tier: 1, description: '具有攻击性的野兽', exp: 30, gold: 25, drops: { hunt_boar_skin: 0.8, hunt_boar_meat: 0.9, hunt_boar_tusk: 0.4 } },
  { id: 'wolf', name: '狼', icon: '🐺', tier: 1, description: '成群出现的捕食者', exp: 35, gold: 30, drops: { hunt_wolf_skin: 0.8, hunt_wolf_fang: 0.5 } },
  { id: 'bear', name: '熊', icon: '🐻', tier: 2, description: '凶猛的大型野兽', exp: 80, gold: 60, drops: { hunt_bear_skin: 0.7, hunt_bear_paw: 0.4, hunt_bear_gall: 0.2 } },
  { id: 'mammoth', name: '猛犸象', icon: '🦣', tier: 3, description: '传说中的远古巨兽', exp: 200, gold: 150, drops: { hunt_mammoth_tusk: 0.3, hunt_mammoth_hide: 0.5 } },
]

const tierClass = (t) => ['', 'tier-common', 'tier-advanced', 'tier-rare', 'tier-boss'][t] || ''
const tierName = (t) => ['普通', '进阶', '高级', 'Boss'][t] || '未知'
const dropName = (id) => id.replace('hunt_', '').replace(/_/g, ' ')

const canHunt = computed(() => {
  if (!player.value) return false
  return (player.value.lingqi ?? 0) >= 15
})

const doHunt = async (wildlifeId) => {
  if (!canHunt.value) return
  huntingLoading.value = true
  try {
    const result = await gameStore.wsCall('hunt_wildlife', { wildlife_id: wildlifeId })
    if (result?.success) {
      ElMessage.success(result.message || '狩猎成功')
    } else {
      ElMessage.error(result?.message || '狩猎失败')
    }
  } catch (e) {
    ElMessage.error('请求失败')
  } finally {
    huntingLoading.value = false
  }
}

const doGather = async () => {
  gatheringLoading.value = true
  try {
    const result = await gameStore.wsCall('gather_herbs')
    if (result?.success) {
      ElMessage.success(result.message || '采集成功')
      await loadGatheringInfo()
    } else {
      ElMessage.error(result?.message || '采集失败')
    }
  } catch (e) {
    ElMessage.error('请求失败')
  } finally {
    gatheringLoading.value = false
  }
}

const loadGatheringInfo = async () => {
  try {
    const info = await gameStore.wsCall('get_gather_info')
    if (info?.data?.gather_info) {
      gatheringInfo.value = info.data.gather_info
    }
  } catch (e) {
    console.error('Failed to load gathering info:', e)
  }
}

const loadAllCraftingData = async () => {
  await loadCraftingRecipes()
  await loadGatheringInfo()
  await loadCraftingMaterials()
  await loadAccessoryRecipes()
}

const loadCraftingRecipes = async () => {
  try {
    const medicalInfo = await gameStore.wsCall('get_medical_info')
    if (medicalInfo && medicalInfo.recipes) {
      craftingRecipes.value = medicalInfo.recipes
    }
  } catch (e) {
    console.error('Failed to load crafting recipes:', e)
  }
}

const loadCraftingMaterials = async () => {
  try {
    const inv = await gameStore.wsCall('get_inventory')
    if (inv && inv.items) {
      const mats = inv.items.filter(i =>
        i.item_id?.startsWith('hunt_') ||
        i.item_id?.startsWith('herb_') ||
        i.item_id?.startsWith('forge_') ||
        i.item_id?.includes('material')
      )
      craftingMaterials.value = mats.map(m => ({
        name: m.name || m.item_id,
        count: m.count,
        category: m.item_id?.startsWith('hunt_') ? '狩猎' : m.item_id?.startsWith('herb_') ? '采集' : '锻造',
      }))
    }
  } catch (e) {
    console.error('Failed to load crafting materials:', e)
  }
}

const loadAccessoryRecipes = async () => {
  accessoryRecipes.value = [
    { id: 'leather_bracelet', name: '皮手环' },
    { id: 'iron_ring', name: '铁戒指' },
    { id: 'silver_necklace', name: '银项链' },
  ]
}

const doCraftAccessory = async () => {
  if (!selectedAccessory.value) {
    ElMessage.warning('请选择饰品')
    return
  }
  craftingLoading.value = true
  try {
    const result = await gameStore.wsCall('craft_accessory', { accessory_id: selectedAccessory.value })
    if (result?.success) {
      ElMessage.success(result.message || '制作完成')
    } else {
      ElMessage.error(result?.message || '制作失败')
    }
  } catch (e) {
    ElMessage.error('请求失败')
  } finally {
    craftingLoading.value = false
  }
}

const doCraft = async (recipeId) => {
  craftingLoading.value = true
  try {
    const result = await gameStore.wsCall('craft_item', { recipe_id: recipeId })
    if (result?.success) {
      ElMessage.success(result.message || '制作完成')
    } else {
      ElMessage.error(result?.message || '制作失败')
    }
  } catch (e) {
    ElMessage.error('请求失败')
  } finally {
    craftingLoading.value = false
    await loadCraftingRecipes()
  }
}

// 药水BUFF时间格式化
const formatBuffTime = (seconds) => {
  if (!seconds || seconds <= 0) return '已过期'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  if (m >= 60) {
    const h = Math.floor(m / 60)
    return `${h}小时${m % 60}分`
  }
  return `${m}分${s}秒`
}

const forgingTab = ref('recipes')
const forgingRecipes = ref([])
const playerForgingMaterials = ref([])
const shopMaterials = ref([])
const forgingLoading = ref(false)
const buyMaterialCounts = ref({})
const currentLocationName = ref('未知')
const canForge = ref(false)

const loadForgingData = async () => {
  try {
    const recipes = await gameStore.wsCall('get_forging_recipes')
    if (recipes && recipes.recipes) {
      forgingRecipes.value = recipes.recipes
    }
    
    const materials = await gameStore.wsCall('get_forging_materials')
    if (materials && materials.materials) {
      playerForgingMaterials.value = Object.values(materials.materials)
    }
    
    const player = gameStore.player
    if (player && player.map_state && player.map_state.current_location) {
      const locId = player.map_state.current_location
      currentLocationName.value = locId
      
      const goods = await gameStore.wsCall('get_trade_goods', { location_id: locId })
      if (goods && goods.goods) {
        shopMaterials.value = goods.goods.filter(g => 
          g.category === '矿产' || g.category === '原料'
        ).map(g => ({
          material_id: g.good_id,
          name: g.name,
          category: g.category,
          price: g.price
        }))
      }
      
      canForge.value = true
    } else {
      canForge.value = false
    }
  } catch (e) {
    console.error('Failed to load forging data:', e)
    canForge.value = false
  }
}

const doForge = async (recipeId) => {
  forgingLoading.value = true
  const result = await gameStore.wsCall('forge_item', { recipe_id: recipeId })
  ElMessage.info(result.message || result.msg || '锻造完成')
  forgingLoading.value = false
  await loadForgingData()
}

const buyMaterial = async (materialId, count) => {
  if (!count || count < 1) {
    ElMessage.warning('请输入购买数量')
    return
  }
  const result = await gameStore.wsCall('buy_forging_material', { material_id: materialId, count: count })
  ElMessage.info(result.message || result.msg || '购买完成')
  await loadForgingData()
}

const handleStartAfk = async () => {
  if (!checkRateLimit()) return
  gameStore.setButtonLoading('afk', true)
  await gameStore.startAfk()
  setTimeout(() => {
    gameStore.setButtonLoading('afk', false)
  }, 500)
}

const handleCancelAfk = async () => {
  if (!checkRateLimit()) return
  gameStore.setButtonLoading('cancel_afk', true)
  await gameStore.cancelAfk()
  setTimeout(() => {
    gameStore.setButtonLoading('cancel_afk', false)
  }, 500)
}

const handleCollectAfk = async () => {
  if (!checkRateLimit()) return
  gameStore.setButtonLoading('collect_afk', true)
  await gameStore.collectAfk()
  setTimeout(() => {
    gameStore.getPanel()
    gameStore.setButtonLoading('collect_afk', false)
  }, 300)
}

const handleAdventure = async () => {
  if (!checkRateLimit()) return
  gameStore.setButtonLoading('adventure', true)
  await gameStore.adventure()
  setTimeout(() => {
    gameStore.setButtonLoading('adventure', false)
  }, 800)
}

const handleBandits = () => {
  if (!checkRateLimit()) return
  gameStore.setButtonLoading('bandits', true)
  gameStore.send({ type: 'get_nearby_bandits' })
  setTimeout(() => {
    gameStore.setButtonLoading('bandits', false)
  }, 500)
}

const handleLogout = () => {
  gameStore.logout()
  router.push('/')
}

const handleWsMessage = (msg) => {
  if (msg.type === 'nearby_bandits') {
    const bandits = msg.data?.bandits || []
    if (bandits.length > 0) {
      ElMessage.success(`发现 ${bandits.length} 个土匪窝点`)
    } else {
      ElMessage.info('附近没有土匪窝点')
    }
  } else if (msg.type === 'bandit_attack_result') {
    if (msg.data?.success) {
      ElMessage.success(msg.data.message || '讨伐成功')
    } else {
      ElMessage.error(msg.data?.message || '讨伐失败')
    }
  }
}

onMounted(async () => {
  if (!gameStore.token) {
    router.push('/')
    return
  }
  const valid = await gameStore.verifyToken()
  if (!valid) {
    gameStore.logout()
    ElMessage.error('登录已过期，请重新登录')
    router.push('/')
    return
  }
  if (!gameStore.connected) {
    await gameStore.connectWs()
  }
  
  const adminToken = localStorage.getItem('qikan_admin_token')
  if (adminToken) {
    try {
      const res = await fetch('/api/admin/verify-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ admin_token: adminToken })
      })
      const data = await res.json()
      if (data.success && data.can_customize_ui) {
        isAdmin.value = true
        adminLevel.value = data.level || 0
      }
    } catch (e) {}
  }
  gameStore.wsMessageHandlers = gameStore.wsMessageHandlers || {}
  gameStore.wsMessageHandlers['home'] = handleWsMessage
  iconStore.loadConfig()
  
  // 获取玩家数据后检查是否需要选择出身
  await gameStore.getPanel()
  await gameStore.getInventory()
  await loadAllCraftingData()
  await loadForgingData()
  
  // 检查是否已完成出身选择
  const hasSpawn = gameStore.player?.spawn_origin && gameStore.player.spawn_origin !== ''
  const spawnCompleted = sessionStorage.getItem('spawn_completed') === '1'
  
  console.log('[Spawn] hasSpawn:', hasSpawn, 'spawnCompleted:', spawnCompleted)
  
  if (!hasSpawn && !spawnCompleted) {
    // 需要选择出身
    forceShowSpawnModal()
  } else if (hasSpawn) {
    // 已完成出身选择，确保标记设置
    sessionStorage.setItem('spawn_completed', '1')
  }
})

// 强制显示出身选择弹窗
const forceShowSpawnModal = async () => {
  console.log('[Spawn] Force showing spawn modal')
  showSpawnModal.value = true
  spawnLoading.value = true
  spawnLocationsLoading.value = true
  
  // 注册消息处理器
  gameStore.wsMessageHandlers = gameStore.wsMessageHandlers || {}
  gameStore.wsMessageHandlers['spawn_select'] = handleSpawnWsMessage
  
  // 确保连接
  if (!gameStore.connected) {
    await gameStore.connectWs()
  }
  
  await new Promise(resolve => setTimeout(resolve, 500))
  
  // 发送请求
  console.log('[Spawn] Sending data requests')
  gameStore.send({ type: 'get_spawn_origins' })
  gameStore.send({ type: 'get_spawn_locations' })
  
  // 超时后显示错误状态
  setTimeout(() => {
    if (spawnLoading.value) {
      spawnLoading.value = false
      ElMessage.warning('加载出身数据超时，点击下方按钮重试')
    }
    if (spawnLocationsLoading.value) {
      spawnLocationsLoading.value = false
    }
  }, 8000)
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  background: linear-gradient(180deg, #0D0D0D 0%, #1A1A1A 50%, #151515 100%);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(90deg, #1A1A1A 0%, #252525 100%);
  border-bottom: 2px solid #8B0000;
  padding: 0 20px;
  height: 56px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  font-size: 28px;
  filter: drop-shadow(0 2px 4px rgba(255, 215, 0, 0.5));
}

.header-left h2 {
  color: #FFD700;
  margin: 0;
  font-size: 20px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.8);
  letter-spacing: 2px;
  font-family: 'Microsoft YaHei', serif;
}

.realm-tag {
  margin-left: 8px;
}

.header-nav {
  display: flex;
  gap: 4px;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #888;
  text-decoration: none;
}

.nav-item:hover {
  background: rgba(139, 0, 0, 0.3);
  color: #FFD700;
}

.nav-item.active {
  background: linear-gradient(145deg, #8B0000 0%, #5C0000 100%);
  color: #FFD700;
}

.nav-icon {
  font-size: 16px;
}

.nav-text {
  font-size: 11px;
  margin-top: 2px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.player-name {
  color: #C4B59D;
  font-size: 14px;
}

.main-content {
  padding: 16px;
}

.player-card, .equipment-card, .info-card, .quick-actions, .log-card, .buff-card {
  background: linear-gradient(145deg, #252525 0%, #1E1E1E 100%);
  border: 1px solid #3D3D3D;
  color: #F5DEB3;
  border-radius: 8px;
}

.log-card {
  height: calc(100vh - 140px);
  display: flex;
  flex-direction: column;
}

.log-card :deep(.el-card__body) {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.log-card .log-messages {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  background: rgba(0, 0, 0, 0.4);
  border-radius: 4px;
}

.buff-card {
  margin-top: 12px;
}

.buff-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.buff-item {
  padding: 8px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.3);
}

.buff-positive {
  border-left: 3px solid #4CAF50;
}

.buff-debuff {
  border-left: 3px solid #f44336;
}

.buff-name {
  font-size: 13px;
  font-weight: bold;
  margin-bottom: 4px;
}

.buff-effects {
  font-size: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.buff-effects .buff {
  color: #4CAF50;
}

.buff-effects .debuff {
  color: #f44336;
}

.buff-timer {
  font-size: 11px;
  color: #888;
  margin-top: 4px;
}

:deep(.el-card__header) {
  background: linear-gradient(90deg, #1A1A1A 0%, #252525 100%);
  border-bottom: 1px solid #3D3D3D;
  padding: 12px 16px;
}

:deep(.el-card__body) {
  padding: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header span {
  color: #FFD700;
  font-size: 15px;
  font-weight: bold;
}

.header-tip {
  font-size: 12px;
  color: #666;
  font-weight: normal;
}

.player-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #3D3D3D;
}

.player-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.player-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(145deg, #8B0000 0%, #5C0000 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: #FFD700;
  border: 2px solid #D4AF37;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.player-details h3 {
  margin: 0;
  color: #FFD700;
  font-size: 18px;
}

.player-badges {
  display: flex;
  gap: 6px;
  margin-top: 4px;
}

.player-location {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #C4B59D;
  font-size: 14px;
  background: rgba(0, 0, 0, 0.3);
  padding: 6px 12px;
  border-radius: 16px;
}

.location-icon {
  font-size: 14px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
}

.exp-tip {
  grid-column: span 6;
  text-align: center;
  color: #ffd700;
  font-size: 12px;
  padding: 8px;
  background: rgba(255, 215, 0, 0.1);
  border-radius: 6px;
  margin-top: 8px;
}

.stat-item {
  text-align: center;
  padding: 8px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
}

.stat-item .label {
  display: block;
  color: #888;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 4px;
}

.stat-item .value {
  display: block;
  color: #FFD700;
  font-size: 16px;
  font-weight: bold;
}

.stat-item .value.attack {
  color: #F44336;
}

.stat-item .value.defense {
  color: #2196F3;
}

.stat-item .value.gold {
  color: #FFD700;
}

.stat-bar {
  height: 4px;
  background: #333;
  border-radius: 2px;
  margin-top: 4px;
  overflow: hidden;
}

.stat-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #8BC34A);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.action-buttons {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-top: 16px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.action-buttons .el-button {
  background: linear-gradient(145deg, #3D3D3D 0%, #2D2D2D 100%);
  border: 1px solid #4D4D4D;
  color: #F5DEB3;
  font-weight: 500;
  transition: all 0.2s ease;
}

.action-buttons .el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.action-buttons .el-button--success {
  background: linear-gradient(145deg, #2E7D32 0%, #1B5E20 100%);
  border-color: #4CAF50;
}

.action-buttons .el-button--primary {
  background: linear-gradient(145deg, #1565C0 0%, #0D47A1 100%);
  border-color: #2196F3;
}

.action-buttons .el-button--warning {
  background: linear-gradient(145deg, #F57C00 0%, #E65100 100%);
  border-color: #FF9800;
}

.action-buttons .el-button--danger {
  background: linear-gradient(145deg, #8B0000 0%, #5C0000 100%);
  border-color: #B22222;
}

.equipment-section {
  margin-bottom: 8px;
}

.section-title {
  color: #D4AF37;
  font-size: 13px;
  margin: 0 0 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.equipment-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.mount-grid {
  grid-template-columns: repeat(4, 1fr);
}

.mount-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.mount-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 可视化装备展示 - 人形模型 */
.visual-equipment {
  display: flex;
  gap: 15px;
  padding: 15px;
  justify-content: center;
}

.humanoid-figure {
  position: relative;
  width: 280px;
  height: 400px;
  background: linear-gradient(180deg, #1a1a2e 0%, #0d0d1a 100%);
  border-radius: 140px 140px 20px 20px;
  border: 3px solid #3d3d5c;
}

.humanoid-figure::before {
  content: '👤';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 120px;
  opacity: 0.15;
}

.equip-slot-visual {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.08);
  border: 2px dashed #4a4a6a;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  padding: 5px;
}

.equip-slot-visual:hover {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.15);
  transform: scale(1.1);
  z-index: 10;
}

.equip-slot-visual.equipped {
  border-style: solid;
  border-color: #4caf50;
  background: rgba(76, 175, 80, 0.2);
}

.slot-emoji {
  font-size: 28px;
}

.slot-label {
  font-size: 11px;
  color: #888;
  margin-top: 2px;
}

.item-name {
  font-size: 10px;
  color: #ffd700;
  text-align: center;
  max-width: 70px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-tip {
  font-size: 9px;
  color: #666;
}

/* 人形装备位置 - 从上到下 */
.equip-slot-visual.head {
  top: 15px;
  left: 50%;
  transform: translateX(-50%);
  width: 80px;
  height: 70px;
}

.equip-slot-visual.shoulder-l {
  top: 110px;
  left: 120px;
  width: 55px;
  height: 50px;
}

.equip-slot-visual.body {
  top: 150px;
  left: 50%;
  transform: translateX(-50%);
  width: 100px;
  height: 90px;
}

.equip-slot-visual.accessory-l {
  top: 60px;
  left: 22px;
  width: 50px;
  height: 50px;
}

.equip-slot-visual.accessory-r {
  top: 60px;
  right: 22px;
  width: 50px;
  height: 50px;
}

.equip-slot-visual.weapon-hand {
  top: 145px;
  right: 15px;
  width: 55px;
  height: 55px;
}

.equip-slot-visual.hand-l {
  top: 175px;
  left: 15px;
  width: 50px;
  height: 50px;
}

.equip-slot-visual.feet {
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  width: 90px;
  height: 60px;
}

/* 属性面板 */
.equip-stats-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px;
  background: rgba(0, 0, 0, 0.4);
  border-radius: 12px;
  min-width: 180px;
}

.stat-title {
  color: #ffd700;
  font-size: 16px;
  font-weight: bold;
  text-align: center;
  margin-bottom: 10px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
}

.stat-label {
  color: #aaa;
}

.stat-value {
  font-weight: bold;
}

.stat-value.attack {
  color: #ff6b6b;
}

.stat-value.defense {
  color: #4dabf7;
}

.stat-value.gold {
  color: #ffd700;
}

.stat-value.strength {
  color: #ff7043;
}

.stat-value.intelligence {
  color: #7e57c2;
}

.stat-value.agility {
  color: #26a69a;
}

.stat-value.points {
  color: #ffd700;
}

.attr-row {
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 4px;
}

.equip-slot {
  text-align: center;
  padding: 10px 8px;
  background: linear-gradient(145deg, #1A1A1A 0%, #0F0F0F 100%);
  border: 2px solid #3D3D3D;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.equip-slot::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(139, 115, 85, 0.1), transparent);
  transition: left 0.5s ease;
}

.equip-slot:hover::before {
  left: 100%;
}

.equip-slot:hover {
  background: linear-gradient(145deg, #3D2B1F 0%, #2D1F15 100%);
  border-color: #D4AF37;
  transform: translateY(-3px);
  box-shadow: 0 6px 16px rgba(212, 175, 55, 0.2);
}

.equip-slot.empty {
  opacity: 0.7;
}

.equip-slot.equipped {
  background: linear-gradient(145deg, #2D2416 0%, #1F1510 100%);
  border-color: #D4AF37;
}

.slot-icon {
  font-size: 28px;
  display: block;
  margin-bottom: 6px;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.6));
}

.slot-name {
  font-size: 12px;
  color: #C4B59D;
  font-weight: 500;
  margin-top: 4px;
}

.slot-item {
  font-size: 11px;
  color: #FFD700;
  margin-top: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 80px;
}

.slot-empty {
  font-size: 10px;
  color: #555;
  margin-top: 6px;
}

.equip-section {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #3D3D3D;
}

.equip-section h4 {
  color: #D4AF37;
  margin: 12px 0 16px;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 2px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
}

.mount-status {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(212, 175, 55, 0.1);
  border: 1px solid #D4AF37;
  border-radius: 8px;
  margin-bottom: 12px;
}

.mount-badge {
  background: linear-gradient(145deg, #D4AF37 0%, #8B7355 100%);
  color: #000;
  padding: 4px 12px;
  border-radius: 4px;
  font-weight: bold;
  font-size: 12px;
}

.mount-name {
  color: #FFD700;
  font-weight: bold;
  flex: 1;
}

.mount-召唤 {
  padding: 12px;
  background: rgba(139, 0, 0, 0.1);
  border: 1px dashed #8B0000;
  border-radius: 8px;
  text-align: center;
  margin-bottom: 12px;
}

.location-info p, .status-info {
  margin: 8px 0;
  color: #C4B59D;
  padding: 8px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
}

.asset-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.asset-item {
  text-align: center;
  padding: 10px 8px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.asset-icon {
  font-size: 20px;
  margin-bottom: 4px;
}

.asset-value {
  color: #FFD700;
  font-size: 16px;
  font-weight: bold;
}

.asset-label {
  color: #888;
  font-size: 11px;
  margin-top: 2px;
}

.quick-btns {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.quick-btns .el-button {
  width: 100%;
  justify-content: center;
}

/* 标签样式 */
:deep(.el-tag) {
  border-color: #8B0000;
  background: linear-gradient(145deg, #5C0000 0%, #3D0000 100%);
  color: #FFD700;
}

/* 输入框样式 */
:deep(.el-input__wrapper) {
  background: #0D0D0D;
  border: 1px solid #3D3D3D;
  box-shadow: none;
}

:deep(.el-input__wrapper:hover) {
  border-color: #8B7355;
}

:deep(.el-input__wrapper.is-focus) {
  border-color: #D4AF37;
  box-shadow: 0 0 8px rgba(212, 175, 55, 0.2);
}

:deep(.el-input__inner) {
  color: #F5DEB3;
}

/* 对话框样式 */
:deep(.el-dialog) {
  background: #1E1E1E;
  border: 2px solid #3D3D3D;
  border-radius: 8px;
}

:deep(.el-dialog__header) {
  background: linear-gradient(90deg, #1A1A1A 0%, #252525 100%);
  border-bottom: 2px solid #8B0000;
}

:deep(.el-dialog__title) {
  color: #FFD700;
}

:deep(.el-dialog__body) {
  color: #F5DEB3;
}

.world-chat-panel {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 500px;
  max-width: calc(100vw - 40px);
  background: rgba(20, 20, 30, 0.95);
  border: 2px solid #3D3D3D;
  border-radius: 12px;
  z-index: 1000;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.6);
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(90deg, #1A1A1A 0%, #252525 100%);
  border-bottom: 1px solid #3D3D3D;
  border-radius: 10px 10px 0 0;
  color: #FFD700;
  font-weight: bold;
  font-size: 15px;
}

.chat-messages {
  height: 350px;
  max-height: 50vh;
  overflow-y: auto;
  padding: 12px;
  background: rgba(0, 0, 0, 0.4);
}

.chat-message {
  margin-bottom: 10px;
  font-size: 14px;
  color: #e0e0e0;
  word-break: break-all;
  line-height: 1.5;
}

.msg-name {
  font-weight: bold;
  margin-right: 6px;
}

.msg-role {
  color: #888;
  margin-right: 6px;
  font-size: 12px;
}

.chat-input {
  display: flex;
  gap: 10px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 0 0 10px 10px;
}

.personal-log-panel {
  position: fixed;
  bottom: 20px;
  left: 80px;
  width: 380px;
  max-height: 400px;
  background: rgba(20, 20, 30, 0.95);
  border: 2px solid #3D3D3D;
  border-radius: 12px;
  z-index: 1000;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.6);
  display: flex;
  flex-direction: column;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: linear-gradient(90deg, #1A1A1A 0%, #252525 100%);
  border-bottom: 1px solid #3D3D3D;
  border-radius: 10px 10px 0 0;
  color: #FFD700;
  font-weight: bold;
  font-size: 14px;
  flex-shrink: 0;
}

.log-header-controls {
  display: flex;
  gap: 5px;
}

.log-messages {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  background: rgba(0, 0, 0, 0.4);
}

.log-resize-handle {
  height: 8px;
  background: linear-gradient(90deg, transparent, #3D3D3D, transparent);
  cursor: ns-resize;
  flex-shrink: 0;
}

.log-resize-handle:hover {
  background: linear-gradient(90deg, transparent, #FFD700, transparent);
}

.log-message {
  margin-bottom: 8px;
  font-size: 13px;
  line-height: 1.4;
  padding: 6px 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.03);
}

.log-message.gold {
  color: #FFD700;
  border-left: 3px solid #FFD700;
}

.log-message.exp {
  color: #4FC3F7;
  border-left: 3px solid #4FC3F7;
}

.log-message.levelup {
  color: #FF9800;
  border-left: 3px solid #FF9800;
  font-weight: bold;
}

.log-message.point {
  color: #81C784;
  border-left: 3px solid #81C784;
}

.log-message.drop {
  color: #CE93D8;
  border-left: 3px solid #CE93D8;
}

.log-message.equip {
  color: #FF7043;
  border-left: 3px solid #FF7043;
}

.log-time {
  color: #666;
  font-size: 11px;
  margin-right: 8px;
}

.log-content {
  color: #e0e0e0;
}

.log-empty {
  text-align: center;
  color: #666;
  padding: 40px 0;
  font-size: 13px;
}

.personal-log-section {
  border-top: 1px solid var(--el-border-color-lighter, #3D3D3D);
  padding-top: 12px;
  margin-top: 8px;
}

.personal-log-section .log-header {
  padding: 8px 12px;
  margin-bottom: 8px;
  background: linear-gradient(90deg, rgba(74, 74, 138, 0.3) 0%, rgba(74, 74, 138, 0.2) 100%);
  border-radius: 6px;
  border: 1px solid var(--el-border-color-lighter, #3D3D3D);
}

.personal-log-section .log-messages {
  height: 200px;
  max-height: 300px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 6px;
  padding: 8px;
}

.personal-log-section .log-resize-handle {
  margin-top: 4px;
}

.chat-input .el-input {
  flex: 1;
  height: 40px;
}

.chat-input .el-button {
  height: 40px;
  padding: 0 20px;
}

/* 出身选择强制弹窗 */
.spawn-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.95);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.spawn-modal {
  background: linear-gradient(145deg, #1a1a2e 0%, #16213e 100%);
  border-radius: 20px;
  border: 3px solid #ffd700;
  box-shadow: 0 0 60px rgba(255, 215, 0, 0.3);
  width: 100%;
  max-width: 900px;
  max-height: 90vh;
  overflow-y: auto;
}

.spawn-modal-header {
  text-align: center;
  padding: 30px;
  border-bottom: 2px solid rgba(255, 215, 0, 0.3);
}

.spawn-modal-header h2 {
  color: #ffd700;
  font-size: 32px;
  margin: 0 0 10px;
  text-shadow: 0 0 20px rgba(255, 215, 0, 0.5);
}

.spawn-modal-header p {
  color: #aaa;
  font-size: 16px;
  margin: 0;
}

.spawn-modal-content {
  padding: 30px;
}

.spawn-modal-content h3 {
  color: #ffd700;
  font-size: 20px;
  margin: 0 0 20px;
  text-align: center;
}

.origin-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.origin-card {
  text-align: center;
  padding: 20px 15px;
  background: rgba(255, 255, 255, 0.05);
  border: 3px solid #3d3d3d;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.origin-card:hover {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.1);
  transform: scale(1.05);
}

.origin-card.selected {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.2);
  box-shadow: 0 0 30px rgba(255, 215, 0, 0.4);
}

.origin-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 10px;
}

.origin-name {
  color: #ffd700;
  font-size: 18px;
  font-weight: bold;
  display: block;
  margin-bottom: 8px;
}

.origin-desc {
  color: #888;
  font-size: 12px;
  display: block;
  margin-bottom: 8px;
  line-height: 1.4;
}

.origin-bonus {
  color: #4caf50;
  font-size: 12px;
  font-weight: bold;
  display: block;
  background: rgba(76, 175, 80, 0.2);
  padding: 6px 10px;
  border-radius: 6px;
}

.location-section {
  margin-top: 30px;
  padding-top: 30px;
  border-top: 2px solid rgba(255, 215, 0, 0.2);
}

.location-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.location-card {
  text-align: center;
  padding: 15px 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 2px solid #3d3d3d;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.location-card:hover {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.1);
}

.location-card.selected {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.2);
}

.loc-icon {
  font-size: 32px;
  display: block;
}

.loc-name {
  color: #ffd700;
  font-size: 14px;
  font-weight: bold;
  display: block;
  margin-top: 5px;
}

.loc-faction {
  color: #888;
  font-size: 11px;
  display: block;
  margin-top: 3px;
}

.spawn-modal-footer {
  text-align: center;
  padding: 30px;
  border-top: 2px solid rgba(255, 215, 0, 0.3);
}

.spawn-modal-footer .el-button {
  height: 60px;
  font-size: 20px;
  padding: 0 60px;
  background: linear-gradient(145deg, #8b0000 0%, #5c0000 100%);
  border: 2px solid #ffd700;
}

.spawn-modal-footer .el-button:hover:not(:disabled) {
  background: linear-gradient(145deg, #b22222 0%, #8b0000 100%);
  box-shadow: 0 0 30px rgba(255, 215, 0, 0.5);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #888;
}

.loading-icon {
  font-size: 40px;
  color: #ffd700;
  animation: spin 1s linear infinite;
  margin-bottom: 15px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 药水BUFF显示区 */
.pills-buff-section {
  margin: 12px 0;
  padding: 12px;
  background: rgba(30, 30, 40, 0.6);
  border: 1px solid #3D3D3D;
  border-radius: 8px;
}

.buff-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.buff-title {
  font-size: 14px;
  font-weight: bold;
  color: #d4a464;
}

.buff-count {
  font-size: 12px;
  color: #888;
}

.buff-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.buff-card {
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  min-width: 140px;
}

.buff-positive {
  background: rgba(76, 175, 80, 0.1);
  border: 1px solid rgba(76, 175, 80, 0.3);
}

.buff-debuff {
  background: rgba(244, 67, 54, 0.1);
  border: 1px solid rgba(244, 67, 54, 0.3);
}

.buff-name {
  font-weight: bold;
  color: #e8e0d0;
  margin-bottom: 4px;
}

.buff-effects {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}

.buff-effects .buff { color: #4caf50; }
.buff-effects .debuff { color: #f44336; }

.buff-timer {
  color: #888;
  font-size: 11px;
}

.time-remaining {
  font-family: monospace;
}

/* 制作tab子tab通用 */
.crafting-subtab {
  padding: 8px 0;
}

/* 狩猎 */
.hunting-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.wildlife-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(20, 20, 35, 0.9);
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  transition: border-color 0.2s;
}

.wildlife-card:hover {
  border-color: #d4a464;
}

.wildlife-icon {
  font-size: 36px;
}

.wildlife-details h3 {
  margin: 0;
  color: #e8e0d0;
  font-size: 14px;
}

.tier-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  margin-left: 6px;
}

.tier-common { background: rgba(150, 150, 150, 0.3); color: #aaa; }
.tier-advanced { background: rgba(76, 175, 80, 0.3); color: #4caf50; }
.tier-rare { background: rgba(33, 150, 243, 0.3); color: #2196f3; }
.tier-boss { background: rgba(255, 152, 0, 0.3); color: #ff9800; }

.wildlife-desc {
  color: #888;
  font-size: 12px;
  margin: 4px 0;
}

.wildlife-drops {
  font-size: 11px;
  color: #aaa;
}

.drop-item {
  margin-right: 6px;
}

.wildlife-rewards {
  display: flex;
  gap: 8px;
  font-size: 11px;
  margin-top: 4px;
}

.reward.exp { color: #ffd700; }
.reward.gold { color: #d4a464; }

/* 采集 */
.gathering-info {
  margin-bottom: 16px;
  padding: 12px;
  background: rgba(20, 20, 35, 0.9);
  border: 1px solid #2a2a3e;
  border-radius: 8px;
}

.gathering-info p {
  margin: 4px 0;
  color: #aaa;
  font-size: 13px;
}

/* 饰品制作 */
.accessory-crafting {
  padding: 16px;
  background: rgba(20, 20, 35, 0.9);
  border: 1px solid #2a2a3e;
  border-radius: 8px;
}
</style>
