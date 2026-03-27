"""游戏常量：等级配置、物品注册表、装备注册表 - 骑马与砍杀风格。"""

import hashlib
import threading
from dataclasses import dataclass, field
from datetime import date
from enum import IntEnum

# 保护注册表热更新（clear+update+refresh）的原子性
_registry_lock = threading.Lock()


class RealmLevel(IntEnum):
    """骑士等级。"""
    MORTAL = 0           # 平民
    QI_REFINING = 1      # 新兵
    FOUNDATION = 2       # 老兵
    GOLDEN_CORE = 3      # 骑士
    NASCENT_SOUL = 4     # 骑士长
    DEITY_TRANSFORM = 5   # 领主
    VOID_MERGE = 6       # 男爵
    TRIBULATION = 7       # 子爵
    MAHAYANA = 8         # 伯爵


# 有小爵位的大爵位范围
SUB_REALM_MIN = RealmLevel.QI_REFINING
SUB_REALM_MAX = RealmLevel.MAHAYANA
MAX_SUB_REALM = 9  # 新兵~伯爵: 0=一期, 9=十期(圆满)
MAX_HIGH_SUB_REALM = 3  # 领主~伯爵: 0=初期, 3=圆满

SUB_REALM_NAMES = ["新兵", "士兵", "老练", "精锐", "精英", "高手", "大师", "宗师", "传奇", "巅峰"]
HIGH_SUB_REALM_NAMES = ["初级", "中级", "高级", "大师级"]

# 骑士长开始，升级有死亡概率
DEATH_REALM_START = RealmLevel.NASCENT_SOUL


REALM_CONFIG: dict[int, dict] = {
    RealmLevel.MORTAL: {
        "name": "平民",
        "has_sub_realm": False,
        "exp_to_next": 100,
        "sub_exp_to_next": 0,
        "base_hp": 100,
        "base_attack": 10,
        "base_defense": 5,
        "base_lingqi": 50,
        "breakthrough_rate": 1.0,
        "death_rate": 0.0,
    },
    RealmLevel.QI_REFINING: {
        "name": "新兵",
        "has_sub_realm": True,
        "exp_to_next": 500,
        "sub_exp_to_next": 50,
        "base_hp": 300,
        "base_attack": 30,
        "base_defense": 15,
        "base_lingqi": 120,
        "breakthrough_rate": 0.85,
        "death_rate": 0.0,
    },
    RealmLevel.FOUNDATION: {
        "name": "老兵",
        "has_sub_realm": True,
        "exp_to_next": 1500,
        "sub_exp_to_next": 150,
        "base_hp": 800,
        "base_attack": 80,
        "base_defense": 40,
        "base_lingqi": 300,
        "breakthrough_rate": 0.7,
        "death_rate": 0.0,
    },
    RealmLevel.GOLDEN_CORE: {
        "name": "骑士",
        "has_sub_realm": True,
        "exp_to_next": 5000,
        "sub_exp_to_next": 500,
        "base_hp": 2000,
        "base_attack": 200,
        "base_defense": 100,
        "base_lingqi": 700,
        "breakthrough_rate": 0.5,
        "death_rate": 0.0,
    },
    RealmLevel.NASCENT_SOUL: {
        "name": "骑士长",
        "has_sub_realm": True,
        "exp_to_next": 15000,
        "sub_exp_to_next": 1500,
        "base_hp": 5000,
        "base_attack": 500,
        "base_defense": 250,
        "base_lingqi": 1600,
        "breakthrough_rate": 0.35,
        "death_rate": 0.05,
    },
    RealmLevel.DEITY_TRANSFORM: {
        "name": "领主",
        "has_sub_realm": True,
        "high_realm": True,
        "exp_to_next": 50000,
        "sub_exp_to_next": 12500,
        "base_hp": 12000,
        "base_attack": 1200,
        "base_defense": 600,
        "base_lingqi": 3600,
        "breakthrough_rate": 0.25,
        "death_rate": 0.10,
        "sub_dao_yun_costs": [50, 80, 100, 120],
        "breakthrough_dao_yun_cost": 120,
    },
    RealmLevel.VOID_MERGE: {
        "name": "男爵",
        "has_sub_realm": True,
        "high_realm": True,
        "exp_to_next": 150000,
        "sub_exp_to_next": 37500,
        "base_hp": 30000,
        "base_attack": 3000,
        "base_defense": 1500,
        "base_lingqi": 8000,
        "breakthrough_rate": 0.18,
        "death_rate": 0.15,
        "sub_dao_yun_costs": [240, 260, 280, 300],
        "breakthrough_dao_yun_cost": 300,
    },
    RealmLevel.TRIBULATION: {
        "name": "子爵",
        "has_sub_realm": True,
        "high_realm": True,
        "exp_to_next": 500000,
        "sub_exp_to_next": 125000,
        "base_hp": 80000,
        "base_attack": 8000,
        "base_defense": 4000,
        "base_lingqi": 18000,
        "breakthrough_rate": 0.12,
        "death_rate": 0.20,
        "sub_dao_yun_costs": [600, 640, 680, 720],
        "breakthrough_dao_yun_cost": 720,
    },
    RealmLevel.MAHAYANA: {
        "name": "伯爵",
        "has_sub_realm": True,
        "high_realm": True,
        "exp_to_next": 999999999,
        "sub_exp_to_next": 250000,
        "base_hp": 200000,
        "base_attack": 20000,
        "base_defense": 10000,
        "base_lingqi": 40000,
        "breakthrough_rate": 0.0,
        "death_rate": 0.30,
        "sub_dao_yun_costs": [1440, 1520, 1600, 1680],
        "breakthrough_dao_yun_cost": 1680,
    },
}


@dataclass
class ItemDef:
    """物品定义。"""
    item_id: str
    name: str
    item_type: str  # "consumable" | "material" | "equipment" | "skill" | "combat_skill"
    description: str
    effect: dict = field(default_factory=dict)


# 初始物品注册表 - 骑砍风格
ITEM_REGISTRY: dict[str, ItemDef] = {
    "healing_pill": ItemDef(
        item_id="healing_pill",
        name="治疗药水",
        item_type="consumable",
        description="恢复50点生命值",
        effect={"heal_hp": 50},
    ),
    "exp_pill": ItemDef(
        item_id="exp_pill",
        name="经验卷轴",
        item_type="consumable",
        description="获得100点战斗经验",
        effect={"exp_bonus": 100},
    ),
    "spirit_stone": ItemDef(
        item_id="spirit_stone",
        name="第纳尔",
        item_type="material",
        description="卡拉迪亚大陆通用货币",
    ),
    "breakthrough_pill": ItemDef(
        item_id="breakthrough_pill",
        name="晋级证书",
        item_type="consumable",
        description="升级时额外增加20%成功率",
        effect={"breakthrough_bonus": 0.2},
    ),
    "body_tempering_pill": ItemDef(
        item_id="body_tempering_pill",
        name="力量药水",
        item_type="consumable",
        description="永久增加10点攻击力",
        effect={"attack_boost": 10},
    ),
    "life_talisman": ItemDef(
        item_id="life_talisman",
        name="护身符",
        item_type="consumable",
        description="战死时免除死亡（骑士长以上）",
        effect={"prevent_death": True},
    ),
}

# ── 注册 200 种新药剂到 ITEM_REGISTRY ──
from .pills import get_pill_item_defs as _get_pill_item_defs  # noqa: E402
ITEM_REGISTRY.update(_get_pill_item_defs())

# 签到药剂权重表：(item_id, weight)
CHECKIN_PILL_WEIGHTS: list[tuple[str, int]] = [
    ("body_tempering_pill", 40),
    ("healing_pill", 30),
    ("exp_pill", 20),
    ("breakthrough_pill", 10),
]


# ──────────────────── 装备系统 ────────────────────

class EquipmentTier(IntEnum):
    """装备品阶。"""
    COMMON = 0       # 普通
    FINE = 1         # 精良
    RARE = 2         # 稀有
    EPIC = 3         # 史诗
    LEGENDARY = 4    # 传说


EQUIPMENT_TIER_NAMES: dict[int, str] = {
    EquipmentTier.COMMON: "普通",
    EquipmentTier.FINE: "精良",
    EquipmentTier.RARE: "稀有",
    EquipmentTier.EPIC: "史诗",
    EquipmentTier.LEGENDARY: "传说",
}

EQUIPMENT_SLOTS = [
    "weapon",     # 武器
    "head",       # 头部
    "body",       # 身体
    "hands",      # 手部
    "legs",       # 腿部
    "shoulders",  # 肩甲/披风
    "accessory1", # 饰品1
    "accessory2", # 饰品2
]

EQUIPMENT_SLOT_NAMES: dict[str, str] = {
    "weapon": "武器",
    "head": "头部",
    "body": "身体",
    "hands": "手部",
    "legs": "腿部",
    "shoulders": "肩甲",
    "accessory1": "饰品",
    "accessory2": "饰品",
}

# 装备品阶 → 可装备的等级范围 (min_realm, max_realm)
TIER_REALM_REQUIREMENTS: dict[int, tuple[int, int]] = {
    EquipmentTier.COMMON: (RealmLevel.MORTAL, RealmLevel.FOUNDATION),
    EquipmentTier.FINE: (RealmLevel.QI_REFINING, RealmLevel.GOLDEN_CORE),
    EquipmentTier.RARE: (RealmLevel.NASCENT_SOUL, RealmLevel.VOID_MERGE),
    EquipmentTier.EPIC: (RealmLevel.VOID_MERGE, RealmLevel.MAHAYANA),
    EquipmentTier.LEGENDARY: (RealmLevel.TRIBULATION, RealmLevel.MAHAYANA),
}


@dataclass
class EquipmentDef:
    """装备定义。"""
    equip_id: str
    name: str
    tier: int          # EquipmentTier
    slot: str          # 装备槽位
    attack: int = 0
    defense: int = 0
    hp: int = 0       # 生命值加成
    special_effect: str = ""  # 特殊效果(仅史诗/传说)
    description: str = ""
    element: str = "无"  # 元素属性（保留字段）
    element_damage: int = 0  # 元素伤害（保留字段）


# ══════════════════════════════════════════════════════════════
# 普通装备 (COMMON) - 基础属性
# ══════════════════════════════════════════════════════════════

_COMMON_WEAPONS: list[EquipmentDef] = [
    EquipmentDef("common_wooden_stick", "木棍", EquipmentTier.COMMON, "weapon",
                 attack=5, description="随手捡来的木棍"),
    EquipmentDef("common_rusty_sword", "生锈短剑", EquipmentTier.COMMON, "weapon",
                 attack=8, description="锈迹斑斑的短剑"),
    EquipmentDef("common_hunting_bow", "猎弓", EquipmentTier.COMMON, "weapon",
                 attack=6, description="猎人使用的简易木弓"),
    EquipmentDef("common_wooden_spear", "木矛", EquipmentTier.COMMON, "weapon",
                 attack=7, description="削尖的木棍充当长矛"),
    EquipmentDef("common_farm_axe", "农斧", EquipmentTier.COMMON, "weapon",
                 attack=9, description="农夫劈柴用的斧头"),
]

_COMMON_HEAD: list[EquipmentDef] = [
    EquipmentDef("common_straw_hat", "草帽", EquipmentTier.COMMON, "head",
                 defense=2, description="农民戴的草编帽子"),
    EquipmentDef("common_cloth_bandana", "布头巾", EquipmentTier.COMMON, "head",
                 defense=1, hp=5, description="一块布条缠在头上"),
    EquipmentDef("common_wooden_helmet", "木头盔", EquipmentTier.COMMON, "head",
                 defense=3, description="木头削成的简陋头盔"),
]

_COMMON_BODY: list[EquipmentDef] = [
    EquipmentDef("common_ragged_cloth", "破旧布衣", EquipmentTier.COMMON, "body",
                 defense=3, hp=10, description="补丁摞补丁的衣服"),
    EquipmentDef("common_vest", "旧背心", EquipmentTier.COMMON, "body",
                 defense=4, description="耐磨的旧皮背心"),
    EquipmentDef("common_poncho", "披风斗篷", EquipmentTier.COMMON, "body",
                 defense=2, hp=15, description="简陋的织物斗篷"),
]

_COMMON_HANDS: list[EquipmentDef] = [
    EquipmentDef("common_leather_gloves", "皮手套", EquipmentTier.COMMON, "hands",
                 defense=2, attack=1, description="粗糙的皮革手套"),
    EquipmentDef("common_wooden_bracers", "木护腕", EquipmentTier.COMMON, "hands",
                 defense=3, description="木头削制的简易护腕"),
    EquipmentDef("common_ragged_wraps", "破布条", EquipmentTier.COMMON, "hands",
                 defense=1, description="缠在手上的破布"),
]

