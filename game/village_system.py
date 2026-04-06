"""
村庄好感系统 - 骑砍英雄传

通过完成村庄任务提升好感度，好感度决定可建造产业等权限。
"""

from __future__ import annotations

import time
import random
from dataclasses import dataclass, field
from typing import Optional


# ══════════════════════════════════════════════════════════════
# 名望等级配置
# ══════════════════════════════════════════════════════════════

@dataclass
class FameLevel:
    """名望等级定义。"""
    name: str                    # 等级名称
    min_fame: int               # 最低名望值
    max_favor: int              # 可达到的最高好感度
    can_visit: bool             # 能否拜访头人
    can_quest: bool             # 能否接任务


FAME_LEVELS: list[FameLevel] = [
    FameLevel(name="平民", min_fame=0, max_favor=0, can_visit=False, can_quest=False),
    FameLevel(name="游历者", min_fame=100, max_favor=20, can_visit=True, can_quest=False),
    FameLevel(name="冒险者", min_fame=300, max_favor=40, can_visit=True, can_quest=True),
    FameLevel(name="侠客", min_fame=600, max_favor=60, can_visit=True, can_quest=True),
    FameLevel(name="领主", min_fame=1000, max_favor=80, can_visit=True, can_quest=True),
    FameLevel(name="侯爵", min_fame=2000, max_favor=100, can_visit=True, can_quest=True),
]


def get_fame_level(fame: int) -> FameLevel:
    """根据名望值获取名望等级。"""
    current = FAME_LEVELS[0]
    for level in FAME_LEVELS:
        if fame >= level.min_fame:
            current = level
        else:
            break
    return current


def get_fame_display(fame: int) -> dict:
    """获取名望显示信息。"""
    level = get_fame_level(fame)
    next_level = None
    for i, l in enumerate(FAME_LEVELS):
        if l.min_fame > level.min_fame:
            next_level = l
            break
    
    result = {
        "level_name": level.name,
        "fame": fame,
        "min_fame": level.min_fame,
        "max_favor": level.max_favor,
        "can_visit": level.can_visit,
        "can_quest": level.can_quest,
        "next_level": None,
    }
    
    if next_level:
        result["next_level"] = {
            "name": next_level.name,
            "required_fame": next_level.min_fame,
            "progress": int((fame - level.min_fame) / (next_level.min_fame - level.min_fame) * 100),
        }
    
    return result


# ══════════════════════════════════════════════════════════════
# 村庄任务定义
# ══════════════════════════════════════════════════════════════

@dataclass
class VillageQuest:
    """村庄任务定义。"""
    quest_id: str
    name: str
    description: str
    difficulty: str                    # easy / normal / hard / legendary
    min_fame: int                     # 所需最低名望
    min_favor: int                    # 所需最低好感
    gold_reward: int                  # 第纳尔奖励
    favor_reward: int                 # 好感奖励
    requires_combat: bool = False      # 是否需要战斗
    requires_time: int = 0            # 需要等待秒数（0表示即时）
    requires_materials: list = field(default_factory=list)  # 所需材料 [(item_id, count)]


