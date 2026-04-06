"""
村庄产业系统 - 骑砍英雄传

通过完成村庄任务提升好感度，好感度达到60后可建造产业。
产业受地域限制，需要匹配村庄类型和产出资源。
NPC提供产业加成，匪患可能导致产业损坏。
"""

from __future__ import annotations

import time
import random
from dataclasses import dataclass, field
from typing import Optional


# ══════════════════════════════════════════════════════════════
# 产业定义
# ══════════════════════════════════════════════════════════════

@dataclass
class IndustryDef:
    """产业定义。"""
    industry_id: str
    name: str
    icon: str
    description: str
    industry_type: str           # agriculture, fishery, animal, mining, general
    base_cost: int              # 建造费用
    upgrade_cost_multiplier: float  # 升级费用倍率
    max_level: int              # 最大等级
    base_daily_income: int      # 每日第纳尔产出
    resource_type: Optional[str] # 产出资源类型
    base_resource_amount: int   # 基础每日资源产出
    required_favor: int         # 所需好感度
    required_village_types: list[str]  # 适用的村庄类型
    required_production: Optional[str]  # 特殊要求（村庄产出资源）
    required_prosperity: int    # 所需最低繁荣度


INDUSTRIES: dict[str, IndustryDef] = {
    # 农业产业
    "farm": IndustryDef(
        industry_id="farm", name="农田", icon="🌾",
        description="开垦农田种植作物，产出小麦等农产品",
        industry_type="agriculture", base_cost=300, upgrade_cost_multiplier=1.5,
        max_level=5, base_daily_income=20, resource_type="wheat",
        base_resource_amount=2, required_favor=60,
        required_village_types=["农业"], required_production=None,
        required_prosperity=0,
    ),
    "mill": IndustryDef(
        industry_id="mill", name="磨坊", icon="🏭",
        description="将谷物磨成面粉，提升农产品附加值",
        industry_type="agriculture", base_cost=500, upgrade_cost_multiplier=1.8,
        max_level=5, base_daily_income=30, resource_type="flour",
        base_resource_amount=1, required_favor=65,
        required_village_types=["农业"], required_production=None,
        required_prosperity=0,
    ),
    "brewery": IndustryDef(
        industry_id="brewery", name="酿酒坊", icon="🍷",
        description="利用葡萄酿造葡萄酒，高附加值产业",
        industry_type="agriculture", base_cost=800, upgrade_cost_multiplier=2.0,
        max_level=5, base_daily_income=50, resource_type="wine",
        base_resource_amount=1, required_favor=70,
        required_village_types=["农业"], required_production="葡萄",
        required_prosperity=0,
    ),
    # 渔业产业
    "fishery": IndustryDef(
        industry_id="fishery", name="渔场", icon="🐟",
        description="在海边或河边建立渔场，每日捕鱼",
        industry_type="fishery", base_cost=300, upgrade_cost_multiplier=1.5,
        max_level=5, base_daily_income=25, resource_type="fish",
        base_resource_amount=3, required_favor=60,
        required_village_types=["渔业"], required_production=None,
        required_prosperity=0,
    ),
    "drying_rack": IndustryDef(
        industry_id="drying_rack", name="腌制坊", icon="🐠",
        description="将鲜鱼腌制成鱼干，延长保存期并提升价值",
        industry_type="fishery", base_cost=450, upgrade_cost_multiplier=1.6,
        max_level=5, base_daily_income=35, resource_type="dried_fish",
        base_resource_amount=2, required_favor=65,
        required_village_types=["渔业"], required_production=None,
        required_prosperity=0,
    ),
    # 畜牧产业
    "ranch": IndustryDef(
        industry_id="ranch", name="牧场", icon="🐄",
        description="放牧牛羊，产出肉类和皮毛",
        industry_type="animal", base_cost=400, upgrade_cost_multiplier=1.5,
        max_level=5, base_daily_income=30, resource_type="cattle",
        base_resource_amount=1, required_favor=60,
        required_village_types=["畜牧"], required_production=None,
        required_prosperity=0,
    ),
    "dairy": IndustryDef(
        industry_id="dairy", name="奶酪坊", icon="🧀",
        description="利用牛奶制作奶酪，高附加值畜牧产品",
        industry_type="animal", base_cost=550, upgrade_cost_multiplier=1.7,
        max_level=5, base_daily_income=40, resource_type="cheese",
        base_resource_amount=2, required_favor=65,
        required_village_types=["畜牧"], required_production=None,
        required_prosperity=0,
    ),
    "tannery": IndustryDef(
        industry_id="tannery", name="皮革工坊", icon="🧶",
        description="将动物皮毛加工成皮革",
        industry_type="animal", base_cost=600, upgrade_cost_multiplier=1.8,
        max_level=5, base_daily_income=45, resource_type="leather",
        base_resource_amount=1, required_favor=70,
        required_village_types=["畜牧"], required_production=None,
        required_prosperity=0,
    ),
    # 矿业产业
    "mine": IndustryDef(
        industry_id="mine", name="矿场", icon="⛏️",
        description="开采矿石，获取珍贵的矿产资源",
        industry_type="mining", base_cost=500, upgrade_cost_multiplier=1.6,
        max_level=5, base_daily_income=35, resource_type="iron_ore",
        base_resource_amount=2, required_favor=60,
        required_village_types=["矿业"], required_production=None,
        required_prosperity=0,
    ),
    "smeltery": IndustryDef(
        industry_id="smeltery", name="冶炼厂", icon="🔥",
        description="将矿石冶炼成金属锭，提升矿产价值",
        industry_type="mining", base_cost=700, upgrade_cost_multiplier=1.9,
        max_level=5, base_daily_income=55, resource_type="iron_ingot",
        base_resource_amount=1, required_favor=70,
        required_village_types=["矿业"], required_production=None,
        required_prosperity=0,
    ),
    # 通用产业
    "tavern": IndustryDef(
        industry_id="tavern", name="旅馆", icon="🏨",
        description="为过往旅人提供住宿，稳定的收入来源",
        industry_type="general", base_cost=600, upgrade_cost_multiplier=1.7,
        max_level=5, base_daily_income=60, resource_type=None,
        base_resource_amount=0, required_favor=65,
        required_village_types=["农业", "渔业", "畜牧", "矿业"], required_production=None,
        required_prosperity=40,
    ),
    "warehouse": IndustryDef(
        industry_id="warehouse", name="仓库", icon="📦",
        description="存储货物的仓库，提供额外的存储空间",
        industry_type="general", base_cost=400, upgrade_cost_multiplier=1.5,
        max_level=5, base_daily_income=15, resource_type=None,
        base_resource_amount=0, required_favor=60,
        required_village_types=["农业", "渔业", "畜牧", "矿业"], required_production=None,
        required_prosperity=0,
    ),
    "market": IndustryDef(
        industry_id="market", name="集市", icon="🏪",
        description="建立集市吸引商人，获得贸易税收",
        industry_type="general", base_cost=800, upgrade_cost_multiplier=2.0,
        max_level=5, base_daily_income=80, resource_type=None,
        base_resource_amount=0, required_favor=75,
        required_village_types=["农业", "渔业", "畜牧", "矿业"], required_production=None,
        required_prosperity=50,
    ),
}