_COMMON_LEGS: list[EquipmentDef] = [
    EquipmentDef("common_cloth_pants", "布裤子", EquipmentTier.COMMON, "legs",
                 defense=2, hp=5, description="普通棉布裤子"),
    EquipmentDef("common_leather_greaves", "皮护腿", EquipmentTier.COMMON, "legs",
                 defense=3, description="皮革缝制的护腿"),
    EquipmentDef("common_rope_belt", "麻绳腰带", EquipmentTier.COMMON, "legs",
                 defense=1, hp=8, description="一根麻绳当腰带"),
]

_COMMON_SHOULDERS: list[EquipmentDef] = [
    EquipmentDef("common_cloth_cape", "旧披风", EquipmentTier.COMMON, "shoulders",
                 defense=2, hp=5, description="破旧的布披风"),
    EquipmentDef("common_leather_cloak", "皮斗篷", EquipmentTier.COMMON, "shoulders",
                 defense=3, description="简陋的皮质斗篷"),
    EquipmentDef("common_patch_cloth", "补丁布", EquipmentTier.COMMON, "shoulders",
                 defense=1, hp=3, description="缝满补丁的布块"),
]

_COMMON_ACCESSORIES: list[EquipmentDef] = [
    EquipmentDef("common_wooden_bead", "木珠子", EquipmentTier.COMMON, "accessory1",
                 hp=5, description="一颗普通的木珠子"),
    EquipmentDef("common_string_ring", "草绳圈", EquipmentTier.COMMON, "accessory1",
                 defense=1, description="草绳编的简单圆环"),
    EquipmentDef("common_rock_charm", "小石头", EquipmentTier.COMMON, "accessory2",
                 attack=1, description="路边捡的有点形状的石头"),
]


# ══════════════════════════════════════════════════════════════
# 精良装备 (FINE) - 进阶属性
# ══════════════════════════════════════════════════════════════

_FINE_WEAPONS: list[EquipmentDef] = [
    EquipmentDef("fine_iron_sword", "铁剑", EquipmentTier.FINE, "weapon",
                 attack=20, defense=2, description="铁匠铺打的普通铁剑"),
    EquipmentDef("fine_steel_axe", "钢斧", EquipmentTier.FINE, "weapon",
                 attack=25, description="铁匠打造的钢制战斧"),
    EquipmentDef("fine_hunting_bow", "猎鹰弓", EquipmentTier.FINE, "weapon",
                 attack=18, defense=1, description="专业猎人的好弓"),
    EquipmentDef("fine_iron_spear", "铁矛", EquipmentTier.FINE, "weapon",
                 attack=22, description="带铁尖的长矛"),
    EquipmentDef("fine_mace", "钉头锤", EquipmentTier.FINE, "weapon",
                 attack=24, defense=1, description="带铁钉的钝器"),
    EquipmentDef("fine_dagger", "短匕", EquipmentTier.FINE, "weapon",
                 attack=16, defense=3, description="便于隐藏的短匕首"),
]

_FINE_HEAD: list[EquipmentDef] = [
    EquipmentDef("fine_leather_cap", "皮帽", EquipmentTier.FINE, "head",
                 defense=8, hp=15, description="皮革缝制的保暖帽"),
    EquipmentDef("fine_iron_helm", "铁头盔", EquipmentTier.FINE, "head",
                 defense=12, description="铁制圆顶头盔"),
    EquipmentDef("fine_hood", "兜帽", EquipmentTier.FINE, "head",
                 defense=6, hp=20, description="带帽檐的织物头饰"),
    EquipmentDef("fine_coif", "锁甲头巾", EquipmentTier.FINE, "head",
                 defense=10, description="锁子甲编制的头套"),
]

_FINE_BODY: list[EquipmentDef] = [
    EquipmentDef("fine_leather_armor", "皮甲", EquipmentTier.FINE, "body",
                 defense=20, hp=30, description="多层皮革缝制的轻甲"),
    EquipmentDef("fine_padded_vest", "棉甲", EquipmentTier.FINE, "body",
                 defense=18, hp=45, description="棉花填充的防护内衬"),
    EquipmentDef("fine_chainmail", "锁子甲", EquipmentTier.FINE, "body",
                 defense=25, description="铁环编制的锁甲"),
    EquipmentDef("fine_brigandine", "棉甲外套", EquipmentTier.FINE, "body",
                 defense=22, hp=35, description="内衬铁片的棉质外套"),
]

_FINE_HANDS: list[EquipmentDef] = [
    EquipmentDef("fine_leather_gauntlets", "皮手套", EquipmentTier.FINE, "hands",
                 defense=10, attack=3, description="带护掌的皮手套"),
    EquipmentDef("fine_metal_bracers", "铁护腕", EquipmentTier.FINE, "hands",
                 defense=12, description="铁片打造的护腕"),
    EquipmentDef("fine_mitten_gloves", "连指皮手套", EquipmentTier.FINE, "hands",
                 defense=8, hp=15, description="保暖的连指手套"),
]

_FINE_LEGS: list[EquipmentDef] = [
    EquipmentDef("fine_leather_greaves", "皮护腿甲", EquipmentTier.FINE, "legs",
                 defense=15, hp=25, description="皮革与铁片的复合护腿"),
    EquipmentDef("fine_cloth_pants", "强化布裤", EquipmentTier.FINE, "legs",
                 defense=12, hp=30, description="内衬软垫的裤子"),
    EquipmentDef("fine_chain_legs", "锁甲护腿", EquipmentTier.FINE, "legs",
                 defense=18, description="锁子甲编制的护腿"),
]

_FINE_SHOULDERS: list[EquipmentDef] = [
    EquipmentDef("fine_leather_cloak", "皮披风", EquipmentTier.FINE, "shoulders",
                 defense=10, hp=20, description="厚实的皮披风"),
    EquipmentDef("fine_pauldron_straps", "肩甲绑带", EquipmentTier.FINE, "shoulders",
                 defense=12, description="皮条固定的简易肩甲"),
    EquipmentDef("fine_cape", "战袍披风", EquipmentTier.FINE, "shoulders",
                 defense=8, hp=25, description="带内衬的披风"),
]

_FINE_ACCESSORIES: list[EquipmentDef] = [
    EquipmentDef("fine_iron_ring", "铁环", EquipmentTier.FINE, "accessory1",
                 attack=3, description="简单的铁质戒指"),
    EquipmentDef("fine_leather_necklace", "皮绳项链", EquipmentTier.FINE, "accessory1",
                 defense=2, hp=15, description="皮革绳串着的饰品"),
    EquipmentDef("fine_lucky_coin", "幸运币", EquipmentTier.FINE, "accessory2",
                 hp=20, description="据说带来好运的硬币"),
    EquipmentDef("fine_small_charm", "护身符", EquipmentTier.FINE, "accessory2",
                 defense=3, description="简单的护身小饰品"),
]


# ══════════════════════════════════════════════════════════════
# 稀有装备 (RARE) - 高阶属性
# ══════════════════════════════════════════════════════════════

_RARE_WEAPONS: list[EquipmentDef] = [
    EquipmentDef("rare_steel_longbow", "钢制长弓", EquipmentTier.RARE, "weapon",
                 attack=60, defense=3, description="优质钢材打造的长弓"),
    EquipmentDef("rare_battle_axe", "战斧", EquipmentTier.RARE, "weapon",
                 attack=75, description="骑士冲锋用的重型战斧"),
    EquipmentDef("rare_crossbow", "弩", EquipmentTier.RARE, "weapon",
                 attack=70, defense=2, description="机械发射的强力十字弩"),
    EquipmentDef("rare_nordic_sword", "诺德长剑", EquipmentTier.RARE, "weapon",
                 attack=65, defense=5, description="北方战士的制式佩剑"),
    EquipmentDef("rare_lance", "骑枪", EquipmentTier.RARE, "weapon",
                 attack=80, description="骑兵冲锋的专用长枪"),
    EquipmentDef("rare_warhammer", "战锤", EquipmentTier.RARE, "weapon",
                 attack=85, defense=3, description="破甲专用的重型战锤"),
]

_RARE_HEAD: list[EquipmentDef] = [
    EquipmentDef("rare_nasal_helm", "鼻梁头盔", EquipmentTier.RARE, "head",
                 defense=30, hp=50, description="带鼻梁护的铁盔"),
    EquipmentDef("rare_great_helm", "大头盔", EquipmentTier.RARE, "head",
                 defense=35, description="覆盖整个头部的大头盔"),
    EquipmentDef("rare_chain_hood", "锁甲兜帽", EquipmentTier.RARE, "head",
                 defense=28, hp=60, description="锁子甲编织的头套"),
]

_RARE_BODY: list[EquipmentDef] = [
    EquipmentDef("rare_plate_armor", "板甲", EquipmentTier.RARE, "body",
                 defense=60, hp=80, description="整块铁板打造的护甲"),
    EquipmentDef("rare_scale_armor", "鳞甲", EquipmentTier.RARE, "body",
                 defense=55, hp=100, description="金属鳞片层层叠合的护甲"),
    EquipmentDef("rare_banded_mail", "条带甲", EquipmentTier.RARE, "body",
                 defense=58, hp=90, description="横条铁片加固的锁甲"),
    EquipmentDef("rare_breastplate", "胸甲", EquipmentTier.RARE, "body",
                 defense=65, hp=70, description="重点防护胸部的护甲"),
]

_RARE_HANDS: list[EquipmentDef] = [
    EquipmentDef("rare_steel_gauntlets", "钢手套", EquipmentTier.RARE, "hands",
                 defense=25, attack=8, description="精钢打造的金属手套"),
    EquipmentDef("rare_mitten_gauntlets", "连指钢手套", EquipmentTier.RARE, "hands",
                 defense=28, hp=40, description="保暖型金属手套"),
    EquipmentDef("rare_chain_gloves", "锁甲手套", EquipmentTier.RARE, "hands",
                 defense=22, attack=5, description="锁子甲编织的防护手套"),
]

_RARE_LEGS: list[EquipmentDef] = [
    EquipmentDef("rare_plate_greaves", "板甲护腿", EquipmentTier.RARE, "legs",
                 defense=35, hp=60, description="金属板片保护的腿部护甲"),
    EquipmentDef("rare_reinforced_pants", "强化护腿裤", EquipmentTier.RARE, "legs",
                 defense=30, hp=75, description="内衬铁片的防护裤"),
    EquipmentDef("rare_cavalry_boots", "骑兵靴", EquipmentTier.RARE, "legs",
                 defense=32, hp=50, description="骑兵专用的强化皮靴"),
]

_RARE_SHOULDERS: list[EquipmentDef] = [
    EquipmentDef("rare_steel_pauldrons", "钢肩甲", EquipmentTier.RARE, "shoulders",
                 defense=30, hp=50, description="金属打造的厚重肩甲"),
    EquipmentDef("rare_leather_cloak", "强化皮披风", EquipmentTier.RARE, "shoulders",
                 defense=25, hp=70, description="多层皮革的防护披风"),
    EquipmentDef("rare_war_banner", "战旗披风", EquipmentTier.RARE, "shoulders",
                 defense=20, attack=5, hp=40, description="代表军团的战旗披风"),
]

_RARE_ACCESSORIES: list[EquipmentDef] = [
    EquipmentDef("rare_silver_ring", "银戒指", EquipmentTier.RARE, "accessory1",
                 attack=8, defense=3, description="纯银打造的戒指"),
    EquipmentDef("rare_war_charm", "战魂符", EquipmentTier.RARE, "accessory1",
                 hp=80, description="据说蕴含战魂的护符"),
    EquipmentDef("rare_command_badge", "指挥徽章", EquipmentTier.RARE, "accessory2",
                 attack=5, defense=5, hp=50, description="指挥官的身份徽章"),
    EquipmentDef("rare_medal", "荣誉勋章", EquipmentTier.RARE, "accessory2",
                 defense=8, hp=60, description="战功卓著获得的勋章"),
]


# ══════════════════════════════════════════════════════════════
# 史诗装备 (EPIC) - 高端属性 + 特殊效果
# ══════════════════════════════════════════════════════════════