VILLAGE_QUESTS: list[VillageQuest] = [
    # 简单任务
    VillageQuest(
        quest_id="quest_deliver_letter",
        name="送信",
        description="帮头人将信件送到附近的城镇",
        difficulty="easy",
        min_fame=100,
        min_favor=20,
        gold_reward=50,
        favor_reward=3,
    ),
    VillageQuest(
        quest_id="quest_shopping",
        name="采购物资",
        description="去城镇采购村庄急需的物资",
        difficulty="easy",
        min_fame=100,
        min_favor=25,
        gold_reward=80,
        favor_reward=4,
    ),
    VillageQuest(
        quest_id="quest_escort_caravan",
        name="护送商队",
        description="护送商队安全通过危险路段",
        difficulty="easy",
        min_fame=150,
        min_favor=25,
        gold_reward=100,
        favor_reward=5,
    ),
    VillageQuest(
        quest_id="quest_find_livestock",
        name="寻找走失家畜",
        description="帮村民找回走失的牛羊",
        difficulty="easy",
        min_fame=100,
        min_favor=30,
        gold_reward=60,
        favor_reward=3,
    ),
    # 普通任务
    VillageQuest(
        quest_id="quest_clear_bandits",
        name="清剿匪患",
        description="消灭骚扰村庄的劫匪",
        difficulty="normal",
        min_fame=300,
        min_favor=40,
        gold_reward=200,
        favor_reward=5,
        requires_combat=True,
    ),
    VillageQuest(
        quest_id="quest_resolve_dispute",
        name="调解纠纷",
        description="调解村民之间的矛盾纠纷",
        difficulty="normal",
        min_fame=300,
        min_favor=45,
        gold_reward=180,
        favor_reward=6,
    ),
    VillageQuest(
        quest_id="quest_guard_village",
        name="守卫村庄",
        description="在村口守卫一天",
        difficulty="normal",
        min_fame=350,
        min_favor=45,
        gold_reward=250,
        favor_reward=7,
        requires_time=300,
    ),
    VillageQuest(
        quest_id="quest_transport_goods",
        name="运送货物",
        description="帮忙运送货物到城镇",
        difficulty="normal",
        min_fame=400,
        min_favor=50,
        gold_reward=300,
        favor_reward=8,
    ),
    # 困难任务
    VillageQuest(
        quest_id="quest_defeat_leader",
        name="驱逐强盗首领",
        description="击败盘踞在附近的强盗首领",
        difficulty="hard",
        min_fame=600,
        min_favor=60,
        gold_reward=500,
        favor_reward=10,
        requires_combat=True,
    ),
    VillageQuest(
        quest_id="quest_build_defense",
        name="修建防御工事",
        description="帮助村庄修建防御设施",
        difficulty="hard",
        min_fame=600,
        min_favor=65,
        gold_reward=400,
        favor_reward=12,
    ),
    VillageQuest(
        quest_id="quest_train_militia",
        name="培训民兵",
        description="帮助村庄训练民兵队伍",
        difficulty="hard",
        min_fame=700,
        min_favor=65,
        gold_reward=350,
        favor_reward=15,
        requires_time=600,
    ),
    VillageQuest(
        quest_id="quest_diplomacy",
        name="外交斡旋",
        description="帮助村庄处理与其他势力的外交事务",
        difficulty="hard",
        min_fame=800,
        min_favor=70,
        gold_reward=600,
        favor_reward=18,
    ),
    # 传奇任务
    VillageQuest(
        quest_id="quest_repel_invasion",
        name="抵御大军压境",
        description="组织村民抵御来袭的军队",
        difficulty="legendary",
        min_fame=1000,
        min_favor=80,
        gold_reward=1000,
        favor_reward=20,
        requires_combat=True,
    ),
    VillageQuest(
        quest_id="quest_revive_village",
        name="复兴村庄繁荣",
        description="帮助村庄恢复往日繁荣",
        difficulty="legendary",
        min_fame=1000,
        min_favor=85,
        gold_reward=800,
        favor_reward=25,
    ),
    VillageQuest(
        quest_id="quest_unite_villages",
        name="联合诸村联盟",
        description="促成周边村庄结成联盟",
        difficulty="legendary",
        min_fame=1500,
        min_favor=90,
        gold_reward=1500,
        favor_reward=30,
    ),
]


def get_quests_for_player(fame: int, favor: int, difficulty: str | None = None) -> list[VillageQuest]:
    """根据玩家名望和好感获取可接任务。"""
    available = []
    for quest in VILLAGE_QUESTS:
        if fame >= quest.min_fame and favor >= quest.min_favor:
            if difficulty is None or quest.difficulty == difficulty:
                available.append(quest)
    return available


def get_quests_by_favor_range(min_favor: int, max_favor: int) -> dict[str, list[VillageQuest]]:
    """按难度分组获取任务。"""
    result = {"easy": [], "normal": [], "hard": [], "legendary": []}
    for quest in VILLAGE_QUESTS:
        if min_favor <= quest.min_favor <= max_favor:
            result[quest.difficulty].append(quest)
    return result


# ══════════════════════════════════════════════════════════════
# 每日任务
# ══════════════════════════════════════════════════════════════