INDUSTRY_MAX_PER_VILLAGE = 5
INDUSTRY_MAX_COLLECT_HOURS_INCOME = 48
INDUSTRY_MAX_COLLECT_HOURS_RESOURCE = 24
INDUSTRY_DAMAGE_BASE_RATE = 0.02


# ══════════════════════════════════════════════════════════════
# NPC产业加成
# ══════════════════════════════════════════════════════════════

@dataclass
class NPCIndustryBonus:
    """NPC产业加成。"""
    npc_id: str
    npc_name: str
    industry_type: str
    bonus_type: str          # income, resource, cost
    bonus_value: float       # 加成比例
    required_favor: int
    description: str


NPC_INDUSTRY_BONUSES: list[NPCIndustryBonus] = [
    NPCIndustryBonus(
        npc_id="elder_village", npc_name="村长",
        industry_type="all", bonus_type="cost", bonus_value=0.10,
        required_favor=70, description="建造费用-10%",
    ),
    NPCIndustryBonus(
        npc_id="elder_village", npc_name="村长",
        industry_type="all", bonus_type="income", bonus_value=0.05,
        required_favor=80, description="所有产业收入+5%",
    ),
]


def get_npc_bonus_for_industry(
    npc_favor_states: dict,
    user_id: str,
    industry_type: str,
) -> dict:
    """获取NPC对产业的加成。"""
    bonuses = {"income": 0.0, "resource": 0.0, "cost": 0.0}
    from .npc_system import get_npc_favor_state, _npc_favor_states
    for bonus_def in NPC_INDUSTRY_BONUSES:
        if bonus_def.industry_type != "all" and bonus_def.industry_type != industry_type:
            continue
        state = get_npc_favor_state(_npc_favor_states, user_id, bonus_def.npc_id)
        if state.favor >= bonus_def.required_favor:
            bonuses[bonus_def.bonus_type] += bonus_def.bonus_value
    return bonuses