_EPIC_WEAPONS: list[EquipmentDef] = [
    EquipmentDef("epic_knightsword", "骑士长剑", EquipmentTier.EPIC, "weapon",
                 attack=150, defense=10,
                 special_effect="冲锋:攻击时有15%概率发动冲锋，造成双倍伤害",
                 description="皇家骑士团的标准佩剑"),
    EquipmentDef("epic_greatsword", "巨剑", EquipmentTier.EPIC, "weapon",
                 attack=180, defense=5,
                 special_effect="重击:攻击时无视目标30%防御",
                 description="需要双手握持的沉重巨剑"),
    EquipmentDef("epic_warbow", "战弓", EquipmentTier.EPIC, "weapon",
                 attack=140, defense=3,
                 special_effect="穿透:攻击时穿透25%护甲",
                 description="能射穿重甲的强力战弓"),
    EquipmentDef("epic_polearm", "长柄战斧", EquipmentTier.EPIC, "weapon",
                 attack=200, defense=8,
                 special_effect="横扫:范围伤害，攻击面前所有敌人",
                 description="骑兵克星的长柄武器"),
]

_EPIC_HEAD: list[EquipmentDef] = [
    EquipmentDef("epic_close_helm", "封闭头盔", EquipmentTier.EPIC, "head",
                 defense=60, hp=120,
                 special_effect="铁壁:受到致命伤害时有10%概率无效化",
                 description="全面保护的封闭式骑士头盔"),
    EquipmentDef("epic_horned_helm", "角盔", EquipmentTier.EPIC, "head",
                 defense=55, attack=10,
                 special_effect="冲锋:骑乘时攻击伤害+20%",
                 description="象征勇气的带角骑士头盔"),
]

_EPIC_BODY: list[EquipmentDef] = [
    EquipmentDef("epic_full_plate", "全身板甲", EquipmentTier.EPIC, "body",
                 defense=120, hp=200,
                 special_effect="不屈:生命值低于30%时，防御力提升50%",
                 description="覆盖全身的重型骑士铠甲"),
    EquipmentDef("epic_dragon_mail", "龙鳞甲", EquipmentTier.EPIC, "body",
                 defense=100, hp=280,
                 special_effect="龙魂:受到伤害时5%概率反弹30%伤害",
                 description="据说用真龙鳞片打造的护甲"),
]

_EPIC_HANDS: list[EquipmentDef] = [
    EquipmentDef("epic_gauntlets_of_might", "力量手套", EquipmentTier.EPIC, "hands",
                 defense=45, attack=25,
                 special_effect="重击:普通攻击有20%概率造成150%伤害",
                 description="增幅攻击力的强化金属手套"),
]

_EPIC_LEGS: list[EquipmentDef] = [
    EquipmentDef("epic_cavalry_greaves", "骑兵护腿", EquipmentTier.EPIC, "legs",
                 defense=65, hp=150,
                 special_effect="铁蹄:骑乘时移动速度+30%",
                 description="骑兵专用的强化护腿甲"),
]

_EPIC_SHOULDERS: list[EquipmentDef] = [
    EquipmentDef("epic_heraldic_cloak", "纹章披风", EquipmentTier.EPIC, "shoulders",
                 defense=50, hp=180,
                 special_effect="号令:战斗开始时，队伍全体防御+10%",
                 description="代表家族荣耀的华丽披风"),
    EquipmentDef("epic_wings_of_protection", "守护之翼", EquipmentTier.EPIC, "shoulders",
                 defense=80, hp=100,
                 special_effect="庇护:身边友军受到伤害时，分担20%",
                 description="造型如翅膀的华丽肩甲"),
]

_EPIC_ACCESSORIES: list[EquipmentDef] = [
    EquipmentDef("epic_ring_of_victory", "胜利之戒", EquipmentTier.EPIC, "accessory1",
                 attack=30, defense=15,
                 special_effect="连胜:连续击败敌人时，每次伤害+5%，最高叠加5层",
                 description="为常胜将军打造的戒指"),
    EquipmentDef("epic_amulet_of_valor", "勇气护符", EquipmentTier.EPIC, "accessory1",
                 hp=300, defense=20,
                 special_effect="勇气:生命值越低，攻击力越高，最低+30%",
                 description="激发使用者勇气的神秘护符"),
    EquipmentDef("epic_warbanner_charm", "战旗徽章", EquipmentTier.EPIC, "accessory2",
                 attack=20, hp=200,
                 special_effect="旗帜:附近友军攻击+15%",
                 description="能鼓舞士气的战旗徽章"),
]


# ══════════════════════════════════════════════════════════════
# 传说装备 (LEGENDARY) - 顶级属性 + 强力特殊效果
# ══════════════════════════════════════════════════════════════

_LEGENDARY_WEAPONS: list[EquipmentDef] = [
    EquipmentDef("legend_blessed_blade", "圣剑", EquipmentTier.LEGENDARY, "weapon",
                 attack=400, defense=30,
                 special_effect="神圣:对邪恶生物伤害+100%，击杀恢复50%生命",
                 description="传说中圣殿骑士团的神圣武器"),
    EquipmentDef("legend_hammer_of_thor", "雷神之锤", EquipmentTier.LEGENDARY, "weapon",
                 attack=450, defense=20,
                 special_effect="雷霆:攻击时30%概率召唤闪电，连锁攻击附近敌人",
                 description="北欧传说中的神话武器"),
    EquipmentDef("legend_dragon_slayer", "屠龙枪", EquipmentTier.LEGENDARY, "weapon",
                 attack=500, defense=25,
                 special_effect="龙杀:对大型生物伤害+150%，无视30%护甲",
                 description="专为猎龙打造的长柄武器"),
]

_LEGENDARY_HEAD: list[EquipmentDef] = [
    EquipmentDef("legend_crown_of_command", "统帅之冠", EquipmentTier.LEGENDARY, "head",
                 defense=100, attack=40, hp=300,
                 special_effect="统御:队伍全员属性+20%，指挥经验+50%",
                 description="王者才能佩戴的头冠"),
]

_LEGENDARY_BODY: list[EquipmentDef] = [
    EquipmentDef("legend_armor_of_invincibility", "无敌铠甲", EquipmentTier.LEGENDARY, "body",
                 defense=250, hp=600,
                 special_effect="无敌:受到致命伤害时，免疫1次并恢复50%生命(每战限1次)",
                 description="传说中只有战神才能穿上的终极铠甲"),
    EquipmentDef("legend_dragon_plate", "龙鳞板甲", EquipmentTier.LEGENDARY, "body",
                 defense=200, hp=800, attack=50,
                 special_effect="龙魂:战斗开始获得50点护盾，每回合恢复10点",
                 description="融合真龙之力的终极护甲"),
]

_LEGENDARY_HANDS: list[EquipmentDef] = [
    EquipmentDef("legend_fists_of_fury", "战神之拳", EquipmentTier.LEGENDARY, "hands",
                 defense=80, attack=80,
                 special_effect="风暴:攻击速度翻倍，连击概率+30%",
                 description="能让最弱之人也拥有战神之力"),
]

_LEGENDARY_LEGS: list[EquipmentDef] = [
    EquipmentDef("legend_boots_of_speed", "疾风之靴", EquipmentTier.LEGENDARY, "legs",
                 defense=90, hp=350,
                 special_effect="瞬移:30%概率完全闪避攻击，骑乘时必定先手",
                 description="传说中刺客之神的战靴"),
]

_LEGENDARY_SHOULDERS: list[EquipmentDef] = [
    EquipmentDef("legend_mantle_of_leader", "领袖披风", EquipmentTier.LEGENDARY, "shoulders",
                 defense=120, hp=500, attack=40,
                 special_effect="领袖:友军死亡时获得其20%属性，战斗结束消失",
                 description="只有真正的领袖才配拥有的披风"),
]

_LEGENDARY_ACCESSORIES: list[EquipmentDef] = [
    EquipmentDef("legend_ring_of_kings", "王者之戒", EquipmentTier.LEGENDARY, "accessory1",
                 attack=60, defense=40, hp=400,
                 special_effect="王者:战斗开始属性最高的敌人属性-20%转移给你",
                 description="传说中统一大陆的王者的戒指"),
    EquipmentDef("legend_phoenix_charm", "凤凰之羽", EquipmentTier.LEGENDARY, "accessory2",
                 hp=600, defense=30,
                 special_effect="涅槃:死亡时25%概率复活并恢复50%生命(每战限1次)",
                 description="蕴含凤凰神力的羽毛饰品"),
    EquipmentDef("legend_chalice_of_power", "力量圣杯", EquipmentTier.LEGENDARY, "accessory2",
                 attack=50, hp=300, defense=50,
                 special_effect="源泉:每回合开始恢复10%已损失生命值",
                 description="据说能激发使用者全部潜能的圣杯"),
]


# 装备注册表
EQUIPMENT_REGISTRY: dict[str, EquipmentDef] = {}
for _eq in (
    _COMMON_WEAPONS + _COMMON_HEAD + _COMMON_BODY + _COMMON_HANDS + _COMMON_LEGS + _COMMON_SHOULDERS + _COMMON_ACCESSORIES +
    _FINE_WEAPONS + _FINE_HEAD + _FINE_BODY + _FINE_HANDS + _FINE_LEGS + _FINE_SHOULDERS + _FINE_ACCESSORIES +
    _RARE_WEAPONS + _RARE_HEAD + _RARE_BODY + _RARE_HANDS + _RARE_LEGS + _RARE_SHOULDERS + _RARE_ACCESSORIES +
    _EPIC_WEAPONS + _EPIC_HEAD + _EPIC_BODY + _EPIC_HANDS + _EPIC_LEGS + _EPIC_SHOULDERS + _EPIC_ACCESSORIES +
    _LEGENDARY_WEAPONS + _LEGENDARY_HEAD + _LEGENDARY_BODY + _LEGENDARY_HANDS + _LEGENDARY_LEGS + _LEGENDARY_SHOULDERS + _LEGENDARY_ACCESSORIES
):
    EQUIPMENT_REGISTRY[_eq.equip_id] = _eq


def _refresh_equipment_items():
    """根据当前 EQUIPMENT_REGISTRY 同步刷新装备物品定义 - 骑砍风格。

    采用先增后删策略：先写入新条目，再删除过时条目，
    避免出现字典中装备条目全部缺失的中间状态。
    """
    new_items = {}
    for eq in EQUIPMENT_REGISTRY.values():
        new_items[eq.equip_id] = ItemDef(
            item_id=eq.equip_id,
            name=eq.name,
            item_type="equipment",
            description=eq.description,
            effect={"equip_id": eq.equip_id},
        )
    # 先写入新条目（覆盖同名旧条目）
    ITEM_REGISTRY.update(new_items)
    # 再删除已不存在的旧装备条目
    stale = [
        item_id for item_id, item in ITEM_REGISTRY.items()
        if getattr(item, "item_type", "") == "equipment" and item_id not in new_items
    ]
    for item_id in stale:
        ITEM_REGISTRY.pop(item_id, None)


def set_equipment_registry(equipments: dict[str, EquipmentDef]):
    """替换装备注册表（供数据库加载后同步到运行时）。

    采用先增后删 + 写锁保护，避免读者看到空/半更新状态。
    在 asyncio 单线程中同步代码不会被协程打断，锁主要防御多线程场景。
    """
    new_data = dict(equipments)
    with _registry_lock:
        # 先写入所有新条目（覆盖同名旧条目）
        EQUIPMENT_REGISTRY.update(new_data)
        # 再删除已不存在的旧条目
        stale = [k for k in EQUIPMENT_REGISTRY if k not in new_data]
        for k in stale:
            del EQUIPMENT_REGISTRY[k]
        _refresh_equipment_items()


_refresh_equipment_items()


_refresh_equipment_items()


# ── 回收定价系统 ──────────────────────────────────────────────

RECYCLE_PRICE_CONSUMABLE: dict[str, int] = {
    "healing_pill": 8,
    "spirit_pill": 15,
    "breakthrough_pill": 50,
    "body_pill": 35,
    "life_talisman": 100,
}

NON_RECYCLABLE_ITEMS: set[str] = {"spirit_stone"}

_TIER_RECYCLE_CONFIG: dict[int, tuple[float, int, int]] = {
    EquipmentTier.COMMON: (1.2, 8, 30),
    EquipmentTier.FINE: (1.8, 80, 250),
    EquipmentTier.RARE: (1.0, 500, 2500),
    EquipmentTier.EPIC: (1.0, 2000, 8000),
    EquipmentTier.LEGENDARY: (1.0, 5000, 15000),
}


