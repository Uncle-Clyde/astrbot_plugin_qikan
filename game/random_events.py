"""
大地图随机事件系统

玩家在旅行途中可能触发随机事件，包括狩猎、采集等。
事件会询问玩家是否消耗体力参与，参与后根据成功率判定结果。

设计原则：
- 小型猎物/采集：高成功率（85-95%），几乎不会失败
- 中型猎物：中等成功率（70-80%），轻微战斗力加成
- 大型猎物：低基础成功率（40-60%），受装备/战斗力显著影响
- 大型猎物失败惩罚严厉（50%HP + 逃跑体力惩罚），迫使玩家停下来恢复
- 高级素材掉落概率：5-10%（独立于基础掉落）
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from .models import Player
from .hunting import HUNT_DROPS
from .gathering import HERBS

EVENT_TYPE_HUNT = "hunt"
EVENT_TYPE_GATHER = "gather"
THREAT_SMALL = "small"
THREAT_MEDIUM = "medium"
THREAT_LARGE = "large"
TRIGGER_RATE_PER_100 = 0.01
MAX_TRIGGER_RATE = 0.30


@dataclass
class RandomEvent:
    event_id: str
    name: str
    description: str
    event_type: str
    lingqi_cost: int
    rewards: dict = field(default_factory=dict)
    success_rate: float = 0.8
    threat_level: str = THREAT_SMALL
    failure_hp_penalty: float = 0.0
    failure_lingqi_penalty: int = 0
    premium_items: dict = field(default_factory=dict)
    min_realm: int = 0


# 事件池
RANDOM_EVENTS: dict[str, RandomEvent] = {
"hunt_rabbit": RandomEvent(
        event_id="hunt_rabbit",
        name="草丛中的野兔",
        description="草丛里有几只野兔窜来窜去，是否尝试捕捉？",
        event_type=EVENT_TYPE_HUNT,
        lingqi_cost=10,
        rewards={"exp": 10, "gold": 8, "items": {"hunt_rabbit_skin": 0.75, "hunt_rabbit_meat": 0.80}},
        success_rate=0.90,
        threat_level=THREAT_SMALL,
        min_realm=0,
    ),
    "hunt_deer": RandomEvent(
        event_id="hunt_deer",
        name="偶遇鹿群",
        description="路边发现了一群正在吃草的鹿，是否消耗体力狩猎？",
        event_type=EVENT_TYPE_HUNT,
        lingqi_cost=15,
        rewards={"exp": 20, "gold": 15, "items": {"hunt_deer_skin": 0.70, "hunt_deer_meat": 0.75}},
        success_rate=0.85,
        threat_level=THREAT_SMALL,
        premium_items={"hunt_deer_antler": 0.05},
        min_realm=0,
    ),
    "hunt_boar": RandomEvent(
        event_id="hunt_boar",
        name="野猪出没",
        description="前方树林传来野猪的嚎叫声，是否前去狩猎？",
        event_type=EVENT_TYPE_HUNT,
        lingqi_cost=20,
        rewards={"exp": 35, "gold": 30, "items": {"hunt_boar_skin": 0.70, "hunt_boar_meat": 0.75, "hunt_boar_tusk": 0.40}},
        success_rate=0.75,
        threat_level=THREAT_MEDIUM,
        premium_items={"hunt_boar_tusk_rare": 0.08},
        min_realm=0,
    ),
    "hunt_wolf": RandomEvent(
        event_id="hunt_wolf",
        name="狼群踪迹",
        description="地上发现了狼的脚印，附近有狼群活动。是否冒险狩猎？⚠️危险！",
        event_type=EVENT_TYPE_HUNT,
        lingqi_cost=25,
        rewards={"exp": 50, "gold": 40, "items": {"hunt_wolf_skin": 0.65, "hunt_wolf_meat": 0.70, "hunt_wolf_fang": 0.45}},
        success_rate=0.50,
        threat_level=THREAT_LARGE,
        failure_hp_penalty=0.50,
        failure_lingqi_penalty=10,
        premium_items={"hunt_wolf_pelt": 0.08},
        min_realm=1,
    ),
    "hunt_bear": RandomEvent(
        event_id="hunt_bear",
        name="巨熊现身",
        description="一只巨大的棕熊挡住了去路！是否迎战狩猎？⚠️极度危险！",
        event_type=EVENT_TYPE_HUNT,
        lingqi_cost=30,
        rewards={"exp": 100, "gold": 80, "items": {"hunt_bear_skin": 0.75, "hunt_bear_paw": 0.55, "hunt_bear_claw": 0.45}},
        success_rate=0.40,
        threat_level=THREAT_LARGE,
        failure_hp_penalty=0.50,
        failure_lingqi_penalty=15,
        premium_items={"hunt_bear_gall": 0.10},
        min_realm=2,
    ),
    "gather_herbs_common": RandomEvent(
        event_id="gather_herbs_common",
        name="路边药草",
        description="路边生长着一些常见的草药，是否顺手采集？",
        event_type=EVENT_TYPE_GATHER,
        lingqi_cost=10,
        rewards={"exp": 8, "gold": 5, "items": {"herb_common": 0.80}},
        success_rate=0.90,
        threat_level=THREAT_SMALL,
        min_realm=0,
    ),
    "gather_herbs_rare": RandomEvent(
        event_id="gather_herbs_rare",
        name="珍稀药园",
        description="在山谷中发现了一片珍稀药草园！是否采集？",
        event_type=EVENT_TYPE_GATHER,
        lingqi_cost=15,
        rewards={"exp": 20, "gold": 15, "items": {"herb_good": 0.70, "herb_rare": 0.40}},
        success_rate=0.85,
        threat_level=THREAT_SMALL,
        premium_items={"herb_ginseng": 0.05},
        min_realm=1,
    ),
    "gather_mushroom": RandomEvent(
        event_id="gather_mushroom",
        name="林中蘑菇",
        description="雨后的树林里长满了蘑菇，是否采集？",
        event_type=EVENT_TYPE_GATHER,
        lingqi_cost=10,
        rewards={"exp": 10, "gold": 8, "items": {"herb_common": 0.75, "herb_good": 0.30}},
        success_rate=0.88,
        threat_level=THREAT_SMALL,
        premium_items={"herb_lingzhi": 0.08},
        min_realm=0,
    ),
}


def get_event(event_id: str) -> Optional[RandomEvent]:
    """获取事件定义"""
    return RANDOM_EVENTS.get(event_id)


def get_applicable_events(player_realm: int) -> list[RandomEvent]:
    """获取适合玩家当前境界的事件"""
    return [
        e for e in RANDOM_EVENTS.values()
        if e.min_realm <= player_realm
    ]


def roll_random_event(distance: float, player_realm: int) -> Optional[RandomEvent]:
    """
    根据旅行距离和境界检查是否触发随机事件。

    Args:
        distance: 旅行距离（地图单位）
        player_realm: 玩家境界

    Returns:
        触发的事件，或 None
    """
    base_chance = TRIGGER_RATE_PER_100 * (distance / 100.0)
    base_chance = min(base_chance, MAX_TRIGGER_RATE)

    if random.random() < base_chance:
        available = get_applicable_events(player_realm)
        if available:
            return random.choice(available)

    return None


def calculate_success_rate(event: RandomEvent, player: Player) -> float:
    """
    计算事件实际成功率。

    - 采集/小型猎物: 固定基础成功率
    - 中型猎物: 轻微战斗力加成(攻击/防御)
    - 大型猎物: 显著战斗力加成(综合战斗力 + 装备)
    """
    base_rate = event.success_rate
    event_type = event.event_type
    threat_level = event.threat_level

    if event_type == EVENT_TYPE_GATHER or threat_level == THREAT_SMALL:
        return base_rate

    if threat_level == THREAT_MEDIUM:
        combat_bonus = (player.attack / 10) * 0.01 + (player.defense / 10) * 0.005
        return min(0.90, base_rate + combat_bonus)

    if threat_level == THREAT_LARGE:
        combat_power = player.attack + player.defense + player.max_hp / 10
        combat_bonus = (combat_power / 50) * 0.05
        equip_bonus = 0.0
        equipment = getattr(player, 'equipment', {}) or {}
        if equipment.get("weapon"):
            equip_bonus += 0.05
        if equipment.get("armor"):
            equip_bonus += 0.05
        return min(0.85, base_rate + combat_bonus + equip_bonus)

    return base_rate


def _add_item_to_inventory(player: Player, item_id: str, quantity: int = 1):
    if not hasattr(player, 'inventory') or not player.inventory:
        player.inventory = {}
    player.inventory[item_id] = player.inventory.get(item_id, 0) + quantity


def resolve_event(event: RandomEvent, player: Player) -> dict:
    if player.lingqi < event.lingqi_cost:
        return {
            "success": False,
            "message": f"体力不足，需要 {event.lingqi_cost} 点体力",
            "event_id": event.event_id,
        }

    player.lingqi -= event.lingqi_cost
    actual_rate = calculate_success_rate(event, player)

    if random.random() < actual_rate:
        rewards = event.rewards.copy()
        gained_items = []
        premium_gained = []

        for item_id, drop_chance in rewards.get("items", {}).items():
            if random.random() < drop_chance:
                _add_item_to_inventory(player, item_id)
                item_name = _get_item_name(item_id)
                gained_items.append(item_name)

        for item_id, premium_chance in event.premium_items.items():
            if random.random() < premium_chance:
                _add_item_to_inventory(player, item_id)
                item_name = _get_item_name(item_id)
                premium_gained.append(item_name)

        exp_gained = rewards.get("exp", 0)
        gold_gained = rewards.get("gold", 0)
        player.exp += exp_gained
        if hasattr(player, 'spirit_stones'):
            player.spirit_stones += gold_gained

        msg = f"{event.name} - 成功！"
        all_items = gained_items + premium_gained
        if all_items:
            display_items = gained_items + [f"✨{name}" for name in premium_gained]
            msg += f" 获得：{'、'.join(display_items)}"
        if exp_gained:
            msg += f" 经验+{exp_gained}"
        if gold_gained:
            msg += f" 第纳尔+{gold_gained}"

        return {
            "success": True,
            "event_success": True,
            "message": msg,
            "event_id": event.event_id,
            "exp_gained": exp_gained,
            "gold_gained": gold_gained,
            "items_gained": gained_items,
            "premium_items_gained": premium_gained,
            "lingqi_cost": event.lingqi_cost,
        }
    else:
        msg = f"{event.name} - 失败了！"

        if event.threat_level == THREAT_LARGE:
            hp_loss = int(player.max_hp * event.failure_hp_penalty)
            hp_loss = max(1, hp_loss)
            player.hp = max(1, player.hp - hp_loss)

            lingqi_penalty = event.failure_lingqi_penalty
            player.lingqi = max(0, player.lingqi - lingqi_penalty)

            msg += f" 被野兽反击，损失{hp_loss}点HP！逃跑时又消耗了{lingqi_penalty}点体力。"
            msg += " 你需要停下来休息恢复。"
        else:
            msg += " 猎物逃走了，什么也没得到。"

        return {
            "success": True,
            "event_success": False,
            "message": msg,
            "event_id": event.event_id,
            "hp_lost": int(player.max_hp * event.failure_hp_penalty) if event.threat_level == THREAT_LARGE else 0,
            "lingqi_penalty": event.failure_lingqi_penalty if event.threat_level == THREAT_LARGE else 0,
            "lingqi_cost": event.lingqi_cost,
        }


def _get_item_name(item_id: str) -> str:
    if item_id in HUNT_DROPS:
        return HUNT_DROPS[item_id]["name"]
    if item_id in HERBS:
        return HERBS[item_id].name
    return item_id


def format_event_for_api(event: RandomEvent, player: Player) -> dict:
    actual_rate = calculate_success_rate(event, player)
    items = []
    for item_id, drop_chance in event.rewards.get("items", {}).items():
        items.append({
            "item_id": item_id,
            "name": _get_item_name(item_id),
            "chance": int(drop_chance * 100),
        })
    premium_items = []
    for item_id, chance in event.premium_items.items():
        premium_items.append({
            "item_id": item_id,
            "name": _get_item_name(item_id),
            "chance": int(chance * 100),
        })
    return {
        "event_id": event.event_id,
        "name": event.name,
        "description": event.description,
        "event_type": event.event_type,
        "lingqi_cost": event.lingqi_cost,
        "success_rate": int(actual_rate * 100),
        "threat_level": event.threat_level,
        "exp_reward": event.rewards.get("exp", 0),
        "gold_reward": event.rewards.get("gold", 0),
        "items": items,
        "premium_items": premium_items,
    }


def format_event_preview(event: RandomEvent) -> str:
    lines = [
        f"🎲 {event.name}",
        f"📝 {event.description}",
        f"💪 体力消耗: {event.lingqi_cost}",
    ]

    if event.threat_level == THREAT_LARGE:
        lines.append(f"⚠️ 危险！基础成功率: {int(event.success_rate * 100)}%")
        lines.append(f"💀 失败惩罚: 损失50%HP + {event.failure_lingqi_penalty}点逃跑体力")
    else:
        lines.append(f"🎯 成功率: {int(event.success_rate * 100)}%")

    lines.append("📦 可能获得:")
    for item_id, drop_chance in event.rewards.get("items", {}).items():
        name = _get_item_name(item_id)
        lines.append(f"   - {name} ({int(drop_chance * 100)}%)")

    if event.premium_items:
        lines.append("✨ 稀有掉落:")
        for item_id, premium_chance in event.premium_items.items():
            name = _get_item_name(item_id)
            lines.append(f"   - {name} ({int(premium_chance * 100)}%)")

    if event.rewards.get("exp"):
        lines.append(f"   - 经验: {event.rewards['exp']}")
    if event.rewards.get("gold"):
        lines.append(f"   - 第纳尔: {event.rewards['gold']}")

    return "\n".join(lines)
