"""
骑砍风格大地图劫匪战斗系统

在大地图上与劫匪群战斗，击败后获得经验和战利品。
"""

from __future__ import annotations

import random
import time

from .constants import (
    EQUIPMENT_REGISTRY, EquipmentTier,
)
from .inventory import add_item


def calculate_damage(attack: int, defense: int, multiplier: float = 1.0) -> int:
    """计算伤害。"""
    base = max(1, attack * 2 - defense)
    variance = random.uniform(0.8, 1.2)
    return max(1, int(base * multiplier * variance))


def get_player_stats(player) -> dict:
    """获取玩家战斗属性。"""
    return {
        "attack": player.attack,
        "defense": player.defense,
        "hp": player.hp,
        "max_hp": player.max_hp,
    }


async def engage_bandit(player, bandit_id: str) -> dict:
    """
    与劫匪交战。
    
    Args:
        player: 玩家对象
        bandit_id: 劫匪群ID
    
    Returns:
        战斗结果字典
    """
    from .map_system import get_bandit_manager, BANDIT_TYPE_NAMES, BANDIT_TYPE_ICONS
    
    manager = get_bandit_manager()
    bandit = manager.bandit_groups.get(bandit_id)
    
    if not bandit:
        return {"success": False, "message": "未找到该劫匪"}
    
    if bandit.is_defeated:
        remaining = int(bandit.last_defeated_time + bandit.respawn_time - time.time())
        if remaining > 0:
            return {"success": False, "message": f"该劫匪已被击败，{remaining}秒后复活"}
        return {"success": False, "message": "劫匪正在复活中..."}
    
    # 计算玩家属性
    stats = get_player_stats(player)
    player_atk = stats["attack"]
    player_def = stats["defense"]
    player_hp = stats["hp"]
    player_max_hp = stats["max_hp"]
    
    # 计算伤害
    base_damage = calculate_damage(player_atk, bandit.defense, random.uniform(0.9, 1.1))
    
    # 劫匪反击
    bandit_damage = calculate_damage(bandit.attack, player_def, random.uniform(0.8, 1.2))
    
    # 应用战斗结果
    result = manager.defeat_bandit(bandit_id, base_damage)
    
    if result["success"]:
        # 扣除玩家生命
        player.hp = max(0, player.hp - bandit_damage)
        
        # 检查是否重伤
        injured = False
        if player.hp <= 0:
            player.is_injured = True
            player.hp = 1
            injured = True
        
        if result["defeated"]:
            # 击败劫匪
            exp_reward = result["exp_reward"]
            gold_reward = result["gold_reward"]
            
            # 更新玩家统计
            if not hasattr(player, 'bandit_stats'):
                from .map_system import PlayerBanditStats
                player.bandit_stats = PlayerBanditStats()
            
            player.bandit_stats.total_defeated += 1
            player.bandit_stats.total_exp_gained += exp_reward
            player.bandit_stats.total_gold_gained += gold_reward
            player.bandit_stats.consecutive_victories += 1
            
            if bandit.level > player.bandit_stats.highest_level_defeated:
                player.bandit_stats.highest_level_defeated = bandit.level
            
            # 按类型统计
            bandit_type = bandit.bandit_type
            player.bandit_stats.bandits_by_type[bandit_type] = \
                player.bandit_stats.bandits_by_type.get(bandit_type, 0) + 1
            
            # 增加经验（使用等级系统）
            from .player_level import LevelSystem
            level_results = LevelSystem.add_exp(player, exp_reward)
            
            # 获得金币（第纳尔）
            player.spirit_stones += gold_reward
            
            # 随机战利品
            loot = get_random_loot_for_bandit(player, bandit.level)
            
            result["player_hp"] = player.hp
            result["player_max_hp"] = player_max_hp
            result["bandit_damage_taken"] = bandit_damage
            result["loot"] = loot
            result["injured"] = injured
            
            # 升级信息
            if level_results:
                result["level_up"] = True
                result["new_level"] = level_results[0]["new_level"]
                result["points_gained"] = level_results[0]["points_gained"]
            
            return result
        else:
            # 劫匪受伤但未击败
            result["player_hp"] = player.hp
            result["player_max_hp"] = player_max_hp
            result["bandit_damage_taken"] = bandit_damage
            result["injured"] = injured
            return result
    
    return result


def get_random_loot_for_bandit(player, bandit_level: int) -> dict | None:
    """
    根据劫匪等级随机掉落物品。
    """
    # 基础掉落率
    drop_chance = 0.3 + min(0.4, bandit_level * 0.05)  # 30%-70%
    
    if random.random() > drop_chance:
        return None
    
    # 决定掉落品质
    if bandit_level >= 8:
        tier_weights = [(EquipmentTier.FINE, 50), (EquipmentTier.RARE, 35), (EquipmentTier.EPIC, 15)]
    elif bandit_level >= 5:
        tier_weights = [(EquipmentTier.COMMON, 40), (EquipmentTier.FINE, 45), (EquipmentTier.RARE, 15)]
    elif bandit_level >= 3:
        tier_weights = [(EquipmentTier.COMMON, 60), (EquipmentTier.FINE, 35), (EquipmentTier.RARE, 5)]
    else:
        tier_weights = [(EquipmentTier.COMMON, 80), (EquipmentTier.FINE, 20)]
    
    tiers = [t[0] for t in tier_weights]
    weights = [t[1] for t in tier_weights]
    tier = random.choices(tiers, weights=weights, k=1)[0]
    
    # 从对应品质的装备中随机选
    candidates = [eq for eq in EQUIPMENT_REGISTRY.values() if eq.tier == tier]
    if not candidates:
        return None
    
    item = random.choice(candidates)
    
    # 添加到玩家背包
    import asyncio
    asyncio.create_task(add_item(player, item.equip_id))
    
    return {
        "item_id": item.equip_id,
        "item_name": item.name,
        "tier": tier,
        "tier_name": {0: "普通", 1: "精良", 2: "稀有", 3: "史诗", 4: "传说"}.get(tier, "普通"),
    }


def get_bandit_encounter_chance(player_x: float, player_y: float, bandit_x: float, bandit_y: float) -> float:
    """
    计算遇到劫匪的概率。
    距离越近，遇到概率越高。
    """
    distance = ((bandit_x - player_x) ** 2 + (bandit_y - player_y) ** 2) ** 0.5
    
    if distance < 50:
        return 0.9  # 非常近，几乎必定遇到
    elif distance < 100:
        return 0.6
    elif distance < 150:
        return 0.3
    elif distance < 200:
        return 0.15
    elif distance < 300:
        return 0.05
    else:
        return 0.0


async def check_random_encounter(player) -> dict | None:
    """
    随机遭遇劫匪检查。
    当玩家在地图上移动时可能遭遇未在视野内的劫匪。
    """
    from .map_system import get_bandit_manager
    
    manager = get_bandit_manager()
    
    # 移动时可能遇到新的劫匪
    if random.random() > 0.1:  # 10%概率遇到
        return None
    
    # 找一个未被玩家发现的劫匪
    for bandit in manager.get_all_active_bandits():
        if get_bandit_encounter_chance(
            player.map_state.x, player.map_state.y,
            bandit.x, bandit.y
        ) > 0:
            return {
                "encounter_type": "random",
                "bandit_id": bandit.bandit_id,
                "bandit_name": bandit.name,
                "bandit_type": bandit.bandit_type,
                "level": bandit.level,
                "message": f"在移动途中，你遭遇了{bandit.name}！",
            }
    
    return None