def get_recycle_base_price(item_id: str) -> int | None:
    """获取物品的基础回收价格。"""
    if item_id in NON_RECYCLABLE_ITEMS:
        return None

    # 消耗品固定价格表
    if item_id in RECYCLE_PRICE_CONSUMABLE:
        return RECYCLE_PRICE_CONSUMABLE[item_id]

    # 装备按品阶公式
    eq = EQUIPMENT_REGISTRY.get(item_id)
    if eq:
        cfg = _TIER_RECYCLE_CONFIG.get(eq.tier)
        if cfg:
            multiplier, lo, hi = cfg
            return max(lo, min(hi, int((eq.attack + eq.defense) * multiplier)))
        return 5

    # 临时被动技能道具不可回收
    stored_hm_id = parse_stored_heart_method_item_id(item_id)
    if stored_hm_id:
        return None

    # 被动技能秘籍
    hm_id = parse_heart_method_manual_id(item_id)
    if hm_id:
        hm = HEART_METHOD_REGISTRY.get(hm_id)
        if hm:
            return int(20 * (1 + hm.realm * 0.8))
        return 20

    # 战技卷轴
    gf_id = parse_gongfa_scroll_id(item_id)
    if gf_id:
        gf = GONGFA_REGISTRY.get(gf_id)
        if gf:
            return gf.recycle_price
        return 1000

    # 注册表中存在的其他物品兜底
    if item_id in ITEM_REGISTRY:
        return 5

    return None


def get_daily_recycle_price(item_id: str, target_date: date | None = None) -> int | None:
    """获取每日浮动回收价格（±5%）。"""
    base = get_recycle_base_price(item_id)
    if base is None:
        return None
    d = target_date or date.today()
    seed_str = f"{item_id}_{d.isoformat()}"
    h = hashlib.md5(seed_str.encode()).hexdigest()
    ratio = int(h[:8], 16) / 0xFFFFFFFF  # 0~1
    fluctuation = 1 + (ratio * 0.1 - 0.05)  # 0.95~1.05
    return max(1, int(base * fluctuation))


def can_equip(realm: int, tier: int) -> bool:
    """检查指定爵位能否装备指定品阶的装备。超出预设上限的爵位视为满足最高品阶要求。"""
    req = TIER_REALM_REQUIREMENTS.get(tier)
    if not req:
        return False
    min_r, max_r = req
    # 爵位超出预设范围时，只检查下限
    if realm > max(v[1] for v in TIER_REALM_REQUIREMENTS.values()):
        return realm >= min_r
    return min_r <= realm <= max_r


def get_equip_bonus(player) -> dict:
    """计算角色装备总加成。

    计算所有装备槽位的攻击、防御、生命加成。
    """
    total_atk = 0
    total_def = 0
    total_hp = 0
    equip_slots = ["weapon", "head", "body", "hands", "legs", "shoulders", "accessory1", "accessory2"]
    for slot in equip_slots:
        item_id = getattr(player, slot, "无")
        eq = EQUIPMENT_REGISTRY.get(item_id)
        if eq:
            total_atk += eq.attack
            total_def += eq.defense
            total_hp += eq.hp
    return {
        "attack": total_atk,
        "defense": total_def,
        "hp": total_hp,
    }


# ──────────────────── 被动技能系统 ────────────────────


class HeartMethodQuality(IntEnum):
    """技能品质。"""
    NORMAL = 0     # 普通
    EPIC = 1       # 稀有
    LEGENDARY = 2  # 传说


HEART_METHOD_QUALITY_NAMES: dict[int, str] = {
    HeartMethodQuality.NORMAL: "普通",
    HeartMethodQuality.EPIC: "稀有",
    HeartMethodQuality.LEGENDARY: "传说",
}

# 技能修炼阶段
MASTERY_LEVELS = ["入门", "熟悉", "精通", "大师"]
MASTERY_MAX = len(MASTERY_LEVELS) - 1  # 3 = 大师


@dataclass
class HeartMethodDef:
    """被动技能定义。"""
    method_id: str
    name: str
    realm: int            # 对应的等级 (RealmLevel)
    quality: int          # HeartMethodQuality
    exp_multiplier: float  # 战斗经验倍率加成（如 0.1 = +10%）
    attack_bonus: int      # 攻击加成
    defense_bonus: int     # 防御加成
    dao_yun_rate: float    # 声望获取速率（战斗额外获得声望的概率）
    description: str = ""
    mastery_exp: int = 100  # 每阶段需要的技能经验


# 技能修炼阶段加成倍率（入门=1.0，熟悉=1.5，精通=2.0，大师=3.0）
MASTERY_MULTIPLIERS = [1.0, 1.5, 2.0, 3.0]


def _hm(method_id: str, name: str, realm: int, quality: int,
         exp_mult: float, atk: int, dfn: int, dao_rate: float,
         desc: str = "", mastery_exp: int = 100) -> HeartMethodDef:
    """技能定义快捷构造。"""
    return HeartMethodDef(
        method_id=method_id, name=name, realm=realm, quality=quality,
        exp_multiplier=exp_mult, attack_bonus=atk, defense_bonus=dfn,
        dao_yun_rate=dao_rate, description=desc, mastery_exp=mastery_exp,
    )


# ── 平民技能（realm=0）─────────────────────────────
_HM_MORTAL = [
    _hm("hm_mortal_01", "基础剑术", 0, 0, 0.05, 1, 1, 0.02, "最基础的剑术入门", 50),
    _hm("hm_mortal_02", "强身健体", 0, 0, 0.06, 2, 1, 0.02, "日常锻炼增强体质", 50),
    _hm("hm_mortal_03", "铁布衫", 0, 0, 0.04, 1, 2, 0.03, "基础的硬气功", 50),
    _hm("hm_mortal_04", "冷静应战", 0, 0, 0.07, 1, 1, 0.04, "保持冷静的战斗心态", 50),
    _hm("hm_mortal_05", "战地急救", 0, 0, 0.08, 2, 0, 0.02, "基础的战场急救术", 50),
    _hm("hm_mortal_06", "耐力训练", 0, 0, 0.05, 2, 2, 0.03, "增强持久战斗能力", 55),
    _hm("hm_mortal_07", "格挡技巧", 0, 0, 0.04, 1, 3, 0.02, "基础格挡技术", 55),
    _hm("hm_mortal_08", "战场指挥", 0, 1, 0.10, 3, 2, 0.05, "基础的部队指挥能力", 80),
    _hm("hm_mortal_09", "骑术入门", 0, 1, 0.12, 2, 3, 0.06, "基础的骑乘技术", 80),
    _hm("hm_mortal_10", "老兵经验", 0, 2, 0.18, 4, 3, 0.10, "经历战阵的老兵心得", 120),
]

# ── 新兵技能（realm=1）─────────────────────────────
_HM_QI_REFINING = [
    _hm("hm_qi_01", "轻剑术", 1, 0, 0.06, 4, 2, 0.03, "轻便灵活的剑术", 100),
    _hm("hm_qi_02", "重击", 1, 0, 0.07, 5, 3, 0.03, "蓄力重击技巧", 100),
    _hm("hm_qi_03", "闪避", 1, 0, 0.05, 3, 5, 0.04, "快速闪避敌人攻击", 100),
    _hm("hm_qi_04", "冲锋号令", 1, 0, 0.08, 4, 3, 0.03, "发起冲锋的战术", 100),
    _hm("hm_qi_05", "木盾防御", 1, 0, 0.06, 5, 4, 0.03, "使用盾牌防御", 100),
    _hm("hm_qi_06", "长矛阵列", 1, 0, 0.07, 6, 2, 0.04, "长枪兵的战术", 110),
    _hm("hm_qi_07", "盾墙", 1, 0, 0.06, 3, 6, 0.04, "密集防守战术", 110),
    _hm("hm_qi_08", "战术大师", 1, 1, 0.12, 7, 5, 0.06, "熟练运用战术", 160),
    _hm("hm_qi_09", "武器大师", 1, 1, 0.14, 6, 6, 0.07, "精通多种武器", 160),
    _hm("hm_qi_10", "将军之才", 1, 2, 0.20, 10, 8, 0.12, "领导部队的天赋", 240),
]

# ── 老兵技能（realm=2）─────────────────────────────
_HM_FOUNDATION = [
    _hm("hm_found_01", "破甲攻击", 2, 0, 0.06, 10, 5, 0.03, "针对重甲的攻击技巧", 200),
    _hm("hm_found_02", "反制冲锋", 2, 0, 0.07, 12, 8, 0.03, "反制敌人冲锋", 200),
    _hm("hm_found_03", "暗箭伤人", 2, 0, 0.05, 8, 12, 0.04, "偷袭的技巧", 200),
    _hm("hm_found_04", "士气激励", 2, 0, 0.08, 10, 8, 0.04, "鼓舞友军士气", 200),
    _hm("hm_found_05", "铜墙铁壁", 2, 0, 0.06, 14, 6, 0.03, "坚不可摧的防御", 210),
    _hm("hm_found_06", "弓弩精通", 2, 0, 0.07, 8, 10, 0.04, "远程武器精通", 210),
    _hm("hm_found_07", "战术撤退", 2, 0, 0.07, 11, 9, 0.04, "有序撤退保存实力", 220),
    _hm("hm_found_08", "重骑兵战术", 2, 1, 0.13, 16, 12, 0.07, "重骑兵的运用", 320),
    _hm("hm_found_09", "围三阙一", 2, 1, 0.15, 14, 14, 0.08, "包围战术", 320),
    _hm("hm_found_10", "霸王之勇", 2, 2, 0.22, 20, 18, 0.14, "项羽般的勇猛", 480),
]

# ── 骑士技能（realm=3）─────────────────────────────
_HM_GOLDEN_CORE = [
    _hm("hm_gold_01", "骑士精神", 3, 0, 0.06, 25, 15, 0.03, "骑士的荣誉与信仰", 400),
    _hm("hm_gold_02", "骑枪冲锋", 3, 0, 0.07, 30, 18, 0.04, "骑枪冲锋的威力", 400),
    _hm("hm_gold_03", "盾击", 3, 0, 0.06, 20, 28, 0.04, "用盾牌攻击敌人", 400),
    _hm("hm_gold_04", "战吼", 3, 0, 0.08, 28, 20, 0.03, "震慑敌人的怒吼", 410),
    _hm("hm_gold_05", "雷霆一击", 3, 0, 0.06, 32, 16, 0.04, "快速而猛烈的攻击", 410),
    _hm("hm_gold_06", "坚守阵地", 3, 0, 0.07, 22, 25, 0.04, "死守阵地不动摇", 420),
    _hm("hm_gold_07", "浴血奋战", 3, 0, 0.07, 26, 22, 0.05, "越战越勇", 420),
    _hm("hm_gold_08", "战神庇护", 3, 1, 0.14, 38, 30, 0.08, "战神赐予的庇护", 640),
    _hm("hm_gold_09", "百战老兵", 3, 1, 0.16, 35, 32, 0.09, "身经百战的老兵", 640),
    _hm("hm_gold_10", "战神降临", 3, 2, 0.24, 50, 40, 0.16, "战神附体的力量", 960),
]

# ── 骑士长技能（realm=4）─────────────────────────────
_HM_NASCENT_SOUL = [
    _hm("hm_soul_01", "军乐团指挥", 4, 0, 0.06, 60, 35, 0.04, "指挥乐队鼓舞全军", 800),
    _hm("hm_soul_02", "情报网络", 4, 0, 0.07, 70, 40, 0.04, "建立情报渠道", 800),
    _hm("hm_soul_03", "坚固阵线", 4, 0, 0.05, 50, 65, 0.05, "打造钢铁防线", 800),
    _hm("hm_soul_04", "出奇制胜", 4, 0, 0.08, 65, 45, 0.04, "出其不意的战术", 810),
    _hm("hm_soul_05", "军旗不倒", 4, 0, 0.07, 72, 38, 0.05, "军旗在人在", 810),
    _hm("hm_soul_06", "刺客信条", 4, 0, 0.06, 55, 60, 0.05, "暗杀技巧", 820),
    _hm("hm_soul_07", "统帅之力", 4, 0, 0.07, 62, 52, 0.05, "领导大军的能力", 820),
    _hm("hm_soul_08", "帝国荣耀", 4, 1, 0.15, 90, 70, 0.09, "为帝国荣耀而战", 1280),
    _hm("hm_soul_09", "战争机器", 4, 1, 0.17, 85, 75, 0.10, "如战争机器般战斗", 1280),
    _hm("hm_soul_10", "征服者", 4, 2, 0.26, 120, 95, 0.18, "征服一切的野心", 1920),
]

