"""
骑马与砍杀风格属性与技能系统

属性：力量、敏捷、智力
技能：每3点对应属性可加1点技能
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


class AttributeType(IntEnum):
    """属性类型"""
    STRENGTH = 1      # 力量
    AGILITY = 2       # 敏捷
    INTELLIGENCE = 3  # 智力


class SkillType(IntEnum):
    """技能类型"""
    # 力量系技能
    IRON_FLESH = 1        # 铁骨 - 增加生命值
    POWER_STRIKE = 2      # 强击 - 增加近战伤害
    WEAPON_MASTER = 3     # 武器专精 - 各类武器伤害加成
    
    # 敏捷系技能
    ATHLETICS = 10        # 跑动 - 增加闪避率
    SHIELD = 11           # 盾防 - 增加防御
    RIDING = 12           # 骑术 - 骑乘能力
    ARCHERY = 13         # 弓术 - 弓箭伤害
    THROWING = 14         # 投掷 - 投掷武器伤害
    
    # 智力系技能
    TACTICS = 20          # 战术 - 战斗策略
    TRAINING = 21         # 教练 - 训练士兵
    TRADE = 22            # 交易 - 买卖折扣
    PRISONER_MANAGEMENT = 23  # 俘虏管理 - 俘虏容量
    
    # 医疗系技能 (智力)
    FIRST_AID = 30        # 急救 - 战场包扎
    HERBALISM = 31        # 草药学 - 采集与制药
    SURGERY = 32         # 外科手术 - 高级治疗


ATTRIBUTE_NAMES = {
    AttributeType.STRENGTH: "力量",
    AttributeType.AGILITY: "敏捷",
    AttributeType.INTELLIGENCE: "智力",
}

ATTRIBUTE_ABBR = {
    AttributeType.STRENGTH: "力",
    AttributeType.AGILITY: "敏",
    AttributeType.INTELLIGENCE: "智",
}


@dataclass
class SkillDefinition:
    """技能定义"""
    skill_id: int
    name: str
    description: str
    icon: str
    attribute: AttributeType  # 主属性
    max_level: int = 10       # 最大等级
    effect_per_level: float = 0  # 每级效果值
    
    # 效果描述
    hp_effect: int = 0        # 每级生命值加成
    attack_effect: int = 0     # 每级攻击加成
    defense_effect: int = 0    # 每级防御加成
    dodge_effect: float = 0   # 每级闪避率(%)
    crit_effect: float = 0    # 每级暴击率(%)
    damage_effect: float = 0  # 每级伤害加成(%)
    ride_effect: int = 0      # 每级骑术加成
    trade_discount: float = 0 # 每级交易折扣(%)
    heal_effect: float = 0    # 每级治疗效果(%)
    gather_effect: int = 0    # 每级采集数量加成
    surgery_effect: bool = False  # 是否解锁外科手术
    
    # 前置技能
    prerequisite: Optional[int] = None


SKILL_DEFINITIONS: dict[int, SkillDefinition] = {
    # ==================== 力量系技能 ====================
    SkillType.IRON_FLESH: SkillDefinition(
        skill_id=SkillType.IRON_FLESH,
        name="铁骨",
        description="锻炼身体，增加生命值上限",
        icon="❤️",
        attribute=AttributeType.STRENGTH,
        max_level=10,
        hp_effect=20,
    ),
    SkillType.POWER_STRIKE: SkillDefinition(
        skill_id=SkillType.POWER_STRIKE,
        name="强击",
        description="全力一击，增加近战伤害",
        icon="⚔️",
        attribute=AttributeType.STRENGTH,
        max_level=10,
        damage_effect=0.05,  # 每级+5%伤害
    ),
    SkillType.WEAPON_MASTER: SkillDefinition(
        skill_id=SkillType.WEAPON_MASTER,
        name="武器专精",
        description="精通各类武器，提升所有武器伤害",
        icon="🗡️",
        attribute=AttributeType.STRENGTH,
        max_level=10,
        attack_effect=3,
    ),
    
    # ==================== 敏捷系技能 ====================
    SkillType.ATHLETICS: SkillDefinition(
        skill_id=SkillType.ATHLETICS,
        name="跑动",
        description="健步如飞，提升闪避率",
        icon="🏃",
        attribute=AttributeType.AGILITY,
        max_level=10,
        dodge_effect=1.5,  # 每级+1.5%闪避
    ),
    SkillType.SHIELD: SkillDefinition(
        skill_id=SkillType.SHIELD,
        name="盾防",
        description="举盾防御，提升防御力",
        icon="🛡️",
        attribute=AttributeType.AGILITY,
        max_level=10,
        defense_effect=2,
    ),
    SkillType.RIDING: SkillDefinition(
        skill_id=SkillType.RIDING,
        name="骑术",
        description="骑术精湛，骑乘时属性大幅提升",
        icon="🐎",
        attribute=AttributeType.AGILITY,
        max_level=10,
        ride_effect=5,
    ),
    SkillType.ARCHERY: SkillDefinition(
        skill_id=SkillType.ARCHERY,
        name="弓术",
        description="百步穿杨，提升弓箭伤害",
        icon="🏹",
        attribute=AttributeType.AGILITY,
        max_level=10,
        damage_effect=0.06,  # 每级+6%弓术伤害
    ),
    SkillType.THROWING: SkillDefinition(
        skill_id=SkillType.THROWING,
        name="投掷",
        description="投掷武器专家，提升投掷伤害",
        icon="🎯",
        attribute=AttributeType.AGILITY,
        max_level=10,
        damage_effect=0.06,
    ),
    
    # ==================== 智力系技能 ====================
    SkillType.TACTICS: SkillDefinition(
        skill_id=SkillType.TACTICS,
        name="战术",
        description="运筹帷幄，战斗中获得的经验提升",
        icon="📖",
        attribute=AttributeType.INTELLIGENCE,
        max_level=10,
        effect_per_level=0.05,  # 每级+5%经验
    ),
    SkillType.TRAINING: SkillDefinition(
        skill_id=SkillType.TRAINING,
        name="教练",
        description="训练士兵，提升训练效率",
        icon="🎓",
        attribute=AttributeType.INTELLIGENCE,
        max_level=10,
        effect_per_level=0.1,  # 每级+10%训练效率
    ),
    SkillType.TRADE: SkillDefinition(
        skill_id=SkillType.TRADE,
        name="交易",
        description="低价进货，高价出售",
        icon="💰",
        attribute=AttributeType.INTELLIGENCE,
        max_level=10,
        trade_discount=0.02,  # 每级+2%折扣
    ),
    SkillType.PRISONER_MANAGEMENT: SkillDefinition(
        skill_id=SkillType.PRISONER_MANAGEMENT,
        name="俘虏管理",
        description="管理俘虏，增加俘虏容量",
        icon="⛓️",
        attribute=AttributeType.INTELLIGENCE,
        max_level=10,
        effect_per_level=2,  # 每级+2俘虏容量
    ),
    
    # ==================== 医疗系技能 ====================
    SkillType.FIRST_AID: SkillDefinition(
        skill_id=SkillType.FIRST_AID,
        name="急救",
        description="战场急救基础知识，提升治疗效果",
        icon="🩹",
        attribute=AttributeType.INTELLIGENCE,
        max_level=10,
        heal_effect=0.05,  # 每级+5%治疗效果
    ),
    SkillType.HERBALISM: SkillDefinition(
        skill_id=SkillType.HERBALISM,
        name="草药学",
        description="辨认和采集草药，提升采集量和制作效率",
        icon="🌿",
        attribute=AttributeType.INTELLIGENCE,
        max_level=10,
        gather_effect=1,  # 每级+1采集数量
    ),
    SkillType.SURGERY: SkillDefinition(
        skill_id=SkillType.SURGERY,
        name="外科手术",
        description="进行外科手术的能力，可治疗重伤",
        icon="🔪",
        attribute=AttributeType.INTELLIGENCE,
        max_level=10,
        heal_effect=0.1,  # 每级+10%治疗效果
        surgery_effect=True,  # 高级治疗能力
    ),
}


def get_skills_by_attribute(attr: AttributeType) -> list[SkillDefinition]:
    """获取指定属性的所有技能"""
    return [s for s in SKILL_DEFINITIONS.values() if s.attribute == attr]


def get_skill_cost(skill_id: int, current_level: int) -> int:
    """
    计算技能升级所需技能点
    基础消耗1点，每级递增
    """
    return 1 + current_level // 3


def get_attribute_requirement(attr: AttributeType) -> int:
    """
    属性与技能的兑换比例
    每3点属性可加1点对应系技能
    """
    return 3


def calculate_skill_max_level(attribute_value: int, attr_requirement: int = 3) -> int:
    """
    根据属性值计算技能最大等级
    例如：9力量 = 3点铁骨 (9/3=3)
    """
    return attribute_value // attr_requirement


def get_total_attributes(strength: int, agility: int, intelligence: int) -> dict:
    """
    计算角色总属性
    """
    return {
        "strength": strength,
        "agility": agility,
        "intelligence": intelligence,
        "total": strength + agility + intelligence,
    }


def get_skill_bonus(skill_id: int, skill_level: int) -> dict:
    """
    获取技能等级提供的属性加成
    """
    skill = SKILL_DEFINITIONS.get(skill_id)
    if not skill:
        return {}
    
    level = min(skill_level, skill.max_level)
    if level <= 0:
        return {}
    
    bonus = {
        "hp": skill.hp_effect * level,
        "attack": skill.attack_effect * level,
        "defense": skill.defense_effect * level,
        "dodge": skill.dodge_effect * level,
        "crit": skill.crit_effect * level,
        "damage": skill.damage_effect * level,
        "ride": skill.ride_effect * level,
        "trade_discount": skill.trade_discount * level,
        "exp_bonus": skill.effect_per_level * level,
        "heal_effect": skill.heal_effect * level,
        "gather_effect": skill.gather_effect * level,
    }
    if skill.surgery_effect and level > 0:
        bonus["surgery_unlocked"] = True
    return bonus
