"""军需商店 —— 每日刷新 NPC 商店。

用确定性种子 `random.Random(f"shop_{date}")` 每天生成同一组商品，无需缓存。
"""

from __future__ import annotations

import random
from datetime import date
from typing import TYPE_CHECKING

from .constants import (
    EQUIPMENT_REGISTRY,
    EQUIPMENT_TIER_NAMES,
    HEART_METHOD_MANUAL_PREFIX,
    HEART_METHOD_QUALITY_NAMES,
    HEART_METHOD_REGISTRY,
    GONGFA_REGISTRY,
    GONGFA_TIER_NAMES,
    GONGFA_SCROLL_PREFIX,
    ITEM_REGISTRY,
    REALM_CONFIG,
    get_daily_recycle_price,
    get_heart_method_manual_id,
    get_gongfa_scroll_id,
    ITEM_PREFIXES,
    PREFIX_COST,
    get_prefix_bonus,
    get_random_prefix,
    PREFIX_QUALITY_ORDER,
)
from .inventory import add_item

if TYPE_CHECKING:
    from .models import Player

# ── 常量 ──────────────────────────────────────────────────────

SHOP_ITEM_COUNT = 12
SHOP_ITEM_DAILY_LIMIT = 20
SHOP_PRICE_MULTIPLIER = 50

TYPE_WEIGHTS: dict[str, int] = {
    "consumable": 150,
    "pill": 250,
    "equipment": 250,
    "heart_method": 200,
    "gongfa": 150,
}

TIER_WEIGHTS: dict[int, int] = {
    0: 500,   # 凡品
    1: 300,   # 良品
    2: 100,   # 精品
    3: 1,     # 极品 — 千分之一
}

HM_QUALITY_WEIGHTS: dict[int, int] = {
    0: 700,   # 普通
    1: 200,   # 史诗
    2: 1,     # 传说 — 千分之一
}

# 技能按品质分档定价（在回收价×倍率基础上再乘）
HM_QUALITY_PRICE_MULTIPLIER: dict[int, int] = {
    0: 1,     # 普通 — 原价
    1: 5,     # 精良 — 5倍
    2: 25,    # 稀有 — 25倍
}

GONGFA_TIER_WEIGHTS: dict[int, int] = {
    1: 500,   # 初级 — 多
    2: 350,   # 中级
    3: 1,     # 高级 — 极稀
}

# ── 辅助 ──────────────────────────────────────────────────────


def _weighted_choice(rng: random.Random, weights: dict) -> object:
    """从 {key: weight} 字典中按权重随机选择一个 key。"""
    keys = list(weights.keys())
    vals = [weights[k] for k in keys]
    return rng.choices(keys, weights=vals, k=1)[0]


def _build_item_dict(
    item_id: str,
    name: str,
    item_type: str,
    price: int,
    description: str,
    *,
    extra: dict | None = None,
    daily_limit: int = 0,
) -> dict:
    d = {
        "item_id": item_id,
        "name": name,
        "type": item_type,
        "price": price,
        "description": description,
    }
    if daily_limit:
        d["daily_limit"] = daily_limit
    if extra:
        d.update(extra)
    return d


# ── 每日商品生成 ──────────────────────────────────────────────