# ── 领主技能（realm=5）─────────────────────────────
_HM_DEITY_TRANSFORM = [
    _hm("hm_deity_01", "领土防御", 5, 0, 0.06, 150, 80, 0.04, "保卫领土的能力", 1600),
    _hm("hm_deity_02", "外交手腕", 5, 0, 0.07, 170, 95, 0.05, "灵活的外交策略", 1600),
    _hm("hm_deity_03", "经济大师", 5, 0, 0.06, 130, 150, 0.05, "发展经济的能力", 1600),
    _hm("hm_deity_04", "攻城略地", 5, 0, 0.08, 165, 100, 0.05, "攻城略地的战术", 1620),
    _hm("hm_deity_05", "火攻计", 5, 0, 0.07, 180, 85, 0.04, "火攻战术", 1620),
    _hm("hm_deity_06", "坚守不出", 5, 0, 0.06, 140, 135, 0.05, "龟缩防守战术", 1640),
    _hm("hm_deity_07", "调虎离山", 5, 0, 0.07, 155, 120, 0.05, "调虎离山之计", 1640),
    _hm("hm_deity_08", "王者风范", 5, 1, 0.16, 220, 170, 0.10, "王者的气质", 2560),
    _hm("hm_deity_09", "帝国崛起", 5, 1, 0.18, 200, 180, 0.11, "建立帝国的雄心", 2560),
    _hm("hm_deity_10", "征服之王", 5, 2, 0.28, 300, 240, 0.20, "成为征服之王", 3840),
]

# ── 男爵技能（realm=6）─────────────────────────────
_HM_VOID_MERGE = [
    _hm("hm_void_01", "分封制度", 6, 0, 0.06, 380, 200, 0.05, "分封贵族的制度", 3200),
    _hm("hm_void_02", "骑士团", 6, 0, 0.07, 420, 230, 0.05, "建立骑士团", 3200),
    _hm("hm_void_03", "联姻外交", 6, 0, 0.06, 350, 380, 0.06, "联姻加强外交", 3200),
    _hm("hm_void_04", "间谍网", 6, 0, 0.08, 400, 260, 0.06, "遍布各地的间谍", 3250),
    _hm("hm_void_05", "暗杀行动", 6, 0, 0.07, 440, 210, 0.05, "暗杀敌对势力", 3250),
    _hm("hm_void_06", "心理战", 6, 0, 0.06, 360, 350, 0.06, "瓦解敌军心理", 3300),
    _hm("hm_void_07", "合纵连横", 6, 0, 0.07, 390, 310, 0.06, "纵横捭阖之术", 3300),
    _hm("hm_void_08", "帝王心术", 6, 1, 0.17, 550, 420, 0.11, "帝王的权谋", 5120),
    _hm("hm_void_09", "天命所归", 6, 1, 0.19, 520, 450, 0.12, "天命的加持", 5120),
    _hm("hm_void_10", "万王之王", 6, 2, 0.30, 750, 600, 0.22, "成为万王之王", 7680),
]

# ── 子爵技能（realm=7）─────────────────────────────
_HM_TRIBULATION = [
    _hm("hm_trib_01", "帝国军制", 7, 0, 0.06, 1000, 550, 0.05, "建立帝国军队", 6400),
    _hm("hm_trib_02", "皇权神授", 7, 0, 0.07, 1100, 600, 0.06, "皇权的神圣性", 6400),
    _hm("hm_trib_03", "铁血政策", 7, 0, 0.06, 900, 1000, 0.06, "铁腕统治", 6400),
    _hm("hm_trib_04", "大一统", 7, 0, 0.08, 1200, 500, 0.05, "统一天下的志向", 6500),
    _hm("hm_trib_05", "仁义之道", 7, 0, 0.07, 1050, 650, 0.06, "仁义治天下", 6500),
    _hm("hm_trib_06", "帝王权谋", 7, 0, 0.07, 950, 900, 0.06, "帝王权术", 6600),
    _hm("hm_trib_07", "万民拥戴", 7, 0, 0.07, 1000, 800, 0.06, "百姓的拥护", 6600),
    _hm("hm_trib_08", "神圣帝国", 7, 1, 0.18, 1500, 1100, 0.12, "建立神圣帝国", 10240),
    _hm("hm_trib_09", "永恒统治", 7, 1, 0.20, 1400, 1200, 0.13, "永恒的统治", 10240),
    _hm("hm_trib_10", "神皇降世", 7, 2, 0.32, 2000, 1600, 0.24, "神皇降临人间", 15360),
]

# ── 伯爵技能（realm=8）─────────────────────────────
_HM_MAHAYANA = [
    _hm("hm_maha_01", "帝王霸业", 8, 0, 0.06, 2500, 1400, 0.06, "帝王霸业的雄心", 12800),
    _hm("hm_maha_02", "千秋万代", 8, 0, 0.07, 2800, 1600, 0.06, "千秋万代的基业", 12800),
    _hm("hm_maha_03", "普天之下", 8, 0, 0.06, 2200, 2500, 0.07, "普天之下莫非王土", 12800),
    _hm("hm_maha_04", "率土之滨", 8, 0, 0.08, 2600, 1800, 0.06, "率土之滨莫非王臣", 13000),
    _hm("hm_maha_05", "天下归心", 8, 0, 0.07, 3000, 1500, 0.06, "天下归心的威望", 13000),
    _hm("hm_maha_06", "开创纪元", 8, 0, 0.07, 2400, 2200, 0.07, "开创历史新纪元", 13200),
    _hm("hm_maha_07", "不世功勋", 8, 0, 0.07, 2700, 2000, 0.07, "建立不世功勋", 13200),
    _hm("hm_maha_08", "传奇帝王", 8, 1, 0.19, 3800, 2800, 0.13, "成为传奇帝王", 20480),
    _hm("hm_maha_09", "永恒帝国", 8, 1, 0.22, 3500, 3000, 0.14, "建立永恒帝国", 20480),
    _hm("hm_maha_10", "天下共主", 8, 2, 0.35, 5000, 4000, 0.28, "成为天下共主", 30720),
]

# 被动技能注册表
HEART_METHOD_REGISTRY: dict[str, HeartMethodDef] = {}
for _hm_list in (
    _HM_MORTAL, _HM_QI_REFINING, _HM_FOUNDATION, _HM_GOLDEN_CORE,
    _HM_NASCENT_SOUL, _HM_DEITY_TRANSFORM, _HM_VOID_MERGE,
    _HM_TRIBULATION, _HM_MAHAYANA,
):
    for _h in _hm_list:
        HEART_METHOD_REGISTRY[_h.method_id] = _h


HEART_METHOD_MANUAL_PREFIX = "heart_manual_"
STORED_HEART_METHOD_PREFIX = "stored_heart_manual_"


def get_heart_method_manual_id(method_id: str) -> str:
    """将被动技能ID转换为秘籍物品ID。"""
    return f"{HEART_METHOD_MANUAL_PREFIX}{method_id}"


def get_stored_heart_method_item_id(method_id: str) -> str:
    """将临时保留被动技能ID转换为道具物品ID。"""
    return f"{STORED_HEART_METHOD_PREFIX}{method_id}"


def parse_heart_method_manual_id(item_id: str) -> str | None:
    """从秘籍物品ID解析被动技能ID。"""
    if not item_id.startswith(HEART_METHOD_MANUAL_PREFIX):
        return None
    return item_id[len(HEART_METHOD_MANUAL_PREFIX):] or None


def parse_stored_heart_method_item_id(item_id: str) -> str | None:
    """从临时被动技能道具ID解析被动技能ID。"""
    if not item_id.startswith(STORED_HEART_METHOD_PREFIX):
        return None
    return item_id[len(STORED_HEART_METHOD_PREFIX):] or None


def _refresh_heart_method_manual_items():
    """根据当前 HEART_METHOD_REGISTRY 重新生成被动技能秘籍定义。

    采用先增后删策略，避免出现秘籍条目全部缺失的中间状态。
    """
    new_items = {}
    for hm in HEART_METHOD_REGISTRY.values():
        manual_id = get_heart_method_manual_id(hm.method_id)
        stored_manual_id = get_stored_heart_method_item_id(hm.method_id)
        realm_name = REALM_CONFIG.get(hm.realm, {}).get("name", "未知爵位")
        quality_name = HEART_METHOD_QUALITY_NAMES.get(hm.quality, "普通")
        new_items[manual_id] = ItemDef(
            item_id=manual_id,
            name=f"{hm.name}秘籍",
            item_type="heart_method",
            description=f"可领悟{quality_name}被动技能【{hm.name}】（{realm_name}）",
            effect={"learn_heart_method": hm.method_id},
        )
        new_items[stored_manual_id] = ItemDef(
            item_id=stored_manual_id,
            name=f"{hm.name}秘籍（临时）",
            item_type="heart_method",
            description=f"保留的{quality_name}被动技能【{hm.name}】（{realm_name}），三日内有效，不可回收",
            effect={"learn_heart_method": hm.method_id},
        )
    # 先写入新条目
    ITEM_REGISTRY.update(new_items)
    # 再删除已不存在的旧被动技能秘籍条目
    stale = [
        item_id for item_id in ITEM_REGISTRY
        if (item_id.startswith(HEART_METHOD_MANUAL_PREFIX) or item_id.startswith(STORED_HEART_METHOD_PREFIX))
        and item_id not in new_items
    ]
    for item_id in stale:
        ITEM_REGISTRY.pop(item_id, None)


def set_heart_method_registry(methods: dict[str, HeartMethodDef]):
    """替换被动技能注册表（供数据库加载后同步到运行时）。

    采用先增后删 + 写锁保护，避免读者看到空/半更新状态。
    """
    new_data = dict(methods)
    with _registry_lock:
        HEART_METHOD_REGISTRY.update(new_data)
        stale = [k for k in HEART_METHOD_REGISTRY if k not in new_data]
        for k in stale:
            del HEART_METHOD_REGISTRY[k]
        _refresh_heart_method_manual_items()


def get_heart_method_bonus(method_id: str, mastery: int) -> dict:
    """计算被动技能加成（含修炼阶段倍率）。

    Returns:
        {exp_multiplier, attack_bonus, defense_bonus, dao_yun_rate, mastery_name}
    """
    hm = HEART_METHOD_REGISTRY.get(method_id)
    if not hm:
        return {
            "exp_multiplier": 0.0, "attack_bonus": 0,
            "defense_bonus": 0, "dao_yun_rate": 0.0,
            "mastery_name": "",
        }
    mult = MASTERY_MULTIPLIERS[min(mastery, MASTERY_MAX)]
    return {
        "exp_multiplier": hm.exp_multiplier * mult,
        "attack_bonus": int(hm.attack_bonus * mult),
        "defense_bonus": int(hm.defense_bonus * mult),
        "dao_yun_rate": hm.dao_yun_rate * mult,
        "mastery_name": MASTERY_LEVELS[min(mastery, MASTERY_MAX)],
    }


def get_realm_heart_methods(realm: int) -> list[HeartMethodDef]:
    """获取指定爵位的所有被动技能。"""
    return [hm for hm in HEART_METHOD_REGISTRY.values() if hm.realm == realm]


_refresh_heart_method_manual_items()


# ──────────────────── 战斗技能系统 ────────────────────


class GongfaTier(IntEnum):
    """技能品阶。"""
    HUANG = 0   # 初级
    XUAN = 1    # 中级
    DI = 2      # 高级
    TIAN = 3    # 大师级


GONGFA_TIER_NAMES: dict[int, str] = {
    GongfaTier.HUANG: "初级",
    GongfaTier.XUAN: "中级",
    GongfaTier.DI: "高级",
    GongfaTier.TIAN: "大师级",
}

# 修炼熟练度所需最低爵位（装备无限制）
GONGFA_TIER_REALM_REQ: dict[int, int] = {
    GongfaTier.HUANG: 0,   # 平民即可修炼
    GongfaTier.XUAN: 1,    # 需要新兵爵位
    GongfaTier.DI: 3,      # 需要骑士爵位
    GongfaTier.TIAN: 6,    # 需要男爵爵位
}


@dataclass
class GongfaDef:
    """战技定义。"""
    gongfa_id: str
    name: str
    tier: int             # GongfaTier
    attack_bonus: int
    defense_bonus: int
    hp_regen: int
    lingqi_regen: int
    description: str = ""
    mastery_exp: int = 200
    dao_yun_cost: int = 0
    recycle_price: int = 1000
    lingqi_cost: int = 0  # 战斗中施展战技消耗的体力


def calc_gongfa_lingqi_cost(tier: int, atk: int, dfn: int, hp_r: int, lq_r: int) -> int:
    """根据战技品阶和属性计算施法耗灵。"""
    tier_base = {0: 10, 1: 25, 2: 50, 3: 100}
    max_stat = max(int(atk), int(dfn), int(hp_r), int(lq_r))
    return int(tier_base.get(int(tier), 10) + max_stat * 0.5)


