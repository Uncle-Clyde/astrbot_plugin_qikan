"""简化部队系统 - 骑砍风格。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TroopType:
    """兵种定义。"""
    troop_id: str
    name: str
    faction: str          # 所属阵营
    attack: int           # 攻击力
    defense: int          # 防御力
    hp: int               # 生命值
    cost: int             # 招募费用（第纳尔）
    wage: int             # 每日军饷（第纳尔）
    description: str


# 兵种注册表 - 6大阵营各3种基础兵种
TROOP_REGISTRY: dict[str, TroopType] = {
    # 斯瓦迪亚
    "swadian_recruit": TroopType(
        troop_id="swadian_recruit", name="斯瓦迪亚新兵", faction="swadia",
        attack=8, defense=5, hp=30, cost=50, wage=2,
        description="斯瓦迪亚的基础步兵。",
    ),
    "swadian_infantry": TroopType(
        troop_id="swadian_infantry", name="斯瓦迪亚步兵", faction="swadia",
        attack=15, defense=12, hp=60, cost=150, wage=5,
        description="训练有素的斯瓦迪亚重装步兵。",
    ),
    "swadian_knight": TroopType(
        troop_id="swadian_knight", name="斯瓦迪亚骑士", faction="swadia",
        attack=30, defense=25, hp=100, cost=400, wage=12,
        description="卡拉迪亚最精锐的重装骑士。",
    ),
    # 维吉亚
    "vaegir_recruit": TroopType(
        troop_id="vaegir_recruit", name="维吉亚新兵", faction="vaegir",
        attack=6, defense=4, hp=25, cost=40, wage=2,
        description="维吉亚的基础步兵。",
    ),
    "vaegir_archer": TroopType(
        troop_id="vaegir_archer", name="维吉亚弓箭手", faction="vaegir",
        attack=18, defense=8, hp=40, cost=120, wage=4,
        description="精准的维吉亚弓箭手。",
    ),
    "vaegir_guard": TroopType(
        troop_id="vaegir_guard", name="维吉亚近卫", faction="vaegir",
        attack=25, defense=20, hp=90, cost=350, wage=10,
        description="维吉亚精锐的近卫步兵。",
    ),
    # 诺德
    "nord_recruit": TroopType(
        troop_id="nord_recruit", name="诺德新兵", faction="nord",
        attack=10, defense=6, hp=35, cost=60, wage=3,
        description="北方来的诺德战士。",
    ),
    "nord_huscarl": TroopType(
        troop_id="nord_huscarl", name="诺德斧兵", faction="nord",
        attack=22, defense=15, hp=70, cost=200, wage=6,
        description="手持巨斧的诺德精锐战士。",
    ),
    "nord_veteran": TroopType(
        troop_id="nord_veteran", name="诺德皇家侍卫", faction="nord",
        attack=35, defense=30, hp=120, cost=500, wage=15,
        description="诺德王国最精锐的皇家侍卫。",
    ),
    # 罗多克
    "rhodok_recruit": TroopType(
        troop_id="rhodok_recruit", name="罗多克民兵", faction="rhodok",
        attack=7, defense=8, hp=30, cost=45, wage=2,
        description="罗多克的民兵部队。",
    ),
    "rhodok_spearman": TroopType(
        troop_id="rhodok_spearman", name="罗多克矛兵", faction="rhodok",
        attack=12, defense=18, hp=55, cost=130, wage=4,
        description="装备长矛的罗多克步兵。",
    ),
    "rhodok_crossbow": TroopType(
        troop_id="rhodok_crossbow", name="罗多克弩手", faction="rhodok",
        attack=20, defense=10, hp=45, cost=180, wage=5,
        description="装备重弩的罗多克远程部队。",
    ),
    # 库吉特
    "khergit_recruit": TroopType(
        troop_id="khergit_recruit", name="库吉特牧民", faction="khergit",
        attack=8, defense=4, hp=25, cost=40, wage=2,
        description="草原上的库吉特牧民。",
    ),
    "khergit_horseman": TroopType(
        troop_id="khergit_horseman", name="库吉特骑手", faction="khergit",
        attack=16, defense=10, hp=50, cost=140, wage=5,
        description="骑射兼备的库吉特骑兵。",
    ),
    "khergit_lancer": TroopType(
        troop_id="khergit_lancer", name="库吉特汗卫", faction="khergit",
        attack=28, defense=18, hp=85, cost=380, wage=11,
        description="库吉特最精锐的骑枪部队。",
    ),
    # 萨兰德
    "sarranid_recruit": TroopType(
        troop_id="sarranid_recruit", name="萨兰德步兵", faction="sarranid",
        attack=7, defense=6, hp=28, cost=45, wage=2,
        description="萨兰德的普通步兵。",
    ),
    "sarranid_sword": TroopType(
        troop_id="sarranid_sword", name="萨兰德剑士", faction="sarranid",
        attack=16, defense=14, hp=55, cost=140, wage=5,
        description="手持弯刀的萨兰德战士。",
    ),
    "sarranid_mamluke": TroopType(
        troop_id="sarranid_mamluke", name="萨兰德马穆鲁克", faction="sarranid",
        attack=26, defense=22, hp=95, cost=420, wage=12,
        description="沙漠中精锐的马穆鲁克骑兵。",
    ),
}

FACTION_NAMES = {
    "swadia": "斯瓦迪亚",
    "vaegir": "维吉亚",
    "nord": "诺德",
    "rhodok": "罗多克",
    "khergit": "库吉特",
    "sarranid": "萨兰德",
}


def get_troop(troop_id: str) -> Optional[TroopType]:
    """获取兵种定义。"""
    return TROOP_REGISTRY.get(troop_id)


def get_all_troops() -> list[TroopType]:
    """获取所有兵种。"""
    return list(TROOP_REGISTRY.values())


def get_troops_by_faction(faction: str) -> list[TroopType]:
    """获取某一阵营的所有兵种。"""
    return [t for t in TROOP_REGISTRY.values() if t.faction == faction]


def calc_troop_damage(troops: dict[str, int]) -> int:
    """计算部队提供的额外伤害。
    
    troops: {troop_id: count}
    返回: 部队总攻击力
    """
    total = 0
    for troop_id, count in troops.items():
        troop = TROOP_REGISTRY.get(troop_id)
        if troop and count > 0:
            total += troop.attack * count
    return total


def calc_total_wage(troops: dict[str, int]) -> int:
    """计算部队总军饷。"""
    total = 0
    for troop_id, count in troops.items():
        troop = TROOP_REGISTRY.get(troop_id)
        if troop and count > 0:
            total += troop.wage * count
    return total


def calc_max_troops(leadership_skill: int) -> int:
    """根据统御技能计算最大部队数量。"""
    return leadership_skill * 5 + 5  # 基础5个，每级统御+5
