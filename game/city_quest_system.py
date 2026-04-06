"""
城市任务系统 - 镇长任务

玩家可以通过贿赂/请求从城镇镇长处获取任务
任务类型与现有游戏系统紧密结合
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import IntEnum
from .map_system import Faction, Location, TOWNS, VILLAGES
from .constants import ITEM_REGISTRY, EQUIPMENT_REGISTRY


class CityQuestType(IntEnum):
    """城市任务类型"""
    # 战斗类
    BANDIT_CLEAR = 1          # 讨伐劫匪
    BOSS_CHALLENGE = 2        # 讨伐BOSS
    DUNGEON_EXPLORE = 3       # 副本探索
    
    # 收集类
    ITEM_COLLECT = 10         # 收集物品
    RESOURCE_GATHER = 11      # 采集资源
    
    # 贸易类
    TRADE_MISSION = 20         # 贸易任务
    ESCORT_MERCHANT = 21       # 护送商人
    
    # 社交类
    FAMILY_TASK = 30           # 家族任务
    PvP_CHALLENGE = 31        # 竞技挑战
    
    # 特殊类
    LEGENDARY_BOUNTY = 50     # 传奇赏金


@dataclass
class CityQuest:
    """城市任务定义"""
    quest_id: str
    name: str
    description: str
    icon: str
    quest_type: int
    
    # 任务要求
    min_level: int = 1
    required_faction: Optional[int] = None  # 需要的阵营声望
    
    # 任务目标
    target_type: str  # "bandit", "boss", "dungeon", "item", "trade", "pvp"
    target_id: str = ""
    target_count: int = 1
    
    # 奖励
    exp_reward: int = 100
    gold_reward: int = 100
    reputation_reward: Dict[int, int] = field(default_factory=dict)  # {faction: value}
    item_rewards: List[str] = field(default_factory=list)  # 物品ID列表
    
    # 消耗
    quest_points_cost: int = 0  # 任务点数消耗
    cooldown_hours: int = 0    # 冷却时间


# 任务模板生成器
def generate_bandit_quest(location: Location, difficulty: int = 1) -> CityQuest:
    """生成讨伐劫匪任务"""
    bandit_types = {
        1: ("mountain_weak", "山贼"),
        2: ("forest_weak", "森林盗匪"),
        3: ("desert_bandit", "沙漠盗贼"),
        4: ("mountain_strong", "精锐山贼"),
        5: ("forest_strong", "绿林精锐"),
    }
    target, name = bandit_types.get(difficulty, ("mountain_weak", "山贼"))
    
    exp = 100 * difficulty
    gold = 50 * difficulty
    
    return CityQuest(
        quest_id=f"quest_bandit_{location.location_id}_{difficulty}",
        name=f"讨伐{name}",
        description=f"镇长请求你击败在{location.name}附近的{difficulty}伙{name}",
        icon="⚔️",
        quest_type=CityQuestType.BANDIT_CLEAR,
        min_level=difficulty * 3,
        target_type="bandit",
        target_id=target,
        target_count=difficulty * 3,
        exp_reward=exp,
        gold_reward=gold,
    )


def generate_item_collect_quest(location: Location, difficulty: int = 1) -> CityQuest:
    """生成物品收集任务"""
    items_by_difficulty = {
        1: [("grain", "谷物"), ("wood", "木材"), ("iron", "铁矿石")],
        2: [("silver", "银矿石"), ("cloth", "丝绸"), ("herb", "草药")],
        3: [("magic_stone", "魔法石"), ("gold", "金矿石"), ("gem", "宝石")],
        4: [("dragon_scale", "龙鳞"), ("phoenix_feather", "凤凰羽"), ("unicorn_horn", "独角")],
        5: [("legendary_ore", "传奇矿石"), ("ancient_relic", "古神遗物"), ("demon_crystal", "恶魔结晶")],
    }
    
    items = items_by_difficulty.get(difficulty, items_by_difficulty[1])
    item_id, item_name = items[difficulty % len(items)]
    
    count = difficulty * 5
    exp = 80 * difficulty
    gold = 40 * difficulty
    
    return CityQuest(
        quest_id=f"quest_collect_{location.location_id}_{difficulty}",
        name=f"收集{item_name}",
        description=f"镇长需要{count}个{item_name}，用于城镇建设",
        icon="📦",
        quest_type=CityQuestType.ITEM_COLLECT,
        min_level=difficulty * 2,
        target_type="item",
        target_id=item_id,
        target_count=count,
        exp_reward=exp,
        gold_reward=gold,
    )


def generate_trade_quest(location: Location, difficulty: int = 1) -> CityQuest:
    """生成贸易任务"""
    # 根据城镇特产生成不同贸易商品
    trade_goods = {
        "town_suno": ("wine", "葡萄酒"),
        "town_reyvadin": ("weapon", "武器"),
        "town_curin": ("iron", "铁矿"),
        "town_jelkala": ("silk", "丝绸"),
        "town_yalen": ("spice", "香料"),
    }
    
    goods_id, goods_name = trade_goods.get(location.location_id, ("grain", "货物"))
    
    count = difficulty * 10
    profit = difficulty * 100
    
    return CityQuest(
        quest_id=f"quest_trade_{location.location_id}_{difficulty}",
        name=f"贸易任务：{goods_name}",
        description=f"将{count}单位{goods_name}从{location.name}运往其他城镇出售",
        icon="💰",
        quest_type=CityQuestType.TRADE_MISSION,
        min_level=difficulty * 2,
        target_type="trade",
        target_id=goods_id,
        target_count=count,
        gold_reward=profit,
        exp_reward=50 * difficulty,
    )


def generate_dungeon_quest(location: Location, difficulty: int = 1) -> CityQuest:
    """生成副本探索任务"""
    dungeons = {
        1: ("ancient_ruins", "古代遗迹", "⚱️"),
        2: ("abandoned_mine", "废弃矿洞", "⛏️"),
        3: ("bandit_stronghold", "盗贼营地", "🏰"),
        4: ("dragon_lair", "巨龙巢穴", "🐉"),
        5: ("demon_temple", "恶魔神殿", "👹"),
    }
    
    dungeon_id, dungeon_name, icon = dungeons.get(difficulty, dungeons[1])
    
    exp = 200 * difficulty
    gold = 100 * difficulty
    
    return CityQuest(
        quest_id=f"quest_dungeon_{location.location_id}_{difficulty}",
        name=f"探索{dungeon_name}",
        description=f"探索位于{location.name}附近的{dungeon_name}，击败首脑",
        icon=icon,
        quest_type=CityQuestType.DUNGEON_EXPLORE,
        min_level=difficulty * 5,
        target_type="dungeon",
        target_id=dungeon_id,
        target_count=1,
        exp_reward=exp,
        gold_reward=gold,
    )


def generate_pvp_quest(location: Location, difficulty: int = 1) -> CityQuest:
    """生成竞技挑战任务"""
    arena_types = {
        1: ("duel", "单挑"),
        2: ("group_battle", "group战"),
        3: ("siege", "攻城战"),
    }
    
    arena_type, arena_name = arena_types.get(difficulty, arena_types[1])
    
    exp = 150 * difficulty
    gold = 80 * difficulty
    
    return CityQuest(
        quest_id=f"quest_pvp_{location.location_id}_{difficulty}",
        name=f"竞技场：{arena_name}",
        description=f"在{location.name}的竞技场赢得{arena_name}比赛",
        icon="🏟️",
        quest_type=CityQuestType.PvP_CHALLENGE,
        min_level=difficulty * 4,
        target_type="pvp",
        target_id=arena_type,
        target_count=1,
        exp_reward=exp,
        gold_reward=gold,
    )


def generate_legendary_bounty_quest(location: Location) -> Optional[CityQuest]:
    """生成传奇赏金任务（需要20级）"""
    # 根据城镇阵营对应传奇BOSS
    boss_mapping = {
        0: ("boss_lord", "黑爵士", "👑"),       # 斯瓦迪亚
        1: ("boss_viking", "海尔伯格", "☠️"),   # 诺德
        2: ("boss_forest", "格林", "🌲"),        # 维吉亚
        3: ("boss_mountain", "巨石", "⛰️"),      # 罗多克
        4: ("boss_nomad", "铁木真", "🐎"),       # 库吉特
    }
    
    faction = location.faction
    boss_id, boss_name, icon = boss_mapping.get(faction, boss_mapping[0])
    
    return CityQuest(
        quest_id=f"quest_legendary_{location.location_id}",
        name=f"传奇赏金：{boss_name}",
        description=f"镇长发布高额赏金，讨伐为祸一方的{boss_name}",
        icon=icon,
        quest_type=CityQuestType.LEGENDARY_BOUNTY,
        min_level=20,
        required_faction=faction,
        target_type="legendary_boss",
        target_id=boss_id,
        target_count=1,
        exp_reward=2000,
        gold_reward=5000,
        reputation_reward={faction: 50},
    )


def generate_all_quests_for_town(location: Location) -> List[CityQuest]:
    """为城镇生成所有可用任务"""
    quests = []
    
    # 讨伐任务 3个难度
    for diff in range(1, 4):
        quests.append(generate_bandit_quest(location, diff))
    
    # 收集任务 3个难度
    for diff in range(1, 4):
        quests.append(generate_item_collect_quest(location, diff))
    
    # 贸易任务 2个难度
    for diff in range(1, 3):
        quests.append(generate_trade_quest(location, diff))
    
    # 副本任务 2个难度
    for diff in range(1, 3):
        quests.append(generate_dungeon_quest(location, diff))
    
    # 竞技任务 2个难度
    for diff in range(1, 3):
        quests.append(generate_pvp_quest(location, diff))
    
    # 传奇赏金（20级）
    quests.append(generate_legendary_bounty_quest(location))
    
    return quests


# 城镇任务NPC配置
TOWN_QUEST_GIVERS = {
    "town_suno": {
        "name": "镇长海尔姆",
        "title": "苏诺城镇长",
        "description": "一位睿智的长者，管理着这座商业城市",
    },
    "town_reyvadin": {
        "name": "镇长格伦",
        "title": "瑞瓦迪恩军事长官",
        "description": "曾经的骑士团长，现在是城镇的军事负责人",
    },
    "town_curin": {
        "name": "镇长布朗",
        "title": "库里姆矿业主",
        "description": "掌握着罗多克王国的矿业命脉",
    },
    "town_jelkala": {
        "name": "镇长伊莎贝拉",
        "title": "贾尔卡拉女爵",
        "description": "罗多克王国的贵族，负责首都事务",
    },
    "town_yalen": {
        "name": "镇长穆罕默德",
        "title": "亚伦香料商人",
        "description": "萨兰德苏丹国的商业巨头",
    },
    "town_pravend": {
        "name": "镇长皮埃尔",
        "title": "普拉文德葡萄酒商",
        "description": "斯瓦迪亚的葡萄酒贸易商人",
    },
    "town_dhirim": {
        "name": "镇长凯恩",
        "title": "迪林姆执政官",
        "description": "管理着斯瓦迪亚的农业中心",
    },
    "town_uxkhal": {
        "name": "镇长帖木儿",
        "title": "乌克斯哈尔部落首领",
        "description": "库吉特汗国的草原部落首领",
    },
    "town_sargoth": {
        "name": "镇长奥拉夫",
        "title": "萨戈斯港口守卫",
        "description": "诺德王国的港口城市管理者",
    },
}


def get_quest_giver_info(location_id: str) -> dict:
    """获取城镇任务发布者信息"""
    return TOWN_QUEST_GIVERS.get(location_id, {
        "name": "镇长",
        "title": "城镇长官",
        "description": "负责发布城镇任务",
    })


def get_available_quests(location_id: str, player_level: int, player_favor: int = 0) -> List[dict]:
    """获取城镇可用任务列表，根据好感度过滤。"""
    location = TOWNS.get(location_id)
    if not location:
        return []
    
    all_quests = generate_all_quests_for_town(location)
    
    # 过滤符合玩家等级和好感度的任务
    available = []
    for quest in all_quests:
        if player_level >= quest.min_level:
            # 好感度决定可接任务的难度范围
            quest_favor_threshold = quest.min_level * 5  # 每级需要5点好感
            if player_favor >= quest_favor_threshold or quest.min_level <= 3:
                available.append({
                    "quest_id": quest.quest_id,
                    "name": quest.name,
                    "description": quest.description,
                    "icon": quest.icon,
                    "quest_type": CityQuestType(quest.quest_type).name,
                    "min_level": quest.min_level,
                    "target_type": quest.target_type,
                    "target_id": quest.target_id,
                    "target_count": quest.target_count,
                    "exp_reward": quest.exp_reward,
                    "gold_reward": quest.gold_reward,
                    "required_favor": quest_favor_threshold,
                })
    
    return available


# 任务进度跟踪
class CityQuestProgress:
    def __init__(self):
        self.active_quests: Dict[str, dict] = {}  # {quest_id: {progress, start_time}}
    
    def accept_quest(self, quest_id: str, player_id: str) -> bool:
        key = f"{player_id}:{quest_id}"
        if key in self.active_quests:
            return False
        self.active_quests[key] = {
            "progress": 0,
            "start_time": __import__("time").time(),
            "status": "in_progress",
        }
        return True
    
    def update_progress(self, player_id: str, quest_id: str, progress: int) -> bool:
        key = f"{player_id}:{quest_id}"
        if key not in self.active_quests:
            return False
        self.active_quests[key]["progress"] = progress
        return True
    
    def complete_quest(self, player_id: str, quest_id: str) -> Optional[dict]:
        key = f"{player_id}:{quest_id}"
        if key not in self.active_quests:
            return None
        quest_data = self.active_quests.pop(key)
        return quest_data
    
    def get_progress(self, player_id: str, quest_id: str) -> Optional[dict]:
        key = f"{player_id}:{quest_id}"
        return self.active_quests.get(key)


city_quest_progress = CityQuestProgress()