def _gf(gongfa_id: str, name: str, tier: int,
         atk: int, dfn: int, hp_r: int, lq_r: int,
         desc: str = "", mastery_exp: int = 200,
         dao_yun_cost: int = 0, recycle_price: int = 1000) -> GongfaDef:
    """战技定义快捷构造。lingqi_cost 根据品阶和属性自动计算。"""
    lingqi_cost = calc_gongfa_lingqi_cost(tier, atk, dfn, hp_r, lq_r)
    return GongfaDef(
        gongfa_id=gongfa_id, name=name, tier=tier,
        attack_bonus=atk, defense_bonus=dfn,
        hp_regen=hp_r, lingqi_regen=lq_r,
        description=desc, mastery_exp=mastery_exp,
        dao_yun_cost=dao_yun_cost, recycle_price=recycle_price,
        lingqi_cost=lingqi_cost,
    )


# 15 种属性组合模板：
# 单属性(4): atk, def, hp, lq
# 双属性(6): atk+def, atk+hp, atk+lq, def+hp, def+lq, hp+lq
# 三属性(4): atk+def+hp, atk+def+lq, atk+hp+lq, def+hp+lq
# 四属性(1): atk+def+hp+lq

# ── 初级战斗技能（60 本）── 15 组合 × 4 变体 ──────────────────
_GF_HUANG: list[GongfaDef] = [
    # 单攻 ×4
    _gf("gf_h_a01", "重劈", 0, 25, 0, 0, 0, "沉重的劈砍攻击", 200, 0, 1000),
    _gf("gf_h_a02", "突刺", 0, 22, 0, 0, 0, "快速突刺敌人要害", 200, 0, 1100),
    _gf("gf_h_a03", "横斩", 0, 20, 0, 0, 0, "大范围的横斩攻击", 200, 0, 1000),
    _gf("gf_h_a04", "下劈", 0, 18, 0, 0, 0, "从上而下的劈砍", 200, 0, 1200),
    # 单防 ×4
    _gf("gf_h_d01", "铁壁", 0, 0, 25, 0, 0, "如铁壁般防御", 200, 0, 1000),
    _gf("gf_h_d02", "格挡", 0, 0, 22, 0, 0, "精准格挡敌人攻击", 200, 0, 1100),
    _gf("gf_h_d03", "固守", 0, 0, 20, 0, 0, "坚守阵地不动摇", 200, 0, 1000),
    _gf("gf_h_d04", "龟甲", 0, 0, 18, 0, 0, "如龟甲般全面防御", 200, 0, 1200),
    # 单血 ×4
    _gf("gf_h_h01", "伤口处理", 0, 0, 0, 25, 0, "快速处理伤口", 200, 0, 1000),
    _gf("gf_h_h02", "坚韧", 0, 0, 0, 22, 0, "更加坚韧的生命力", 200, 0, 1100),
    _gf("gf_h_h03", "恢复", 0, 0, 0, 20, 0, "战后快速恢复", 200, 0, 1000),
    _gf("gf_h_h04", "再生", 0, 0, 0, 18, 0, "缓慢恢复生命", 200, 0, 1200),
    # 单耐力 ×4
    _gf("gf_h_l01", "体力充沛", 0, 0, 0, 0, 25, "更加充沛的体力", 200, 0, 1000),
    _gf("gf_h_l02", "耐力训练", 0, 0, 0, 0, 22, "增强耐力", 200, 0, 1100),
    _gf("gf_h_l03", "持久战", 0, 0, 0, 0, 20, "适合持久战斗", 200, 0, 1000),
    _gf("gf_h_l04", "呼吸法", 0, 0, 0, 0, 18, "调节呼吸节省体力", 200, 0, 1200),
    # 攻防 ×4
    _gf("gf_h_ad01", "攻守兼备", 0, 18, 15, 0, 0, "攻防平衡的战斗方式", 200, 0, 1300),
    _gf("gf_h_ad02", "以攻为守", 0, 15, 18, 0, 0, "以攻击代替防守", 200, 0, 1300),
    _gf("gf_h_ad03", "剑盾术", 0, 20, 15, 0, 0, "剑与盾的配合", 200, 0, 1400),
    _gf("gf_h_ad04", "双刃", 0, 16, 16, 0, 0, "双武器战斗技巧", 200, 0, 1200),
    # 攻血 ×4
    _gf("gf_h_ah01", "狂暴攻击", 0, 18, 0, 15, 0, "以伤换伤的打法", 200, 0, 1300),
    _gf("gf_h_ah02", "浴血", 0, 15, 0, 18, 0, "越战越勇", 200, 0, 1300),
    _gf("gf_h_ah03", "猛攻", 0, 20, 0, 15, 0, "连续猛攻", 200, 0, 1400),
    _gf("gf_h_ah04", "血性", 0, 16, 0, 16, 0, "激发血性增强攻击", 200, 0, 1200),
    # 攻耐力 ×4
    _gf("gf_h_al01", "速攻", 0, 18, 0, 0, 15, "快速攻击节省体力", 200, 0, 1300),
    _gf("gf_h_al02", "连击", 0, 15, 0, 0, 18, "连续攻击技巧", 200, 0, 1300),
    _gf("gf_h_al03", "快剑", 0, 20, 0, 0, 15, "快速剑术", 200, 0, 1400),
    _gf("gf_h_al04", "穿刺", 0, 16, 0, 0, 16, "精准穿刺攻击", 200, 0, 1200),
    # 防血 ×4
    _gf("gf_h_dh01", "防御姿态", 0, 0, 18, 15, 0, "防御优先的战斗姿态", 200, 0, 1300),
    _gf("gf_h_dh02", "铁甲", 0, 0, 15, 18, 0, "重甲防御", 200, 0, 1300),
    _gf("gf_h_dh03", "坚守", 0, 0, 20, 15, 0, "死守阵地", 200, 0, 1400),
    _gf("gf_h_dh04", "盾墙", 0, 0, 16, 16, 0, "组成盾墙", 200, 0, 1200),
    # 防耐力 ×4
    _gf("gf_h_dl01", "节省体力", 0, 0, 18, 0, 15, "防御时节省体力", 200, 0, 1300),
    _gf("gf_h_dl02", "防御恢复", 0, 0, 15, 0, 18, "防御中恢复体力", 200, 0, 1300),
    _gf("gf_h_dl03", "持久防御", 0, 0, 20, 0, 15, "长时间防御", 200, 0, 1400),
    _gf("gf_h_dl04", "龟缩", 0, 0, 16, 0, 16, "最小消耗的防御", 200, 0, 1200),
    # 血耐力 ×4
    _gf("gf_h_hl01", "持久作战", 0, 0, 0, 18, 15, "持久作战能力", 200, 0, 1300),
    _gf("gf_h_hl02", "恢复训练", 0, 0, 0, 15, 18, "训练恢复能力", 200, 0, 1300),
    _gf("gf_h_hl03", "耐力恢复", 0, 0, 0, 20, 15, "耐力与恢复兼备", 200, 0, 1400),
    _gf("gf_h_hl04", "养生", 0, 0, 0, 16, 16, "养生之道", 200, 0, 1200),
    # 攻防血 ×4
    _gf("gf_h_adh01", "老兵经验", 0, 15, 15, 15, 0, "身经百战的老兵经验", 200, 0, 1500),
    _gf("gf_h_adh02", "战场适应", 0, 18, 15, 15, 0, "适应各种战场", 200, 0, 1600),
    _gf("gf_h_adh03", "全能战士", 0, 15, 18, 15, 0, "攻防恢复兼备", 200, 0, 1600),
    _gf("gf_h_adh04", "生存专家", 0, 15, 15, 18, 0, "战场生存专家", 200, 0, 1600),
    # 攻防耐力 ×4
    _gf("gf_h_adl01", "战斗节奏", 0, 15, 15, 0, 15, "掌控战斗节奏", 200, 0, 1500),
    _gf("gf_h_adl02", "体力管理", 0, 18, 15, 0, 15, "合理管理体力", 200, 0, 1600),
    _gf("gf_h_adl03", "高效战斗", 0, 15, 18, 0, 15, "高效利用体力", 200, 0, 1600),
    _gf("gf_h_adl04", "节能打法", 0, 15, 15, 0, 18, "节省体力的打法", 200, 0, 1600),
    # 攻血耐力 ×4
    _gf("gf_h_ahl01", "全能进攻", 0, 15, 0, 15, 15, "攻守兼备的进攻", 200, 0, 1500),
    _gf("gf_h_ahl02", "恢复攻击", 0, 18, 0, 15, 15, "攻击中恢复", 200, 0, 1600),
    _gf("gf_h_ahl03", "战地医生", 0, 15, 0, 18, 15, "边战斗边治疗", 200, 0, 1600),
    _gf("gf_h_ahl04", "持久攻击", 0, 15, 0, 15, 18, "持久的攻击", 200, 0, 1600),
    # 防血耐力 ×4
    _gf("gf_h_dhl01", "防守反击", 0, 0, 15, 15, 15, "防守后反击", 200, 0, 1500),
    _gf("gf_h_dhl02", "消耗战", 0, 0, 18, 15, 15, "与敌人消耗", 200, 0, 1600),
    _gf("gf_h_dhl03", "持久防御", 0, 0, 15, 18, 15, "持久的防御", 200, 0, 1600),
    _gf("gf_h_dhl04", "乌龟战术", 0, 0, 15, 15, 18, "像乌龟一样战斗", 200, 0, 1600),
    # 四属性 ×4
    _gf("gf_h_all01", "骑士精神", 0, 15, 15, 15, 15, "骑士的战斗精神", 200, 0, 2000),
    _gf("gf_h_all02", "战场大师", 0, 18, 16, 16, 16, "战场上的大师", 200, 0, 2000),
    _gf("gf_h_all03", "百战余生", 0, 16, 18, 16, 16, "百战余生的老兵", 200, 0, 2000),
    _gf("gf_h_all04", "全能士兵", 0, 16, 16, 18, 16, "全能型士兵", 200, 0, 2000),
]

