"""
骑砍风格医疗技能系统

医疗技能基于玩家的急救/草药学/外科手术技能等级，
治疗消耗体力(lingqi)。
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
        lingqi_cost: int,
        skill_level_req: int = 0,
        skill_type: str = "first_aid",  # first_aid, surgery
        can_cure_injury: bool = False,
    ):
        self.skill_id = skill_id
        self.name = name
        self.description = description
        self.base_heal = base_heal
        self.cooldown = cooldown
        self.lingqi_cost = lingqi_cost
        self.skill_level_req = skill_level_req
        self.skill_type = skill_type
        self.can_cure_injury = can_cure_injury


HEAL_SKILLS: dict[str, HealSkill] = {
    # 急救技能 (需要 FIRST_AID 技能)
    "bandage": HealSkill(
        skill_id="bandage",
        name="战场包扎",
        description="基础的战场急救，用绷带止血",
        base_heal=30,
        cooldown=30,
        lingqi_cost=10,
        skill_level_req=1,
        skill_type="first_aid",
    ),
    "field_dressing": HealSkill(
        skill_id="field_dressing",
        name="野战救护",
        description="在恶劣环境下进行紧急救护",
        base_heal=60,
        cooldown=60,
        lingqi_cost=15,
        skill_level_req=3,
        skill_type="first_aid",
    ),
    "battlefield_medicine": HealSkill(
        skill_id="battlefield_medicine",
        name="战地医疗",
        description="专业的战地医疗知识",
        base_heal=100,
        cooldown=90,
        lingqi_cost=20,
        skill_level_req=5,
        skill_type="first_aid",
    ),
    
    # 外科手术技能 (需要 SURGERY 技能)
    "field_surgery": HealSkill(
        skill_id="field_surgery",
        name="野战外科",
        description="处理重伤员的外科手术",
        base_heal=180,
        cooldown=120,
        lingqi_cost=30,
        skill_level_req=1,
        skill_type="surgery",
        can_cure_injury=True,
    ),
    "trauma_treatment": HealSkill(
        skill_id="trauma_treatment",
        name="创伤治疗",
        description="处理各种创伤的专业技术",
        base_heal=280,
        cooldown=180,
        lingqi_cost=40,
        skill_level_req=4,
        skill_type="surgery",
        can_cure_injury=True,
    ),
    "master_surgeon": HealSkill(
        skill_id="master_surgeon",
        name="外科大师",
        description="精通各种外科手术的大师级技能",
        base_heal=400,
        cooldown=240,
        lingqi_cost=50,
        skill_level_req=7,
        skill_type="surgery",
        can_cure_injury=True,
    ),
}


def get_heal_skill(skill_id: str) -> HealSkill | None:
    """获取医疗技能"""
    return HEAL_SKILLS.get(skill_id)


def get_all_heal_skills() -> list[HealSkill]:
    """获取所有医疗技能"""
    return list(HEAL_SKILLS.values())


def get_available_heal_skills(first_aid_level: int, surgery_level: int) -> list[HealSkill]:
    """根据技能等级获取可用技能"""
    available = []
    for skill in HEAL_SKILLS.values():
        if skill.skill_type == "first_aid" and first_aid_level >= skill.skill_level_req:
            available.append(skill)
        elif skill.skill_type == "surgery" and surgery_level >= skill.skill_level_req:
            available.append(skill)
    return available


def calculate_heal(player, skill: HealSkill) -> int:
    """
    计算实际治疗量
    
    治疗量 = 基础治疗量 × (1 + 技能加成)
    """
    first_aid_level = player.skills.get(30, 0)  # FIRST_AID
    surgery_level = player.skills.get(32, 0)  # SURGERY
    
    skill_level = first_aid_level if skill.skill_type == "first_aid" else surgery_level
    
    from .mb_attributes import get_skill_bonus
    bonus = get_skill_bonus(30 if skill.skill_type == "first_aid" else 32, skill_level)
    heal_bonus = bonus.get("heal_effect", 0)
    
    heal_amount = int(skill.base_heal * (1 + heal_bonus))
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
    
    first_aid_level = player.skills.get(30, 0)
    surgery_level = player.skills.get(32, 0)
    
    if skill.skill_type == "first_aid" and first_aid_level < skill.skill_level_req:
        return {
            "success": False, 
            "message": f"需要急救技能 {skill.skill_level_req} 级才能使用此技能",
            "healed": 0
        }
    elif skill.skill_type == "surgery" and surgery_level < skill.skill_level_req:
        return {
            "success": False, 
            "message": f"需要外科手术技能 {skill.skill_level_req} 级才能使用此技能",
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
    
    if player.lingqi < skill.lingqi_cost:
        return {
            "success": False,
            "message": f"体力不足，需要 {skill.lingqi_cost} 点体力",
            "healed": 0
        }
    
    player.lingqi -= skill.lingqi_cost
    
    heal_amount = calculate_heal(player, skill)
    player.hp = min(player.max_hp, player.hp + heal_amount)
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
    first_aid_level = player.skills.get(30, 0)
    surgery_level = player.skills.get(32, 0)
    
    lines = ["🏥 医疗技能：", ""]
    
    for skill in HEAL_SKILLS.values():
        if skill.skill_type == "first_aid":
            player_level = first_aid_level
            skill_name = "急救"
        else:
            player_level = surgery_level
            skill_name = "外科"
        
        available = player_level >= skill.skill_level_req
        cooldown = get_skill_cooldown(player, skill.skill_id)
        
        if cooldown > 0:
            status = f"⏳ 冷却中({cooldown}秒)"
        elif available:
            status = "✅ 可用"
        else:
            status = f"🔒 需要{skill_name}{skill.skill_level_req}级"
        
        max_heal = calculate_heal(player, skill)
        lines.append(f"{status} {skill.name}")
        lines.append(f"   治疗量: {skill.base_heal}~{max_heal} | 体力消耗: {skill.lingqi_cost} | 冷却: {skill.cooldown}秒")
        if skill.can_cure_injury:
            lines.append(f"   ⚕️ 可治疗重伤")
        lines.append(f"   {skill.description}")
        lines.append("")
    
    lines.append(f"当前技能等级: 急救 {first_aid_level}级 | 外科 {surgery_level}级")
    
    return "\n".join(lines)


def cure_injury_with_skill(player, skill: HealSkill) -> dict:
    """
    使用医疗技能治疗重伤状态
    
    治疗重伤需要外科手术技能和更多体力
    """
    if not skill.can_cure_injury:
        return {"success": False, "message": "该技能无法治疗重伤", "cured": False}
    
    surgery_level = player.skills.get(32, 0)
    if surgery_level < skill.skill_level_req:
        return {
            "success": False,
            "message": f"需要外科手术 {skill.skill_level_req} 级才能治疗重伤",
            "cured": False,
        }
    
    required_lingqi = skill.lingqi_cost * 3
    if player.lingqi < required_lingqi:
        return {
            "success": False,
            "message": f"治疗重伤需要 {required_lingqi} 点体力，你只有 {player.lingqi} 点",
            "cured": False,
        }
    
    player.lingqi -= required_lingqi
    
    heal_amount = int(player.max_hp * 0.5)
    player.hp = min(player.max_hp, player.hp + heal_amount)
    
    if hasattr(player, 'is_injured'):
        player.is_injured = False
    if hasattr(player, 'injured_until'):
        player.injured_until = 0.0
    
    return {
        "success": True,
        "message": f"手术成功！重伤已治愈，生命恢复至 {player.hp}/{player.max_hp}",
        "cured": True,
        "hp_restored": heal_amount,
        "lingqi_cost": required_lingqi,
    }
