"""
骑砍技能系统 - 精简版

参考 Mount & Blade 原始技能系统：
- 个人技能：铁骨、强击、跑动、盾防
- 武器技能：单手、双手、长柄、远程
- 骑乘技能：骑术
- 社交技能：领导、交易、掠夺

保留核心，删除冗余。
"""

from __future__ import annotations

from .constants import (
    HeartMethodDef, GongfaDef,
    HEART_METHOD_REGISTRY, GONGFA_REGISTRY,
    HeartMethodQuality, GongfaTier,
)


def _hm(method_id: str, name: str, level_req: int, quality: int,
         exp_mult: float, atk: int, dfn: int, hp: int,
         desc: str = "", mastery_exp: int = 100) -> HeartMethodDef:
    """被动技能定义"""
    return HeartMethodDef(
        method_id=method_id, name=name, realm=level_req, quality=quality,
        exp_multiplier=exp_mult, attack_bonus=atk, defense_bonus=dfn,
        dao_yun_rate=0.0, description=desc, mastery_exp=mastery_exp,
    )


def _gf(gongfa_id: str, name: str, tier: int,
         atk: int, dfn: int, effect_type: str = "damage",
         effect_value: int = 0, cooldown: int = 60,
         desc: str = "", price: int = 1000,
         lingqi_cost: int = 0) -> GongfaDef:
    """战斗技能定义"""
    return GongfaDef(
        gongfa_id=gongfa_id, name=name, tier=tier,
        attack_bonus=atk, defense_bonus=dfn,
        hp_regen=effect_value if effect_type == "heal" else 0,
        lingqi_regen=effect_value if effect_type == "stamina" else 0,
        description=desc, mastery_exp=200,
        dao_yun_cost=0, recycle_price=price,
        lingqi_cost=lingqi_cost,
    )


# ══════════════════════════════════════════════════════════════
# 个人技能 - Personal Skills
# ══════════════════════════════════════════════════════════════

# 铁骨 - 增加生命值
IRONFLESH = [
    _hm("skill_ironflesh_1", "铁骨·初", 0, 0, 0.02, 0, 0, 20, "增加生命上限20", 80),
    _hm("skill_ironflesh_2", "铁骨·中", 1, 0, 0.03, 0, 0, 50, "增加生命上限50", 160),
    _hm("skill_ironflesh_3", "铁骨·高", 2, 1, 0.05, 0, 0, 100, "增加生命上限100", 320),
    _hm("skill_ironflesh_4", "铁骨·大", 3, 1, 0.08, 0, 0, 180, "增加生命上限180", 640),
    _hm("skill_ironflesh_5", "铁骨·宗", 4, 2, 0.12, 0, 0, 300, "增加生命上限300", 1280),
]

# 强击 - 增加攻击力
POWER_STRIKE = [
    _hm("skill_powerstrike_1", "强击·初", 0, 0, 0.02, 5, 0, 0, "增加攻击5", 80),
    _hm("skill_powerstrike_2", "强击·中", 1, 0, 0.03, 12, 0, 0, "增加攻击12", 160),
    _hm("skill_powerstrike_3", "强击·高", 2, 1, 0.05, 25, 0, 0, "增加攻击25", 320),
    _hm("skill_powerstrike_4", "强击·大", 3, 1, 0.08, 45, 0, 0, "增加攻击45", 640),
    _hm("skill_powerstrike_5", "强击·宗", 4, 2, 0.12, 80, 0, 0, "增加攻击80", 1280),
]

# 盾防 - 增加防御
SHIELD = [
    _hm("skill_shield_1", "盾防·初", 0, 0, 0.02, 0, 5, 0, "增加防御5", 80),
    _hm("skill_shield_2", "盾防·中", 1, 0, 0.03, 0, 12, 0, "增加防御12", 160),
    _hm("skill_shield_3", "盾防·高", 2, 1, 0.05, 0, 25, 0, "增加防御25", 320),
    _hm("skill_shield_4", "盾防·大", 3, 1, 0.08, 0, 45, 0, "增加防御45", 640),
    _hm("skill_shield_5", "盾防·宗", 4, 2, 0.12, 0, 80, 0, "增加防御80", 1280),
]

