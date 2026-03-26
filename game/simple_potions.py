"""
骑砍风格药剂系统 - 简化版

药剂只提供小幅恢复效果，生命恢复主要依赖医疗技能。
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional


@dataclass
class SimplePotion:
    """简化药剂"""
    potion_id: str
    name: str
    description: str
    heal_amount: int       # 恢复生命值
    cooldown: int         # 使用冷却（秒）
    price: int           # 售价
    tier: int            # 品质 0-2


SIMPLE_POTIONS: dict[str, SimplePotion] = {
    # 低级药剂
    "potion_bandage": SimplePotion(
        potion_id="potion_bandage",
        name="绷带",
        description="简单的战场绷带，止血用",
        heal_amount=20,
        cooldown=30,
        price=10,
        tier=0,
    ),
    "potion_herb": SimplePotion(
        potion_id="potion_herb",
        name="草药",
        description="野外采集的草药，有一定疗效",
        heal_amount=35,
        cooldown=60,
        price=25,
        tier=0,
    ),
    "potion_apothecary": SimplePotion(
        potion_id="potion_apothecary",
        name="劣质药剂",
        description="炼金术士粗制滥造的产品",
        heal_amount=50,
        cooldown=90,
        price=50,
        tier=0,
    ),
    # 中级药剂
    "potion_health_small": SimplePotion(
        potion_id="potion_health_small",
        name="小型治疗药水",
        description="小瓶治疗药水，战场常用",
        heal_amount=80,
        cooldown=120,
        price=100,
        tier=1,
    ),
    "potion_health_medium": SimplePotion(
        potion_id="potion_health_medium",
        name="中型治疗药水",
        description="效果更好的治疗药水",
        heal_amount=150,
        cooldown=180,
        price=250,
        tier=1,
    ),
    "potion_antidote": SimplePotion(
        potion_id="potion_antidote",
        name="解毒剂",
        description="解除中毒状态",
        heal_amount=30,
        cooldown=60,
        price=80,
        tier=1,
    ),
    # 高级药剂
    "potion_health_large": SimplePotion(
        potion_id="potion_health_large",
        name="大型治疗药水",
        description="珍贵的治疗药水",
        heal_amount=300,
        cooldown=300,
        price=500,
        tier=2,
    ),
    "potion_health_elixir": SimplePotion(
        potion_id="potion_health_elixir",
        name="治疗秘药",
        description="传说中的治疗秘药",
        heal_amount=500,
        cooldown=600,
        price=1500,
        tier=2,
    ),
    "potion_grand_healing": SimplePotion(
        potion_id="potion_grand_healing",
        name="神圣治疗药水",
        description="神殿炼制的神圣药水",
        heal_amount=800,
        cooldown=900,
        price=3000,
        tier=2,
    ),
}

POTION_TIER_NAMES = {0: "普通", 1: "精良", 2: "稀有"}


def get_potion(potion_id: str) -> Optional[SimplePotion]:
    """获取药剂定义"""
    return SIMPLE_POTIONS.get(potion_id)


def get_all_potions() -> list[SimplePotion]:
    """获取所有药剂"""
    return list(SIMPLE_POTIONS.values())


def get_potions_by_tier(tier: int) -> list[SimplePotion]:
    """按品质获取药剂"""
    return [p for p in SIMPLE_POTIONS.values() if p.tier == tier]


def roll_random_potion(rng: random.Random, max_tier: int = 1) -> Optional[SimplePotion]:
    """根据最高品质随机抽取药剂"""
    available = [p for p in SIMPLE_POTIONS.values() if p.tier <= max_tier]
    if not available:
        return None
    
    weights = [100 if p.tier < max_tier else 30 for p in available]
    return rng.choices(available, weights=weights, k=1)[0]


def use_potion(player, potion_id: str) -> dict:
    """
    使用药剂，返回使用结果
    
    Returns:
        dict: {"success": bool, "message": str, "healed": int}
    """
    potion = get_potion(potion_id)
    if not potion:
        return {"success": False, "message": "未知的药剂"}
    
    if not hasattr(player, 'potion_cooldowns'):
        player.potion_cooldowns = {}
    
    current_time = getattr(player, '_last_action_time', 0)
    import time
    current_time = time.time()
    
    last_used = player.potion_cooldowns.get(potion_id, 0)
    if current_time - last_used < potion.cooldown:
        remaining = int(potion.cooldown - (current_time - last_used))
        return {
            "success": False, 
            "message": f"该药剂冷却中，请等待 {remaining} 秒",
            "healed": 0
        }
    
    heal_amount = min(potion.heal_amount, player.max_hp - player.hp)
    player.hp += heal_amount
    player.potion_cooldowns[potion_id] = current_time
    
    return {
        "success": True,
        "message": f"使用了{potion.name}，恢复了 {heal_amount} 点生命",
        "healed": heal_amount,
        "current_hp": player.hp,
        "max_hp": player.max_hp,
    }


def get_potion_cooldown(player, potion_id: str) -> int:
    """获取药剂剩余冷却时间"""
    if not hasattr(player, 'potion_cooldowns'):
        return 0
    
    import time
    last_used = player.potion_cooldowns.get(potion_id, 0)
    potion = get_potion(potion_id)
    if not potion:
        return 0
    
    remaining = potion.cooldown - (time.time() - last_used)
    return max(0, int(remaining))


def format_potion_shop() -> str:
    """格式化商店药剂列表"""
    lines = ["🏥 军需药剂商店：", ""]
    
    for tier in range(3):
        potions = get_potions_by_tier(tier)
        if potions:
            lines.append(f"【{POTION_TIER_NAMES[tier]}】")
            for p in potions:
                lines.append(f"  {p.name}: 恢复{p.heal_amount}HP | {p.price}金币 | 冷却{p.cooldown}秒")
            lines.append("")
    
    return "\n".join(lines)