# ══════════════════════════════════════════════════════════════
# 产业状态
# ══════════════════════════════════════════════════════════════

INDUSTRY_STATUS_INTACT = "intact"
INDUSTRY_STATUS_LIGHT_DAMAGE = "light_damage"
INDUSTRY_STATUS_HEAVY_DAMAGE = "heavy_damage"
INDUSTRY_STATUS_DESTROYED = "destroyed"

INDUSTRY_STATUS_NAMES = {
    INDUSTRY_STATUS_INTACT: "完好",
    INDUSTRY_STATUS_LIGHT_DAMAGE: "轻微损坏",
    INDUSTRY_STATUS_HEAVY_DAMAGE: "严重损坏",
    INDUSTRY_STATUS_DESTROYED: "完全摧毁",
}

INDUSTRY_STATUS_OUTPUT_MULTIPLIER = {
    INDUSTRY_STATUS_INTACT: 1.0,
    INDUSTRY_STATUS_LIGHT_DAMAGE: 0.5,
    INDUSTRY_STATUS_HEAVY_DAMAGE: 0.0,
    INDUSTRY_STATUS_DESTROYED: 0.0,
}

INDUSTRY_REPAIR_COST_MULTIPLIER = {
    INDUSTRY_STATUS_LIGHT_DAMAGE: 0.20,
    INDUSTRY_STATUS_HEAVY_DAMAGE: 0.50,
    INDUSTRY_STATUS_DESTROYED: 1.0,
}


@dataclass
class IndustryInstance:
    """玩家拥有的产业实例。"""
    industry_id: str
    level: int = 1
    status: str = INDUSTRY_STATUS_INTACT
    built_time: float = 0.0
    last_collect_time: float = 0.0
    last_damage_time: float = 0.0


@dataclass
class VillageIndustries:
    """村庄的产业集合。"""
    village_id: str
    industries: dict[str, IndustryInstance] = field(default_factory=dict)
    total_count: int = 0


# ══════════════════════════════════════════════════════════════
# 核心函数
# ══════════════════════════════════════════════════════════════

def get_available_industries(
    village_id: str,
    village_type: str,
    village_production: str,
    village_prosperity: int,
    favor: int,
    current_count: int,
) -> list[dict]:
    """获取可建造和已建造的产业信息。"""
    from .map_system import ALL_LOCATIONS
    loc = ALL_LOCATIONS.get(village_id)
    if not loc:
        return []

    result = []
    for ind_id, ind_def in INDUSTRIES.items():
        if village_type not in ind_def.required_village_types:
            continue
        if ind_def.required_production and village_production != ind_def.required_production:
            continue
        if village_prosperity < ind_def.required_prosperity:
            continue
        if favor < ind_def.required_favor:
            continue
        if current_count >= INDUSTRY_MAX_PER_VILLAGE and ind_id not in []:
            continue

        result.append({
            "industry_id": ind_def.industry_id,
            "name": ind_def.name,
            "icon": ind_def.icon,
            "description": ind_def.description,
            "industry_type": ind_def.industry_type,
            "base_cost": ind_def.base_cost,
            "upgrade_cost_multiplier": ind_def.upgrade_cost_multiplier,
            "max_level": ind_def.max_level,
            "base_daily_income": ind_def.base_daily_income,
            "resource_type": ind_def.resource_type,
            "base_resource_amount": ind_def.base_resource_amount,
            "required_favor": ind_def.required_favor,
            "required_prosperity": ind_def.required_prosperity,
        })
    return result