@dataclass
class DailyQuest:
    """每日任务定义。"""
    quest_id: str
    name: str
    description: str
    gold_reward: int
    favor_reward: int
    quest_type: str                 # farm / patrol / trade


DAILY_QUESTS: list[DailyQuest] = [
    DailyQuest(
        quest_id="daily_farm_work",
        name="帮助农活",
        description="帮村民干一天的农活",
        gold_reward=30,
        favor_reward=2,
        quest_type="farm",
    ),
    DailyQuest(
        quest_id="daily_patrol",
        name="巡视边界",
        description="巡视村庄周边安全",
        gold_reward=40,
        favor_reward=2,
        quest_type="patrol",
    ),
    DailyQuest(
        quest_id="daily_shop",
        name="购买特产",
        description="购买村庄特产支持经济",
        gold_reward=50,
        favor_reward=1,
        quest_type="trade",
    ),
]


# ══════════════════════════════════════════════════════════════
# 每周任务
# ══════════════════════════════════════════════════════════════

@dataclass
class WeeklyQuest:
    """每周任务定义。"""
    quest_id: str
    name: str
    description: str
    min_fame: int
    gold_reward: int
    favor_reward: int


WEEKLY_QUESTS: list[WeeklyQuest] = [
    WeeklyQuest(
        quest_id="weekly_market_guard",
        name="集市日守卫",
        description="在村庄集市日维持秩序",
        min_fame=300,
        gold_reward=500,
        favor_reward=10,
    ),
    WeeklyQuest(
        quest_id="weekly_harvest",
        name="丰收节庆典",
        description="协助举办丰收节庆典",
        min_fame=500,
        gold_reward=800,
        favor_reward=15,
    ),
    WeeklyQuest(
        quest_id="weekly_defense",
        name="村庄防御周",
        description="组织全村进行防御演习",
        min_fame=800,
        gold_reward=1200,
        favor_reward=20,
    ),
]


# ══════════════════════════════════════════════════════════════
# 礼物系统
# ══════════════════════════════════════════════════════════════

@dataclass
class GiftItem:
    """礼物物品定义。"""
    item_id: str
    name: str
    value: int                      # 第纳尔价值
    can_unlock_legendary: bool = False


GIFT_ITEMS: dict[str, GiftItem] = {
    # 普通礼物 (1-30第纳尔)
    "bread": GiftItem("bread", "面包", 5),
    "dried_meat": GiftItem("dried_meat", "肉干", 10),
    "dried_fish": GiftItem("dried_fish", "鱼干", 8),
    "grain": GiftItem("grain", "谷物", 5),
    "vegetables": GiftItem("vegetables", "蔬菜", 5),
    "eggs": GiftItem("eggs", "鸡蛋", 3),
    "butter": GiftItem("butter", "黄油", 8),
    # 中级礼物 (31-80第纳尔)
    "fresh_fish": GiftItem("fresh_fish", "鲜鱼", 35),
    "pickled_meat": GiftItem("pickled_meat", "腌肉", 40),
    "cheese": GiftItem("cheese", "奶酪", 45),
    "honey": GiftItem("honey", "蜂蜜", 50),
    "poultry": GiftItem("poultry", "家禽", 60),
    # 高级礼物 (81-150第纳尔)
    "wine": GiftItem("wine", "葡萄酒", 85),
    "wool": GiftItem("wool", "羊毛", 90),
    "spices": GiftItem("spices", "香料", 100),
    "silk": GiftItem("silk", "丝绸", 120),
    "furs": GiftItem("furs", "毛皮", 110),
    "dates": GiftItem("dates", "椰枣", 80),
    # 稀有礼物 (151+第纳尔)
    "horse": GiftItem("horse", "骏马", 200, can_unlock_legendary=True),
    "iron_sword": GiftItem("iron_sword", "铁剑", 180, can_unlock_legendary=True),
    "leather_armor": GiftItem("leather_armor", "皮甲", 160, can_unlock_legendary=True),
    "silver_item": GiftItem("silver_item", "银器", 250, can_unlock_legendary=True),
    "war_horse": GiftItem("war_horse", "战马", 400, can_unlock_legendary=True),
}


