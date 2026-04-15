import { defineStore } from 'pinia'

const STORAGE_KEY = 'qikan_player_logs'
const MAX_LOGS = 300

const LOG_TYPE_MAP = {
  cultivate: { type: 'cultivate', icon: '🧘' },
  adventure: { type: 'combat', icon: '⚔️' },
  checkin: { type: 'system', icon: '📅' },
  heal: { type: 'system', icon: '💊' },
  heal_troops: { type: 'system', icon: '💊' },
  start_afk: { type: 'system', icon: '💤' },
  cancel_afk: { type: 'system', icon: '⏹️' },
  collect_afk: { type: 'reward', icon: '🎁' },
  collect_industry_income: { type: 'reward', icon: '💰' },
  equip: { type: 'equip', icon: '🛡️' },
  unequip: { type: 'equip', icon: '📦' },
  use_item: { type: 'item', icon: '💊' },
  shop_buy: { type: 'trade', icon: '🛒' },
  market_buy: { type: 'trade', icon: '🏪' },
  market_list: { type: 'trade', icon: '📤' },
  market_cancel: { type: 'trade', icon: '❌' },
  market_clear_history: { type: 'trade', icon: '🗑️' },
  recycle: { type: 'trade', icon: '♻️' },
  trade_buy: { type: 'trade', icon: '💳' },
  trade_sell: { type: 'trade', icon: '💵' },
  enter_location: { type: 'travel', icon: '🏰' },
  leave_location: { type: 'travel', icon: '🚶' },
  rest_at_settlement: { type: 'travel', icon: '🍺' },
  map_travel: { type: 'travel', icon: '🗺️' },
  map_arrive: { type: 'travel', icon: '📍' },
  build_industry: { type: 'travel', icon: '🏗️' },
  upgrade_industry: { type: 'travel', icon: '⬆️' },
  repair_industry: { type: 'travel', icon: '🔧' },
  start_npc_dialog: { type: 'social', icon: '💬' },
  give_gift_to_npc: { type: 'social', icon: '🎁' },
  allocate_attribute_points: { type: 'cultivate', icon: '⭐' },
  allocate_skill_points: { type: 'cultivate', icon: '📜' },
  breakthrough: { type: 'cultivate', icon: '🔥' },
  learn_heart_method: { type: 'cultivate', icon: '📖' },
  forget_gongfa: { type: 'cultivate', icon: '📓' },
  sect_create: { type: 'social', icon: '🏛️' },
  sect_join: { type: 'social', icon: '🤝' },
  sect_leave: { type: 'social', icon: '🚪' },
  sect_kick: { type: 'social', icon: '👢' },
  sect_set_role: { type: 'social', icon: '📋' },
  sect_update_info: { type: 'social', icon: '✏️' },
  sect_transfer: { type: 'social', icon: '🔄' },
  sect_disband: { type: 'social', icon: '💥' },
  sect_warehouse_deposit: { type: 'social', icon: '📥' },
  sect_warehouse_exchange: { type: 'social', icon: '🔁' },
  sect_set_submit_rule: { type: 'social', icon: '📜' },
  sect_set_exchange_rule: { type: 'social', icon: '📜' },
  sect_accept_task: { type: 'system', icon: '📋' },
  sect_create_task: { type: 'system', icon: '📋' },
  sect_update_task_progress: { type: 'system', icon: '📝' },
  sect_cancel_task: { type: 'system', icon: '❌' },
  travel: { type: 'travel', icon: '🗺️' },
  combat: { type: 'combat', icon: '⚔️' },
  gathering: { type: 'gather', icon: '🌿' },
  gather_herbs: { type: 'gather', icon: '🌿' },
  hunting: { type: 'combat', icon: '🏹' },
  hunt_wildlife: { type: 'combat', icon: '🏹' },
  crafting: { type: 'system', icon: '🔨' },
  craft_item: { type: 'system', icon: '🔨' },
  craft_accessory: { type: 'system', icon: '💍' },
  forging: { type: 'system', icon: '⚒️' },
  forge_item: { type: 'system', icon: '⚒️' },
  buy_forging_material: { type: 'system', icon: '🧱' },
  blacksmith_repair: { type: 'system', icon: '🔨' },
  blacksmith_enhance: { type: 'system', icon: '✨' },
  reset_player: { type: 'system', icon: '🔄' },
  set_spawn_origin: { type: 'system', icon: '🎭' },
  confirm_replace_heart_method: { type: 'cultivate', icon: '✅' },
  use_heal_skill: { type: 'system', icon: '💖' },
  dungeon_start: { type: 'combat', icon: '🚪' },
  dungeon_advance: { type: 'combat', icon: '➡️' },
  dungeon_combat: { type: 'combat', icon: '⚔️' },
  dungeon_exit: { type: 'combat', icon: '🚪' },
  pvp_action: { type: 'combat', icon: '🤺' },
  pvp_challenge_response: { type: 'combat', icon: '🤝' },
  pvp_flee_offer: { type: 'combat', icon: '🏃' },
  pvp_flee_response: { type: 'combat', icon: '✅' },
  tournament_combat: { type: 'combat', icon: '🏟️' },
  death_confirm_keep: { type: 'system', icon: '💎' },
}

const DEFAULT_LOG_TYPE = { type: 'system', icon: '🔧' }