def calculate_build_cost(ind_def: IndustryDef, npc_bonuses: dict) -> int:
    """计算建造费用（含NPC加成）。"""
    cost = ind_def.base_cost
    cost_discount = npc_bonuses.get("cost", 0.0)
    return max(1, int(cost * (1 - cost_discount)))


def calculate_upgrade_cost(ind_def: IndustryDef, current_level: int, npc_bonuses: dict) -> int:
    """计算升级费用。"""
    base = ind_def.base_cost
    multiplier = ind_def.upgrade_cost_multiplier ** (current_level - 1)
    cost = int(base * multiplier)
    cost_discount = npc_bonuses.get("cost", 0.0)
    return max(1, int(cost * (1 - cost_discount)))


def calculate_industry_output(
    ind_def: IndustryDef,
    instance: IndustryInstance,
    npc_bonuses: dict,
) -> dict:
    """计算产业累积产出。"""
    now = time.time()
    hours_passed = (now - instance.last_collect_time) / 3600.0
    if hours_passed < 0.1:
        hours_passed = 0.1

    level_multiplier = 1.0 + (instance.level - 1) * 0.5
    status_multiplier = INDUSTRY_STATUS_OUTPUT_MULTIPLIER.get(instance.status, 0.0)
    income_bonus = npc_bonuses.get("income", 0.0)
    resource_bonus = npc_bonuses.get("resource", 0.0)

    max_hours_income = min(hours_passed, INDUSTRY_MAX_COLLECT_HOURS_INCOME)
    income = int(ind_def.base_daily_income * level_multiplier * (1 + income_bonus) * status_multiplier * max_hours_income / 24)

    resource_amount = 0
    resource_type = ind_def.resource_type
    if resource_type and status_multiplier > 0:
        max_hours_resource = min(hours_passed, INDUSTRY_MAX_COLLECT_HOURS_RESOURCE)
        resource_amount = int(ind_def.base_resource_amount * level_multiplier * (1 + resource_bonus) * status_multiplier * max_hours_resource / 24)
        resource_amount = max(0, resource_amount)

    return {
        "income": max(0, income),
        "resource_type": resource_type,
        "resource_amount": resource_amount,
        "hours_passed": round(hours_passed, 1),
    }


def build_industry(
    village_industries: dict,
    user_id: str,
    village_id: str,
    industry_id: str,
    village_type: str,
    village_production: str,
    village_prosperity: int,
    favor: int,
    player_gold: int,
    npc_bonuses: dict,
) -> dict:
    """建造产业。"""
    ind_def = INDUSTRIES.get(industry_id)
    if not ind_def:
        return {"success": False, "message": "产业不存在"}

    if village_type not in ind_def.required_village_types:
        return {"success": False, "message": f"{ind_def.name}不能在{village_type}村建造"}
    if ind_def.required_production and village_production != ind_def.required_production:
        return {"success": False, "message": f"{ind_def.name}需要村庄产出为{ind_def.required_production}"}
    if village_prosperity < ind_def.required_prosperity:
        return {"success": False, "message": f"繁荣度不足，需要{ind_def.required_prosperity}"}
    if favor < ind_def.required_favor:
        return {"success": False, "message": f"好感度不足，需要{ind_def.required_favor}"}

    if village_id not in village_industries:
        village_industries[village_id] = {"industries": {}, "total_count": 0}
    v_ind = village_industries[village_id]
    if v_ind.get("total_count", 0) >= INDUSTRY_MAX_PER_VILLAGE:
        return {"success": False, "message": f"该村庄产业已达上限({INDUSTRY_MAX_PER_VILLAGE}个)"}
    if industry_id in v_ind.get("industries", {}):
        return {"success": False, "message": "该产业已存在"}

    cost = calculate_build_cost(ind_def, npc_bonuses)
    if player_gold < cost:
        return {"success": False, "message": f"第纳尔不足，需要{cost}"}

    now = time.time()
    v_ind["industries"][industry_id] = {
        "level": 1,
        "status": INDUSTRY_STATUS_INTACT,
        "built_time": now,
        "last_collect_time": now,
        "last_damage_time": 0,
    }
    v_ind["total_count"] = v_ind.get("total_count", 0) + 1

    return {
        "success": True,
        "message": f"成功建造{ind_def.name}",
        "cost": cost,
        "industry": {
            "industry_id": industry_id,
            "name": ind_def.name,
            "icon": ind_def.icon,
            "level": 1,
            "status": INDUSTRY_STATUS_INTACT,
        },
    }


