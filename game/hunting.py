"""
狩猎系统 - Mount & Blade 风格

玩家可以猎杀野生动物获取材料。
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional


@dataclass
class Wildlife:
    """野生动物定义"""
    wildlife_id: str
    name: str
    description: str
    tier: int  # 0=普通, 1=进阶, 2=高级, 3=Boss
    habitat: list[str]  # 栖息地类型
    drop_items: dict[str, float]  # 掉落物品及概率 {item_id: chance}
    exp_reward: int
    gold_reward: int


WILDLIFE: dict[str, Wildlife] = {
    # 普通动物
    "deer": Wildlife(
        wildlife_id="deer",
        name="鹿",
        description="森林中常见的温顺动物",
        tier=0,
        habitat=["forest", "grassland"],
        drop_items={
            "hunt_deer_skin": 0.8,  # 鹿皮
            "hunt_deer_meat": 0.9,  # 鹿肉
            "hunt_deer_antler": 0.3,  # 鹿角
        },
        exp_reward=15,
        gold_reward=10,
    ),
    "rabbit": Wildlife(
        wildlife_id="rabbit",
        name="野兔",
        description="草地常见的的小动物",
        tier=0,
        habitat=["grassland", "forest"],
        drop_items={
            "hunt_rabbit_skin": 0.7,  # 兔皮
            "hunt_rabbit_meat": 0.9,  # 兔肉
        },
        exp_reward=8,
        gold_reward=5,
    ),
    "chicken": Wildlife(
        wildlife_id="chicken",
        name="野鸡",
        description="村庄附近的野生禽类",
        tier=0,
        habitat=["village", "grassland"],
        drop_items={
            "hunt_feather": 0.8,  # 羽毛
            "hunt_chicken_meat": 0.9,  # 鸡肉
        },
        exp_reward=5,
        gold_reward=3,
    ),
    
    # 进阶动物
    "boar": Wildlife(
        wildlife_id="boar",
        name="野猪",
        description="具有攻击性的野兽",
        tier=1,
        habitat=["forest", "mountain"],
        drop_items={
            "hunt_boar_skin": 0.8,  # 野猪皮
            "hunt_boar_meat": 0.9,  # 猪肉
            "hunt_boar_tusk": 0.4,  # 獠牙
        },
        exp_reward=30,
        gold_reward=25,
    ),
    "wolf": Wildlife(
        wildlife_id="wolf",
        name="狼",
        description="成群出现的捕食者",
        tier=1,
        habitat=["forest", "mountain"],
        drop_items={
            "hunt_wolf_skin": 0.7,  # 狼皮
            "hunt_wolf_meat": 0.8,  # 狼肉
            "hunt_wolf_fang": 0.5,  # 狼牙
        },
        exp_reward=35,
        gold_reward=30,
    ),
    "snake": Wildlife(
        wildlife_id="snake",
        name="毒蛇",
        description="有毒的爬行动物",
        tier=1,
        habitat=["desert", "grassland"],
        drop_items={
            "hunt_snake_skin": 0.7,  # 蛇皮
            "hunt_snake_gall": 0.4,  # 蛇胆
        },
        exp_reward=25,
        gold_reward=20,
    ),
    
    # 高级动物
    "bear": Wildlife(
        wildlife_id="bear",
        name="熊",
        description="森林深处的顶级捕食者",
        tier=2,
        habitat=["forest", "mountain"],
        drop_items={
            "hunt_bear_skin": 0.9,  # 熊皮
            "hunt_bear_paw": 0.6,  # 熊掌
            "hunt_bear_gall": 0.3,  # 熊胆
            "hunt_bear_claw": 0.5,  # 熊爪
        },
        exp_reward=80,
        gold_reward=100,
    ),
    
    # Boss级
    "wolf_pack_leader": Wildlife(
        wildlife_id="wolf_pack_leader",
        name="狼王",
        description="狼群的首领",
        tier=3,
        habitat=["forest", "mountain"],
        drop_items={
            "hunt_wolf_skin": 1.0,
            "hunt_wolf_fang": 0.9,
            "hunt_wolf_pelt": 0.5,  # 狼王毛皮
        },
        exp_reward=150,
        gold_reward=200,
    ),
}


# 掉落物品定义
HUNT_DROPS: dict[str, dict] = {
    # 皮革类
    "hunt_deer_skin": {"name": "鹿皮", "category": "皮革", "price": 15},
    "hunt_rabbit_skin": {"name": "兔皮", "category": "皮革", "price": 8},
    "hunt_boar_skin": {"name": "野猪皮", "category": "皮革", "price": 25},
    "hunt_wolf_skin": {"name": "狼皮", "category": "皮革", "price": 30},
    "hunt_bear_skin": {"name": "熊皮", "category": "高级皮革", "price": 80},
    "hunt_wolf_pelt": {"name": "狼王毛皮", "category": "珍稀皮革", "price": 150},
    "hunt_snake_skin": {"name": "蛇皮", "category": "皮革", "price": 20},
    
    # 肉食类
    "hunt_deer_meat": {"name": "鹿肉", "category": "肉类", "price": 10},
    "hunt_rabbit_meat": {"name": "兔肉", "category": "肉类", "price": 5},
    "hunt_chicken_meat": {"name": "鸡肉", "category": "肉类", "price": 3},
    "hunt_boar_meat": {"name": "猪肉", "category": "肉类", "price": 15},
    "hunt_wolf_meat": {"name": "狼肉", "category": "肉类", "price": 12},
    "hunt_bear_paw": {"name": "熊掌", "category": "珍稀", "price": 100},
    
    # 材料类
    "hunt_deer_antler": {"name": "鹿角", "category": "材料", "price": 30},
    "hunt_boar_tusk": {"name": "獠牙", "category": "材料", "price": 35},
    "hunt_wolf_fang": {"name": "狼牙", "category": "材料", "price": 40},
    "hunt_bear_claw": {"name": "熊爪", "category": "材料", "price": 60},
    "hunt_feather": {"name": "羽毛", "category": "材料", "price": 5},
    
    # 药材类
    "hunt_snake_gall": {"name": "蛇胆", "category": "药材", "price": 50},
    "hunt_bear_gall": {"name": "熊胆", "category": "珍稀药材", "price": 120},
}


def get_wildlife(wildlife_id: str) -> Optional[Wildlife]:
    """获取野生动物定义"""
    return WILDLIFE.get(wildlife_id)


def get_all_wildlife() -> list[Wildlife]:
    """获取所有野生动物"""
    return list(WILDLIFE.values())


def get_wildlife_by_habitat(habitat: str) -> list[Wildlife]:
    """根据栖息地获取野生动物"""
    return [w for w in WILDLIFE.values() if habitat in w.habitat]


def get_drop_item(item_id: str) -> Optional[dict]:
    """获取掉落物品定义"""
    return HUNT_DROPS.get(item_id)


def calculate_hunt_drops(wildlife: Wildlife) -> dict[str, int]:
    """计算狩猎掉落"""
    drops = {}
    
    for item_id, chance in wildlife.drop_items.items():
        if random.random() < chance:
            drops[item_id] = 1
    
    return drops


def format_hunt_drops(drops: dict[str, int]) -> str:
    """格式化掉落列表"""
    if not drops:
        return "无"
    
    lines = []
    for item_id, count in drops.items():
        item = get_drop_item(item_id)
        if item:
            lines.append(f"{item['name']}x{count}")
    
    return "、".join(lines) if lines else "无"


def get_hunting_tips(location_id: str) -> str:
    """根据位置获取狩猎提示"""
    from .map_system import TOWNS, VILLAGES, CASTLES
    
    # 根据城镇/村庄位置判断栖息地
    habitat_hints = {
        "town_sargoth": "港口城市，周边有狼群出没",
        "town_dhirim": "农业发达，周边有野兔和野鸡",
        "town_curin": "山城附近有熊和野猪",
        "town_pravend": "葡萄酒产区，周边森林有鹿",
        "village_teona": "渔村，周边可以打到水鸟",
    }
    
    return habitat_hints.get(location_id, "进入野外寻找野生动物")


# 城镇猎人商店出售的材料
def get_hunter_shop_materials(location_id: str) -> list[dict]:
    """获取城镇猎人商店材料"""
    base_materials = [
        {"item_id": "hunt_rabbit_skin", "price": 10, "name": "兔皮"},
        {"item_id": "hunt_feather", "price": 8, "name": "羽毛"},
    ]
    
    # 部分城镇有进阶材料
    if location_id in ("town_curin", "town_dhirim"):
        base_materials.extend([
            {"item_id": "hunt_boar_skin", "price": 30, "name": "野猪皮"},
            {"item_id": "hunt_boar_tusk", "price": 40, "name": "獠牙"},
        ])
    
    if location_id == "town_sargoth":
        base_materials.extend([
            {"item_id": "hunt_wolf_skin", "price": 35, "name": "狼皮"},
            {"item_id": "hunt_wolf_fang", "price": 50, "name": "狼牙"},
        ])
    
    return base_materials
