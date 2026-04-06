"""
饰品制作系统 - Mount & Blade 风格

玩家可以用狩猎获得的材料制作饰品。
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional


# 饰品属性加成
ACCESSORY_STATS = {
    "attack": "攻击",
    "defense": "防御", 
    "hp": "生命",
    "dodge": "闪避",
    "crit": "暴击",
}


@dataclass
class Accessory:
    """饰品定义"""
    accessory_id: str
    name: str
    description: str
    tier: int  # 0=普通, 1=进阶, 2=高级, 3=稀有
    stat_type: str  # 属性类型
    stat_value: int  # 属性值
    recipe_materials: dict[str, int]  # 需要的材料 {material_id: count}


ACCESSORIES: dict[str, Accessory] = {
    # 普通饰品
    "acc_leather_strap": Accessory(
        accessory_id="acc_leather_strap",
        name="皮绳",
        description="简单的皮绳",
        tier=0,
        stat_type="none",
        stat_value=0,
        recipe_materials={
            "hunt_deer_skin": 2,
        },
    ),
    
    # 进阶饰品
    "acc_wolf_fang_necklace": Accessory(
        accessory_id="acc_wolf_fang_necklace",
        name="狼牙项链",
        description="用狼牙制成的项链",
        tier=1,
        stat_type="attack",
        stat_value=5,
        recipe_materials={
            "hunt_wolf_fang": 2,
            "hunt_deer_skin": 1,
        },
    ),
    "acc_boar_tusk_amulet": Accessory(
        accessory_id="acc_boar_tusk_amulet",
        name="獠牙护符",
        description="野猪獠牙制成的护符",
        tier=1,
        stat_type="defense",
        stat_value=3,
        recipe_materials={
            "hunt_boar_tusk": 2,
            "hunt_boar_skin": 1,
        },
    ),
    "acc_rabbit_pouch": Accessory(
        accessory_id="acc_rabbit_pouch",
        name="兔皮袋",
        description="用兔皮制成的小袋子",
        tier=0,
        stat_type="hp",
        stat_value=20,
        recipe_materials={
            "hunt_rabbit_skin": 3,
        },
    ),
    
    # 高级饰品
    "acc_bear_claw_ring": Accessory(
        accessory_id="acc_bear_claw_ring",
        name="熊爪戒指",
        description="用熊爪制成的戒指",
        tier=2,
        stat_type="attack",
        stat_value=10,
        recipe_materials={
            "hunt_bear_claw": 1,
            "hunt_wolf_fang": 1,
            "hunt_bear_skin": 1,
        },
    ),
    "acc_bear_paw_amulet": Accessory(
        accessory_id="acc_bear_paw_amulet",
        name="熊掌护符",
        description="用熊掌制成的护符",
        tier=2,
        stat_type="hp",
        stat_value=100,
        recipe_materials={
            "hunt_bear_paw": 1,
            "hunt_bear_skin": 2,
        },
    ),
    "acc_deer_antler_hairpin": Accessory(
        accessory_id="acc_deer_antler_hairpin",
        name="鹿角发簪",
        description="用鹿角制成的发簪",
        tier=1,
        stat_type="dodge",
        stat_value=3,
        recipe_materials={
            "hunt_deer_antler": 2,
            "hunt_deer_skin": 1,
        },
    ),
    "acc_snake_gall_bracelet": Accessory(
        accessory_id="acc_snake_gall_bracelet",
        name="蛇胆手环",
        description="用蛇胆制成的手环",
        tier=2,
        stat_type="defense",
        stat_value=8,
        recipe_materials={
            "hunt_snake_gall": 1,
            "hunt_snake_skin": 2,
        },
    ),
    
    # 稀有饰品
    "acc_wolf_pelt_cape": Accessory(
        accessory_id="acc_wolf_pelt_cape",
        name="狼王披风",
        description="用狼王毛皮制成的披风",
        tier=3,
        stat_type="attack",
        stat_value=15,
        recipe_materials={
            "hunt_wolf_pelt": 1,
            "hunt_wolf_fang": 3,
            "hunt_bear_skin": 1,
        },
    ),
    "acc_bear_gall_elixir": Accessory(
        accessory_id="acc_bear_gall_elixir",
        name="熊胆护身符",
        description="用熊胆制成的护身符",
        tier=3,
        stat_type="hp",
        stat_value=200,
        recipe_materials={
            "hunt_bear_gall": 1,
            "hunt_bear_claw": 1,
            "hunt_bear_skin": 2,
        },
    ),
}


def get_accessory(accessory_id: str) -> Optional[Accessory]:
    """获取饰品定义"""
    return ACCESSORIES.get(accessory_id)


def get_all_accessories() -> list[Accessory]:
    """获取所有饰品"""
    return list(ACCESSORIES.values())


def get_accessories_by_tier(tier: int) -> list[Accessory]:
    """按等级获取饰品"""
    return [a for a in ACCESSORIES.values() if a.tier == tier]


def craft_accessory(player, accessory_id: str) -> dict:
    """
    制作饰品
    
    Returns:
        {"success": bool, "message": str, "accessory_id": str}
    """
    accessory = get_accessory(accessory_id)
    if not accessory:
        return {"success": False, "message": "未知的饰品", "accessory_id": None}
    
    # 检查材料
    if not hasattr(player, 'hunting_materials'):
        player.hunting_materials = {}
    
    materials = player.hunting_materials
    
    missing = []
    for mat_id, count in accessory.recipe_materials.items():
        current = materials.get(mat_id, 0)
        if current < count:
            from .hunting import HUNT_DROPS
            mat_name = HUNT_DROPS.get(mat_id, {}).get("name", mat_id)
            missing.append(f"{mat_name}需要{count}个")
    
    if missing:
        return {"success": False, "message": f"材料不足: {'，'.join(missing)}", "accessory_id": None}
    
    # 消耗材料
    for mat_id, count in accessory.recipe_materials.items():
        materials[mat_id] -= count
    
    # 添加成品到背包
    if not hasattr(player, 'inventory'):
        player.inventory = {}
    
    player.inventory[accessory_id] = player.inventory.get(accessory_id, 0) + 1
    
    stat_info = ""
    if accessory.stat_type != "none":
        stat_name = ACCESSORY_STATS.get(accessory.stat_type, accessory.stat_type)
        stat_info = f"，{stat_name}+{accessory.stat_value}"
    
    return {
        "success": True,
        "message": f"制作成功！获得【{accessory.name}】{stat_info}",
        "accessory_id": accessory_id,
    }


def add_hunting_material(player, material_id: str, count: int = 1):
    """添加狩猎材料"""
    if not hasattr(player, 'hunting_materials'):
        player.hunting_materials = {}
    player.hunting_materials[material_id] = player.hunting_materials.get(material_id, 0) + count


def get_hunting_material_count(player, material_id: str) -> int:
    """获取狩猎材料数量"""
    if not hasattr(player, 'hunting_materials'):
        return 0
    return player.hunting_materials.get(material_id, 0)


def format_hunting_materials(player) -> str:
    """格式化狩猎材料列表"""
    if not hasattr(player, 'hunting_materials') or not player.hunting_materials:
        return "狩猎材料: (空)"
    
    from .hunting import HUNT_DROPS
    
    lines = ["🎒 狩猎材料:", ""]
    
    categories = {}
    for mat_id, count in player.hunting_materials.items():
        if count <= 0:
            continue
        mat = HUNT_DROPS.get(mat_id)
        if mat:
            cat = mat.get("category", "其他")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(f"{mat['name']}x{count}")
    
    for cat, items in categories.items():
        lines.append(f"【{cat}】")
        lines.append("  " + "，".join(items))
    
    return "\n".join(lines) if lines else "狩猎材料: (空)"


def format_accessory_recipes(player) -> str:
    """格式化饰品配方列表"""
    from .hunting import HUNT_DROPS
    
    lines = ["💍 饰品制作:", ""]
    
    # 按等级分组
    tiers = {0: "普通", 1: "进阶", 2: "高级", 3: "稀有"}
    
    for tier in range(4):
        tier_accessories = get_accessories_by_tier(tier)
        if not tier_accessories:
            continue
        
        lines.append(f"【{tiers.get(tier, '普通')}】")
        
        for acc in tier_accessories:
            # 检查材料是否足够
            can_craft = True
            if hasattr(player, 'hunting_materials'):
                for mat_id, count in acc.recipe_materials.items():
                    if player.hunting_materials.get(mat_id, 0) < count:
                        can_craft = False
                        break
            else:
                can_craft = False
            
            status = "✅" if can_craft else "❌"
            
            mats = []
            for mat_id, count in acc.recipe_materials.items():
                mat = HUNT_DROPS.get(mat_id, {})
                mats.append(f"{mat.get('name', mat_id)}x{count}")
            
            stat_info = ""
            if acc.stat_type != "none":
                stat_name = ACCESSORY_STATS.get(acc.stat_type, acc.stat_type)
                stat_info = f" ({stat_name}+{acc.stat_value})"
            
            lines.append(f"  {status} {acc.name}{stat_info}")
            lines.append(f"      材料: {' + '.join(mats)}")
    
    return "\n".join(lines)
