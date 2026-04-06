"""同伴系统 - 骑砍风格。"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CompanionDef:
    """同伴定义。"""
    companion_id: str
    name: str
    title: str           # 称号，如"老兵"、"学者"
    recruit_location: str  # 招募地点
    recruit_cost: int     # 招募费用（第纳尔）
    attack: int           # 基础攻击
    defense: int          # 基础防御
    hp: int               # 基础生命
    buff_type: str        # buff类型: attack/defense/hp/crit/all
    buff_value: int       # buff数值
    description: str
    gift_preferences: list[str] = field(default_factory=list)  # 喜欢的礼物


# 同伴注册表
COMPANION_REGISTRY: dict[str, CompanionDef] = {
    "borcha": CompanionDef(
        companion_id="borcha",
        name="博尔察",
        title="草原斥候",
        recruit_location="库吉特酒馆",
        recruit_cost=500,
        attack=15, defense=10, hp=50,
        buff_type="attack", buff_value=10,
        description="来自草原的老练斥候，擅长侦察与追踪。",
        gift_preferences=["烤肉", "马奶酒"],
    ),
    "matheld": CompanionDef(
        companion_id="matheld",
        name="玛蒂尔德",
        title="诺德女战士",
        recruit_location="诺德酒馆",
        recruit_cost=800,
        attack=25, defense=15, hp=80,
        buff_type="attack", buff_value=20,
        description="北方来的勇猛女战士，手持战斧无人能挡。",
        gift_preferences=["烈酒", "战利品"],
    ),
    "jeremus": CompanionDef(
        companion_id="jeremus",
        name="杰鲁墨斯",
        title="战场医师",
        recruit_location="斯瓦迪亚酒馆",
        recruit_cost=600,
        attack=5, defense=10, hp=40,
        buff_type="hp", buff_value=100,
        description="经验丰富的战场医师，能救治伤员。",
        gift_preferences=["草药", "医书"],
    ),
    "katre": CompanionDef(
        companion_id="katre",
        name="卡特尔",
        title="罗多克神射手",
        recruit_location="罗多克酒馆",
        recruit_cost=700,
        attack=30, defense=8, hp=45,
        buff_type="crit", buff_value=5,
        description="百步穿杨的神射手，弩箭从不虚发。",
        gift_preferences=["好弓", "箭矢"],
    ),
    "marnid": CompanionDef(
        companion_id="marnid",
        name="马尔尼德",
        title="维吉亚猎人",
        recruit_location="维吉亚酒馆",
        recruit_cost=400,
        attack=12, defense=12, hp=55,
        buff_type="defense", buff_value=10,
        description="森林中的老猎人，追踪与生存专家。",
        gift_preferences=["兽皮", "猎物"],
    ),
    "rolf": CompanionDef(
        companion_id="rolf",
        name="罗尔夫",
        title="前海盗头目",
        recruit_location="沿海酒馆",
        recruit_cost=1000,
        attack=35, defense=20, hp=100,
        buff_type="all", buff_value=8,
        description="令人闻风丧胆的海盗头目，现已金盆洗手。",
        gift_preferences=["金币", "朗姆酒"],
    ),
    "beatrix": CompanionDef(
        companion_id="beatrix",
        name="贝娅特丽克丝",
        title="流浪学者",
        recruit_location="萨兰德酒馆",
        recruit_cost=450,
        attack=3, defense=5, hp=30,
        buff_type="hp", buff_value=60,
        description="博学的流浪学者，通晓多国语言与历史。",
        gift_preferences=["古籍", "墨水"],
    ),
    "baheshtur": CompanionDef(
        companion_id="baheshtur",
        name="巴赫斯特尔",
        title="沙漠佣兵",
        recruit_location="萨兰德酒馆",
        recruit_cost=650,
        attack=22, defense=18, hp=70,
        buff_type="defense", buff_value=15,
        description="沙漠中身经百战的佣兵，擅长沙漠作战。",
        gift_preferences=["香料", "水袋"],
    ),
    "ymira": CompanionDef(
        companion_id="ymira",
        name="伊米拉",
        title="驯马师",
        recruit_location="库吉特酒馆",
        recruit_cost=550,
        attack=8, defense=12, hp=50,
        buff_type="attack", buff_value=12,
        description="草原上最好的驯马师，能与任何马匹建立联系。",
        gift_preferences=["燕麦", "马具"],
    ),
    "deshavi": CompanionDef(
        companion_id="deshavi",
        name="德沙维",
        title="萨兰德舞者",
        recruit_location="萨兰德酒馆",
        recruit_cost=350,
        attack=10, defense=8, hp=35,
        buff_type="crit", buff_value=3,
        description="以舞蹈为掩护的情报收集者。",
        gift_preferences=["丝绸", "珠宝"],
    ),
    "tredian": CompanionDef(
        companion_id="tredian",
        name="特雷迪安",
        title="斯瓦迪亚骑士",
        recruit_location="斯瓦迪亚酒馆",
        recruit_cost=1200,
        attack=40, defense=30, hp=120,
        buff_type="all", buff_value=12,
        description="被剥夺领地的斯瓦迪亚骑士，渴望重获荣耀。",
        gift_preferences=["战马", "骑士勋章"],
    ),
    "lezalit": CompanionDef(
        companion_id="lezalit",
        name="雷扎里特",
        title="纪律教官",
        recruit_location="斯瓦迪亚酒馆",
        recruit_cost=900,
        attack=18, defense=25, hp=90,
        buff_type="defense", buff_value=20,
        description="严苛的纪律教官，能将乌合之众训练成精锐。",
        gift_preferences=["军规手册", "铁鞭"],
    ),
}

# 礼物注册表
GIFT_REGISTRY: dict[str, dict] = {
    "烤肉": {"base_price": 30, "description": "香喷喷的烤肉"},
    "马奶酒": {"base_price": 50, "description": "草原特产马奶酒"},
    "烈酒": {"base_price": 80, "description": "北方烈性酒"},
    "战利品": {"base_price": 100, "description": "战斗中缴获的战利品"},
    "草药": {"base_price": 40, "description": "各种药用植物"},
    "医书": {"base_price": 120, "description": "医学典籍"},
    "好弓": {"base_price": 200, "description": "一把精良的弓"},
    "箭矢": {"base_price": 20, "description": "一捆箭矢"},
    "兽皮": {"base_price": 50, "description": "处理过的兽皮"},
    "猎物": {"base_price": 60, "description": "新鲜猎获的动物"},
    "金币": {"base_price": 500, "description": "一袋金币"},
    "朗姆酒": {"base_price": 100, "description": "海盗最爱的朗姆酒"},
    "古籍": {"base_price": 150, "description": "珍贵的古代文献"},
    "墨水": {"base_price": 30, "description": "优质墨水"},
    "香料": {"base_price": 80, "description": "来自东方的香料"},
    "水袋": {"base_price": 20, "description": "装满清水的皮水袋"},
    "燕麦": {"base_price": 25, "description": "优质燕麦饲料"},
    "马具": {"base_price": 100, "description": "精致的马具"},
    "丝绸": {"base_price": 200, "description": "精美的丝绸布料"},
    "珠宝": {"base_price": 300, "description": "闪亮的珠宝首饰"},
    "战马": {"base_price": 800, "description": "一匹优良的战马"},
    "骑士勋章": {"base_price": 500, "description": "象征荣耀的勋章"},
    "军规手册": {"base_price": 80, "description": "军队纪律手册"},
    "铁鞭": {"base_price": 60, "description": "训练用的铁鞭"},
}


@dataclass
class PlayerCompanion:
    """玩家同伴数据。"""
    companion_id: str
    loyalty: int = 50          # 忠诚度 0-100
    gifts_given: int = 0       # 已赠送礼物次数
    last_gift_time: float = 0  # 上次赠送礼物时间
    is_active: bool = False    # 是否出战


def get_companion(companion_id: str) -> Optional[CompanionDef]:
    """获取同伴定义。"""
    return COMPANION_REGISTRY.get(companion_id)


def get_all_companions() -> list[CompanionDef]:
    """获取所有同伴。"""
    return list(COMPANION_REGISTRY.values())


def get_companion_buff(companion: PlayerCompanion) -> dict:
    """获取同伴提供的buff。"""
    comp_def = COMPANION_REGISTRY.get(companion.companion_id)
    if not comp_def or not companion.is_active:
        return {"attack": 0, "defense": 0, "hp": 0, "crit": 0}
    
    loyalty_mult = companion.loyalty / 100.0
    value = int(comp_def.buff_value * loyalty_mult)
    
    if comp_def.buff_type == "attack":
        return {"attack": value, "defense": 0, "hp": 0, "crit": 0}
    elif comp_def.buff_type == "defense":
        return {"attack": 0, "defense": value, "hp": 0, "crit": 0}
    elif comp_def.buff_type == "hp":
        return {"attack": 0, "defense": 0, "hp": value, "crit": 0}
    elif comp_def.buff_type == "crit":
        return {"attack": 0, "defense": 0, "hp": 0, "crit": value}
    elif comp_def.buff_type == "all":
        return {"attack": value, "defense": value, "hp": value * 2, "crit": 0}
    return {"attack": 0, "defense": 0, "hp": 0, "crit": 0}


def calculate_gift_loyalty_gain(companion_id: str, gift_id: str) -> int:
    """计算赠送礼物获得的忠诚度。"""
    comp_def = COMPANION_REGISTRY.get(companion_id)
    if not comp_def:
        return 0
    
    if gift_id in comp_def.gift_preferences:
        return random.randint(8, 12)
    else:
        return random.randint(2, 5)


def calculate_recruit_cost(companion_id: str) -> int:
    """获取招募费用。"""
    comp_def = COMPANION_REGISTRY.get(companion_id)
    if not comp_def:
        return 0
    return comp_def.recruit_cost