def upgrade_industry(
    village_industries: dict,
    user_id: str,
    village_id: str,
    industry_id: str,
    player_gold: int,
    npc_bonuses: dict,
) -> dict:
    """升级产业。"""
    ind_def = INDUSTRIES.get(industry_id)
    if not ind_def:
        return {"success": False, "message": "产业不存在"}

    if village_id not in village_industries:
        return {"success": False, "message": "该村庄没有产业"}
    v_ind = village_industries[village_id]
    if industry_id not in v_ind.get("industries", {}):
        return {"success": False, "message": "该产业不存在"}

    inst = v_ind["industries"][industry_id]
    if inst["level"] >= ind_def.max_level:
        return {"success": False, "message": f"产业已达最高等级({ind_def.max_level})"}

    cost = calculate_upgrade_cost(ind_def, inst["level"], npc_bonuses)
    if player_gold < cost:
        return {"success": False, "message": f"第纳尔不足，需要{cost}"}

    inst["level"] += 1
    return {
        "success": True,
        "message": f"{ind_def.name}升级到Lv.{inst['level']}",
        "cost": cost,
        "new_level": inst["level"],
    }


def collect_industry_income(
    village_industries: dict,
    user_id: str,
    village_id: str,
    npc_bonuses: dict,
) -> dict:
    """收取所有产业产出。"""
    if village_id not in village_industries:
        return {"success": False, "message": "该村庄没有产业"}
    v_ind = village_industries[village_id]
    industries = v_ind.get("industries", {})
    if not industries:
        return {"success": False, "message": "没有可收取的产业"}

    total_income = 0
    total_resources: dict[str, int] = {}
    collected = []

    for ind_id, inst in industries.items():
        ind_def = INDUSTRIES.get(ind_id)
        if not ind_def:
            continue
        if inst["status"] == INDUSTRY_STATUS_DESTROYED:
            continue

        ind_bonuses = npc_bonuses
        output = calculate_industry_output(ind_def, IndustryInstance(
            industry_id=ind_id,
            level=inst["level"],
            status=inst["status"],
            last_collect_time=inst["last_collect_time"],
        ), ind_bonuses)

        if output["income"] > 0 or output["resource_amount"] > 0:
            total_income += output["income"]
            if output["resource_type"] and output["resource_amount"] > 0:
                total_resources[output["resource_type"]] = total_resources.get(output["resource_type"], 0) + output["resource_amount"]
            inst["last_collect_time"] = time.time()
            collected.append({
                "industry_id": ind_id,
                "name": ind_def.name,
                "icon": ind_def.icon,
                "income": output["income"],
                "resource_type": output["resource_type"],
                "resource_amount": output["resource_amount"],
            })

    if not collected:
        return {"success": False, "message": "暂无可收取的产出"}

    return {
        "success": True,
        "message": f"收取了{len(collected)}个产业的产出",
        "total_income": total_income,
        "total_resources": total_resources,
        "collected": collected,
    }


def repair_industry(
    village_industries: dict,
    user_id: str,
    village_id: str,
    industry_id: str,
    player_gold: int,
) -> dict:
    """修复产业。"""
    ind_def = INDUSTRIES.get(industry_id)
    if not ind_def:
        return {"success": False, "message": "产业不存在"}

    if village_id not in village_industries:
        return {"success": False, "message": "该村庄没有产业"}
    v_ind = village_industries[village_id]
    if industry_id not in v_ind.get("industries", {}):
        return {"success": False, "message": "该产业不存在"}

    inst = v_ind["industries"][industry_id]
    if inst["status"] == INDUSTRY_STATUS_INTACT:
        return {"success": False, "message": "产业状态完好，无需修复"}
    if inst["status"] == INDUSTRY_STATUS_DESTROYED:
        return {"success": False, "message": "产业已完全摧毁，需要重新建造"}

    repair_multiplier = INDUSTRY_REPAIR_COST_MULTIPLIER.get(inst["status"], 0.5)
    cost = int(ind_def.base_cost * repair_multiplier)
    if player_gold < cost:
        return {"success": False, "message": f"第纳尔不足，需要{cost}"}

    inst["status"] = INDUSTRY_STATUS_INTACT
    return {
        "success": True,
        "message": f"{ind_def.name}已修复",
        "cost": cost,
    }


