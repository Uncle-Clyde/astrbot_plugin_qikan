"""
卡拉迪亚大陆地图系统 - Mount & Blade 风格

模拟骑砍的大地图系统，包含城镇、城堡、村庄等据点，
玩家可以在地图上移动、接受任务、进行交易等。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional
import random


class LocationType(IntEnum):
    """地点类型。"""
    VILLAGE = 0      # 村庄 - 基础资源点
    TOWN = 1         # 城镇 - 交易/任务中心
    CASTLE = 2       # 城堡 - 军事重镇
    BANDIT_CAMP = 3  # 匪窝 - 战斗区域


class Faction(IntEnum):
    """势力。"""
    SWADIA = 0       # 斯瓦迪亚王国
    VAEGIRS = 1      # 维吉亚王国
    NORDS = 2        # 诺德王国
    RHODOKS = 3      # 罗多克王国
    KHERGITS = 4     # 库吉特汗国
    SARRANIDS = 5    # 萨兰德苏丹国


FACTION_NAMES = {
    Faction.SWADIA: "斯瓦迪亚王国",
    Faction.VAEGIRS: "维吉亚王国",
    Faction.NORDS: "诺德王国",
    Faction.RHODOKS: "罗多克王国",
    Faction.KHERGITS: "库吉特汗国",
    Faction.SARRANIDS: "萨兰德苏丹国",
}

FACTION_SHORT_NAMES = {
    Faction.SWADIA: "斯瓦迪亚",
    Faction.VAEGIRS: "维吉亚",
    Faction.NORDS: "诺德",
    Faction.RHODOKS: "罗多克",
    Faction.KHERGITS: "库吉特",
    Faction.SARRANIDS: "萨兰德",
}


@dataclass
class Location:
    """地图上的一个地点。"""
    location_id: str
    name: str
    location_type: int           # LocationType
    faction: int                 # Faction
    x: float                    # 地图坐标 X (0-1000)
    y: float                    # 地图坐标 Y (0-1000)
    level_range: tuple[int, int]  # 适合的玩家等级范围
    description: str = ""
    
    # 城镇特有
    shop_items: list[str] = field(default_factory=list)  # 商品列表
    tax_rate: float = 0.1  # 税率
    
    # 村庄特有
    village_type: str = "普通"  # 普通/农业/畜牧/矿业
    production: str = ""  # 产出资源
    prosperity: int = 50  # 繁荣度 0-100
    
    # 城堡特有
    garrison_size: int = 100  # 守军数量
    strategic_value: int = 50  # 战略价值 0-100
    
    # 匪窝特有
    bandit_type: str = "普通"  # 山贼/海寇/草原强盗
    difficulty: int = 1  # 难度 1-5
    rewards: int = 100  # 击败奖励


@dataclass
class Quest:
    """任务定义。"""
    quest_id: str
    name: str
    description: str
    quest_type: str  # "deliver" | "escort" | "combat" | "trade" | "explore" | "patrol"
    difficulty: int   # 1-5
    level_range: tuple[int, int]
    exp_reward: int
    gold_reward: int
    duration: int  # 秒
    
    # 任务目标
    target_location: Optional[str] = None  # 目的地(如果是送货/护送任务)
    target_enemy: Optional[str] = None    # 敌人类型(如果是战斗任务)
    target_item: Optional[str] = None     # 物品ID(如果是送货任务)
    target_count: int = 1               # 目标数量
    
    # 任务接受者
    quest_giver: str = ""  # 发布任务的NPC名
    quest_giver_location: str = ""  # 发布任务的地点
    
    # 特殊效果
    special_reward: Optional[dict] = None  # 特殊奖励
    faction_relation_bonus: int = 0  # 势力关系奖励


@dataclass
class PlayerMapState:
    """玩家在地图上的状态。"""
    current_location: str = ""  # 当前所在地点ID
    x: float = 500.0           # 地图坐标X
    y: float = 500.0           # 地图坐标Y
    travel_progress: float = 0.0  # 旅行进度 0-100
    travel_destination: str = ""   # 旅行目的地
    travel_time: float = 0.0      # 旅行需要的时间
    active_quests: list[str] = field(default_factory=list)  # 进行中的任务ID
    completed_quests: list[str] = field(default_factory=list)  # 已完成的任务ID
    reputation: dict[int, int] = field(default_factory=dict)  # {faction: reputation}
    
    # 每日任务
    daily_quests_available: int = 3  # 今日可用任务数
    last_daily_reset: str = ""  # 上次重置日期 YYYY-MM-DD


# ══════════════════════════════════════════════════════════════
# 地图数据 - 卡拉迪亚大陆
# ══════════════════════════════════════════════════════════════

# 城镇列表
TOWNS: dict[str, Location] = {
    "town_suno": Location(
        location_id="town_suno", name="苏诺", location_type=LocationType.TOWN,
        faction=Faction.VAEGIRS, x=680, y=150,
        level_range=(0, 3), description="维吉亚王国北部城市，商业繁荣",
        shop_items=["grain", "iron", "cloth"], tax_rate=0.08,
    ),
    "town_reyvadin": Location(
        location_id="town_reyvadin", name="瑞瓦迪恩", location_type=LocationType.TOWN,
        faction=Faction.SWADIA, x=350, y=380,
        level_range=(2, 5), description="斯瓦迪亚王国中部大城市，军事要塞",
        shop_items=["iron", "weapons", "armor"], tax_rate=0.12,
    ),
    "town_curin": Location(
        location_id="town_curin", name="库里姆", location_type=LocationType.TOWN,
        faction=Faction.RHODOKS, x=500, y=500,
        level_range=(3, 7), description="罗多克王国山城，矿业发达",
        shop_items=["iron", "silver", "weapons"], tax_rate=0.10,
    ),
    "town_jelkala": Location(
        location_id="town_jelkala", name="贾尔卡拉", location_type=LocationType.TOWN,
        faction=Faction.RHODOKS, x=550, y=600,
        level_range=(5, 9), description="罗多克王国首都，繁华的商业都市",
        shop_items=["luxury_goods", "iron", "cloth"], tax_rate=0.15,
    ),
    "town_dhirim": Location(
        location_id="town_dhirim", name="迪林姆", location_type=LocationType.TOWN,
        faction=Faction.SWADIA, x=400, y=450,
        level_range=(1, 4), description="斯瓦迪亚中部城镇，农业发达",
        shop_items=["grain", "cattle", "cloth"], tax_rate=0.06,
    ),
    "town_sargoth": Location(
        location_id="town_sargoth", name="萨戈斯", location_type=LocationType.TOWN,
        faction=Faction.NORDS, x=600, y=100,
        level_range=(4, 8), description="诺德王国港口城市，渔业繁荣",
        shop_items=["fish", "iron", "timber"], tax_rate=0.10,
    ),
    "town_pravend": Location(
        location_id="town_pravend", name="普拉文德", location_type=LocationType.TOWN,
        faction=Faction.SWADIA, x=200, y=350,
        level_range=(0, 3), description="斯瓦迪亚王国西部城镇，葡萄酒产地",
        shop_items=["wine", "grain", "cattle"], tax_rate=0.07,
    ),
    "town_uxkhal": Location(
        location_id="town_uxkhal", name="乌克斯哈尔", location_type=LocationType.TOWN,
        faction=Faction.KHERGITS, x=850, y=400,
        level_range=(2, 6), description="库吉特汗国城市，草原贸易中心",
        shop_items=["horses", "wool", "spices"], tax_rate=0.09,
    ),
    "town_yalen": Location(
        location_id="town_yalen", name="亚伦", location_type=LocationType.TOWN,
        faction=Faction.SARRANIDS, x=300, y=650,
        level_range=(3, 7), description="萨兰德苏丹国港口，香料贸易中心",
        shop_items=["spices", "silk", "dates"], tax_rate=0.11,
    ),
    "town_desh shapuri": Location(
        location_id="town_desh_shapuri", name="德什沙普里", location_type=LocationType.TOWN,
        faction=Faction.SARRANIDS, x=250, y=700,
        level_range=(5, 9), description="萨兰德苏丹国首都，沙漠中的绿洲城市",
        shop_items=["spices", "silk", "gold"], tax_rate=0.14,
    ),
}

# 城堡列表
CASTLES: dict[str, Location] = {
    "castle_tulga": Location(
        location_id="castle_tulga", name="图尔加城堡", location_type=LocationType.CASTLE,
        faction=Faction.KHERGITS, x=800, y=350,
        level_range=(3, 6), description="库吉特汗国边境城堡",
        garrison_size=150, strategic_value=60,
    ),
    "castle_yalen": Location(
        location_id="castle_yalen", name="亚伦城堡", location_type=LocationType.CASTLE,
        faction=Faction.SARRANIDS, x=350, y=680,
        level_range=(4, 7), description="萨兰德苏丹国边境要塞",
        garrison_size=200, strategic_value=70,
    ),
    "castle_ethEL_b": Location(
        location_id="castle_ethEL_b", name="以瑟堡", location_type=LocationType.CASTLE,
        faction=Faction.NORDS, x=650, y=180,
        level_range=(5, 9), description="诺德王国北方堡垒",
        garrison_size=180, strategic_value=75,
    ),
    "castle_runen": Location(
        location_id="castle_runen", name="鲁嫩城堡", location_type=LocationType.CASTLE,
        faction=Faction.SWADIA, x=280, y=420,
        level_range=(2, 5), description="斯瓦迪亚王国中部城堡",
        garrison_size=120, strategic_value=50,
    ),
    "castle_curin": Location(
        location_id="castle_curin", name="库里姆城堡", location_type=LocationType.CASTLE,
        faction=Faction.RHODOKS, x=480, y=480,
        level_range=(4, 8), description="罗多克王国山城防线",
        garrison_size=160, strategic_value=65,
    ),
}

# 村庄列表
VILLAGES: dict[str, Location] = {
    "village_chambers": Location(
        location_id="village_chambers", name="钱伯斯村", location_type=LocationType.VILLAGE,
        faction=Faction.VAEGIRS, x=720, y=120,
        level_range=(0, 2), description="维吉亚北部小村庄",
        village_type="农业", production="小麦", prosperity=40,
    ),
    "village_teona": Location(
        location_id="village_teona", name="提欧纳村", location_type=LocationType.VILLAGE,
        faction=Faction.VAEGIRS, x=650, y=180,
        level_range=(0, 2), description="维吉亚东部渔村",
        village_type="渔业", production="鱼", prosperity=35,
    ),
    "village_bismar": Location(
        location_id="village_bismar", name="比斯玛村", location_type=LocationType.VILLAGE,
        faction=Faction.NORDS, x=580, y=140,
        level_range=(1, 3), description="诺德王国村庄",
        village_type="渔业", production="鱼", prosperity=45,
    ),
    "village_nord_farmers": Location(
        location_id="village_nord_farmers", name="诺德农场", location_type=LocationType.VILLAGE,
        faction=Faction.NORDS, x=620, y=100,
        level_range=(0, 2), description="诺德王国农场村落",
        village_type="农业", production="大麦", prosperity=50,
    ),
    "village_talmur": Location(
        location_id="village_talmur", name="塔尔穆村", location_type=LocationType.VILLAGE,
        faction=Faction.SWADIA, x=320, y=400,
        level_range=(0, 2), description="斯瓦迪亚中部村庄",
        village_type="农业", production="小麦", prosperity=55,
    ),
    "village_ogre_C": Location(
        location_id="village_ogre_C", name="奥格尔村", location_type=LocationType.VILLAGE,
        faction=Faction.SWADIA, x=380, y=350,
        level_range=(1, 3), description="斯瓦迪亚东部村庄",
        village_type="畜牧", production="牛", prosperity=48,
    ),
    "village_egrent": Location(
        location_id="village_egrent", name="艾格伦特村", location_type=LocationType.VILLAGE,
        faction=Faction.SWADIA, x=220, y=380,
        level_range=(0, 2), description="斯瓦迪亚西部村庄",
        village_type="农业", production="葡萄", prosperity=60,
    ),
    "village_Khergit_f": Location(
        location_id="village_Khergit_f", name="库吉特牧场", location_type=LocationType.VILLAGE,
        faction=Faction.KHERGITS, x=820, y=380,
        level_range=(1, 3), description="库吉特汗国游牧营地",
        village_type="畜牧", production="马", prosperity=42,
    ),
    "village_Rhadegund": Location(
        location_id="village_Rhadegund", name="拉德贡德村", location_type=LocationType.VILLAGE,
        faction=Faction.RHODOKS, x=520, y=550,
        level_range=(1, 3), description="罗多克王国山村",
        village_type="矿业", production="铁矿", prosperity=38,
    ),
    "village_Zaikes": Location(
        location_id="village_Zaikes", name="扎伊克斯村", location_type=LocationType.VILLAGE,
        faction=Faction.SARRANIDS, x=280, y=680,
        level_range=(2, 4), description="萨兰德苏丹国沙漠村庄",
        village_type="农业", production="椰枣", prosperity=30,
    ),
}

# 匪窝列表
BANDIT_CAMPS: dict[str, Location] = {
    "bandit_forest": Location(
        location_id="bandit_forest", name="森林匪窝", location_type=LocationType.BANDIT_CAMP,
        faction=Faction.SWADIA, x=380, y=420,
        level_range=(1, 3), description="隐藏在森林中的山贼营地",
        bandit_type="山贼", difficulty=2, rewards=150,
    ),
    "bandit_mountain": Location(
        location_id="bandit_mountain", name="山地匪窝", location_type=LocationType.BANDIT_CAMP,
        faction=Faction.RHODOKS, x=500, y=520,
        level_range=(3, 5), description="高山中的强盗据点",
        bandit_type="山贼", difficulty=3, rewards=300,
    ),
    "bandit_sea": Location(
        location_id="bandit_sea", name="海岸匪窝", location_type=LocationType.BANDIT_CAMP,
        faction=Faction.NORDS, x=640, y=120,
        level_range=(4, 6), description="海岸线上的海盗营地",
        bandit_type="海寇", difficulty=4, rewards=500,
    ),
    "bandit_steppe": Location(
        location_id="bandit_steppe", name="草原匪窝", location_type=LocationType.BANDIT_CAMP,
        faction=Faction.KHERGITS, x=780, y=400,
        level_range=(2, 4), description="草原上的游牧强盗",
        bandit_type="草原强盗", difficulty=3, rewards=350,
    ),
    "bandit_desert": Location(
        location_id="bandit_desert", name="沙漠匪窝", location_type=LocationType.BANDIT_CAMP,
        faction=Faction.SARRANIDS, x=300, y=720,
        level_range=(5, 7), description="沙漠中的盗贼巢穴",
        bandit_type="沙漠盗贼", difficulty=5, rewards=800,
    ),
}

# 所有地点汇总
ALL_LOCATIONS: dict[str, Location] = {}
ALL_LOCATIONS.update(TOWNS)
ALL_LOCATIONS.update(CASTLES)
ALL_LOCATIONS.update(VILLAGES)
ALL_LOCATIONS.update(BANDIT_CAMPS)


# ══════════════════════════════════════════════════════════════
# 任务模板
# ══════════════════════════════════════════════════════════════

# 送货任务模板
QUEST_TEMPLATES_DELIVER: list[dict] = [
    {
        "name": "货物运送",
        "desc": "将{from_loc}的{货品}送到{to_loc}",
        "base_exp": 50, "base_gold": 100, "duration": 300,
    },
    {
        "name": "紧急快递",
        "desc": "将重要信件从{from_loc}送往{to_loc}",
        "base_exp": 80, "base_gold": 150, "duration": 200,
    },
    {
        "name": "商品运输",
        "desc": "商人需要将{货品}从{from_loc}运到{to_loc}",
        "base_exp": 60, "base_gold": 120, "duration": 400,
    },
]

# 战斗任务模板
QUEST_TEMPLATES_COMBAT: list[dict] = [
    {
        "name": "剿匪行动",
        "desc": "前往{location}消灭{敌人类型}",
        "base_exp": 100, "base_gold": 200, "duration": 600,
    },
    {
        "name": "护送商队",
        "desc": "护送商队安全通过{location}区域",
        "base_exp": 80, "base_gold": 180, "duration": 500,
    },
    {
        "name": "清剿残敌",
        "desc": "在{location}击败残余势力",
        "base_exp": 120, "base_gold": 250, "duration": 400,
    },
]

# 巡逻任务模板
QUEST_TEMPLATES_PATROL: list[dict] = [
    {
        "name": "边境巡逻",
        "desc": "在{location}附近进行巡逻",
        "base_exp": 40, "base_gold": 80, "duration": 300,
    },
    {
        "name": "侦察任务",
        "desc": "侦察{location}周边敌情",
        "base_exp": 60, "base_gold": 100, "duration": 400,
    },
]

# 探索任务模板
QUEST_TEMPLATES_EXPLORE: list[dict] = [
    {
        "name": "探索未知",
        "desc": "探索{location}周边的区域",
        "base_exp": 70, "base_gold": 50, "duration": 350,
    },
]


def get_location_by_id(location_id: str) -> Optional[Location]:
    """根据ID获取地点。"""
    return ALL_LOCATIONS.get(location_id)


def get_nearby_locations(x: float, y: float, radius: float = 100) -> list[Location]:
    """获取指定坐标附近的地点。"""
    nearby = []
    for loc in ALL_LOCATIONS.values():
        distance = ((loc.x - x) ** 2 + (loc.y - y) ** 2) ** 0.5
        if distance <= radius:
            nearby.append((loc, distance))
    nearby.sort(key=lambda t: t[1])
    return [loc for loc, _ in nearby]


def calculate_travel_time(from_x: float, from_y: float, to_x: float, to_y: float) -> float:
    """计算两地之间的旅行时间（秒）。"""
    distance = ((to_x - from_x) ** 2 + (to_y - from_y) ** 2) ** 0.5
    speed = 50.0  # 每秒移动的地图单位
    return distance / speed


def generate_quest(player_level: int, location: Location) -> Optional[Quest]:
    """根据地点和玩家等级生成任务。"""
    if location.location_type == LocationType.BANDIT_CAMP:
        return None
    
    # 根据地点类型选择任务模板
    if location.location_type == LocationType.VILLAGE:
        templates = QUEST_TEMPLATES_DELIVER + QUEST_TEMPLATES_PATROL
    elif location.location_type == LocationType.TOWN:
        templates = QUEST_TEMPLATES_DELIVER + QUEST_TEMPLATES_COMBAT + QUEST_TEMPLATES_PATROL
    elif location.location_type == LocationType.CASTLE:
        templates = QUEST_TEMPLATES_COMBAT + QUEST_TEMPLATES_PATROL
    else:
        return None
    
    template = random.choice(templates)
    
    # 找到合适的目的地
    possible_targets = []
    for loc in ALL_LOCATIONS.values():
        if loc.location_id != location.location_id:
            if location.level_range[0] <= player_level <= location.level_range[1]:
                possible_targets.append(loc)
    
    if not possible_targets:
        return None
    
    target = random.choice(possible_targets)
    
    # 计算难度和奖励
    difficulty = max(1, min(5, player_level // 2 + 1))
    exp_mult = 1.0 + (difficulty - 1) * 0.3
    gold_mult = 1.0 + (difficulty - 1) * 0.5
    
    quest_id = f"quest_{location.location_id}_{random.randint(1000, 9999)}"
    
    return Quest(
        quest_id=quest_id,
        name=template["name"],
        description=template["desc"].format(
            from_loc=location.name,
            to_loc=target.name,
            location=location.name,
            敌人类型="山贼" if random.random() > 0.5 else "残敌",
            货品=random.choice(["粮食", "布料", "铁器"]),
        ),
        quest_type="deliver" if "运送" in template["name"] or "快递" in template["name"] or "运输" in template["name"] else "combat" if "剿" in template["name"] or "护送" in template["name"] else "patrol",
        difficulty=difficulty,
        level_range=location.level_range,
        exp_reward=int(template["base_exp"] * exp_mult),
        gold_reward=int(template["base_gold"] * gold_mult),
        duration=template["duration"],
        target_location=target.location_id,
        quest_giver=f"{location.name}长老" if location.location_type == LocationType.VILLAGE else f"{location.name}领主",
        quest_giver_location=location.location_id,
    )


def get_faction_relation(player: "Player", faction: int) -> int:
    """获取玩家对某势力的关系（-100到100）。"""
    return player.map_state.reputation.get(faction, 0)


def modify_faction_relation(player: "Player", faction: int, amount: int):
    """修改玩家对某势力的关系。"""
    current = player.map_state.reputation.get(faction, 0)
    new_val = max(-100, min(100, current + amount))
    player.map_state.reputation[faction] = new_val


# ══════════════════════════════════════════════════════════════
# 骑砍风格动态劫匪系统
# ══════════════════════════════════════════════════════════════

import time


class BanditType(IntEnum):
    """劫匪类型。"""
    MOUNTAIN = 0      # 山贼 - 森林/山地
    SEA_RAIDER = 1    # 海寇 - 海岸线
    STEPPE_RAIDER = 2 # 草原强盗 - 草原
    DESERT_BANDIT = 3 # 沙漠盗贼 - 沙漠
    FOREST_BANDIT = 4 # 森林盗匪 - 森林深处
    MOUNTAIN_BANDIT = 5  # 山地匪徒 - 高山地带


BANDIT_TYPE_NAMES = {
    BanditType.MOUNTAIN: "山贼",
    BanditType.SEA_RAIDER: "海寇",
    BanditType.STEPPE_RAIDER: "草原强盗",
    BanditType.DESERT_BANDIT: "沙漠盗贼",
    BanditType.FOREST_BANDIT: "森林盗匪",
    BanditType.MOUNTAIN_BANDIT: "山地匪徒",
}

BANDIT_TYPE_ICONS = {
    BanditType.MOUNTAIN: "⚔️",
    BanditType.SEA_RAIDER: "☠️",
    BanditType.STEPPE_RAIDER: "🏇",
    BanditType.DESERT_BANDIT: "🐪",
    BanditType.FOREST_BANDIT: "🌲",
    BanditType.MOUNTAIN_BANDIT: "⛰️",
}


@dataclass
class BanditGroup:
    """大地图上的一组劫匪。"""
    bandit_id: str
    name: str
    bandit_type: int           # BanditType
    x: float                   # 地图坐标 X
    y: float                   # 地图坐标 Y
    level: int                 # 难度等级 1-10
    member_count: int          # 人数
    max_member_count: int      # 最大人数
    hp: int                   # 当前血量
    max_hp: int               # 最大血量
    attack: int               # 攻击力
    defense: int              # 防御力
    exp_reward: int           # 经验奖励
    gold_reward: int          # 金币奖励
    spawn_time: float         # 生成时间
    last_defeated_time: float = 0.0  # 上次被击败时间
    respawn_time: float = 0.0        # 复活时间
    is_defeated: bool = False         # 是否被击败
    
    # 移动相关
    is_patrolling: bool = False       # 是否在巡逻
    patrol_range: float = 50.0       # 巡逻范围
    patrol_target_x: float = 0.0
    patrol_target_y: float = 0.0


BANDIT_TEMPLATES = {
    # 初级劫匪 (等级1-2)
    "mountain_weak": {
        "name": "落魄山贼",
        "bandit_type": BanditType.MOUNTAIN,
        "level_range": (1, 2),
        "member_range": (3, 6),
        "hp_base": 30,
        "hp_per_level": 15,
        "atk_base": 8,
        "atk_per_level": 4,
        "def_base": 3,
        "def_per_level": 2,
        "exp_base": 20,
        "exp_per_level": 15,
        "gold_base": 20,
        "gold_per_level": 15,
        "respawn_time": 300,  # 5分钟
    },
    "forest_weak": {
        "name": "森林盗匪",
        "bandit_type": BanditType.FOREST_BANDIT,
        "level_range": (1, 2),
        "member_range": (2, 5),
        "hp_base": 25,
        "hp_per_level": 12,
        "atk_base": 7,
        "atk_per_level": 3,
        "def_base": 2,
        "def_per_level": 2,
        "exp_base": 18,
        "exp_per_level": 12,
        "gold_base": 18,
        "gold_per_level": 12,
        "respawn_time": 240,
    },
    # 中级劫匪 (等级3-5)
    "mountain_mid": {
        "name": "凶悍山贼",
        "bandit_type": BanditType.MOUNTAIN,
        "level_range": (3, 5),
        "member_range": (5, 10),
        "hp_base": 50,
        "hp_per_level": 20,
        "atk_base": 12,
        "atk_per_level": 5,
        "def_base": 5,
        "def_per_level": 3,
        "exp_base": 40,
        "exp_per_level": 25,
        "gold_base": 40,
        "gold_per_level": 30,
        "respawn_time": 480,
    },
    "steppe_mid": {
        "name": "草原强盗",
        "bandit_type": BanditType.STEPPE_RAIDER,
        "level_range": (3, 5),
        "member_range": (6, 12),
        "hp_base": 45,
        "hp_per_level": 18,
        "atk_base": 14,
        "atk_per_level": 5,
        "def_base": 4,
        "def_per_level": 3,
        "exp_base": 45,
        "exp_per_level": 28,
        "gold_base": 35,
        "gold_per_level": 25,
        "respawn_time": 420,
    },
    "sea_mid": {
        "name": "凶残海寇",
        "bandit_type": BanditType.SEA_RAIDER,
        "level_range": (3, 5),
        "member_range": (4, 8),
        "hp_base": 55,
        "hp_per_level": 22,
        "atk_base": 13,
        "atk_per_level": 5,
        "def_base": 6,
        "def_per_level": 3,
        "exp_base": 50,
        "exp_per_level": 30,
        "gold_base": 60,
        "gold_per_level": 35,
        "respawn_time": 540,
    },
    # 高级劫匪 (等级6-8)
    "mountain_strong": {
        "name": "山贼首领",
        "bandit_type": BanditType.MOUNTAIN,
        "level_range": (6, 8),
        "member_range": (8, 15),
        "hp_base": 80,
        "hp_per_level": 30,
        "atk_base": 20,
        "atk_per_level": 8,
        "def_base": 10,
        "def_per_level": 5,
        "exp_base": 80,
        "exp_per_level": 50,
        "gold_base": 80,
        "gold_per_level": 50,
        "respawn_time": 720,
    },
    "desert_mid": {
        "name": "沙漠盗贼",
        "bandit_type": BanditType.DESERT_BANDIT,
        "level_range": (5, 7),
        "member_range": (5, 10),
        "hp_base": 60,
        "hp_per_level": 25,
        "atk_base": 18,
        "atk_per_level": 6,
        "def_base": 7,
        "def_per_level": 4,
        "exp_base": 60,
        "exp_per_level": 40,
        "gold_base": 70,
        "gold_per_level": 45,
        "respawn_time": 600,
    },
    # 精英劫匪 (等级9-10)
    "mountain_elite": {
        "name": "山贼王",
        "bandit_type": BanditType.MOUNTAIN,
        "level_range": (9, 10),
        "member_range": (15, 25),
        "hp_base": 120,
        "hp_per_level": 40,
        "atk_base": 28,
        "atk_per_level": 10,
        "def_base": 15,
        "def_per_level": 7,
        "exp_base": 150,
        "exp_per_level": 80,
        "gold_base": 150,
        "gold_per_level": 80,
        "respawn_time": 1200,
    },
    "sea_elite": {
        "name": "海寇王",
        "bandit_type": BanditType.SEA_RAIDER,
        "level_range": (9, 10),
        "member_range": (10, 20),
        "hp_base": 130,
        "hp_per_level": 45,
        "atk_base": 30,
        "atk_per_level": 12,
        "def_base": 18,
        "def_per_level": 8,
        "exp_base": 180,
        "exp_per_level": 100,
        "gold_base": 200,
        "gold_per_level": 100,
        "respawn_time": 1500,
    },
    "desert_elite": {
        "name": "沙漠之王",
        "bandit_type": BanditType.DESERT_BANDIT,
        "level_range": (9, 10),
        "member_range": (12, 22),
        "hp_base": 140,
        "hp_per_level": 50,
        "atk_base": 32,
        "atk_per_level": 12,
        "def_base": 16,
        "def_per_level": 8,
        "exp_base": 200,
        "exp_per_level": 110,
        "gold_base": 180,
        "gold_per_level": 90,
        "respawn_time": 1800,
    },
}


class BanditManager:
    """劫匪管理器 - 管理大地图上的所有劫匪。"""
    
    MAX_BANDIT_GROUPS = 30  # 最大劫匪群数量
    SPAWN_INTERVAL = 60     # 生成间隔（秒）
    MAP_WIDTH = 1000
    MAP_HEIGHT = 1000
    
    def __init__(self):
        self.bandit_groups: dict[str, BanditGroup] = {}
        self.last_spawn_time: float = 0.0
        self._bandit_id_counter = 0
    
    def _generate_bandit_id(self) -> str:
        """生成唯一ID。"""
        self._bandit_id_counter += 1
        return f"bandit_{self._bandit_id_counter}"
    
    def _is_location_suitable(self, x: float, y: float) -> bool:
        """检查位置是否适合生成劫匪（避开城镇、城堡）。"""
        for loc in ALL_LOCATIONS.values():
            if loc.location_type in (LocationType.TOWN, LocationType.CASTLE):
                dist = ((loc.x - x) ** 2 + (loc.y - y) ** 2) ** 0.5
                if dist < 80:  # 城镇/城堡周围80单位内不生成
                    return False
        return True
    
    def _get_random_position(self) -> tuple[float, float]:
        """获取随机位置。"""
        attempts = 0
        x = self.MAP_WIDTH / 2
        y = self.MAP_HEIGHT / 2
        while attempts < 50:
            x = random.uniform(50, self.MAP_WIDTH - 50)
            y = random.uniform(50, self.MAP_HEIGHT - 50)
            if self._is_location_suitable(x, y):
                return x, y
            attempts += 1
        return x, y  # fallback
    
    def _select_template_for_level(self, player_level: int) -> dict:
        """根据玩家等级选择劫匪模板。"""
        suitable = []
        for tid, tmpl in BANDIT_TEMPLATES.items():
            lvl_min, lvl_max = tmpl["level_range"]
            if lvl_min <= player_level <= lvl_max + 2:
                suitable.append((tid, tmpl))
            elif abs(player_level - (lvl_min + lvl_max) / 2) <= 3:
                suitable.append((tid, tmpl))
        
        if not suitable:
            suitable = [(tid, tmpl) for tid, tmpl in BANDIT_TEMPLATES.items()]
        
        return random.choice(suitable)[1]
    
    def spawn_bandit(self, player_level: int = 1) -> Optional[BanditGroup]:
        """生成一组劫匪。"""
        if len(self.bandit_groups) >= self.MAX_BANDIT_GROUPS:
            return None
        
        template = self._select_template_for_level(player_level)
        level = random.randint(*template["level_range"])
        member_count = random.randint(*template["member_range"])
        
        x, y = self._get_random_position()
        hp = template["hp_base"] + template["hp_per_level"] * level
        atk = template["atk_base"] + template["atk_per_level"] * level
        defense = template["def_base"] + template["def_per_level"] * level
        exp = template["exp_base"] + template["exp_per_level"] * level
        gold = template["gold_base"] + template["gold_per_level"] * level
        
        bandit_id = self._generate_bandit_id()
        name = f"{template['name']}{random.randint(1, 99)}号"
        
        bandit = BanditGroup(
            bandit_id=bandit_id,
            name=name,
            bandit_type=template["bandit_type"],
            x=x,
            y=y,
            level=level,
            member_count=member_count,
            max_member_count=member_count,
            hp=hp,
            max_hp=hp,
            attack=atk,
            defense=defense,
            exp_reward=exp,
            gold_reward=gold,
            spawn_time=time.time(),
            last_defeated_time=0.0,
            respawn_time=template["respawn_time"],
            is_defeated=False,
            is_patrolling=random.random() > 0.5,
            patrol_range=random.uniform(30, 80),
            patrol_target_x=x,
            patrol_target_y=y,
        )
        
        self.bandit_groups[bandit_id] = bandit
        return bandit
    
    def spawn_initial_bandits(self, count: int = 15):
        """生成初始劫匪群。"""
        for _ in range(count):
            self.spawn_bandit(random.randint(1, 10))
    
    def update(self, delta_time: float = 1.0):
        """更新劫匪状态（巡逻、复活等）。"""
        current_time = time.time()
        
        # 检查复活
        for bandit in self.bandit_groups.values():
            if bandit.is_defeated:
                if current_time - bandit.last_defeated_time >= bandit.respawn_time:
                    # 复活
                    bandit.is_defeated = False
                    bandit.member_count = bandit.max_member_count
                    bandit.hp = bandit.max_hp
        
        # 巡逻移动
        for bandit in self.bandit_groups.values():
            if bandit.is_defeated or not bandit.is_patrolling:
                continue
            
            # 更新巡逻目标
            dx = bandit.patrol_target_x - bandit.x
            dy = bandit.patrol_target_y - bandit.y
            dist = (dx ** 2 + dy ** 2) ** 0.5
            
            if dist < 10:  # 到达目标
                # 设置新目标
                bandit.patrol_target_x = bandit.x + random.uniform(-bandit.patrol_range, bandit.patrol_range)
                bandit.patrol_target_y = bandit.y + random.uniform(-bandit.patrol_range, bandit.patrol_range)
                bandit.patrol_target_x = max(20, min(self.MAP_WIDTH - 20, bandit.patrol_target_x))
                bandit.patrol_target_y = max(20, min(self.MAP_HEIGHT - 20, bandit.patrol_target_y))
            else:
                # 向目标移动
                speed = 5.0 * delta_time  # 每秒5单位
                bandit.x += (dx / dist) * speed
                bandit.y += (dy / dist) * speed
        
        # 自动生成新劫匪
        if current_time - self.last_spawn_time >= self.SPAWN_INTERVAL:
            active_count = sum(1 for b in self.bandit_groups.values() if not b.is_defeated)
            if active_count < self.MAX_BANDIT_GROUPS - 5:
                self.spawn_bandit(random.randint(1, 10))
            self.last_spawn_time = current_time
    
    def get_nearby_bandits(self, x: float, y: float, radius: float = 150) -> list[BanditGroup]:
        """获取附近的劫匪。"""
        nearby = []
        for bandit in self.bandit_groups.values():
            if bandit.is_defeated:
                continue
            dist = ((bandit.x - x) ** 2 + (bandit.y - y) ** 2) ** 0.5
            if dist <= radius:
                nearby.append((bandit, dist))
        nearby.sort(key=lambda t: t[1])
        return [b for b, _ in nearby]
    
    def get_visible_bandits(self, x: float, y: float, radius: float = 300) -> list[BanditGroup]:
        """获取视野范围内的劫匪。"""
        return self.get_nearby_bandits(x, y, radius)
    
    def get_all_active_bandits(self) -> list[BanditGroup]:
        """获取所有活跃劫匪。"""
        return [b for b in self.bandit_groups.values() if not b.is_defeated]
    
    def defeat_bandit(self, bandit_id: str, player_damage: float) -> dict:
        """击败劫匪。"""
        bandit = self.bandit_groups.get(bandit_id)
        if not bandit or bandit.is_defeated:
            return {"success": False, "message": "劫匪不存在或已被击败"}
        
        # 计算伤害
        bandit.hp = int(bandit.hp - player_damage)
        bandit.member_count = max(0, int(bandit.member_count * (bandit.hp / bandit.max_hp)))
        
        if bandit.hp <= 0:
            bandit.is_defeated = True
            bandit.last_defeated_time = time.time()
            bandit.member_count = 0
            bandit.hp = 0
            return {
                "success": True,
                "defeated": True,
                "name": bandit.name,
                "exp_reward": bandit.exp_reward,
                "gold_reward": bandit.gold_reward,
                "member_count_lost": bandit.max_member_count,
                "message": f"你击败了{bandit.name}！获得经验 {bandit.exp_reward}，战利品 {bandit.gold_reward} 第纳尔！",
            }
        
        return {
            "success": True,
            "defeated": False,
            "name": bandit.name,
            "hp": bandit.hp,
            "max_hp": bandit.max_hp,
            "member_count": bandit.member_count,
            "message": f"对{bandit.name}造成 {int(player_damage)} 点伤害！剩余血量 {bandit.hp}/{bandit.max_hp}",
        }
    
    def to_dict(self) -> dict:
        """序列化为字典（用于前端显示）。"""
        current_time = time.time()
        return {
            "bandits": [
                {
                    "bandit_id": b.bandit_id,
                    "name": b.name,
                    "type": BANDIT_TYPE_NAMES.get(BanditType(b.bandit_type), "未知"),
                    "icon": BANDIT_TYPE_ICONS.get(BanditType(b.bandit_type), "⚔️"),
                    "x": b.x,
                    "y": b.y,
                    "level": b.level,
                    "member_count": b.member_count,
                    "hp": b.hp,
                    "max_hp": b.max_hp,
                    "is_defeated": b.is_defeated,
                    "defeated_time_remaining": max(0, int(b.last_defeated_time + b.respawn_time - current_time)) if b.is_defeated else 0,
                }
                for b in self.bandit_groups.values()
            ]
        }


# 全局劫匪管理器实例
_bandit_manager: BanditManager | None = None


def get_bandit_manager() -> BanditManager:
    """获取劫匪管理器实例。"""
    global _bandit_manager
    if _bandit_manager is None:
        _bandit_manager = BanditManager()
    return _bandit_manager


def init_bandit_system(initial_bandits: int = 15):
    """初始化劫匪系统。"""
    manager = get_bandit_manager()
    if not manager.bandit_groups:
        manager.spawn_initial_bandits(initial_bandits)


# ══════════════════════════════════════════════════════════════
# 玩家劫匪战斗进度追踪
# ══════════════════════════════════════════════════════════════


@dataclass
class PlayerBanditStats:
    """玩家对劫匪的战斗统计。"""
    total_defeated: int = 0                    # 总击败数
    bandits_by_type: dict[int, int] = field(default_factory=dict)  # {BanditType: count}
    total_exp_gained: int = 0                  # 总获得经验
    total_gold_gained: int = 0                # 总获得金币
    highest_level_defeated: int = 0            # 击败过的最高等级
    consecutive_victories: int = 0              # 连胜次数
    last_defeat_time: float = 0.0              # 上次失败时间


def get_player_bandit_rank(total_defeated: int) -> tuple[str, int, int]:
    """
    根据击败总数获取称号和下一级所需击败数。
    返回: (称号, 当前级, 下一级所需)
    """
    ranks = [
        (0, "新兵", 10),
        (10, "士兵", 30),
        (40, "老兵", 60),
        (100, "骑士", 100),
        (200, "骑士长", 150),
        (350, "男爵", 200),
        (550, "子爵", 300),
        (850, "伯爵", 400),
        (1250, "侯爵", 500),
        (1750, "公爵", 999999),
        (2750, "领主"),
    ]
    
    for i, entry in enumerate(ranks):
        count = entry[0]
        name = entry[1]
        if len(entry) > 2:
            next_req = entry[2]
        else:
            next_req = 999999
        
        if total_defeated < count:
            prev_entry = ranks[i - 1]
            return prev_entry[1], i, count - total_defeated
        
        if i == len(ranks) - 1:
            return name, i + 1, 999999
    
    return "领主", len(ranks), 999999
