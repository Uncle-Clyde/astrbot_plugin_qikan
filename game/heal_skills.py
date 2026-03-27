"""
骑砍风格医疗技能系统

医疗是玩家恢复生命值的主要手段。
"""

from __future__ import annotations

import time
import random


class HealSkill:
    """医疗技能定义"""
    
    def __init__(
        self,
        skill_id: str,
        name: str,
        description: str,
        base_heal: int,
        cooldown: int,
        stamina_cost: int,
        success_rate: float = 1.0,
        skill_level_req: int = 0,
    ):
        self.skill_id = skill_id
        self.name = name
        self.description = description
        self.base_heal = base_heal
        self.cooldown = cooldown
        self.stamina_cost = stamina_cost
        self.success_rate = success_rate
        self.skill_level_req = skill_level_req


HEAL_SKILLS: dict[str, HealSkill] = {
    "basic_bandage": HealSkill(
        skill_id="basic_bandage",
        name="战场包扎",
        description="基础的战场急救技能，用绷带包扎伤口",
        base_heal=30,
        cooldown=60,
        stamina_cost=10,
        skill_level_req=0,
    ),
    "field_dressing": HealSkill(
        skill_id="field_dressing",
        name="野战救护",
        description="在恶劣环境下进行紧急救护的能力",
        base_heal=60,
        cooldown=90,
        stamina_cost=15,
        skill_level_req=1,
    ),
    "battlefield_medicine": HealSkill(
        skill_id="battlefield_medicine",
        name="战地医疗",
        description="专业的战地医疗知识和技术",
        base_heal=100,
        cooldown=120,
        stamina_cost=20,
        success_rate=0.95,
        skill_level_req=2,
    ),
    "field_surgery": HealSkill(
        skill_id="field_surgery",
        name="野战外科",
        description="处理重伤员的外科手术技能",
        base_heal=180,
        cooldown=180,
        stamina_cost=30,
        success_rate=0.9,
        skill_level_req=3,
    ),
    "trauma_treatment": HealSkill(
        skill_id="trauma_treatment",
        name="创伤治疗",
        description="处理各种创伤的专业医疗技术",
        base_heal=280,
        cooldown=240,
        stamina_cost=40,
        success_rate=0.85,
        skill_level_req=4,
    ),
    "master_surgeon": HealSkill(
        skill_id="master_surgeon",
        name="外科大师",
        description="精通各种外科手术的大师级技能",
        base_heal=400,
        cooldown=300,
        stamina_cost=50,
        success_rate=0.8,
        skill_level_req=5,
    ),
    "battle_healer": HealSkill(
        skill_id="battle_healer",
        name="战地治愈者",
        description="在战斗中快速治愈伤口的能力",
        base_heal=250,
        cooldown=60,
        stamina_cost=25,
        success_rate=0.9,
        skill_level_req=3,
    ),
    "triage": HealSkill(
        skill_id="triage",
        name="伤员检伤分类",
        description="快速评估和分类伤员救治优先级",
        base_heal=150,
        cooldown=45,
        stamina_cost=15,
        success_rate=0.95,
        skill_level_req=2,
    ),
}


def get_heal_skill(skill_id: str) -> HealSkill | None:
    """获取医疗技能"""
    return HEAL_SKILLS.get(skill_id)


def get_all_heal_skills() -> list[HealSkill]:
    """获取所有医疗技能"""
    return list(HEAL_SKILLS.values())


def get_heal_skill_by_level(level: int) -> list[HealSkill]:
    """根据技能等级获取可用技能"""
    return [s for s in HEAL_SKILLS.values() if s.skill_level_req <= level]


def calculate_heal(player, skill: HealSkill) -> int:
    """
    计算实际治疗量
    
    治疗量 = 基础治疗量 × (1 + 活力加成)
    """
    vitality_bonus = 1.0 + (player.attributes.vitality if hasattr(player, 'attributes') else 0) * 0.02
    
    heal_amount = int(skill.base_heal * vitality_bonus)
    
    heal_amount = min(heal_amount, player.max_hp - player.hp)
    
    return max(0, heal_amount)


