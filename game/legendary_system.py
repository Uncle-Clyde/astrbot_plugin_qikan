"""
传奇盗匪BOSS系统

5个传奇BOSS对应5个国家/盗匪文化
击败后掉落传奇装备，集齐套装有额外加成

规则：
- 传奇套装只能从对应的BOSS身上掉落
- 一次性不会掉落所有部件
- 传奇BOSS刷新时间：每周三和周日
- 传奇套装武器每个玩家只能刷出来一次
- 每次掉落必定是不同的部件
- 每个BOSS每周最多只能复活2次（周三和周日）
- BOSS等级和属性根据服务器最高玩家等级成长
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict
from enum import IntEnum
import time
import random
from .constants import EquipmentTier, EquipmentDef, EQUIPMENT_REGISTRY


class LegendarySetType(IntEnum):
    """传奇套装类型"""
    VIKING = 1       # 海盗套装 (诺德)
    NOMAD = 2        # 响马套装 (库吉特)
    FOREST = 3       # 绿林套装 (维吉亚)
    MOUNTAIN = 4     # 山贼套装 (罗多克)
    LORD = 5         # 盗圣套装 (斯瓦迪亚)


# 传奇BOSS刷新时间：周三(2)和周日(0)
LEGENDARY_BOSS_RESPAWN_DAYS = {2, 0}


# BOSS基础属性
BOSS_BASE_LEVEL = 30
BOSS_BASE_HP = 5000
BOSS_BASE_ATTACK = 200
BOSS_BASE_DEFENSE = 100


@dataclass
class LegendarySet:
    """传奇套装定义"""
    set_id: int
    name: str
    description: str
    icon: str
    pieces: list[str]
    set_bonus_2: str
    set_bonus_3: str
    set_bonus_5: str
    set_hp_bonus: int = 0
    set_attack_bonus: int = 0
    set_defense_bonus: int = 0
    set_dodge_bonus: float = 0
    set_crit_bonus: float = 0


@dataclass
class LegendaryBoss:
    """传奇BOSS定义"""
    boss_id: str
    name: str
    title: str
    description: str
    icon: str
    faction: int
    set_type: int
    level: int = 30
    hp: int = 5000
    attack: int = 200
    defense: int = 100
    drop_count_min: int = 1
    drop_count_max: int = 2
    bounty_gold: int = 5000
    bounty_exp: int = 2000


LEGENDARY_SETS: dict[int, LegendarySet] = {
    LegendarySetType.VIKING: LegendarySet(
        set_id=LegendarySetType.VIKING,
        name="海盗王套装",
        description="诺德海盗王的传奇装备，蕴含着北方大海的力量",
        icon="☠️",
        pieces=["vikings_helmet", "vikings_armor", "vikings_sword", "vikings_shield", "vikings_boots"],
        set_bonus_2="生命+200",
        set_bonus_3="攻击+30, 生命+300",
        set_bonus_5="攻击+50, 生命+500, 暴击+10%",
        set_hp_bonus=500,
        set_attack_bonus=50,
        set_defense_bonus=20,
        set_crit_bonus=10,
    ),
    LegendarySetType.NOMAD: LegendarySet(
        set_id=LegendarySetType.NOMAD,
        name="响马王套装",
        description="库吉特草原响马王的传奇装备，来去如风的象征",
        icon="🐎",
        pieces=["nomad_helmet", "nomad_armor", "nomad_bow", "nomad_saber", "nomad_cape"],
        set_bonus_2="闪避+5%",
        set_bonus_3="闪避+10%, 移动速度+5%",
        set_bonus_5="闪避+15%, 移动速度+10%, 弓术伤害+20%",
        set_hp_bonus=200,
        set_attack_bonus=30,
        set_defense_bonus=10,
        set_dodge_bonus=15,
    ),
    LegendarySetType.FOREST: LegendarySet(
        set_id=LegendarySetType.FOREST,
        name="绿林王套装",
        description="维吉亚绿林好汉的传奇装备，森林中的幽灵",
        icon="🌲",
        pieces=["forest_helmet", "forest_armor", "forest_bow", "forest_dagger", "forest_cloak"],
        set_bonus_2="暴击+5%",
        set_bonus_3="暴击+10%, 闪避+5%",
        set_bonus_5="暴击+20%, 闪避+10%, 弓术伤害+25%",
        set_hp_bonus=150,
        set_attack_bonus=40,
        set_defense_bonus=15,
        set_crit_bonus=20,
    ),
    LegendarySetType.MOUNTAIN: LegendarySet(
        set_id=LegendarySetType.MOUNTAIN,
        name="山贼王套装",
        description="罗多克山地战士的传奇装备，坚如磐石",
        icon="⛰️",
        pieces=["mountain_helmet", "mountain_armor", "mountain_hammer", "mountain_shield", "mountain_boots"],
        set_bonus_2="防御+20",
        set_bonus_3="防御+40, 生命+200",
        set_bonus_5="防御+60, 生命+400, 减伤+10%",
        set_hp_bonus=400,
        set_attack_bonus=25,
        set_defense_bonus=60,
    ),
    LegendarySetType.LORD: LegendarySet(
        set_id=LegendarySetType.LORD,
        name="盗圣套装",
        description="斯瓦迪亚盗匪之王的传奇装备，盗亦有道",
        icon="👑",
        pieces=["lord_helmet", "lord_armor", "lord_sword", "lord_cape", "lord_ring"],
        set_bonus_2="全属性+10",
        set_bonus_3="全属性+20, 经验+10%",
        set_bonus_5="全属性+30, 经验+20%, 掉落率+10%",
        set_hp_bonus=300,
        set_attack_bonus=35,
        set_defense_bonus=30,
    ),
}


LEGENDARY_BOSSES: dict[str, LegendaryBoss] = {
    "boss_viking": LegendaryBoss(
        boss_id="boss_viking",
        name="海尔伯格",
        title="海尔伯格",
        description="诺德海域最恐怖的海盗王",
        icon="☠️",
        faction=1,
        set_type=LegendarySetType.VIKING,
    ),
    "boss_nomad": LegendaryBoss(
        boss_id="boss_nomad",
        name="铁木真",
        title="草原之狼",
        description="库吉特草原上最传奇的响马王",
        icon="🐎",
        faction=4,
        set_type=LegendarySetType.NOMAD,
    ),
    "boss_forest": LegendaryBoss(
        boss_id="boss_forest",
        name="格林",
        title="绿影刺客",
        description="维吉亚森林中最神秘的绿林王",
        icon="🌲",
        faction=2,
        set_type=LegendarySetType.FOREST,
    ),
    "boss_mountain": LegendaryBoss(
        boss_id="boss_mountain",
        name="巨石",
        title="山地巨兽",
        description="罗多克山脉中最恐怖的山贼王",
        icon="⛰️",
        faction=3,
        set_type=LegendarySetType.MOUNTAIN,
    ),
    "boss_lord": LegendaryBoss(
        boss_id="boss_lord",
        name="黑爵士",
        title="暗影主宰",
        description="斯瓦迪亚最神秘的盗匪之王",
        icon="👑",
        faction=0,
        set_type=LegendarySetType.LORD,
    ),
}


# BOSS状态管理器
class LegendaryBossManager:
    def __init__(self):
        self.boss_states: Dict[str, dict] = {}
        self.player_drops: Dict[str, Dict[str, list]] = {}
        self.boss_dynamic_states: Dict[str, dict] = {}

    def can_boss_respawn(self, boss_id: str) -> bool:
        now = time.time()
        current_weekday = time.localtime(now).tm_wday
        if current_weekday not in LEGENDARY_BOSS_RESPAWN_DAYS:
            return False
        state = self.boss_states.get(boss_id, {})
        last_respawn = state.get("last_respawn", 0)
        if last_respawn:
            last_weekday = time.localtime(last_respawn).tm_wday
            if last_weekday in LEGENDARY_BOSS_RESPAWN_DAYS:
                return False
        return True

    def respawn_boss(self, boss_id: str) -> bool:
        if not self.can_boss_respawn(boss_id):
            return False
        now = time.time()
        if boss_id not in self.boss_states:
            self.boss_states[boss_id] = {"respawn_count": 0, "week_start": now}
        self.boss_states[boss_id]["last_respawn"] = now
        self.boss_states[boss_id]["respawn_count"] = self.boss_states[boss_id].get("respawn_count", 0) + 1
        week_start = self._get_week_start(now)
        if self.boss_states[boss_id].get("week_start", 0) < week_start:
            self.boss_states[boss_id]["respawn_count"] = 1
            self.boss_states[boss_id]["week_start"] = week_start
        return True

    def _get_week_start(self, timestamp: float) -> float:
        tm = time.localtime(timestamp)
        days_since_monday = tm.tm_wday
        monday_timestamp = timestamp - days_since_monday * 86400
        return monday_timestamp - tm.tm_hour * 3600 - tm.tm_min * 60 - tm.tm_sec

    def is_boss_alive(self, boss_id: str) -> bool:
        state = self.boss_states.get(boss_id, {})
        last_respawn = state.get("last_respawn", 0)
        if last_respawn == 0:
            return False
        current_weekday = time.localtime(time.time()).tm_wday
        if current_weekday not in LEGENDARY_BOSS_RESPAWN_DAYS:
            return False
        return True

    def get_player_obtained_pieces(self, user_id: str, boss_id: str) -> list:
        if user_id not in self.player_drops:
            return []
        return self.player_drops[user_id].get(boss_id, [])

    def add_player_drop(self, user_id: str, boss_id: str, piece_id: str):
        if user_id not in self.player_drops:
            self.player_drops[user_id] = {}
        if boss_id not in self.player_drops[user_id]:
            self.player_drops[user_id][boss_id] = []
        self.player_drops[user_id][boss_id].append(piece_id)

    def generate_drops(self, user_id: str, boss_id: str) -> list[str]:
        boss = LEGENDARY_BOSSES.get(boss_id)
        if not boss:
            return []
        set_def = LEGENDARY_SETS.get(boss.set_type)
        if not set_def:
            return []
        obtained = self.get_player_obtained_pieces(user_id, boss_id)
        available_pieces = [p for p in set_def.pieces if p not in obtained]
        if not available_pieces:
            return []
        drop_count = random.randint(boss.drop_count_min, boss.drop_count_max)
        drop_count = min(drop_count, len(available_pieces))
        drops = random.sample(available_pieces, drop_count)
        for piece in drops:
            self.add_player_drop(user_id, boss_id, piece)
        return drops

    def spawn_boss_with_growth(self, boss_id: str, player_max_level: int):
        stats = calculate_boss_stats(player_max_level)
        self.boss_dynamic_states[boss_id] = {
            "level": stats["level"],
            "hp": stats["hp"],
            "max_hp": stats["hp"],
            "attack": stats["attack"],
            "defense": stats["defense"],
            "spawn_time": time.time(),
            "grown": True,
        }
        return self.respawn_boss(boss_id)

    def get_boss_dynamic_state(self, boss_id: str) -> dict:
        return self.boss_dynamic_states.get(boss_id, {})


legendary_boss_manager = LegendaryBossManager()


def calculate_boss_stats(player_max_level: int) -> dict:
    """根据最高玩家等级计算BOSS属性"""
    if player_max_level < 20:
        player_max_level = 20
    level_bonus = (player_max_level - 20) * 0.5
    boss_level = min(50, int(BOSS_BASE_LEVEL + level_bonus))
    hp_factor = 1 + (player_max_level - 20) * 0.15
    attack_factor = 1 + (player_max_level - 20) * 0.08
    defense_factor = 1 + (player_max_level - 20) * 0.06
    return {
        "level": boss_level,
        "hp": int(BOSS_BASE_HP * hp_factor),
        "attack": int(BOSS_BASE_ATTACK * attack_factor),
        "defense": int(BOSS_BASE_DEFENSE * defense_factor),
    }


def get_set_by_piece(piece_id: str) -> Optional[LegendarySet]:
    for set_def in LEGENDARY_SETS.values():
        if piece_id in set_def.pieces:
            return set_def
    return None


def check_set_bonus(player_items: list[str]) -> dict:
    set_counts = {}
    player_set_pieces = {}
    for set_id, set_def in LEGENDARY_SETS.items():
        count = 0
        pieces = []
        for piece in set_def.pieces:
            if piece in player_items:
                count += 1
                pieces.append(piece)
        if count > 0:
            set_counts[set_id] = count
            player_set_pieces[set_id] = pieces
    result = {"sets": {}, "total_bonus": {}}
    for set_id, count in set_counts.items():
        set_def = LEGENDARY_SETS.get(set_id)
        if not set_def:
            continue
        bonuses = []
        if count >= 2:
            bonuses.append({"pieces": 2, "effect": set_def.set_bonus_2})
        if count >= 3:
            bonuses.append({"pieces": 3, "effect": set_def.set_bonus_3})
        if count >= 5:
            bonuses.append({"pieces": 5, "effect": set_def.set_bonus_5})
        result["sets"][set_def.name] = {
            "count": count,
            "pieces": player_set_pieces.get(set_id, []),
            "bonuses": bonuses,
            "max_bonus": set_def.set_bonus_5 if count >= 5 else (set_def.set_bonus_3 if count >= 3 else (set_def.set_bonus_2 if count >= 2 else "")),
        }
        if count >= 2:
            result["total_bonus"]["hp"] = result["total_bonus"].get("hp", 0) + set_def.set_hp_bonus // 2
            result["total_bonus"]["attack"] = result["total_bonus"].get("attack", 0) + set_def.set_attack_bonus // 3
            result["total_bonus"]["defense"] = result["total_bonus"].get("defense", 0) + set_def.set_defense_bonus // 3
    return result


def get_boss_by_faction(faction: int) -> Optional[LegendaryBoss]:
    for boss in LEGENDARY_BOSSES.values():
        if boss.faction == faction:
            return boss
    return None


def get_all_bosses() -> list[LegendaryBoss]:
    return list(LEGENDARY_BOSSES.values())


def get_all_sets() -> list[LegendarySet]:
    return list(LEGENDARY_SETS.values())


def can_legendary_boss_respawn(boss_id: str) -> bool:
    return legendary_boss_manager.can_boss_respawn(boss_id)


def try_respawn_legendary_boss(boss_id: str, player_max_level: int = 20) -> bool:
    return legendary_boss_manager.spawn_boss_with_growth(boss_id, player_max_level)


def is_legendary_boss_alive(boss_id: str) -> bool:
    return legendary_boss_manager.is_boss_alive(boss_id)


def get_legendary_drops(user_id: str, boss_id: str) -> list[str]:
    return legendary_boss_manager.generate_drops(user_id, boss_id)


def get_boss_status(boss_id: str) -> dict:
    boss = LEGENDARY_BOSSES.get(boss_id)
    if not boss:
        return {}
    is_alive = legendary_boss_manager.is_boss_alive(boss_id)
    can_respawn = legendary_boss_manager.can_boss_respawn(boss_id)
    set_info = LEGENDARY_SETS.get(boss.set_type)
    dynamic_state = legendary_boss_manager.get_boss_dynamic_state(boss_id)
    if dynamic_state:
        level = dynamic_state.get("level", boss.level)
        hp = dynamic_state.get("hp", boss.hp) if is_alive else 0
        max_hp = dynamic_state.get("max_hp", boss.hp)
        attack = dynamic_state.get("attack", boss.attack)
        defense = dynamic_state.get("defense", boss.defense)
    else:
        level = boss.level
        hp = boss.hp if is_alive else 0
        max_hp = boss.hp
        attack = boss.attack
        defense = boss.defense
    return {
        "boss_id": boss_id,
        "name": boss.name,
        "title": boss.title,
        "icon": boss.icon,
        "is_alive": is_alive,
        "can_respawn": can_respawn,
        "level": level,
        "hp": hp,
        "max_hp": max_hp,
        "attack": attack,
        "defense": defense,
        "set_name": set_info.name if set_info else "",
    }


def get_all_boss_status() -> list[dict]:
    return [get_boss_status(boss_id) for boss_id in LEGENDARY_BOSSES.keys()]


def get_boss_growth_info(player_max_level: int) -> dict:
    return calculate_boss_stats(player_max_level)