# 跑动 - 敏捷/闪避
ATHLETICS = [
    _hm("skill_athletics_1", "跑动·初", 0, 0, 0.02, 2, 3, 10, "敏捷提升", 80),
    _hm("skill_athletics_2", "跑动·中", 1, 0, 0.03, 5, 8, 25, "更灵活", 160),
    _hm("skill_athletics_3", "跑动·高", 2, 1, 0.05, 10, 15, 50, "如风", 320),
    _hm("skill_athletics_4", "跑动·大", 3, 1, 0.08, 18, 25, 90, "疾如风", 640),
    _hm("skill_athletics_5", "跑动·宗", 4, 2, 0.12, 30, 40, 150, "来去如风", 1280),
]


# ══════════════════════════════════════════════════════════════
# 武器技能 - Weapon Skills
# ══════════════════════════════════════════════════════════════

# 单手武器
ONE_HANDED = [
    _hm("skill_onehanded_1", "单手·初", 0, 0, 0.02, 3, 2, 0, "单手武器伤害+5%", 80),
    _hm("skill_onehanded_2", "单手·中", 1, 0, 0.03, 7, 5, 0, "单手武器伤害+10%", 160),
    _hm("skill_onehanded_3", "单手·高", 2, 1, 0.05, 14, 10, 0, "单手武器伤害+18%", 320),
    _hm("skill_onehanded_4", "单手·大", 3, 1, 0.08, 25, 18, 0, "单手武器伤害+28%", 640),
    _hm("skill_onehanded_5", "单手·宗", 4, 2, 0.12, 40, 30, 0, "单手武器伤害+40%", 1280),
]

# 双手武器
TWO_HANDED = [
    _hm("skill_twohanded_1", "双手·初", 0, 0, 0.02, 5, 0, 0, "双手武器伤害+8%", 80),
    _hm("skill_twohanded_2", "双手·中", 1, 0, 0.03, 12, 0, 0, "双手武器伤害+15%", 160),
    _hm("skill_twohanded_3", "双手·高", 2, 1, 0.05, 22, 0, 0, "双手武器伤害+25%", 320),
    _hm("skill_twohanded_4", "双手·大", 3, 1, 0.08, 38, 0, 0, "双手武器伤害+38%", 640),
    _hm("skill_twohanded_5", "双手·宗", 4, 2, 0.12, 60, 0, 0, "双手武器伤害+55%", 1280),
]

# 长柄武器
POLEARM = [
    _hm("skill_polearm_1", "长柄·初", 0, 0, 0.02, 4, 1, 0, "长柄武器伤害+6%", 80),
    _hm("skill_polearm_2", "长柄·中", 1, 0, 0.03, 10, 3, 0, "长柄武器伤害+12%", 160),
    _hm("skill_polearm_3", "长柄·高", 2, 1, 0.05, 20, 6, 0, "长柄武器伤害+20%", 320),
    _hm("skill_polearm_4", "长柄·大", 3, 1, 0.08, 35, 10, 0, "长柄武器伤害+32%", 640),
    _hm("skill_polearm_5", "长柄·宗", 4, 2, 0.12, 55, 15, 0, "长柄武器伤害+48%", 1280),
]

# 弓弩/远程
ARCHERY = [
    _hm("skill_archery_1", "弓弩·初", 0, 0, 0.02, 4, 0, 0, "弓弩伤害+8%", 80),
    _hm("skill_archery_2", "弓弩·中", 1, 0, 0.03, 10, 0, 0, "弓弩伤害+15%", 160),
    _hm("skill_archery_3", "弓弩·高", 2, 1, 0.05, 20, 0, 0, "弓弩伤害+25%", 320),
    _hm("skill_archery_4", "弓弩·大", 3, 1, 0.08, 35, 0, 0, "弓弩伤害+38%", 640),
    _hm("skill_archery_5", "弓弩·宗", 4, 2, 0.12, 55, 0, 0, "弓弩伤害+55%", 1280),
]


# ══════════════════════════════════════════════════════════════
# 骑乘技能 - Horse Skills
# ══════════════════════════════════════════════════════════════

RIDING = [
    _hm("skill_riding_1", "骑术·初", 0, 0, 0.02, 3, 2, 0, "骑乘时攻防+5%", 80),
    _hm("skill_riding_2", "骑术·中", 1, 0, 0.03, 8, 5, 0, "骑乘时攻防+12%", 160),
    _hm("skill_riding_3", "骑术·高", 2, 1, 0.05, 16, 10, 0, "骑乘时攻防+20%", 320),
    _hm("skill_riding_4", "骑术·大", 3, 1, 0.08, 28, 18, 0, "骑乘时攻防+32%", 640),
    _hm("skill_riding_5", "骑术·宗", 4, 2, 0.12, 45, 30, 0, "骑乘时攻防+50%", 1280),
]