def process_industry_damage(
    village_industries: dict,
    village_id: str,
    bandit_threat_level: int,
    guard_bonus: float = 0.0,
) -> list[dict]:
    """处理产业损害（定时任务调用）。"""
    if village_id not in village_industries:
        return []
    v_ind = village_industries[village_id]
    industries = v_ind.get("industries", {})
    damaged = []

    damage_rate = INDUSTRY_DAMAGE_BASE_RATE * (1 + bandit_threat_level * 0.3) * (1 - guard_bonus)
    if damage_rate <= 0:
        return []

    for ind_id, inst in industries.items():
        if inst["status"] == INDUSTRY_STATUS_DESTROYED:
            continue
        if random.random() < damage_rate:
            old_status = inst["status"]
            if old_status == INDUSTRY_STATUS_INTACT:
                inst["status"] = INDUSTRY_STATUS_LIGHT_DAMAGE
            elif old_status == INDUSTRY_STATUS_LIGHT_DAMAGE:
                inst["status"] = INDUSTRY_STATUS_HEAVY_DAMAGE
            elif old_status == INDUSTRY_STATUS_HEAVY_DAMAGE:
                inst["status"] = INDUSTRY_STATUS_DESTROYED

            inst["last_damage_time"] = time.time()
            ind_def = INDUSTRIES.get(ind_id)
            damaged.append({
                "industry_id": ind_id,
                "name": ind_def.name if ind_def else ind_id,
                "old_status": INDUSTRY_STATUS_NAMES.get(old_status, old_status),
                "new_status": INDUSTRY_STATUS_NAMES.get(inst["status"], inst["status"]),
            })

    return damaged


def get_industry_status_detail(
    village_industries: dict,
    village_id: str,
    npc_bonuses: dict,
) -> dict:
    """获取产业详细状态。"""
    if village_id not in village_industries:
        return {"industries": [], "total_count": 0, "max_count": INDUSTRY_MAX_PER_VILLAGE}

    v_ind = village_industries[village_id]
    industries = v_ind.get("industries", {})
    result = []

    for ind_id, inst in industries.items():
        ind_def = INDUSTRIES.get(ind_id)
        if not ind_def:
            continue

        output = calculate_industry_output(ind_def, IndustryInstance(
            industry_id=ind_id,
            level=inst["level"],
            status=inst["status"],
            last_collect_time=inst["last_collect_time"],
        ), npc_bonuses)

        upgrade_cost = 0
        can_upgrade = False
        if inst["level"] < ind_def.max_level:
            can_upgrade = True
            upgrade_cost = calculate_upgrade_cost(ind_def, inst["level"], npc_bonuses)

        repair_cost = 0
        can_repair = False
        if inst["status"] in (INDUSTRY_STATUS_LIGHT_DAMAGE, INDUSTRY_STATUS_HEAVY_DAMAGE):
            can_repair = True
            repair_cost = int(ind_def.base_cost * INDUSTRY_REPAIR_COST_MULTIPLIER[inst["status"]])

        result.append({
            "industry_id": ind_id,
            "name": ind_def.name,
            "icon": ind_def.icon,
            "description": ind_def.description,
            "industry_type": ind_def.industry_type,
            "level": inst["level"],
            "max_level": ind_def.max_level,
            "status": inst["status"],
            "status_name": INDUSTRY_STATUS_NAMES.get(inst["status"], inst["status"]),
            "pending_income": output["income"],
            "pending_resource_type": output["resource_type"],
            "pending_resource_amount": output["resource_amount"],
            "hours_since_collect": output["hours_passed"],
            "can_upgrade": can_upgrade,
            "upgrade_cost": upgrade_cost,
            "can_repair": can_repair,
            "repair_cost": repair_cost,
            "built_time": inst["built_time"],
            "last_collect_time": inst["last_collect_time"],
        })

    return {
        "industries": result,
        "total_count": v_ind.get("total_count", 0),
        "max_count": INDUSTRY_MAX_PER_VILLAGE,
    }