def generate_daily_items(target_date: date | None = None) -> list[dict]:
    """生成当天商店商品列表（确定性）。"""
    d = target_date or date.today()
    rng = random.Random(f"shop_{d.isoformat()}")

    items: list[dict] = []
    seen_ids: set[str] = set()

    consumables = [
        it for it in ITEM_REGISTRY.values()
        if it.item_type == "consumable"
        and not it.item_id.startswith(HEART_METHOD_MANUAL_PREFIX)
        and not it.item_id.startswith(GONGFA_SCROLL_PREFIX)
        and not it.item_id.startswith("pill_")
    ]
    heart_manual_ids = {
        get_heart_method_manual_id(hm.method_id)
        for hm in HEART_METHOD_REGISTRY.values()
        if get_heart_method_manual_id(hm.method_id) in ITEM_REGISTRY
    }

    max_attempts = SHOP_ITEM_COUNT * 12
    attempts = 0
    while len(items) < SHOP_ITEM_COUNT and attempts < max_attempts:
        attempts += 1
        cat = _weighted_choice(rng, TYPE_WEIGHTS)

        if cat == "consumable":
            if not consumables:
                continue
            chosen = rng.choice(consumables)
            iid = chosen.item_id
            if iid in seen_ids:
                continue
            price = (get_daily_recycle_price(iid, d) or 5) * SHOP_PRICE_MULTIPLIER
            items.append(_build_item_dict(
                item_id=iid,
                name=chosen.name,
                item_type="consumable",
                price=price,
                description=chosen.description,
                daily_limit=SHOP_ITEM_DAILY_LIMIT,
            ))

        elif cat == "pill":
            from .pills import (
                pick_random_pill, SHOP_PILL_TIER_WEIGHTS, SHOP_PILL_GRADE_WEIGHTS,
                PILL_TIER_NAMES, PILL_GRADE_NAMES,
            )
            pill = pick_random_pill(rng, SHOP_PILL_TIER_WEIGHTS, SHOP_PILL_GRADE_WEIGHTS)
            if not pill:
                continue
            iid = pill.pill_id
            if iid in seen_ids:
                continue
            tier_name = PILL_TIER_NAMES.get(pill.tier, "")
            grade_name = PILL_GRADE_NAMES.get(pill.grade, "")
            items.append(_build_item_dict(
                item_id=iid,
                name=pill.name,
                item_type="pill",
                price=pill.price,
                description=pill.description,
                daily_limit=SHOP_ITEM_DAILY_LIMIT,
                extra={
                    "pill_tier": pill.tier,
                    "pill_tier_name": tier_name,
                    "pill_grade": pill.grade,
                    "pill_grade_name": grade_name,
                    "is_temp": pill.is_temp,
                    "duration": pill.duration,
                    "side_effect_desc": pill.side_effect_desc,
                },
            ))

        elif cat == "equipment":
            tier = _weighted_choice(rng, TIER_WEIGHTS)
            candidates = [eq for eq in EQUIPMENT_REGISTRY.values() if eq.tier == tier]
            if not candidates:
                continue
            eq = rng.choice(candidates)
            iid = eq.equip_id
            if iid in seen_ids:
                continue
            price = (get_daily_recycle_price(iid, d) or 5) * SHOP_PRICE_MULTIPLIER
            tier_name = EQUIPMENT_TIER_NAMES.get(eq.tier, "未知")
            items.append(_build_item_dict(
                item_id=iid,
                name=eq.name,
                item_type="equipment",
                price=price,
                description=eq.description,
                daily_limit=SHOP_ITEM_DAILY_LIMIT,
                extra={
                    "tier": eq.tier,
                    "tier_name": tier_name,
                    "slot": eq.slot,
                    "attack": eq.attack,
                    "defense": eq.defense,
                    "element": eq.element,
                    "element_damage": eq.element_damage,
                },
            ))

        elif cat == "heart_method":
            quality = _weighted_choice(rng, HM_QUALITY_WEIGHTS)
            candidates = [
                hm for hm in HEART_METHOD_REGISTRY.values()
                if hm.quality == quality and get_heart_method_manual_id(hm.method_id) in heart_manual_ids
            ]
            if not candidates:
                continue
            hm = rng.choice(candidates)
            iid = get_heart_method_manual_id(hm.method_id)
            if iid in seen_ids:
                continue
            price = (get_daily_recycle_price(iid, d) or 20) * SHOP_PRICE_MULTIPLIER * HM_QUALITY_PRICE_MULTIPLIER.get(hm.quality, 1)
            quality_name = HEART_METHOD_QUALITY_NAMES.get(hm.quality, "普通")
            realm_name = REALM_CONFIG.get(hm.realm, {}).get("name", "未知")
            items.append(_build_item_dict(
                item_id=iid,
                name=f"{hm.name}技能书",
                item_type="heart_method",
                price=price,
                description=hm.description,
                daily_limit=SHOP_ITEM_DAILY_LIMIT,
                extra={
                    "quality": hm.quality,
                    "quality_name": quality_name,
                    "realm": hm.realm,
                    "realm_name": realm_name,
                    "attack_bonus": hm.attack_bonus,
                    "defense_bonus": hm.defense_bonus,
                    "exp_multiplier": hm.exp_multiplier,
                },
            ))

        elif cat == "gongfa":
            gf_tier = _weighted_choice(rng, GONGFA_TIER_WEIGHTS)
            candidates = [gf for gf in GONGFA_REGISTRY.values() if gf.tier == gf_tier]
            if not candidates:
                continue
            gf = rng.choice(candidates)
            iid = get_gongfa_scroll_id(gf.gongfa_id)
            if iid in seen_ids:
                continue
            price = gf.recycle_price * SHOP_PRICE_MULTIPLIER
            tier_name = GONGFA_TIER_NAMES.get(gf.tier, "未知")
            parts = []
            if gf.attack_bonus:
                parts.append(f"攻+{gf.attack_bonus}")
            if gf.defense_bonus:
                parts.append(f"防+{gf.defense_bonus}")
            if gf.hp_regen:
                parts.append(f"血+{gf.hp_regen}")
            if gf.lingqi_regen:
                parts.append(f"灵+{gf.lingqi_regen}")
            stat_str = "/".join(parts) if parts else ""
            items.append(_build_item_dict(
                item_id=iid,
                name=f"{gf.name}战技",
                item_type="gongfa",
                price=price,
                description=gf.description,
                daily_limit=SHOP_ITEM_DAILY_LIMIT,
                extra={
                    "tier": gf.tier,
                    "tier_name": tier_name,
                    "attack_bonus": gf.attack_bonus,
                    "defense_bonus": gf.defense_bonus,
                    "hp_regen": gf.hp_regen,
                    "lingqi_regen": gf.lingqi_regen,
                    "stat_str": stat_str,
                },
            ))

        seen_ids.add(items[-1]["item_id"] if len(items) > len(seen_ids) else "")

    return items