def calculate_gift_value(gift_ids: list[str]) -> int:
    """计算礼物总价值。"""
    total = 0
    for gift_id in gift_ids:
        gift = GIFT_ITEMS.get(gift_id)
        if gift:
            total += gift.value
    return total


def get_available_quests_for_gifts(gift_ids: list[str], player_fame: int) -> list[VillageQuest]:
    """根据礼物获取可接任务。"""
    total_value = calculate_gift_value(gift_ids)
    available = []
    
    for quest in VILLAGE_QUESTS:
        if player_fame < quest.min_fame:
            continue
        
        # 根据礼物价值决定可接任务难度
        if quest.difficulty == "easy" and total_value >= 1:
            available.append(quest)
        elif quest.difficulty == "normal" and total_value >= 31:
            available.append(quest)
        elif quest.difficulty == "hard" and total_value >= 81:
            available.append(quest)
        elif quest.difficulty == "legendary":
            # 传奇任务需要稀有礼物
            has_legendary = any(
                GIFT_ITEMS.get(gid, GiftItem("", "", 0, False)).can_unlock_legendary
                for gid in gift_ids
            )
            if has_legendary and total_value >= 151:
                available.append(quest)
    
    return available


def get_gift_category(gift_id: str) -> str:
    """获取礼物等级分类。"""
    gift = GIFT_ITEMS.get(gift_id)
    if not gift:
        return "unknown"
    value = gift.value
    if value <= 30:
        return "common"
    elif value <= 80:
        return "medium"
    elif value <= 150:
        return "advanced"
    else:
        return "rare"


def get_gift_suggestions(quest: VillageQuest) -> list[str]:
    """获取完成任务的建议礼物。"""
    if quest.difficulty == "easy":
        return ["bread", "dried_meat", "dried_fish", "grain"]
    elif quest.difficulty == "normal":
        return ["fresh_fish", "pickled_meat", "cheese", "honey", "poultry"]
    elif quest.difficulty == "hard":
        return ["wine", "wool", "spices", "silk", "furs"]
    else:  # legendary
        return ["horse", "iron_sword", "leather_armor", "silver_item", "war_horse"]


# ══════════════════════════════════════════════════════════════
# 玩家村庄状态
# ══════════════════════════════════════════════════════════════

@dataclass
class PlayerVillageState:
    """玩家在村庄的状态。"""
    user_id: str
    village_id: str
    favor: int = 0                          # 当前好感度
    total_quests_completed: int = 0          # 累计完成任务数
    last_interaction_time: float = 0         # 上次互动时间戳
    last_interaction_date: str = ""          # 上次互动日期 (YYYY-MM-DD)
    quest_history: list[str] = field(default_factory=list)  # 已完成任务ID
    
    # 每日任务状态
    daily_quests: list[str] = field(default_factory=list)  # 今日任务ID
    daily_completed: list[str] = field(default_factory=list)  # 今日已完成
    daily_reset_date: str = ""                # 上次重置日期
    
    # 每周任务状态
    weekly_quest: str = ""                   # 本周任务ID
    weekly_completed: bool = False            # 本周是否完成
    weekly_reset_week: int = 0              # 上次重置周数
    
    # 好感衰减记录
    decay_warning_shown: bool = False         # 是否已显示衰减警告


def get_village_state(player_states: dict, user_id: str, village_id: str) -> PlayerVillageState:
    """获取或创建玩家村庄状态。"""
    key = f"{user_id}_{village_id}"
    if key not in player_states:
        player_states[key] = PlayerVillageState(
            user_id=user_id,
            village_id=village_id,
        )
    return player_states[key]


def can_accept_quest(state: PlayerVillageState, quest: VillageQuest, player_fame: int) -> tuple[bool, str]:
    """检查是否可以接受任务。"""
    fame_level = get_fame_level(player_fame)
    
    if not fame_level.can_quest:
        return False, "你的名望不足，还不能接受任务"
    
    if state.favor < quest.min_favor:
        return False, f"好感度不足，需要 {quest.min_favor} 好感度才能接受此任务"
    
    if quest.quest_id in state.quest_history:
        return False, "你已经完成过这个任务"
    
    return True, ""