# ══════════════════════════════════════════════════════════════
# 社交技能 - Social Skills
# ══════════════════════════════════════════════════════════════

# 领导
LEADERSHIP = [
    _hm("skill_leadership_1", "领导·初", 0, 0, 0.02, 2, 2, 10, "队伍成员攻防+5%", 80),
    _hm("skill_leadership_2", "领导·中", 1, 0, 0.03, 5, 5, 25, "队伍成员攻防+10%", 160),
    _hm("skill_leadership_3", "领导·高", 2, 1, 0.05, 10, 10, 50, "队伍成员攻防+18%", 320),
    _hm("skill_leadership_4", "领导·大", 3, 1, 0.08, 18, 18, 90, "队伍成员攻防+28%", 640),
    _hm("skill_leadership_5", "领导·宗", 4, 2, 0.12, 30, 30, 150, "队伍成员攻防+40%", 1280),
]

# 交易
TRADE = [
    _hm("skill_trade_1", "交易·初", 0, 0, 0.02, 0, 0, 0, "商店价格-5%", 80),
    _hm("skill_trade_2", "交易·中", 1, 0, 0.03, 0, 0, 0, "商店价格-10%", 160),
    _hm("skill_trade_3", "交易·高", 2, 1, 0.05, 0, 0, 0, "商店价格-18%", 320),
    _hm("skill_trade_4", "交易·大", 3, 1, 0.08, 0, 0, 0, "商店价格-28%", 640),
    _hm("skill_trade_5", "交易·宗", 4, 2, 0.12, 0, 0, 0, "商店价格-40%", 1280),
]

# 掠夺
LOOTING = [
    _hm("skill_looting_1", "掠夺·初", 0, 0, 0.02, 0, 0, 0, "战利品+5%", 80),
    _hm("skill_looting_2", "掠夺·中", 1, 0, 0.03, 0, 0, 0, "战利品+10%", 160),
    _hm("skill_looting_3", "掠夺·高", 2, 1, 0.05, 0, 0, 0, "战利品+18%", 320),
    _hm("skill_looting_4", "掠夺·大", 3, 1, 0.08, 0, 0, 0, "战利品+28%", 640),
    _hm("skill_looting_5", "掠夺·宗", 4, 2, 0.12, 0, 0, 0, "战利品+40%", 1280),
]


# ══════════════════════════════════════════════════════════════
# 战斗技能 - Active Combat Skills
# ══════════════════════════════════════════════════════════════

# 冲锋 - 骑乘冲锋
SKILL_CHARGE = [
    _gf("combo_charge_1", "冲锋·初", 0, 30, 0, "damage", 0, 60, "骑枪冲锋", 1000, 10),
    _gf("combo_charge_2", "冲锋·中", 1, 60, 0, "damage", 0, 90, "猛烈冲锋", 2000, 18),
    _gf("combo_charge_3", "冲锋·高", 2, 120, 0, "damage", 0, 120, "毁灭冲锋", 3500, 28),
]

# 战吼 - 震慑敌人
SKILL_BATTLE_CRY = [
    _gf("combo_battlecry_1", "战吼·初", 0, 0, 5, "debuff", 10, 45, "震慑敌人，降低其防御", 1000, 12),
    _gf("combo_battlecry_2", "战吼·中", 1, 0, 12, "debuff", 20, 60, "敌人闻风丧胆", 2000, 20),
    _gf("combo_battlecry_3", "战吼·高", 2, 0, 25, "debuff", 35, 90, "战神咆哮", 3500, 32),
]

# 狂暴 - 以伤换伤
SKILL_BERSERK = [
    _gf("combo_berserk_1", "狂暴·初", 0, 25, -5, "damage", 0, 30, "以伤换伤，大幅提升攻击", 1200, 10),
    _gf("combo_berserk_2", "狂暴·中", 1, 50, -10, "damage", 0, 45, "更加狂暴", 2200, 18),
    _gf("combo_berserk_3", "狂暴·高", 2, 100, -18, "damage", 0, 60, "化身狂神", 3800, 28),
]

