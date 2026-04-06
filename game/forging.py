"""
锻造材料系统 - Mount & Blade 风格

用于武器锻造和强化的各种材料。
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional


@dataclass
class ForgingMaterial:
    """锻造材料定义"""
    material_id: str
    name: str
    description: str
    tier: int  # 0=普通, 1=进阶, 2=高级, 3=稀有
    category: str  # "fuel", "metal", "accessory"
    price: int  # 参考价格


# ══════════════════════════════════════════════════════════════════════
# 燃料类材料
# ══════════════════════════════════════════════════════════════════════

FORGING_MATERIALS: dict[str, ForgingMaterial] = {
    # 燃料
    "fuel_wood": ForgingMaterial("fuel_wood", "木柴", "基础的燃料，城镇商店有售", 0, "fuel", 5),
    "fuel_charcoal": ForgingMaterial("fuel_charcoal", "木炭", "比木柴更耐烧，适合基础锻造", 1, "fuel", 15),
    "fuel_coal": ForgingMaterial("fuel_coal", "煤炭", "高级燃料，矿洞产出", 2, "fuel", 40),
    "fuel_coke": ForgingMaterial("fuel_coke", "焦炭", "最高级燃料，极少量产出", 3, "fuel", 100),
    
    # 金属
    "metal_pig_iron": ForgingMaterial("metal_pig_iron", "生铁", "最基础的金属，矿村有售", 0, "metal", 20),
    "metal_crude_steel": ForgingMaterial("metal_crude_steel", "粗钢", "经过一次提炼，城镇可购", 1, "metal", 50),
    "metal_wrought_iron": ForgingMaterial("metal_wrought_iron", "熟铁", "比粗钢更好，产量较少", 2, "metal", 120),
    "metal_refined_iron": ForgingMaterial("metal_refined_iron", "精铁", "高级金属，较稀有", 3, "metal", 300),
    "metal_damascus": ForgingMaterial("metal_damascus", "大马士革钢", "传说中的顶级钢材", 4, "metal", 800),
    
    # 辅料
    "acc_leather": ForgingMaterial("acc_leather", "皮革", "增加耐久，剥皮获取", 0, "accessory", 15),
    "acc_oil": ForgingMaterial("acc_oil", "油脂", "增加锋利度，猎户掉落", 1, "accessory", 25),
    "acc_fluorite": ForgingMaterial("acc_fluorite", "萤石", "少量发光效果，特定地点采集", 2, "accessory", 60),
    "acc_gem": ForgingMaterial("acc_gem", "宝石", "少量特殊效果，Boss掉落", 3, "accessory", 150),
    "acc_pearl": ForgingMaterial("acc_pearl", "珍珠", "稀有装饰用，港口城市", 3, "accessory", 200),
}


# ══════════════════════════════════════════════════════════════════════
# 锻造配方
# ══════════════════════════════════════════════════════════════════════

@dataclass
class ForgingRecipe:
    """锻造配方"""
    recipe_id: str
    name: str
    description: str
    result_item_id: str  # 成品装备ID
    fuel_required: str  # 需要的燃料
    metal_required: str  # 需要的金属
    accessory_required: str = ""  # 可选的辅料
    skill_level_req: int = 0  # 需要锻造技能等级


RECIPES: dict[str, ForgingRecipe] = {
    # 武器配方
    "forge_iron_sword": ForgingRecipe(
        recipe_id="forge_iron_sword",
        name="锻造铁剑",
        description="最基础的武器锻造",
        result_item_id="equipment_iron_sword",
        fuel_required="fuel_wood",
        metal_required="metal_pig_iron",
        skill_level_req=0,
    ),
    "forge_iron_sword_better": ForgingRecipe(
        recipe_id="forge_iron_sword_better",
        name="锻造优质铁剑",
        description="用木炭锻造的较好铁剑",
        result_item_id="equipment_iron_sword",
        fuel_required="fuel_charcoal",
        metal_required="metal_pig_iron",
        skill_level_req=1,
    ),
    "forge_steel_sword": ForgingRecipe(
        recipe_id="forge_steel_sword",
        name="锻造钢剑",
        description="用粗钢锻造的钢剑",
        result_item_id="equipment_steel_sword",
        fuel_required="fuel_charcoal",
        metal_required="metal_crude_steel",
        skill_level_req=2,
    ),
    "forge_carbon_sword": ForgingRecipe(
        recipe_id="forge_carbon_sword",
        name="锻造碳钢剑",
        description="用煤炭锻造的碳钢剑",
        result_item_id="equipment_carbon_sword",
        fuel_required="fuel_coal",
        metal_required="metal_crude_steel",
        skill_level_req=3,
    ),
    "forge_quality_sword": ForgingRecipe(
        recipe_id="forge_quality_sword",
        name="锻造优质钢剑",
        description="用熟铁锻造的优质钢剑",
        result_item_id="equipment_quality_sword",
        fuel_required="fuel_coal",
        metal_required="metal_wrought_iron",
        skill_level_req=4,
    ),
    "forge_refined_sword": ForgingRecipe(
        recipe_id="forge_refined_sword",
        name="锻造精铁剑",
        description="用精铁打造的高级剑",
        result_item_id="equipment_refined_sword",
        fuel_required="fuel_coal",
        metal_required="metal_refined_iron",
        accessory_required="acc_fluorite",
        skill_level_req=5,
    ),
    "forge_damascus_sword": ForgingRecipe(
        recipe_id="forge_damascus_sword",
        name="锻造大马士革剑",
        description="传说中的顶级武器",
        result_item_id="equipment_damascus_sword",
        fuel_required="fuel_coke",
        metal_required="metal_damascus",
        accessory_required="acc_gem",
        skill_level_req=7,
    ),
    
    # 防具配方
    "forge_leather_armor": ForgingRecipe(
        recipe_id="forge_leather_armor",
        name="锻造皮甲",
        description="用皮革制作的皮甲",
        result_item_id="equipment_leather_armor",
        fuel_required="fuel_wood",
        metal_required="metal_pig_iron",
        accessory_required="acc_leather",
        skill_level_req=0,
    ),
    "forge_steel_armor": ForgingRecipe(
        recipe_id="forge_steel_armor",
        name="锻造钢制皮甲",
        description="用粗钢加强的皮甲",
        result_item_id="equipment_steel_armor",
        fuel_required="fuel_charcoal",
        metal_required="metal_crude_steel",
        accessory_required="acc_leather",
        skill_level_req=2,
    ),
    "forge_chainmail": ForgingRecipe(
        recipe_id="forge_chainmail",
        name="锻造锁甲",
        description="用熟铁打造的锁甲",
        result_item_id="equipment_chainmail",
        fuel_required="fuel_coal",
        metal_required="metal_wrought_iron",
        skill_level_req=4,
    ),
    "forge_plate_armor": ForgingRecipe(
        recipe_id="forge_plate_armor",
        name="锻造精钢甲",
        description="用精铁打造的高级甲",
        result_item_id="equipment_plate_armor",
        fuel_required="fuel_coal",
        metal_required="metal_refined_iron",
        accessory_required="acc_oil",
        skill_level_req=5,
    ),
    "forge_damascus_armor": ForgingRecipe(
        recipe_id="forge_damascus_armor",
        name="锻造大马士革甲",
        description="传说中的顶级甲",
        result_item_id="equipment_damascus_armor",
        fuel_required="fuel_coke",
        metal_required="metal_damascus",
        accessory_required="acc_gem",
        skill_level_req=7,
    ),
}


def get_material(material_id: str) -> Optional[ForgingMaterial]:
    """获取材料定义"""
    return FORGING_MATERIALS.get(material_id)


def get_all_materials() -> list[ForgingMaterial]:
    """获取所有材料"""
    return list(FORGING_MATERIALS.values())


def get_materials_by_category(category: str) -> list[ForgingMaterial]:
    """按类别获取材料"""
    return [m for m in FORGING_MATERIALS.values() if m.category == category]


def get_materials_by_tier(tier: int) -> list[ForgingMaterial]:
    """按等级获取材料"""
    return [m for m in FORGING_MATERIALS.values() if m.tier == tier]


def get_recipe(recipe_id: str) -> Optional[ForgingRecipe]:
    """获取配方"""
    return RECIPES.get(recipe_id)


def get_all_recipes() -> list[ForgingRecipe]:
    """获取所有配方"""
    return list(RECIPES.values())


def get_available_recipes(skill_level: int) -> list[ForgingRecipe]:
    """根据锻造技能等级获取可用配方"""
    return [r for r in RECIPES.values() if r.skill_level_req <= skill_level]


def get_forging_cost(metal_tier: int, fuel_tier: int, has_accessory: bool = False) -> int:
    """计算锻造费用（基于材料等级）"""
    base_cost = 10
    metal_cost = metal_tier * 30
    fuel_cost = fuel_tier * 10
    accessory_cost = 50 if has_accessory else 0
    return base_cost + metal_cost + fuel_cost + accessory_cost


def forge_item(player, recipe_id: str) -> dict:
    """
    锻造装备
    
    Returns:
        {"success": bool, "message": str, "item_id": str}
    """
    from .map_system import TOWNS, VILLAGES
    
    can_forge = False
    location_name = "未知"
    
    if hasattr(player, 'map_state') and player.map_state:
        loc_id = player.map_state.current_location
        
        if loc_id in TOWNS:
            loc = TOWNS[loc_id]
            if loc.has_blacksmith:
                can_forge = True
                location_name = loc.name
        elif loc_id in VILLAGES:
            loc = VILLAGES[loc_id]
            if loc.has_blacksmith:
                can_forge = True
                location_name = loc.name
    
    if not can_forge:
        return {"success": False, "message": f"你当前在 {location_name}，无法锻造。请前往有铁匠铺的城镇或村庄。", "item_id": None}
    
    recipe = get_recipe(recipe_id)
    if not recipe:
        return {"success": False, "message": "未知的锻造配方", "item_id": None}
    
    # 检查技能等级
    skill_level = getattr(player, 'smithing_level', 0)
    if skill_level < recipe.skill_level_req:
        return {
            "success": False,
            "message": f"需要锻造技能 {recipe.skill_level_req} 级",
            "item_id": None
        }
    
    if not hasattr(player, 'forging_materials'):
        player.forging_materials = {}
    
    materials = player.forging_materials
    
    # 检查燃料
    fuel_id = recipe.fuel_required
    if materials.get(fuel_id, 0) < 1:
        fuel = get_material(fuel_id)
        return {"success": False, "message": f"需要燃料: {fuel.name if fuel else fuel_id}", "item_id": None}
    
    # 检查金属
    metal_id = recipe.metal_required
    if materials.get(metal_id, 0) < 1:
        metal = get_material(metal_id)
        return {"success": False, "message": f"需要金属: {metal.name if metal else metal_id}", "item_id": None}
    
    # 检查辅料（如果有）
    if recipe.accessory_required:
        acc_id = recipe.accessory_required
        if materials.get(acc_id, 0) < 1:
            acc = get_material(acc_id)
            return {"success": False, "message": f"需要辅料: {acc.name if acc else acc_id}", "item_id": None}
        materials[acc_id] -= 1
    
    # 消耗材料
    materials[fuel_id] -= 1
    materials[metal_id] -= 1
    
    # 计算锻造费用
    fuel = get_material(fuel_id)
    metal = get_material(metal_id)
    cost = get_forging_cost(
        metal.tier if metal else 0,
        fuel.tier if fuel else 0,
        bool(recipe.accessory_required)
    )
    
    if player.spirit_stones < cost:
        return {"success": False, "message": f"第纳尔不足，需要{cost}第纳尔", "item_id": None}
    
    player.spirit_stones -= cost
    
    # 添加成品装备
    if not hasattr(player, 'inventory'):
        player.inventory = {}
    
    result_item = recipe.result_item_id
    player.inventory[result_item] = player.inventory.get(result_item, 0) + 1
    
    return {
        "success": True,
        "message": f"锻造成功！消耗{get_material(fuel_id).name}、{get_material(metal_id).name}，花费{cost}第纳尔，获得【{result_item}】",
        "item_id": result_item,
        "cost": cost,
    }


def add_material(player, material_id: str, count: int = 1):
    """添加锻造材料"""
    if not hasattr(player, 'forging_materials'):
        player.forging_materials = {}
    player.forging_materials[material_id] = player.forging_materials.get(material_id, 0) + count


def get_material_count(player, material_id: str) -> int:
    """获取材料数量"""
    if not hasattr(player, 'forging_materials'):
        return 0
    return player.forging_materials.get(material_id, 0)


def format_materials_list(player) -> str:
    """格式化材料列表"""
    if not hasattr(player, 'forging_materials') or not player.forging_materials:
        return "锻造材料: (空)"
    
    lines = ["🔨 锻造材料:", ""]
    
    # 按类别显示
    categories = {"fuel": "燃料", "metal": "金属", "accessory": "辅料"}
    for cat, cat_name in categories.items():
        cat_materials = get_materials_by_category(cat)
        has_any = False
        for m in cat_materials:
            count = get_material_count(player, m.material_id)
            if count > 0:
                if not has_any:
                    lines.append(f"【{cat_name}】")
                    has_any = True
                lines.append(f"  {m.name}: {count}个")
        
        if has_any:
            lines.append("")
    
    return "\n".join(lines)


def format_recipes_list(player) -> str:
    """格式化配方列表"""
    skill_level = getattr(player, 'smithing_level', 0)
    available = get_available_recipes(skill_level)
    
    lines = ["⚒️ 锻造配方:", ""]
    
    # 按类别分组
    weapons = [r for r in available if "sword" in r.result_item_id]
    armors = [r for r in available if "armor" in r.result_item_id]
    
    if weapons:
        lines.append("【武器】")
        for r in weapons:
            fuel = get_material(r.fuel_required)
            metal = get_material(r.metal_required)
            acc = get_material(r.accessory_required) if r.accessory_required else None
            
            req = f"{fuel.name}+{metal.name}"
            if acc:
                req += f"+{acc.name}"
            
            lines.append(f"  {r.name}: {req}")
        lines.append("")
    
    if armors:
        lines.append("【防具】")
        for r in armors:
            fuel = get_material(r.fuel_required)
            metal = get_material(r.metal_required)
            acc = get_material(r.accessory_required) if r.accessory_required else None
            
            req = f"{fuel.name}+{metal.name}"
            if acc:
                req += f"+{acc.name}"
            
            lines.append(f"  {r.name}: {req}")
        lines.append("")
    
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════
# 城镇商店出售的基础材料
# ══════════════════════════════════════════════════════════════════════

def get_shop_materials(location_id: str) -> list[dict]:
    """获取城镇商店可购买的材料"""
    # 所有城镇都出售基础材料
    shop_materials = [
        {"material_id": "fuel_wood", "price": 5, "name": "木柴"},
        {"material_id": "metal_pig_iron", "price": 20, "name": "生铁"},
        {"material_id": "acc_leather", "price": 15, "name": "皮革"},
    ]
    
    # 特殊城镇出售进阶材料
    if location_id in ("town_curin", "town_jelkala", "town_reyvadin"):
        shop_materials.extend([
            {"material_id": "fuel_charcoal", "price": 15, "name": "木炭"},
            {"material_id": "metal_crude_steel", "price": 50, "name": "粗钢"},
            {"material_id": "acc_oil", "price": 25, "name": "油脂"},
        ])
    
    if location_id in ("town_sargoth", "town_yalen"):
        shop_materials.extend([
            {"material_id": "acc_pearl", "price": 200, "name": "珍珠"},
        ])
    
    return shop_materials