# ── 中级战斗技能（45 本）── 15 组合 × 3 变体 ──────────────────
_GF_XUAN: list[GongfaDef] = [
    # 单攻 ×3
    _gf("gf_x_a01", "旋风斩", 1, 70, 0, 0, 0, "旋转攻击周围敌人", 500, 0, 3000),
    _gf("gf_x_a02", "破甲斩", 1, 60, 0, 0, 0, "专门破坏护甲", 500, 0, 3500),
    _gf("gf_x_a03", "穿心刺", 1, 55, 0, 0, 0, "刺穿敌人心脏", 500, 0, 4000),
    # 单防 ×3
    _gf("gf_x_d01", "不动如山", 1, 0, 70, 0, 0, "如山般稳固", 500, 0, 3000),
    _gf("gf_x_d02", "铁壁阵", 1, 0, 60, 0, 0, "组成铁壁防线", 500, 0, 3500),
    _gf("gf_x_d03", "金钟罩", 1, 0, 55, 0, 0, "金钟般的防御", 500, 0, 4000),
    # 单血 ×3
    _gf("gf_x_h01", "不屈意志", 1, 0, 0, 70, 0, "不屈的战斗意志", 500, 0, 3000),
    _gf("gf_x_h02", "战地医生", 1, 0, 0, 60, 0, "战场急救能力", 500, 0, 3500),
    _gf("gf_x_h03", "坚韧生命", 1, 0, 0, 55, 0, "更加坚韧的生命", 500, 0, 4000),
    # 单耐力 ×3
    _gf("gf_x_l01", "耐力无限", 1, 0, 0, 0, 70, "近乎无限的耐力", 500, 0, 3000),
    _gf("gf_x_l02", "体力充沛", 1, 0, 0, 0, 60, "充沛的体力", 500, 0, 3500),
    _gf("gf_x_l03", "持久战专家", 1, 0, 0, 0, 55, "持久战专家", 500, 0, 4000),
    # 攻防 ×3
    _gf("gf_x_ad01", "攻防一体", 1, 50, 40, 0, 0, "攻防完美结合", 500, 0, 4500),
    _gf("gf_x_ad02", "剑盾精通", 1, 45, 45, 0, 0, "精通剑盾配合", 500, 0, 4500),
    _gf("gf_x_ad03", "双刀流", 1, 55, 40, 0, 0, "双刀战斗流派", 500, 0, 5000),
    # 攻血 ×3
    _gf("gf_x_ah01", "血战到底", 1, 50, 0, 40, 0, "血战到底", 500, 0, 4500),
    _gf("gf_x_ah02", "不灭战魂", 1, 45, 0, 45, 0, "不灭的战斗之魂", 500, 0, 4500),
    _gf("gf_x_ah03", "浴血奋战", 1, 55, 0, 40, 0, "浴血奋战到底", 500, 0, 5000),
    # 攻耐力 ×3
    _gf("gf_x_al01", "疾风剑", 1, 50, 0, 0, 40, "疾风般的剑术", 500, 0, 4500),
    _gf("gf_x_al02", "快攻连击", 1, 45, 0, 0, 45, "快速的连击", 500, 0, 4500),
    _gf("gf_x_al03", "速度压制", 1, 55, 0, 0, 40, "用速度压制敌人", 500, 0, 5000),
    # 防血 ×3
    _gf("gf_x_dh01", "固若金汤", 1, 0, 50, 40, 0, "固若金汤的防御", 500, 0, 4500),
    _gf("gf_x_dh02", "不死小强", 1, 0, 45, 45, 0, "打不死的小强", 500, 0, 4500),
    _gf("gf_x_dh03", "铜墙铁壁", 1, 0, 55, 40, 0, "铜墙铁壁的防御", 500, 0, 5000),
    # 防耐力 ×3
    _gf("gf_x_dl01", "体力护盾", 1, 0, 50, 0, 40, "用体力形成护盾", 500, 0, 4500),
    _gf("gf_x_dl02", "防御恢复", 1, 0, 45, 0, 45, "防御中恢复体力", 500, 0, 4500),
    _gf("gf_x_dl03", "持久防御", 1, 0, 55, 0, 40, "持久的防御能力", 500, 0, 5000),
    # 血耐力 ×3
    _gf("gf_x_hl01", "持久恢复", 1, 0, 0, 50, 40, "持久的恢复能力", 500, 0, 4500),
    _gf("gf_x_hl02", "生命力", 1, 0, 0, 45, 45, "强大的生命力", 500, 0, 4500),
    _gf("gf_x_hl03", "战场续航", 1, 0, 0, 55, 40, "强大的战场续航", 500, 0, 5000),
    # 攻防血 ×3
    _gf("gf_x_adh01", "全能战士", 1, 40, 40, 40, 0, "全能型战士", 500, 0, 5500),
    _gf("gf_x_adh02", "百战老兵", 1, 50, 40, 40, 0, "身经百战的老兵", 500, 0, 5500),
    _gf("gf_x_adh03", "战场大师", 1, 40, 50, 40, 0, "战场上的大师", 500, 0, 6000),
    # 攻防耐力 ×3
    _gf("gf_x_adl01", "战斗节奏", 1, 40, 40, 0, 40, "掌控战斗节奏", 500, 0, 5500),
    _gf("gf_x_adl02", "体力掌控", 1, 50, 40, 0, 40, "掌控自身体力", 500, 0, 5500),
    _gf("gf_x_adl03", "高效战斗", 1, 40, 50, 0, 40, "高效的战斗方式", 500, 0, 6000),
    # 攻血耐力 ×3
    _gf("gf_x_ahl01", "全面进攻", 1, 40, 0, 40, 40, "全面的进攻能力", 500, 0, 5500),
    _gf("gf_x_ahl02", "战地恢复", 1, 50, 0, 40, 40, "在战斗中恢复", 500, 0, 5500),
    _gf("gf_x_ahl03", "持久攻击", 1, 40, 0, 50, 40, "持久的攻击能力", 500, 0, 6000),
    # 防血耐力 ×3
    _gf("gf_x_dhl01", "防御大师", 1, 0, 40, 40, 40, "防御方面的大师", 500, 0, 5500),
    _gf("gf_x_dhl02", "消耗战术", 1, 0, 50, 40, 40, "与敌人消耗", 500, 0, 5500),
    _gf("gf_x_dhl03", "持久作战", 1, 0, 40, 50, 40, "持久的作战能力", 500, 0, 6000),
    # 四属性 ×3
    _gf("gf_x_all01", "全能冠军", 1, 40, 40, 40, 40, "全能型的冠军", 500, 0, 6000),
    _gf("gf_x_all02", "完美战士", 1, 45, 45, 40, 40, "接近完美的战士", 500, 0, 6000),
    _gf("gf_x_all03", "战场王者", 1, 40, 40, 45, 45, "战场上的王者", 500, 0, 6000),
]

# ── 高级战斗技能（30 本）── 15 组合 × 2 变体 ──────────────────
_GF_DI: list[GongfaDef] = [
    # 单攻 ×2
    _gf("gf_d_a01", "致命一击", 2, 180, 0, 0, 0, "给予敌人致命伤害", 1500, 50, 10000),
    _gf("gf_d_a02", "毁灭打击", 2, 160, 0, 0, 0, "毁灭性的打击", 1500, 60, 12000),
    # 单防 ×2
    _gf("gf_d_d01", "绝对防御", 2, 0, 180, 0, 0, "绝对无法晋升的防御", 1500, 50, 10000),
    _gf("gf_d_d02", "钢铁城墙", 2, 0, 160, 0, 0, "如钢铁城墙般坚固", 1500, 60, 12000),
    # 单血 ×2
    _gf("gf_d_h01", "不屈生命", 2, 0, 0, 180, 0, "不屈不挠的生命力", 1500, 50, 10000),
    _gf("gf_d_h02", "再生能力", 2, 0, 0, 160, 0, "强大的再生能力", 1500, 60, 12000),
    # 单耐力 ×2
    _gf("gf_d_l01", "无限体力", 2, 0, 0, 0, 180, "接近无限的体力", 1500, 50, 10000),
    _gf("gf_d_l02", "耐力源泉", 2, 0, 0, 0, 160, "耐力的源泉", 1500, 60, 12000),
    # 攻防 ×2
    _gf("gf_d_ad01", "完美攻防", 2, 130, 100, 0, 0, "完美的攻防技巧", 1500, 70, 14000),
    _gf("gf_d_ad02", "攻守转换", 2, 110, 120, 0, 0, "攻守自如转换", 1500, 70, 14000),
    # 攻血 ×2
    _gf("gf_d_ah01", "以命换命", 2, 130, 0, 100, 0, "以命换命的战斗方式", 1500, 70, 14000),
    _gf("gf_d_ah02", "不灭战意", 2, 110, 0, 120, 0, "不灭的战斗意志", 1500, 70, 14000),
    # 攻耐力 ×2
    _gf("gf_d_al01", "疾风骤雨", 2, 130, 0, 0, 100, "疾风骤雨般的攻击", 1500, 80, 15000),
    _gf("gf_d_al02", "连绵不绝", 2, 110, 0, 0, 120, "连绵不绝的攻击", 1500, 80, 15000),
    # 防血 ×2
    _gf("gf_d_dh01", "铁血防御", 2, 0, 130, 100, 0, "铁血般的防御", 1500, 70, 14000),
    _gf("gf_d_dh02", "不死之身", 2, 0, 110, 120, 0, "拥有不死之身", 1500, 70, 14000),
    # 防耐力 ×2
    _gf("gf_d_dl01", "持久防线", 2, 0, 130, 0, 100, "持久的防御战线", 1500, 80, 15000),
    _gf("gf_d_dl02", "铁桶阵", 2, 0, 110, 0, 120, "铁桶般的防御阵型", 1500, 80, 15000),
    # 血耐力 ×2
    _gf("gf_d_hl01", "持久作战", 2, 0, 0, 130, 100, "超强的持久作战", 1500, 80, 15000),
    _gf("gf_d_hl02", "恢复大师", 2, 0, 0, 110, 120, "恢复方面的大师", 1500, 80, 15000),
    # 攻防血 ×2
    _gf("gf_d_adh01", "战场指挥官", 2, 110, 100, 100, 0, "出色的战场指挥官", 1500, 90, 17000),
    _gf("gf_d_adh02", "全能将军", 2, 120, 110, 100, 0, "全能的将军", 1500, 90, 17000),
    # 攻防耐力 ×2
    _gf("gf_d_adl01", "节奏大师", 2, 110, 100, 0, 100, "掌控战斗节奏大师", 1500, 90, 17000),
    _gf("gf_d_adl02", "体力管理", 2, 120, 110, 0, 100, "完美的体力管理", 1500, 90, 17000),
    # 攻血耐力 ×2
    _gf("gf_d_ahl01", "战场永动机", 2, 110, 0, 100, 100, "战场上的永动机", 1500, 90, 18000),
    _gf("gf_d_ahl02", "不竭战斗", 2, 120, 0, 110, 100, "永不枯竭的战斗", 1500, 90, 18000),
    # 防血耐力 ×2
    _gf("gf_d_dhl01", "永生堡垒", 2, 0, 110, 100, 100, "永生不灭的堡垒", 1500, 100, 18000),
    _gf("gf_d_dhl02", "不灭要塞", 2, 0, 120, 110, 100, "永不陷落要塞", 1500, 100, 18000),
    # 四属性 ×2
    _gf("gf_d_all01", "传奇战士", 2, 110, 100, 100, 100, "传奇般的战士", 1500, 100, 20000),
    _gf("gf_d_all02", "完美骑士", 2, 120, 110, 110, 100, "完美无缺的骑士", 1500, 100, 20000),
]

# ── 大师级战斗技能（15 本）── 15 组合 × 1 变体 ──────────────────
_GF_TIAN: list[GongfaDef] = [
    _gf("gf_t_a01", "灭世一击", 3, 400, 0, 0, 0, "足以毁灭世界的攻击", 4000, 200, 30000),
    _gf("gf_t_d01", "神盾庇护", 3, 0, 400, 0, 0, "神的盾牌庇护", 4000, 200, 30000),
    _gf("gf_t_h01", "不死之身", 3, 0, 0, 400, 0, "真正的不死之身", 4000, 200, 30000),
    _gf("gf_t_l01", "无限之力", 3, 0, 0, 0, 400, "无限的力量源泉", 4000, 200, 30000),
    _gf("gf_t_ad01", "战神降临", 3, 300, 250, 0, 0, "战神降临人间", 4000, 250, 40000),
    _gf("gf_t_ah01", "嗜血狂暴", 3, 300, 0, 250, 0, "嗜血的狂暴战斗", 4000, 250, 40000),
    _gf("gf_t_al01", "闪电攻击", 3, 300, 0, 0, 250, "如闪电般的攻击", 4000, 300, 45000),
    _gf("gf_t_dh01", "不朽堡垒", 3, 0, 300, 250, 0, "永不陷落的不朽堡垒", 4000, 250, 40000),
    _gf("gf_t_dl01", "永恒防御", 3, 0, 300, 0, 250, "永恒存在的防御", 4000, 300, 45000),
    _gf("gf_t_hl01", "生命之源", 3, 0, 0, 300, 250, "生命的不竭之源", 4000, 300, 45000),
    _gf("gf_t_adh01", "全能战神", 3, 280, 260, 260, 0, "全能的战神", 4000, 350, 50000),
    _gf("gf_t_adl01", "完美战斗", 3, 280, 260, 0, 260, "完美的战斗技巧", 4000, 350, 50000),
    _gf("gf_t_ahl01", "永恒战士", 3, 280, 0, 260, 260, "永恒存在的战士", 4000, 400, 55000),
    _gf("gf_t_dhl01", "不朽之王", 3, 0, 280, 260, 260, "不朽的战斗之王", 4000, 400, 55000),
    _gf("gf_t_all01", "天下无敌", 3, 280, 260, 260, 260, "天下无敌的存在", 4000, 500, 60000),
]

# 战技注册表
GONGFA_REGISTRY: dict[str, GongfaDef] = {}
for _gf_list in (_GF_HUANG, _GF_XUAN, _GF_DI, _GF_TIAN):
    for _g in _gf_list:
        GONGFA_REGISTRY[_g.gongfa_id] = _g


GONGFA_SCROLL_PREFIX = "gongfa_scroll_"


def get_gongfa_scroll_id(gongfa_id: str) -> str:
    """将战技ID转换为卷轴物品ID。"""
    return f"{GONGFA_SCROLL_PREFIX}{gongfa_id}"


def parse_gongfa_scroll_id(item_id: str) -> str | None:
    """从卷轴物品ID解析战技ID。"""
    if not item_id.startswith(GONGFA_SCROLL_PREFIX):
        return None
    return item_id[len(GONGFA_SCROLL_PREFIX):] or None