# 反击 - 格挡后反击
SKILL_COUNTER = [
    _gf("combo_counter_1", "反击·初", 0, 15, 15, "damage", 0, 45, "格挡后反击", 1000, 12),
    _gf("combo_counter_2", "反击·中", 1, 35, 35, "damage", 0, 60, "更有效反击", 2000, 20),
    _gf("combo_counter_3", "反击·高", 2, 70, 70, "damage", 0, 90, "无懈可击", 3500, 32),
]


# ══════════════════════════════════════════════════════════════
# 注册所有技能
# ══════════════════════════════════════════════════════════════

def register_skills():
    """注册精简后的骑砍技能"""
    
    passive_skills = [
        IRONFLESH, POWER_STRIKE, SHIELD, ATHLETICS,
        ONE_HANDED, TWO_HANDED, POLEARM, ARCHERY,
        RIDING, LEADERSHIP, TRADE, LOOTING,
    ]
    
    for skill_list in passive_skills:
        for skill in skill_list:
            HEART_METHOD_REGISTRY[skill.method_id] = skill
    
    active_skills = [
        SKILL_CHARGE, SKILL_BATTLE_CRY, SKILL_BERSERK, SKILL_COUNTER,
    ]
    
    for skill_list in active_skills:
        for skill in skill_list:
            GONGFA_REGISTRY[skill.gongfa_id] = skill
    
    return {
        "passive": sum(len(s) for s in passive_skills),
        "active": sum(len(s) for s in active_skills),
    }


# ══════════════════════════════════════════════════════════════
# 技能树信息
# ══════════════════════════════════════════════════════════════

SKILL_TREES = {
    "ironflesh": {
        "name": "铁骨",
        "category": "personal",
        "desc": "增加生命值上限",
        "skills": [s.method_id for s in IRONFLESH],
    },
    "powerstrike": {
        "name": "强击", 
        "category": "personal",
        "desc": "增加攻击力",
        "skills": [s.method_id for s in POWER_STRIKE],
    },
    "shield": {
        "name": "盾防",
        "category": "personal", 
        "desc": "增加防御力",
        "skills": [s.method_id for s in SHIELD],
    },
    "athletics": {
        "name": "跑动",
        "category": "personal",
        "desc": "增加敏捷和闪避",
        "skills": [s.method_id for s in ATHLETICS],
    },
    "onehanded": {
        "name": "单手",
        "category": "weapon",
        "desc": "单手武器伤害加成",
        "skills": [s.method_id for s in ONE_HANDED],
    },
    "twohanded": {
        "name": "双手",
        "category": "weapon",
        "desc": "双手武器伤害加成",
        "skills": [s.method_id for s in TWO_HANDED],
    },
    "polearm": {
        "name": "长柄",
        "category": "weapon",
        "desc": "长柄武器伤害加成",
        "skills": [s.method_id for s in POLEARM],
    },
    "archery": {
        "name": "弓弩",
        "category": "weapon",
        "desc": "远程武器伤害加成",
        "skills": [s.method_id for s in ARCHERY],
    },
    "riding": {
        "name": "骑术",
        "category": "horse",
        "desc": "骑乘战斗能力",
        "skills": [s.method_id for s in RIDING],
    },
    "leadership": {
        "name": "领导",
        "category": "social",
        "desc": "队伍成员属性加成",
        "skills": [s.method_id for s in LEADERSHIP],
    },
    "trade": {
        "name": "交易",
        "category": "social",
        "desc": "商店价格折扣",
        "skills": [s.method_id for s in TRADE],
    },
    "looting": {
        "name": "掠夺",
        "category": "social",
        "desc": "战利品获取增加",
        "skills": [s.method_id for s in LOOTING],
    },
}


def get_skill_trees_by_category() -> dict:
    """按类别获取技能树"""
    categories = {
        "personal": [],
        "weapon": [],
        "horse": [],
        "social": [],
    }
    
    for tree_id, tree in SKILL_TREES.items():
        cat = tree["category"]
        if cat in categories:
            categories[cat].append({
                "id": tree_id,
                "name": tree["name"],
                "desc": tree["desc"],
                "skill_count": len(tree["skills"]),
            })
    
    return categories


# 自动注册
SKILL_STATS = register_skills()