# ── 购买逻辑 ──────────────────────────────────────────────────


async def buy_from_shop(
    player: Player,
    item_id: str,
    quantity: int,
) -> dict:
    """玩家从军需商店购买商品。"""
    if quantity < 1:
        return {"success": False, "message": "购买数量至少为1"}

    today = date.today().isoformat()
    daily_items = generate_daily_items()
    target = None
    for it in daily_items:
        if it["item_id"] == item_id:
            target = it
            break

    if target is None:
        return {"success": False, "message": "该商品不在今日商店中"}

    total_cost = target["price"] * quantity
    if player.spirit_stones < total_cost:
        return {
            "success": False,
            "message": f"第纳尔不足，需要{total_cost}第纳尔（持有{player.spirit_stones}）",
        }

    if item_id not in ITEM_REGISTRY:
        return {"success": False, "message": "该商品尚未完成注册，请稍后再试"}

    daily_limit = target.get("daily_limit", 0)
    player.spirit_stones -= total_cost

    result = await add_item(player, item_id, quantity)
    if not result["success"]:
        player.spirit_stones += total_cost
        return result

    return {
        "success": True,
        "message": f"成功购买{quantity}个【{target['name']}】，花费{total_cost}第纳尔",
        "item_name": target["name"],
        "quantity": quantity,
        "total_cost": total_cost,
        "_purchase_meta": {
            "item_id": item_id,
            "item_name": target["name"],
            "quantity": quantity,
            "unit_price": target["price"],
            "total_cost": total_cost,
            "purchased_at": today,
            "daily_limit": daily_limit,
        },
    }


# ── 铁匠铺功能 ─────────────────────────────────────────────────