def _refresh_gongfa_scroll_items():
    """根据当前 GONGFA_REGISTRY 重新生成战技卷轴定义。

    采用先增后删策略，避免出现卷轴条目全部缺失的中间状态。
    """
    new_items = {}
    for gf in GONGFA_REGISTRY.values():
        scroll_id = get_gongfa_scroll_id(gf.gongfa_id)
        tier_name = GONGFA_TIER_NAMES.get(gf.tier, "未知")
        parts = []
        if gf.attack_bonus:
            parts.append(f"攻+{gf.attack_bonus}")
        if gf.defense_bonus:
            parts.append(f"防+{gf.defense_bonus}")
        if gf.hp_regen:
            parts.append(f"血+{gf.hp_regen}")
        if gf.lingqi_regen:
            parts.append(f"灵+{gf.lingqi_regen}")
        stat_str = "/".join(parts) if parts else "无加成"
        new_items[scroll_id] = ItemDef(
            item_id=scroll_id,
            name=f"{gf.name}卷轴",
            item_type="gongfa",
            description=f"{tier_name}战技【{gf.name}】卷轴（{stat_str}）",
            effect={"learn_gongfa": gf.gongfa_id},
        )
    # 先写入新条目
    ITEM_REGISTRY.update(new_items)
    # 再删除已不存在的旧战技卷轴条目
    stale = [
        item_id for item_id in ITEM_REGISTRY
        if item_id.startswith(GONGFA_SCROLL_PREFIX) and item_id not in new_items
    ]
    for item_id in stale:
        ITEM_REGISTRY.pop(item_id, None)


def set_gongfa_registry(gongfas: dict[str, GongfaDef]):
    """替换战技注册表（供数据库加载后同步到运行时）。

    采用先增后删 + 写锁保护，避免读者看到空/半更新状态。
    """
    new_data = dict(gongfas)
    with _registry_lock:
        GONGFA_REGISTRY.update(new_data)
        stale = [k for k in GONGFA_REGISTRY if k not in new_data]
        for k in stale:
            del GONGFA_REGISTRY[k]
        _refresh_gongfa_scroll_items()


def can_learn_gongfa() -> bool:
    """装备无限制，任何爵位都能装备任何品阶的战技。"""
    return True


def can_cultivate_gongfa(realm: int, tier: int) -> bool:
    """检查爵位是否满足修炼熟练度的要求。"""
    min_realm = GONGFA_TIER_REALM_REQ.get(tier, 0)
    return realm >= min_realm


def get_gongfa_bonus(gongfa_id: str, mastery: int, realm: int) -> dict:
    """计算战技加成（含爵位缩放和精通倍率）。

    公式：effective = base * (1 + 0.1 * realm) * MASTERY_MULTIPLIERS[mastery]

    Returns:
        {attack_bonus, defense_bonus, hp_regen, lingqi_regen, mastery_name}
    """
    gf = GONGFA_REGISTRY.get(gongfa_id)
    if not gf:
        return {
            "attack_bonus": 0, "defense_bonus": 0,
            "hp_regen": 0, "lingqi_regen": 0,
            "mastery_name": "",
        }
    realm_scale = 1.0 + 0.1 * realm
    mastery_mult = MASTERY_MULTIPLIERS[min(mastery, MASTERY_MAX)]
    factor = realm_scale * mastery_mult
    return {
        "attack_bonus": int(gf.attack_bonus * factor),
        "defense_bonus": int(gf.defense_bonus * factor),
        "hp_regen": int(gf.hp_regen * factor),
        "lingqi_regen": int(gf.lingqi_regen * factor),
        "mastery_name": MASTERY_LEVELS[min(mastery, MASTERY_MAX)],
    }


def get_total_gongfa_bonus(player) -> dict:
    """汇总 3 个槽位的战技效果。"""
    total = {"attack_bonus": 0, "defense_bonus": 0, "hp_regen": 0, "lingqi_regen": 0}
    for slot in ("gongfa_1", "gongfa_2", "gongfa_3"):
        gongfa_id = getattr(player, slot, "无")
        if not gongfa_id or gongfa_id == "无":
            continue
        mastery = getattr(player, f"{slot}_mastery", 0)
        bonus = get_gongfa_bonus(gongfa_id, mastery, player.realm)
        total["attack_bonus"] += bonus["attack_bonus"]
        total["defense_bonus"] += bonus["defense_bonus"]
        total["hp_regen"] += bonus["hp_regen"]
        total["lingqi_regen"] += bonus["lingqi_regen"]
    return total


_refresh_gongfa_scroll_items()


def set_realm_config(realms: dict[int, dict]):
    """替换爵位配置（供数据库加载后同步到运行时）。"""
    REALM_CONFIG.clear()
    REALM_CONFIG.update(realms)


def get_sorted_realm_levels() -> list[int]:
    """按从低到高返回当前已配置的爵位等级。"""
    return sorted(int(level) for level in REALM_CONFIG.keys())


def get_max_realm_level() -> int:
    """获取当前配置的最大爵位等级。"""
    levels = get_sorted_realm_levels()
    return levels[-1] if levels else 0


def get_next_realm_level(realm: int) -> int | None:
    """获取比当前爵位更高的下一个已配置爵位。"""
    current = int(realm)
    for level in get_sorted_realm_levels():
        if level > current:
            return level
    return None


def get_previous_realm_level(realm: int) -> int | None:
    """获取比当前爵位更低的上一个已配置爵位。"""
    current = int(realm)
    prev = None
    for level in get_sorted_realm_levels():
        if level >= current:
            break
        prev = level
    return prev


def get_nearest_realm_level(realm: int) -> int:
    """获取与给定等级最接近的已配置爵位，优先回退到更低爵位。"""
    current = int(realm)
    if current in REALM_CONFIG:
        return current
    levels = get_sorted_realm_levels()
    if not levels:
        return 0
    prev = get_previous_realm_level(current)
    nxt = get_next_realm_level(current)
    if prev is None:
        return nxt if nxt is not None else levels[0]
    if nxt is None:
        return prev
    if abs(current - prev) <= abs(nxt - current):
        return prev
    return nxt


def has_sub_realm(realm: int) -> bool:
    """该大爵位是否有小爵位。"""
    cfg = REALM_CONFIG.get(realm)
    return bool(cfg and cfg.get("has_sub_realm"))


def is_high_realm(realm: int) -> bool:
    """是否为高阶大爵位（领主~伯爵，4层小爵位）。"""
    cfg = REALM_CONFIG.get(realm)
    return bool(cfg and cfg.get("high_realm"))


def get_max_sub_realm(realm: int) -> int:
    """获取该大爵位的最大小爵位索引。"""
    if is_high_realm(realm):
        return MAX_HIGH_SUB_REALM
    if has_sub_realm(realm):
        return MAX_SUB_REALM
    return 0


def get_sub_realm_dao_yun_cost(realm: int, sub_realm: int) -> int:
    """获取从 sub_realm 升到 sub_realm+1 所需声望（从 REALM_CONFIG 动态读取）。"""
    cfg = REALM_CONFIG.get(realm, {})
    costs = cfg.get("sub_dao_yun_costs", [])
    if not costs:
        return 0
    return costs[sub_realm] if sub_realm < len(costs) else 0


def get_breakthrough_dao_yun_cost(realm: int) -> int:
    """获取从 realm 晋升到 realm+1 所需声望（从 REALM_CONFIG 动态读取）。"""
    cfg = REALM_CONFIG.get(realm, {})
    return int(cfg.get("breakthrough_dao_yun_cost", 0))


def get_realm_name(realm: int, sub_realm: int = 0) -> str:
    """获取完整等级名称，如 '新兵·士兵' 或 '领主·中级'。"""
    cfg = REALM_CONFIG.get(realm)
    if not cfg:
        return "未知"
    name = cfg["name"]
    if cfg.get("has_sub_realm"):
        if cfg.get("high_realm"):
            if 0 <= sub_realm <= MAX_HIGH_SUB_REALM:
                name += "·" + HIGH_SUB_REALM_NAMES[sub_realm]
        elif 0 <= sub_realm <= MAX_SUB_REALM:
            name += "·" + SUB_REALM_NAMES[sub_realm]
    return name


def get_max_lingqi_by_realm(realm: int, sub_realm: int = 0) -> int:
    """根据等级与小等级计算体力上限。"""
    cfg = REALM_CONFIG.get(realm, {})
    base_lingqi = int(cfg.get("base_lingqi", 50))
    if not has_sub_realm(realm):
        return base_lingqi
    max_sr = get_max_sub_realm(realm)
    sub_realm = max(0, min(max_sr, int(sub_realm)))
    lingqi_step = max(1, int(base_lingqi * 0.08))
    return base_lingqi + lingqi_step * sub_realm


def get_realm_base_stats(realm: int, sub_realm: int = 0) -> dict[str, int]:
    """根据等级与小等级计算基础属性。"""
    cfg = REALM_CONFIG.get(realm, {})
    base_hp = int(cfg.get("base_hp", 100))
    base_attack = int(cfg.get("base_attack", 10))
    base_defense = int(cfg.get("base_defense", 5))
    base_lingqi = int(cfg.get("base_lingqi", 50))
    if not has_sub_realm(realm):
        return {
            "max_hp": base_hp,
            "attack": base_attack,
            "defense": base_defense,
            "max_lingqi": base_lingqi,
        }
    max_sr = get_max_sub_realm(realm)
    sub_realm = max(0, min(max_sr, int(sub_realm)))
    hp_step = int(base_hp * 0.08)
    atk_step = int(base_attack * 0.06)
    def_step = int(base_defense * 0.06)
    lingqi_step = max(1, int(base_lingqi * 0.08))
    return {
        "max_hp": base_hp + hp_step * sub_realm,
        "attack": base_attack + atk_step * sub_realm,
        "defense": base_defense + def_step * sub_realm,
        "max_lingqi": base_lingqi + lingqi_step * sub_realm,
    }


def get_player_base_stats(player) -> dict[str, int]:
    """根据玩家当前等级与永久药剂加成计算基础属性。"""
    stats = get_realm_base_stats(player.realm, player.sub_realm)
    stats["max_hp"] += max(0, int(getattr(player, "permanent_max_hp_bonus", 0)))
    stats["attack"] += max(0, int(getattr(player, "permanent_attack_bonus", 0)))
    stats["defense"] += max(0, int(getattr(player, "permanent_defense_bonus", 0)))
    stats["max_lingqi"] += max(0, int(getattr(player, "permanent_lingqi_bonus", 0)))
    return stats


def get_player_base_max_lingqi(player) -> int:
    """根据玩家当前等级与永久体力加成计算体力上限。"""
    return get_player_base_stats(player)["max_lingqi"]


# ── 副本常量 - 骑砍风格 ──────────────────────────────────────
LAYER_PASS_RATES = [0.80, 0.72, 0.64, 0.56, 0.50]
LAYER_REWARD_TYPES = ["gold", "equipment", "potion", "skill", "combat_skill"]
LAYER_NAMES = ["财宝洞窟", "武器库", "药剂储藏室", "技能训练场", "战利品密室"]
DANGER_WEIGHTS = {"disaster": 80, "monster": 15, "enemy": 5}
DISASTER_OUTCOMES = {"hp_damage": 90, "level_down": 7, "catastrophe": 3}
FLEE_BASE_RATES = [0.70, 0.60, 0.50, 0.40, 0.30]
DUNGEON_RISK_SCORE_CAP = 100.0
DUNGEON_LOW_HP_LINE = 0.20
DUNGEON_FAILURE_WEIGHTS = {
    "hp_loss": 0.38,
    "threat_gap": 0.24,
    "layer": 0.16,
    "risk_stack": 0.14,
    "low_hp": 0.08,
}
DUNGEON_FAILURE_THRESHOLDS = {
    "minor": 35.0,
    "serious": 55.0,
    "critical": 75.0,
}
DUNGEON_DEATH_MODEL = {
    "guard_layers": 2,
    "base": 0.003,
    "per_point": 0.0006,
    "max": 0.018,
}
DUNGEON_RISK_ADJUSTMENTS = {
    "safe_pass": -4.0,
    "combat_win": -6.0,
    "disaster_damage_base": 8.0,
    "disaster_damage_ratio": 28.0,
    "low_hp_bonus": 12.0,
    "failed_flee": 10.0,
    "catastrophe": 18.0,
    "level_down": 16.0,
}
# (概率, 属性比) — "realm_up" 表示高1等级
ENEMY_TIERS: list[tuple] = [(0.90, 0.70), (0.09, 1.50), (0.01, "realm_up")]
COMBAT_MAX_ROUNDS = 30
PVP_ROUND_TIMEOUT = 30  # 秒