export const useLogStore = defineStore('log', {
  state: () => ({
    logs: [],
    filter: 'all',
  }),

  getters: {
    filteredLogs: (state) => {
      if (state.filter === 'all') return state.logs
      return state.logs.filter(l => l.type === state.filter)
    },
  },

  actions: {
    init() {
      try {
        const stored = localStorage.getItem(STORAGE_KEY)
        if (stored) {
          this.logs = JSON.parse(stored)
        }
      } catch (e) {
        console.error('Failed to load logs:', e)
        this.logs = []
      }
    },

    getActionLogType(action) {
      return LOG_TYPE_MAP[action]?.type || DEFAULT_LOG_TYPE.type
    },

    getActionLogIcon(action) {
      return LOG_TYPE_MAP[action]?.icon || DEFAULT_LOG_TYPE.icon
    },

    addLog(entry, rawData = null) {
      let content = entry.content || ''
      let title = entry.title || ''

      if (rawData) {
        if (rawData.location && rawData.location.name) {
          content = `进入 ${rawData.location.name}`
          if (rawData.npcs && rawData.npcs.length > 0) {
            const npcNames = rawData.npcs.map(n => n.name).join('、')
            content += `，遇到 ${npcNames}`
          }
        } else if (rawData.message) {
          const msg = rawData.message
          const itemMatch = msg.match(/【(.+?)】/g)
          if (itemMatch) {
            const items = itemMatch.join('、')
            if (!title && entry.action) {
              title = entry.action
            }
            const actionName = this.getActionLogTitle(entry.action)
            content = actionName ? `${actionName}: ${msg}` : msg
          } else {
            content = msg
          }
        }

        if (entry.type === 'travel' && rawData.message && !content) {
          content = rawData.message
        }
      }

      if (!title && entry.action) {
        title = this.getActionLogTitle(entry.action) || entry.action
      }

      const log = {
        id: Date.now() + '_' + Math.random().toString(36).substr(2, 5),
        timestamp: new Date().toISOString(),
        type: entry.type || 'system',
        icon: entry.icon || '🔧',
        title: title,
        content: content || '操作成功',
        action: entry.action,
        ...entry,
      }

      this.logs.unshift(log)
      if (this.logs.length > MAX_LOGS) {
        this.logs = this.logs.slice(0, MAX_LOGS)
      }

      this._save()
    },

    getActionLogTitle(action) {
      const titles = {
        cultivate: '修炼',
        adventure: '征战',
        checkin: '签到',
        heal: '治疗',
        heal_troops: '治疗部队',
        start_afk: '开始驻守',
        cancel_afk: '取消驻守',
        collect_afk: '结算驻守',
        collect_industry_income: '收取产出',
        equip: '装备',
        unequip: '卸下装备',
        use_item: '使用物品',
        shop_buy: '商店购买',
        market_buy: '市场购买',
        market_list: '上架商品',
        market_cancel: '取消上架',
        market_clear_history: '清空历史',
        recycle: '回收物品',
        trade_buy: '交易购买',
        trade_sell: '交易出售',
        enter_location: '进入地点',
        leave_location: '离开地点',
        rest_at_settlement: '休息',
        map_travel: '地图移动',
        map_arrive: '抵达',
        build_industry: '建造建筑',
        upgrade_industry: '升级建筑',
        repair_industry: '修复建筑',
        start_npc_dialog: '对话',
        give_gift_to_npc: '送礼',
        allocate_attribute_points: '分配属性点',
        allocate_skill_points: '分配技能点',
        breakthrough: '突破境界',
        learn_heart_method: '学习心法',
        forget_gongfa: '遗忘战技',
        sect_create: '创建家族',
        sect_join: '加入家族',
        sect_leave: '离开家族',
        sect_kick: '踢出家族',
        sect_set_role: '设置职位',
        sect_update_info: '更新家族',
        sect_transfer: '转让家族',
        sect_disband: '解散家族',
        sect_warehouse_deposit: '仓库存入',
        sect_warehouse_exchange: '仓库兑换',
        sect_set_submit_rule: '设置贡献规则',
        sect_set_exchange_rule: '设置兑换规则',
        sect_accept_task: '接受任务',
        sect_create_task: '创建任务',
        sect_update_task_progress: '更新任务',
        sect_cancel_task: '取消任务',
        travel: '移动',
        combat: '战斗',
        gathering: '采集',
        gather_herbs: '采药',
        hunting: '狩猎',
        hunt_wildlife: '狩猎',
        crafting: '制作',
        craft_item: '制作物品',
        craft_accessory: '制作饰品',
        forging: '锻造',
        forge_item: '锻造物品',
        buy_forging_material: '购买材料',
        blacksmith_repair: '铁匠修复',
        blacksmith_enhance: '铁匠强化',
        reset_player: '重置角色',
        set_spawn_origin: '设置出生点',
        confirm_replace_heart_method: '替换心法',
        use_heal_skill: '使用治疗',
        dungeon_start: '进入副本',
        dungeon_advance: '推进副本',
        dungeon_combat: '副本战斗',
        dungeon_exit: '离开副本',
        pvp_action: 'PVP战斗',
        pvp_challenge_response: 'PVP应战',
        pvp_flee_offer: 'PVP求和',
        pvp_flee_response: 'PVP和谈',
        tournament_combat: '比武战斗',
        death_confirm_keep: '道陨保物',
      }
      return titles[action] || action
    },

    clearLogs() {
      this.logs = []
      this._save()
    },

    setFilter(filter) {
      this.filter = filter
    },

    _save() {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(this.logs))
      } catch (e) {
        console.error('Failed to save logs:', e)
      }
    },
  },
})