def use_heal_skill(player, skill_id: str) -> dict:
    """
    使用医疗技能
    
    Returns:
        dict: {"success": bool, "message": str, "healed": int, "skill_name": str}
    """
    skill = get_heal_skill(skill_id)
    if not skill:
        return {"success": False, "message": "未知的医疗技能", "healed": 0}
    
    skill_level = getattr(player, 'heal_skill_level', 0)
    if skill.skill_level_req > skill_level:
        return {
            "success": False, 
            "message": f"需要医疗技能等级 {skill.skill_level_req} 才能使用此技能",
            "healed": 0
        }
    
    if not hasattr(player, 'skill_cooldowns'):
        player.skill_cooldowns = {}
    
    current_time = time.time()
    last_used = player.skill_cooldowns.get(skill_id, 0)
    if current_time - last_used < skill.cooldown:
        remaining = int(skill.cooldown - (current_time - last_used))
        return {
            "success": False,
            "message": f"{skill.name}冷却中，请等待 {remaining} 秒",
            "healed": 0
        }
    
    if player.lingqi < skill.stamina_cost:
        return {
            "success": False,
            "message": f"体力不足，需要 {skill.stamina_cost} 点体力",
            "healed": 0
        }
    
    player.lingqi -= skill.stamina_cost
    
    if random.random() > skill.success_rate:
        heal_amount = int(calculate_heal(player, skill) * 0.5)
        if heal_amount > 0:
            player.hp += heal_amount
        player.skill_cooldowns[skill_id] = current_time
        return {
            "success": True,
            "message": f"治疗失误，勉强恢复 {heal_amount} 点生命",
            "healed": heal_amount,
            "skill_name": skill.name,
        }
    
    heal_amount = calculate_heal(player, skill)
    player.hp += heal_amount
    player.skill_cooldowns[skill_id] = current_time
    
    heal_pct = (heal_amount / player.max_hp) * 100
    
    return {
        "success": True,
        "message": f"使用{skill.name}，恢复了 {heal_amount} 点生命 ({heal_pct:.0f}%)",
        "healed": heal_amount,
        "skill_name": skill.name,
        "current_hp": player.hp,
        "max_hp": player.max_hp,
        "lingqi_remaining": player.lingqi,
    }


def get_skill_cooldown(player, skill_id: str) -> int:
    """获取技能冷却时间"""
    if not hasattr(player, 'skill_cooldowns'):
        return 0
    
    last_used = player.skill_cooldowns.get(skill_id, 0)
    skill = get_heal_skill(skill_id)
    if not skill:
        return 0
    
    remaining = skill.cooldown - (time.time() - last_used)
    return max(0, int(remaining))


def format_heal_skills_list(player) -> str:
    """格式化医疗技能列表"""
    skill_level = getattr(player, 'heal_skill_level', 0)
    lines = ["🏥 医疗技能：", ""]
    
    for skill in HEAL_SKILLS.values():
        available = skill.skill_level_req <= skill_level
        cooldown = get_skill_cooldown(player, skill.skill_id)
        
        status = "✅" if available else f"🔒 (需要等级{skill.skill_level_req})"
        if cooldown > 0:
            status = f"⏳ ({cooldown}秒)"
        
        max_heal = calculate_heal(player, skill)
        lines.append(f"{status} {skill.name}")
        lines.append(f"   治疗量: {skill.base_heal}-{max_heal} | 体力消耗: {skill.stamina_cost} | 冷却: {skill.cooldown}秒")
        lines.append(f"   {skill.description}")
        lines.append("")
    
    lines.append(f"当前医疗技能等级: {skill_level}")
    
    return "\n".join(lines)


def cure_injury(player, skill: HealSkill) -> dict:
    """
    使用医疗技能治疗重伤状态
    
    治疗重伤需要更高级的技能和更多的体力消耗
    """
    if not player.is_injured:
        return {"success": False, "message": "你没有受伤，不需要治疗", "cured": False}
    
    skill_level = getattr(player, 'heal_skill_level', 0)
    if skill.skill_level_req > skill_level:
        return {
            "success": False,
            "message": f"需要医疗技能等级 {skill.skill_level_req + 1} 才能治疗重伤",
            "cured": False,
        }
    
    required_stamina = skill.stamina_cost * 3
    if player.lingqi < required_stamina:
        return {
            "success": False,
            "message": f"治疗重伤需要 {required_stamina} 点体力，你只有 {player.lingqi} 点",
            "cured": False,
        }
    
    if random.random() > skill.success_rate:
        player.lingqi -= required_stamina
        return {
            "success": True,
            "message": f"治疗失败，消耗了 {required_stamina} 点体力，但伤势未愈",
            "cured": False,
            "healed": 0,
        }
    
    player.lingqi -= required_stamina
    player.is_injured = False
    player.injured_until = 0.0
    player.hp = int(player.max_hp * 0.5)
    
    return {
        "success": True,
        "message": f"治疗成功！重伤状态已解除，生命恢复至 {player.hp}/{player.max_hp}",
        "cured": True,
        "hp_restored": player.hp,
        "stamina_cost": required_stamina,
    }


def can_fight(player) -> tuple[bool, str]:
    """
    检查玩家是否可以战斗
    
    Returns:
        (can_fight: bool, reason: str)
    """
    if player.is_injured:
        return False, "你处于重伤状态，无法战斗，需要治疗才能恢复"
    
    if player.hp <= 0:
        return False, "生命值为0，无法战斗"
    
    return True, ""


def check_injury_expired(player) -> bool:
    """检查 временные 重伤是否过期"""
    if not player.is_injured:
        return False
    
    if player.injured_until > 0 and time.time() >= player.injured_until:
        player.is_injured = False
        player.injured_until = 0.0
        player.hp = int(player.max_hp * 0.3)
        return True
    
    return False
