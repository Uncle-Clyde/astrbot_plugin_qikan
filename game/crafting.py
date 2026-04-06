"""
制作系统

玩家可以消耗草药制作医疗物品，需要草药学技能。
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional


@dataclass
class CraftRecipe:
    """制作配方"""
    recipe_id: str
    name: str
    description: str
    herb_cost: dict[str, int]  # {herb_id: count}
    lingqi_cost: int
    skill_level_req: int
    result_item_id: str
    result_count: int = 1
    result_heal: int = 0


RECIPES: dict[str, CraftRecipe] = {
    "make_bandage": CraftRecipe(
        recipe_id="make_bandage",
        name="制作绷带",
        description="用普通草药制作绷带",
        herb_cost={"herb_common": 1},
        lingqi_cost=5,
        skill_level_req=1,
        result_item_id="bandage",
        result_count=1,
        result_heal=25,
    ),
    "make_bandage_advanced": CraftRecipe(
        recipe_id="make_bandage_advanced",
        name="制作高级绷带",
        description="用优质草药制作，效果更好",
        herb_cost={"herb_good": 2},
        lingqi_cost=10,
        skill_level_req=3,
        result_item_id="bandage_advanced",
        result_count=1,
        result_heal=60,
    ),
    "make_antidote": CraftRecipe(
        recipe_id="make_antidote",
        name="制作解毒剂",
        description="用珍稀草药制作，可解毒",
        herb_cost={"herb_good": 1, "herb_rare": 2},
        lingqi_cost=15,
        skill_level_req=5,
        result_item_id="antidote",
        result_count=1,
        result_heal=20,
    ),
    "make_healing_herb": CraftRecipe(
        recipe_id="make_healing_herb",
        name="制作草药包",
        description="直接使用草药，恢复生命",
        herb_cost={"herb_common": 1},
        lingqi_cost=0,
        skill_level_req=1,
        result_item_id="herb_use",
        result_count=1,
        result_heal=15,
    ),
}


MEDICAL_ITEMS: dict[str, dict] = {
    "bandage": {
        "name": "绷带",
        "description": "战场用绷带，可恢复少量生命",
        "heal_amount": 25,
        "can_use_in_combat": True,
    },
    "bandage_advanced": {
        "name": "高级绷带",
        "description": "效果更好的绷带，可恢复较多生命",
        "heal_amount": 60,
        "can_use_in_combat": True,
    },
    "herb_use": {
        "name": "直接使用草药",
        "description": "直接食用采集的草药",
        "heal_amount": 15,
        "can_use_in_combat": True,
    },
    "antidote": {
        "name": "解毒剂",
        "description": "解除中毒状态",
        "heal_amount": 20,
        "can_use_in_combat": True,
        "clears_debuff": "poison",
    },
}


def get_recipe(recipe_id: str) -> Optional[CraftRecipe]:
    """获取配方"""
    return RECIPES.get(recipe_id)


def get_all_recipes() -> list[CraftRecipe]:
    """获取所有配方"""
    return list(RECIPES.values())


def get_available_recipes(herbalism_level: int) -> list[CraftRecipe]:
    """根据草药学等级获取可用配方"""
    return [r for r in RECIPES.values() if r.skill_level_req <= herbalism_level]


def can_craft(player, recipe: CraftRecipe) -> tuple[bool, str]:
    """
    检查是否可以制作
    
    Returns:
        (can_craft: bool, reason: str)
    """
    herbalism_level = player.skills.get(31, 0)
    
    if herbalism_level < recipe.skill_level_req:
        return False, f"需要草药学 {recipe.skill_level_req} 级"
    
    if player.lingqi < recipe.lingqi_cost:
        return False, f"体力不足，需要 {recipe.lingqi_cost} 点体力"
    
    for herb_id, count in recipe.herb_cost.items():
        current = player.inventory.get(herb_id, 0) if hasattr(player, 'inventory') else 0
        if current < count:
            herb_name = herb_id.replace("herb_", "")
            return False, f"材料不足: 需要{count}个{herb_name}"
    
    return True, ""


def craft_item(player, recipe_id: str) -> dict:
    """
    制作物品
    
    Returns:
        dict: {"success": bool, "message": str, "item": str}
    """
    recipe = get_recipe(recipe_id)
    if not recipe:
        return {"success": False, "message": "未知的配方", "item": None}
    
    can, reason = can_craft(player, recipe)
    if not can:
        return {"success": False, "message": reason, "item": None}
    
    if not hasattr(player, 'inventory'):
        player.inventory = {}
    
    for herb_id, count in recipe.herb_cost.items():
        player.inventory[herb_id] = player.inventory.get(herb_id, 0) - count
    
    player.lingqi -= recipe.lingqi_cost
    
    item_def = MEDICAL_ITEMS.get(recipe.result_item_id, {})
    item_name = item_def.get("name", recipe.result_item_id)
    
    if recipe.result_item_id != "herb_use":
        player.inventory[recipe.result_item_id] = player.inventory.get(recipe.result_item_id, 0) + recipe.result_count
    
    return {
        "success": True,
        "message": f"消耗{recipe.lingqi_cost}点体力，制作成功: {item_name}x{recipe.result_count}",
        "item": recipe.result_item_id,
        "item_name": item_name,
        "count": recipe.result_count,
        "lingqi_remaining": player.lingqi,
        "inventory": player.inventory,
    }


def use_medical_item(player, item_id: str) -> dict:
    """
    使用医疗物品
    
    Returns:
        dict: {"success": bool, "message": str, "healed": int}
    """
    if not hasattr(player, 'inventory'):
        player.inventory = {}
    
    item_def = MEDICAL_ITEMS.get(item_id)
    if not item_def:
        return {"success": False, "message": "未知的物品", "healed": 0}
    
    if item_id != "herb_use" and player.inventory.get(item_id, 0) <= 0:
        return {"success": False, "message": "物品不足", "healed": 0}
    
    if item_id == "herb_use":
        herbs = ["herb_common", "herb_good", "herb_rare"]
        usable = [h for h in herbs if player.inventory.get(h, 0) > 0]
        if not usable:
            return {"success": False, "message": "没有可用草药", "healed": 0}
        
        herb_id = random.choice(usable)
        player.inventory[herb_id] -= 1
        item_name = "草药"
    else:
        player.inventory[item_id] -= 1
        item_name = item_def["name"]
    
    heal_amount = item_def.get("heal_amount", 0)
    actual_heal = min(heal_amount, player.max_hp - player.hp)
    player.hp = min(player.max_hp, player.hp + actual_heal)
    
    result = {
        "success": True,
        "message": f"使用{item_name}，恢复了 {actual_heal} 点生命",
        "healed": actual_heal,
        "current_hp": player.hp,
        "max_hp": player.max_hp,
    }
    
    if "clears_debuff" in item_def:
        result["debuff_cleared"] = item_def["clears_debuff"]
    
    return result


def format_recipes_list(player) -> str:
    """格式化配方列表"""
    herbalism_level = player.skills.get(31, 0)
    available = get_available_recipes(herbalism_level)
    
    lines = ["🔧 制作配方：", ""]
    
    for recipe in RECIPES.values():
        available = herbalism_level >= recipe.skill_level_req
        
        status = "✅ 可制作" if available else f"🔒 需要草药学{recipe.skill_level_req}级"
        
        herb_parts = []
        for herb_id, count in recipe.herb_cost.items():
            herb_name = herb_id.replace("herb_", "").replace("common", "普通草").replace("good", "优质草").replace("rare", "珍稀草")
            herb_parts.append(f"{count}个{herb_name}")
        
        lines.append(f"{status} {recipe.name}")
        lines.append(f"   材料: {' + '.join(herb_parts)}")
        lines.append(f"   体力: {recipe.lingqi_cost} | 产出: {recipe.result_item_id}")
        lines.append("")
    
    return "\n".join(lines)


def format_inventory_medical(player) -> str:
    """格式化背包医疗物品"""
    if not hasattr(player, 'inventory'):
        player.inventory = {}
    
    lines = ["🎒 背包医疗物品：", ""]
    
    has_items = False
    for item_id, count in player.inventory.items():
        if item_id in MEDICAL_ITEMS and count > 0:
            item_def = MEDICAL_ITEMS[item_id]
            lines.append(f"  {item_def['name']}: {count}个 (恢复{item_def['heal_amount']}HP)")
            has_items = True
    
    herb_types = {
        "herb_common": "普通草药",
        "herb_good": "优质草药", 
        "herb_rare": "珍稀草药"
    }
    for herb_id, herb_name in herb_types.items():
        count = player.inventory.get(herb_id, 0)
        if count > 0:
            lines.append(f"  {herb_name}: {count}株")
            has_items = True
    
    if not has_items:
        lines.append("  (无医疗物品)")
    
    return "\n".join(lines)