def _calc_equipment_value(item_id: str) -> int:
    """计算装备价值（基于基础属性和品质）"""
    eq = EQUIPMENT_REGISTRY.get(item_id)
    if not eq:
        return 100
    
    base_value = (eq.attack + eq.defense + eq.hp // 10) * 10
    
    tier_multiplier = {0: 1.0, 1: 1.5, 2: 2.5, 3: 5.0}
    tier_mult = tier_multiplier.get(eq.tier, 1.0)
    
    return max(10, int(base_value * tier_mult))


async def blacksmith_repair_prefix(player: "Player", item_id: str) -> dict:
    """铁匠铺：修复装备前缀（移除坏前缀）- 按装备价值百分比收费"""
    if item_id not in player.inventory:
        return {"success": False, "message": "背包中没有此物品"}
    
    if not item_id.startswith("equipment_"):
        return {"success": False, "message": "只能修复装备的前缀"}
    
    current_prefix = getattr(player, f"{item_id}_prefix", None) or "none"
    prefix_def = ITEM_PREFIXES.get(current_prefix, ITEM_PREFIXES["none"])
    
    if prefix_def.quality not in ("terrible", "poor"):
        return {"success": False, "message": f"此装备前缀无需修复（当前：{prefix_def.name}）"}
    
    equip_value = _calc_equipment_value(item_id)
    
    if prefix_def.quality == "terrible":
        cost = int(equip_value * 0.4)
    else:
        cost = int(equip_value * 0.25)
    
    cost = max(1, cost)
    
    if player.spirit_stones < cost:
        return {"success": False, "message": f"第纳尔不足，需要{cost}第纳尔（装备价值：{equip_value}）"}
    
    player.spirit_stones -= cost
    
    setattr(player, f"{item_id}_prefix", "none")
    
    equip_def = EQUIPMENT_REGISTRY.get(item_id)
    equip_name = equip_def.name if equip_def else item_id
    
    return {
        "success": True,
        "message": f"成功修复【{equip_name}】的前缀，消耗{cost}第纳尔（装备价值：{equip_value}）",
        "cost": cost,
        "equip_value": equip_value,
    }


async def blacksmith_enhance_prefix(player: "Player", item_id: str, target_quality: str = "good") -> dict:
    """铁匠铺：为无前缀或普通前缀的装备添加好前缀 - 固定比例收费"""
    if item_id not in player.inventory:
        return {"success": False, "message": "背包中没有此物品"}
    
    if not item_id.startswith("equipment_"):
        return {"success": False, "message": "只能强化装备的前缀"}
    
    current_prefix = getattr(player, f"{item_id}_prefix", None) or "none"
    prefix_def = ITEM_PREFIXES.get(current_prefix, ITEM_PREFIXES["none"])
    
    if prefix_def.quality in ("excellent", "good"):
        return {"success": False, "message": "此装备已有优质前缀，无需强化"}
    
    if prefix_def.quality in ("terrible", "poor"):
        return {"success": False, "message": "此装备前缀损坏严重，请先修复后再强化"}
    
    equip_value = _calc_equipment_value(item_id)
    enhance_rate = 0.20
    cost = int(equip_value * enhance_rate)
    cost = max(1, cost)
    
    if player.spirit_stones < cost:
        return {"success": False, "message": f"第纳尔不足，需要{cost}第纳尔（装备价值：{equip_value}）"}
    
    player.spirit_stones -= cost
    
    new_prefix = get_random_prefix()
    while ITEM_PREFIXES.get(new_prefix, ITEM_PREFIXES["none"]).quality not in ("good", "excellent", "normal"):
        new_prefix = get_random_prefix()
    
    setattr(player, f"{item_id}_prefix", new_prefix)
    
    new_prefix_def = ITEM_PREFIXES[new_prefix]
    equip_def = EQUIPMENT_REGISTRY.get(item_id)
    equip_name = equip_def.name if equip_def else item_id
    
    return {
        "success": True,
        "message": f"成功为【{equip_name}】添加前缀【{new_prefix_def.name}】！消耗{cost}第纳尔（装备价值：{equip_value}）",
        "new_prefix": new_prefix,
        "new_prefix_name": new_prefix_def.name,
        "cost": cost,
    }


async def get_item_prefix_info(player: "Player", item_id: str) -> dict:
    """获取装备前缀信息"""
    if item_id not in player.inventory:
        return {"success": False, "message": "背包中没有此物品"}
    
    if not item_id.startswith("equipment_"):
        return {"success": False, "message": "这不是装备"}
    
    current_prefix = getattr(player, f"{item_id}_prefix", None) or "none"
    prefix_def = ITEM_PREFIXES.get(current_prefix, ITEM_PREFIXES["none"])
    
    equip_def = EQUIPMENT_REGISTRY.get(item_id)
    if not equip_def:
        return {"success": False, "message": "装备不存在"}
    
    base_attack = getattr(equip_def, "attack", 0)
    base_defense = getattr(equip_def, "defense", 0)
    base_hp = getattr(equip_def, "hp", 0)
    
    total_attack = base_attack + prefix_def.attack_bonus
    total_defense = base_defense + prefix_def.defense_bonus
    total_hp = base_hp + prefix_def.hp_bonus
    
    equip_value = _calc_equipment_value(item_id)
    
    if prefix_def.quality == "terrible":
        repair_cost = int(equip_value * 0.4)
    elif prefix_def.quality == "poor":
        repair_cost = int(equip_value * 0.25)
    else:
        repair_cost = 0
    
    enhance_cost = int(equip_value * 0.20)
    
    can_enhance = prefix_def.quality in ("none", "normal")
    
    return {
        "success": True,
        "item_id": item_id,
        "item_name": equip_def.name,
        "equip_value": equip_value,
        "prefix": current_prefix,
        "prefix_name": prefix_def.name,
        "prefix_quality": prefix_def.quality,
        "prefix_description": prefix_def.description,
        "bonuses": {
            "attack": prefix_def.attack_bonus,
            "defense": prefix_def.defense_bonus,
            "hp": prefix_def.hp_bonus,
            "crit_chance": prefix_def.crit_chance,
        },
        "total_stats": {
            "attack": total_attack,
            "defense": total_defense,
            "hp": total_hp,
        },
        "can_repair": prefix_def.quality in ("terrible", "poor"),
        "repair_cost": repair_cost,
        "can_enhance": can_enhance,
        "enhance_cost": enhance_cost,
    }