def can_visit(fame: int) -> tuple[bool, str]:
    """检查是否可以拜访头人。"""
    fame_level = get_fame_level(fame)
    
    if not fame_level.can_visit:
        return False, f"名望不足，需要达到 {fame_level.min_fame} 点名望才能拜访头人"
    
    return True, ""


def apply_favor_decay(state: PlayerVillageState, current_date: str) -> int:
    """应用好感衰减，返回衰减量。"""
    if state.favor <= 0:
        return 0
    
    if state.last_interaction_date == current_date:
        return 0
    
    days_since = 0
    if state.last_interaction_date:
        try:
            parts = state.last_interaction_date.split("-")
            last_y, last_m, last_d = int(parts[0]), int(parts[1]), int(parts[2])
            cur_parts = current_date.split("-")
            cur_y, cur_m, cur_d = int(cur_parts[0]), int(cur_parts[1]), int(cur_parts[2])
            
            days_last = last_y * 365 + last_m * 30 + last_d
            days_cur = cur_y * 365 + cur_m * 30 + cur_d
            days_since = days_cur - days_last
        except:
            days_since = 0
    
    if days_since >= 7:
        decay = min(state.favor, (days_since - 6))  # 最多衰减到0
        state.favor = max(0, state.favor - decay)
        return decay
    
    return 0


def refresh_daily_quests(state: PlayerVillageState, current_date: str, player_fame: int) -> list[DailyQuest]:
    """刷新每日任务。"""
    if state.daily_reset_date != current_date:
        state.daily_reset_date = current_date
        state.daily_quests = []
        state.daily_completed = []
        
        # 根据名望选择每日任务
        available = list(DAILY_QUESTS)
        selected = random.sample(available, min(3, len(available)))
        state.daily_quests = [q.quest_id for q in selected]
    
    return [q for q in DAILY_QUESTS if q.quest_id in state.daily_quests]


def refresh_weekly_quest(state: PlayerVillageState, current_week: int, player_fame: int) -> Optional[WeeklyQuest]:
    """刷新每周任务。"""
    if state.weekly_reset_week != current_week:
        state.weekly_reset_week = current_week
        state.weekly_completed = False
        
        # 根据名望选择每周任务
        available = [q for q in WEEKLY_QUESTS if player_fame >= q.min_fame]
        if available:
            state.weekly_quest = random.choice(available).quest_id
        else:
            state.weekly_quest = ""
    
    if not state.weekly_quest:
        return None
    
    return next((q for q in WEEKLY_QUESTS if q.quest_id == state.weekly_quest), None)


def get_current_week() -> int:
    """获取当前周数（用于每周任务刷新）。"""
    import datetime
    today = datetime.date.today()
    return today.isocalendar()[1] + today.year * 52


def get_favor_status(favor: int) -> tuple[str, str]:
    """获取好感状态描述。"""
    if favor < 20:
        return "陌生人", "冷漠"
    elif favor < 40:
        return "点头之交", "友善"
    elif favor < 60:
        return "熟悉", "欢迎"
    elif favor < 80:
        return "信任", "信任"
    else:
        return "支持者", "臣服"


def get_favor_benefits(favor: int) -> dict:
    """获取好感度对应的权益。"""
    benefits = {
        "can_buy": favor >= 20,
        "can_basic_quest": favor >= 40,
        "can_build_industry": favor >= 60,
        "can_control": favor >= 80,
    }
    
    descriptions = []
    if benefits["can_buy"]:
        descriptions.append("可购买基础商品")
    if benefits["can_basic_quest"]:
        descriptions.append("可接普通任务")
    if benefits["can_build_industry"]:
        descriptions.append("可建造产业")
    if benefits["can_control"]:
        descriptions.append("获得村庄支持")
    
    return {
        "benefits": benefits,
        "descriptions": descriptions,
        "next_threshold": next_threshold(favor),
    }


def next_threshold(favor: int) -> Optional[int]:
    """获取下一个阈值。"""
    thresholds = [20, 40, 60, 80, 100]
    for t in thresholds:
        if favor < t:
            return t
    return None
