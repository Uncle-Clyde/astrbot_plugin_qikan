"""
开局选择系统 - 骑砍风格出身选择

玩家注册时可选择不同的出身背景，决定出生地点和初始加成。
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from .map_system import Faction, FACTION_NAMES
from .mb_attributes import SkillType


class SpawnOriginType:
    """出身类型"""
    FARMER = "farmer"           # 农民
    MERCHANT = "merchant"        # 商人
    MERCENARY = "mercenary"     # 佣兵
    NOBLE = "noble"              # 贵族
    OUTLAW = "outlaw"            # 盗匪
    SCHOLAR = "scholar"          # 学者
    PIRATE = "pirate"           # 海盗
    BANDIT_RIDER = "bandit_rider"  # 响马
    FOREST_BANDIT = "forest_bandit"  # 绿林强盗
    MOUNTAIN_BANDIT = "mountain_bandit"  # 山贼
    BARD = "bard"               # 吟游诗人


SPAWN_ORIGIN_NAMES = {
    SpawnOriginType.FARMER: "农民",
    SpawnOriginType.MERCHANT: "商人",
    SpawnOriginType.MERCENARY: "佣兵",
    SpawnOriginType.NOBLE: "贵族",
    SpawnOriginType.OUTLAW: "盗匪",
    SpawnOriginType.SCHOLAR: "学者",
    SpawnOriginType.PIRATE: "海盗",
    SpawnOriginType.BANDIT_RIDER: "响马",
    SpawnOriginType.FOREST_BANDIT: "绿林强盗",
    SpawnOriginType.MOUNTAIN_BANDIT: "山贼",
    SpawnOriginType.BARD: "吟游诗人",
}


@dataclass
class SpawnOrigin:
    """出身定义"""
    origin_id: str
    name: str
    description: str
    icon: str
    
    # 骑砍属性加成
    bonus_strength: int = 0     # 力量
    bonus_agility: int = 0      # 敏捷
    bonus_intelligence: int = 0  # 智力
    
    # 初始属性加成（旧版兼容）
    bonus_hp: int = 0
    bonus_attack: int = 0
    bonus_defense: int = 0
    bonus_lingqi: int = 0
    bonus_spirit_stones: int = 0
    bonus_exp: int = 0
    
    # 额外物品奖励
    bonus_items: dict[str, int] = None
    
    # 推荐阵营
    recommended_factions: list[int] = None
    
    # 特色描述
    specialty: str = ""
    
    # 初始技能
    bonus_skills: dict[int, int] = None  # {skill_id: level}
    
    def __post_init__(self):
        if self.bonus_items is None:
            self.bonus_items = {}
        if self.recommended_factions is None:
            self.recommended_factions = []
        if self.bonus_skills is None:
            self.bonus_skills = {}


SPAWN_ORIGINS: dict[str, SpawnOrigin] = {
    SpawnOriginType.FARMER: SpawnOrigin(
        origin_id=SpawnOriginType.FARMER,
        name="农民",
        description="生于普通村庄勤劳耕作，身体健硕熟悉农活",
        icon="🌾",
        bonus_strength=3,
        bonus_agility=2,
        bonus_intelligence=1,
        bonus_spirit_stones=50,
        bonus_items={"healing_pill": 2, "common_straw_hat": 1, "pitchfork": 1},
        bonus_skills={SkillType.IRON_FLESH: 2},  # 铁骨+2善于劳作
        recommended_factions=[Faction.SWADIA, Faction.RHODOKS],
        specialty="力量+3 铁骨+2 获得草帽和草叉",
    ),
    SpawnOriginType.MERCHANT: SpawnOrigin(
        origin_id=SpawnOriginType.MERCHANT,
        name="商人",
        description="从小在城镇商业区长大，耳濡目染通晓贸易之道",
        icon="💰",
        bonus_strength=1,
        bonus_agility=2,
        bonus_intelligence=3,
        bonus_spirit_stones=200,
        bonus_items={
            "healing_pill": 1,
            "exp_pill": 1,
        },
        bonus_skills={SkillType.TRADE: 2},  # 交易+2
        recommended_factions=[Faction.VAEGIRS, Faction.SARRANIDS],
        specialty="智力+3 交易+2",
    ),
    SpawnOriginType.MERCENARY: SpawnOrigin(
        origin_id=SpawnOriginType.MERCENARY,
        name="佣兵",
        description="在刀口上讨生活的雇佣兵，战斗经验丰富",
        icon="⚔️",
        bonus_strength=3,
        bonus_agility=3,
        bonus_intelligence=1,
        bonus_items={
            "healing_pill": 3,
            "iron_sword": 1,
        },
        bonus_skills={SkillType.POWER_STRIKE: 2},  # 强击+2
        recommended_factions=[Faction.NORDS, Faction.KHERGITS],
        specialty="力量+3 敏捷+3 强击+2",
    ),
    SpawnOriginType.NOBLE: SpawnOrigin(
        origin_id=SpawnOriginType.NOBLE,
        name="贵族",
        description="出身名门望族，自幼接受武艺与学识的熏陶",
        icon="👑",
        bonus_strength=2,
        bonus_agility=2,
        bonus_intelligence=3,
        bonus_spirit_stones=100,
        bonus_items={
            "healing_pill": 2,
            "iron_sword": 1,
        },
        bonus_skills={SkillType.TRAINING: 2},  # 教练+2
        recommended_factions=[Faction.SWADIA, Faction.RHODOKS, Faction.VAEGIRS],
        specialty="全属性+2 智力+3 教练+2",
    ),
    SpawnOriginType.OUTLAW: SpawnOrigin(
        origin_id=SpawnOriginType.OUTLAW,
        name="盗匪",
        description="在山野间落草为寇，熟悉野外生存之道",
        icon="🏴‍☠️",
        bonus_strength=4,
        bonus_agility=3,
        bonus_intelligence=0,
        bonus_items={
            "healing_pill": 4,
            "common_farm_axe": 1,
        },
        bonus_skills={SkillType.ATHLETICS: 2},  # 跑动+2
        recommended_factions=[Faction.NORDS, Faction.KHERGITS],
        specialty="力量+4 敏捷+3 跑动+2",
    ),
    SpawnOriginType.SCHOLAR: SpawnOrigin(
        origin_id=SpawnOriginType.SCHOLAR,
        name="学者",
        description="在学院中研习武学典籍，知识渊博",
        icon="📚",
        bonus_strength=1,
        bonus_agility=1,
        bonus_intelligence=5,
        bonus_items={
            "healing_pill": 1,
            "exp_pill": 3,
        },
        bonus_skills={SkillType.TACTICS: 2},  # 战术+2
        recommended_factions=[Faction.SARRANIDS, Faction.VAEGIRS],
        specialty="智力+5 战术+2",
    ),
    SpawnOriginType.PIRATE: SpawnOrigin(
        origin_id=SpawnOriginType.PIRATE,
        name="海盗",
        description="纵横海域的海盗，擅长白刃战和劫掠，水性极佳",
        icon="☠️",
        bonus_strength=5,
        bonus_agility=2,
        bonus_intelligence=0,
        bonus_items={
            "healing_pill": 2,
            "pirate_sword": 1,
        },
        bonus_skills={SkillType.POWER_STRIKE: 2},  # 强击+2
        recommended_factions=[Faction.NORDS, Faction.RHODOKS],
        specialty="力量+5 强击+2 获得海盗刀",
    ),
    SpawnOriginType.BANDIT_RIDER: SpawnOrigin(
        origin_id=SpawnOriginType.BANDIT_RIDER,
        name="响马",
        description="纵横草原的马贼，来去如风，擅长骑射和快速突袭",
        icon="💨",
        bonus_strength=2,
        bonus_agility=5,
        bonus_intelligence=0,
        bonus_items={
            "healing_pill": 2,
            "nomad_saber": 1,
            "arrow": 30,
        },
        bonus_skills={SkillType.RIDING: 2},  # 骑术+2
        recommended_factions=[Faction.KHERGITS],
        specialty="敏捷+5 骑术+2",
    ),
    SpawnOriginType.FOREST_BANDIT: SpawnOrigin(
        origin_id=SpawnOriginType.FOREST_BANDIT,
        name="绿林强盗",
        description="占山为王的绿林好汉，擅长弓箭和伏击，来去如风",
        icon="🌲",
        bonus_strength=2,
        bonus_agility=5,
        bonus_intelligence=0,
        bonus_items={
            "healing_pill": 2,
            "short_bow": 1,
            "arrow": 30,
        },
        bonus_skills={SkillType.ARCHERY: 2},  # 弓术+2
        recommended_factions=[Faction.VAEGIRS],
        specialty="敏捷+5 弓术+2 获得猎弓",
    ),
    SpawnOriginType.MOUNTAIN_BANDIT: SpawnOrigin(
        origin_id=SpawnOriginType.MOUNTAIN_BANDIT,
        name="山贼",
        description="占山为寇的山贼头目，擅长棍棒和近身搏斗",
        icon="⛰️",
        bonus_strength=4,
        bonus_agility=3,
        bonus_intelligence=0,
        bonus_items={
            "healing_pill": 2,
            "club": 1,
        },
        bonus_skills={SkillType.IRON_FLESH: 2},  # 铁骨+2
        recommended_factions=[Faction.RHODOKS],
        specialty="力量+4 铁骨+2 获得木棍",
    ),
    SpawnOriginType.BARD: SpawnOrigin(
        origin_id=SpawnOriginType.BARD,
        name="吟游诗人",
        description="走遍大陆的吟游诗人，能说会道，善于用歌声和故事打动人心",
        icon="🪕",
        bonus_strength=1,
        bonus_agility=2,
        bonus_intelligence=4,
        bonus_items={
            "healing_pill": 2,
            "mana_potion": 3,
        },
        bonus_skills={SkillType.TRADE: 2, SkillType.TRAINING: 1},  # 交易+2 教练+1
        recommended_factions=[Faction.SWADIA, Faction.VAEGIRS, Faction.SARRANIDS],
        specialty="智力+4 交易+2 教练+1",
    ),
}


@dataclass
class SpawnLocation:
    """出生地点定义"""
    location_id: str
    name: str
    x: float
    y: float
    faction: int
    description: str
    icon: str
    available_origins: list[str] = None
    
    def __post_init__(self):
        if self.available_origins is None:
            self.available_origins = list(SPAWN_ORIGINS.keys())


SPAWN_LOCATIONS: dict[str, SpawnLocation] = {
    # 斯瓦迪亚王国阵营 - 适合新手/重装战士
    "town_pravend": SpawnLocation(
        location_id="town_pravend",
        name="普拉文德",
        x=200, y=350,
        faction=Faction.SWADIA,
        description="斯瓦迪亚王国西部城镇，葡萄酒产地",
        icon="🍷",
        available_origins=[SpawnOriginType.FARMER, SpawnOriginType.MERCHANT, SpawnOriginType.NOBLE, SpawnOriginType.BARD],
    ),
    "town_dhirim": SpawnLocation(
        location_id="town_dhirim",
        name="迪林姆",
        x=400, y=450,
        faction=Faction.SWADIA,
        description="斯瓦迪亚中部城镇，农业发达",
        icon="🌾",
        available_origins=[SpawnOriginType.FARMER, SpawnOriginType.SCHOLAR, SpawnOriginType.MERCENARY, SpawnOriginType.BARD],
    ),
    "town_reyvadin": SpawnLocation(
        location_id="town_reyvadin",
        name="瑞瓦迪恩",
        x=350, y=380,
        faction=Faction.SWADIA,
        description="斯瓦迪亚中部大城市，军事要塞",
        icon="🏰",
        available_origins=[SpawnOriginType.MERCENARY, SpawnOriginType.NOBLE, SpawnOriginType.OUTLAW, SpawnOriginType.BARD],
    ),
    # 维吉亚王国阵营 - 适合猎人/学者
    "town_suno": SpawnLocation(
        location_id="town_suno",
        name="苏诺",
        x=680, y=150,
        faction=Faction.VAEGIRS,
        description="维吉亚王国北部城市，商业繁荣",
        icon="🏛️",
        available_origins=[SpawnOriginType.MERCHANT, SpawnOriginType.SCHOLAR, SpawnOriginType.NOBLE, SpawnOriginType.FOREST_BANDIT],
    ),
    # 诺德王国阵营 - 适合战士
    "town_sargoth": SpawnLocation(
        location_id="town_sargoth",
        name="萨戈斯",
        x=600, y=100,
        faction=Faction.NORDS,
        description="诺德王国港口城市，渔业繁荣",
        icon="⚓",
        available_origins=[SpawnOriginType.MERCENARY, SpawnOriginType.OUTLAW, SpawnOriginType.FARMER, SpawnOriginType.PIRATE],
    ),
    # 罗多克王国阵营 - 适合狙击手
    "town_curin": SpawnLocation(
        location_id="town_curin",
        name="库里姆",
        x=500, y=500,
        faction=Faction.RHODOKS,
        description="罗多克王国山城，矿业发达",
        icon="⛏️",
        available_origins=[SpawnOriginType.FARMER, SpawnOriginType.MERCENARY, SpawnOriginType.NOBLE, SpawnOriginType.MOUNTAIN_BANDIT],
    ),
    "town_jelkala": SpawnLocation(
        location_id="town_jelkala",
        name="贾尔卡拉",
        x=550, y=600,
        faction=Faction.RHODOKS,
        description="罗多克王国首都，繁华的商业都市",
        icon="👑",
        available_origins=[SpawnOriginType.MERCHANT, SpawnOriginType.NOBLE, SpawnOriginType.SCHOLAR, SpawnOriginType.MOUNTAIN_BANDIT],
    ),
    # 库吉特汗国阵营 - 适合草原骑手
    "town_uxkhal": SpawnLocation(
        location_id="town_uxkhal",
        name="乌克斯哈尔",
        x=850, y=400,
        faction=Faction.KHERGITS,
        description="库吉特汗国城市，草原贸易中心",
        icon="🐎",
        available_origins=[SpawnOriginType.OUTLAW, SpawnOriginType.MERCENARY, SpawnOriginType.FARMER, SpawnOriginType.BANDIT_RIDER],
    ),
    # 萨兰德苏丹国阵营 - 适合商人/学者
    "town_yalen": SpawnLocation(
        location_id="town_yalen",
        name="亚伦",
        x=300, y=650,
        faction=Faction.SARRANIDS,
        description="萨兰德苏丹国港口，香料贸易中心",
        icon="🏺",
        available_origins=[SpawnOriginType.MERCHANT, SpawnOriginType.SCHOLAR, SpawnOriginType.NOBLE, SpawnOriginType.BANDIT_RIDER],
    ),
}


def get_all_spawn_origins() -> list[dict]:
    """获取所有出身选项"""
    from .mb_attributes import SKILL_DEFINITIONS
    
    result = []
    for origin in SPAWN_ORIGINS.values():
        skill_info = []
        for skill_id, level in (origin.bonus_skills or {}).items():
            skill_def = SKILL_DEFINITIONS.get(skill_id)
            if skill_def:
                skill_info.append({"name": skill_def.name, "level": level})
        
        result.append({
            "origin_id": origin.origin_id,
            "name": origin.name,
            "description": origin.description,
            "icon": origin.icon,
            "specialty": origin.specialty,
            # 骑砍属性
            "bonus_strength": origin.bonus_strength,
            "bonus_agility": origin.bonus_agility,
            "bonus_intelligence": origin.bonus_intelligence,
            # 初始技能
            "bonus_skills": skill_info,
            # 旧版兼容
            "bonus_hp": origin.bonus_hp,
            "bonus_attack": origin.bonus_attack,
            "bonus_defense": origin.bonus_defense,
            "bonus_lingqi": origin.bonus_lingqi,
            "bonus_spirit_stones": origin.bonus_spirit_stones,
        })
    return result


def get_all_spawn_locations() -> list[dict]:
    """获取所有出生地点"""
    return [
        {
            "location_id": loc.location_id,
            "name": loc.name,
            "x": loc.x,
            "y": loc.y,
            "faction": loc.faction,
            "faction_name": FACTION_NAMES.get(loc.faction, "未知"),
            "description": loc.description,
            "icon": loc.icon,
            "available_origins": loc.available_origins,
        }
        for loc in SPAWN_LOCATIONS.values()
    ]


def get_spawn_locations_by_faction(faction: int) -> list[dict]:
    """根据阵营获取出生地点"""
    return [
        {
            "location_id": loc.location_id,
            "name": loc.name,
            "x": loc.x,
            "y": loc.y,
            "faction": loc.faction,
            "faction_name": FACTION_NAMES.get(loc.faction, "未知"),
            "description": loc.description,
            "icon": loc.icon,
            "available_origins": loc.available_origins,
        }
        for loc in SPAWN_LOCATIONS.values() if loc.faction == faction
    ]


def get_spawn_origin(origin_id: str) -> Optional[SpawnOrigin]:
    """获取出身详情"""
    return SPAWN_ORIGINS.get(origin_id)


def get_spawn_location(location_id: str) -> Optional[SpawnLocation]:
    """获取地点详情"""
    return SPAWN_LOCATIONS.get(location_id)


def validate_spawn_selection(origin_id: str, location_id: str) -> tuple[bool, str]:
    """验证出生选择是否有效"""
    origin = SPAWN_ORIGINS.get(origin_id)
    if not origin:
        return False, "无效的出身选择"
    
    location = SPAWN_LOCATIONS.get(location_id)
    if not location:
        return False, "无效的出生地点"
    
    if origin_id not in location.available_origins:
        return False, f"{location.name}不接受{origin.name}出身的玩家"
    
    return True, ""
