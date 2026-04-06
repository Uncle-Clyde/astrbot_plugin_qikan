"""
草药采集系统

玩家可以在野外采集草药，需要消耗体力。
"""

from __future__ import annotations

import time
import random
from dataclasses import dataclass
from typing import Optional


@dataclass
class Herb:
    """草药定义"""
    herb_id: str
    name: str
    description: str
    heal_amount: int
    rarity: float  # 0-1, 越低越稀有


HERBS: dict[str, Herb] = {
    "herb_common": Herb(
        herb_id="herb_common",
        name="普通草药",
        description="野外常见的草药，可用于制作绷带",
        heal_amount=20,
        rarity=0.6,
    ),
    "herb_good": Herb(
        herb_id="herb_good",
        name="优质草药",
        description="药效较好的草药",
        heal_amount=40,
        rarity=0.3,
    ),
    "herb_rare": Herb(
        herb_id="herb_rare",
        name="珍稀草药",
        description="很难采集到的珍稀草药",
        heal_amount=80,
        rarity=0.1,
    ),
}


GATHER_COOLDOWN = 5  # 采集冷却(秒)
GATHER_LINGQI_COST = 10  # 采集消耗体力


def _get_skill_level(player, skill_id: int) -> int:
    """获取技能等级，兼容JSON序列化后的字符串键。"""
    return player.skills.get(skill_id, player.skills.get(str(skill_id), 0))


def get_herb(herb_id: str) -> Optional[Herb]:
    """获取草药定义"""
    return HERBS.get(herb_id)


def get_all_herbs() -> list[Herb]:
    """获取所有草药"""
    return list(HERBS.values())


def can_gather(player) -> tuple[bool, str]:
    """
    检查是否可以采集
    
    Returns:
        (can_gather: bool, reason: str)
    """
    herbalism_level = _get_skill_level(player, 31)  # HERBALISM
    
    if herbalism_level < 1:
        return False, "你需要学习草药学才能采集草药"
    
    if player.lingqi < GATHER_LINGQI_COST:
        return False, f"体力不足，需要 {GATHER_LINGQI_COST} 点体力"
    
    if not hasattr(player, 'last_gather_time'):
        player.last_gather_time = 0
    
    current_time = time.time()
    if current_time - player.last_gather_time < GATHER_COOLDOWN:
        remaining = int(GATHER_COOLDOWN - (current_time - player.last_gather_time))
        return False, f"采集冷却中，请等待 {remaining} 秒"
    
    return True, ""


def gather_herbs(player) -> dict:
    """
    采集草药
    
    Returns:
        dict: {"success": bool, "message": str, "herbs": list}
    """
    can, reason = can_gather(player)
    if not can:
        return {"success": False, "message": reason, "herbs": []}
    
    herbalism_level = _get_skill_level(player, 31)
    
    from .mb_attributes import get_skill_bonus
    bonus = get_skill_bonus(31, herbalism_level)
    gather_bonus = bonus.get("gather_effect", 0)
    
    base_count = 1 + int(herbalism_level / 3) + gather_bonus
    actual_count = random.randint(max(1, base_count - 1), base_count + 1)
    
    player.lingqi -= GATHER_LINGQI_COST
    player.last_gather_time = time.time()
    
    gathered = []
    for _ in range(actual_count):
        roll = random.random()
        if roll < HERBS["herb_rare"].rarity:
            herb = HERBS["herb_rare"]
        elif roll < HERBS["herb_rare"].rarity + HERBS["herb_good"].rarity:
            herb = HERBS["herb_good"]
        else:
            herb = HERBS["herb_common"]
        
        gathered.append({
            "herb_id": herb.herb_id,
            "name": herb.name,
            "heal_amount": herb.heal_amount,
        })
        
        if not hasattr(player, 'inventory'):
            player.inventory = {}
        player.inventory[herb.herb_id] = player.inventory.get(herb.herb_id, 0) + 1
    
    herb_names = [h["name"] for h in gathered]
    count_str = "、".join(herb_names[:3])
    if len(herb_names) > 3:
        count_str += f" 等({len(herb_names)}种)"
    
    return {
        "success": True,
        "message": f"消耗{GATHER_LINGQI_COST}点体力，采集到: {count_str}",
        "herbs": gathered,
        "lingqi_remaining": player.lingqi,
        "inventory": player.inventory,
    }


def get_gather_info(player) -> dict:
    """获取采集信息"""
    herbalism_level = _get_skill_level(player, 31)
    
    can_gather_now, reason = can_gather(player)
    
    cooldown_remaining = 0
    if hasattr(player, 'last_gather_time'):
        elapsed = time.time() - player.last_gather_time
        if elapsed < GATHER_COOLDOWN:
            cooldown_remaining = int(GATHER_COOLDOWN - elapsed)
    
    from .mb_attributes import get_skill_bonus
    bonus = get_skill_bonus(31, herbalism_level)
    gather_bonus = bonus.get("gather_effect", 0)
    base_count = 1 + int(herbalism_level / 3) + gather_bonus
    
    return {
        "can_gather": can_gather_now,
        "reason": reason,
        "cooldown_remaining": cooldown_remaining,
        "lingqi_cost": GATHER_LINGQI_COST,
        "skill_level": herbalism_level,
        "estimated_herbs": f"{max(1, base_count - 1)}-{base_count + 1}",
        "herbalism_level": herbalism_level,
    }


def format_gather_info(player) -> str:
    """格式化采集信息"""
    info = get_gather_info(player)
    
    lines = ["🌿 采集提示：", ""]
    
    if info["herbalism_level"] < 1:
        lines.append("🔒 需要学习草药学技能才能采集")
    else:
        lines.append(f"📊 预计采集: {info['estimated_herbs']} 株")
        lines.append(f"⏱️ 冷却时间: {GATHER_COOLDOWN} 秒")
        lines.append(f"💪 体力消耗: {info['lingqi_cost']} 点")
        
        if not info["can_gather"]:
            lines.append(f"❌ {info['reason']}")
        else:
            lines.append("✅ 可以采集")
    
    return "\n".join(lines)
