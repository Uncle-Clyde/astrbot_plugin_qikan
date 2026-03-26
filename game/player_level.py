"""
骑砍风格等级与属性系统

替代原有的爵位晋升系统，采用更直观的等级+属性点模式。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


MAX_LEVEL = 100

LEVEL_CONFIG: dict[int, dict] = {}

for level in range(1, MAX_LEVEL + 1):
    base_exp = 100
    if level <= 10:
        exp_needed = base_exp + (level - 1) * 50
    elif level <= 20:
        exp_needed = base_exp + 450 + (level - 10) * 100
    elif level <= 40:
        exp_needed = base_exp + 1450 + (level - 20) * 150
    elif level <= 60:
        exp_needed = base_exp + 4450 + (level - 40) * 250
    elif level <= 80:
        exp_needed = base_exp + 9450 + (level - 60) * 400
    else:
        exp_needed = base_exp + 17450 + (level - 80) * 600
    
    LEVEL_CONFIG[level] = {
        "exp_to_next": exp_needed,
        "attribute_points": 2 if level <= 50 else 1,  # 50级前每级2点，50级后每级1点
        "hp_bonus": 10 + level * 2,
        "attack_bonus": 1 + level // 10,
        "defense_bonus": 1 + level // 15,
    }


def get_level_config(level: int) -> dict:
    """获取指定等级的配置。"""
    if level < 1:
        level = 1
    if level > MAX_LEVEL:
        level = MAX_LEVEL
    return LEVEL_CONFIG[level]


def calculate_total_exp_for_level(target_level: int) -> int:
    """计算升到指定等级需要的总经验。"""
    total = 0
    for lvl in range(1, target_level):
        total += LEVEL_CONFIG[lvl]["exp_to_next"]
    return total


@dataclass
class AttributeStats:
    """玩家属性点分配。"""
    strength: int = 0      # 力量 - 影响攻击力
    agility: int = 0       # 敏捷 - 影响防御和闪避
    vitality: int = 0      # 活力 - 影响生命值
    leadership: int = 0    # 统御 - 影响队伍加成
    
    def get_attack_bonus(self) -> int:
        """力量加成：每点力量+2攻击"""
        return self.strength * 2
    
    def get_defense_bonus(self) -> int:
        """敏捷加成：每点敏捷+1防御"""
        return self.agility * 1
    
    def get_hp_bonus(self) -> int:
        """活力加成：每点活力+20生命"""
        return self.vitality * 20
    
    def get_leadership_bonus(self) -> float:
        """统御加成：每点统御+5%队伍属性"""
        return self.leadership * 0.05
    
    def total_points(self) -> int:
        """已分配的属性点总数"""
        return self.strength + self.agility + self.vitality + self.leadership
    
    def to_dict(self) -> dict:
        return {
            "strength": self.strength,
            "agility": self.agility,
            "vitality": self.vitality,
            "leadership": self.leadership,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AttributeStats":
        return cls(
            strength=data.get("strength", 0),
            agility=data.get("agility", 0),
            vitality=data.get("vitality", 0),
            leadership=data.get("leadership", 0),
        )


class TitleManager:
    """称号管理器 - 管理员自定义称号"""
    
    def __init__(self):
        self._titles: dict[str, dict] = {}
        self._player_titles: dict[str, str] = {}  # user_id -> title_id
        self._next_id = 1
    
    def create_title(
        self,
        name: str,
        description: str = "",
        attack_bonus: int = 0,
        defense_bonus: int = 0,
        hp_bonus: int = 0,
        exp_bonus: float = 0,
        gold_bonus: float = 0,
    ) -> dict:
        """创建新称号"""
        title_id = f"title_{self._next_id}"
        self._next_id += 1
        
        self._titles[title_id] = {
            "id": title_id,
            "name": name,
            "description": description,
            "attack_bonus": attack_bonus,
            "defense_bonus": defense_bonus,
            "hp_bonus": hp_bonus,
            "exp_bonus": exp_bonus,
            "gold_bonus": gold_bonus,
            "created_at": time.time(),
        }
        
        return self._titles[title_id]
    
    def get_title(self, title_id: str) -> Optional[dict]:
        """获取称号"""
        return self._titles.get(title_id)
    
    def get_all_titles(self) -> list[dict]:
        """获取所有称号"""
        return list(self._titles.values())
    
    def delete_title(self, title_id: str) -> bool:
        """删除称号"""
        if title_id not in self._titles:
            return False
        
        # 移除所有使用该称号的玩家
        for uid, tid in list(self._player_titles.items()):
            if tid == title_id:
                del self._player_titles[uid]
        
        del self._titles[title_id]
        return True
    
    def assign_title(self, user_id: str, title_id: str) -> bool:
        """分配称号给玩家"""
        if title_id not in self._titles:
            return False
        self._player_titles[user_id] = title_id
        return True
    
    def remove_title(self, user_id: str) -> bool:
        """移除玩家称号"""
        if user_id in self._player_titles:
            del self._player_titles[user_id]
            return True
        return False
    
    def get_player_title(self, user_id: str) -> Optional[dict]:
        """获取玩家当前称号"""
        title_id = self._player_titles.get(user_id)
        if title_id:
            return self._titles.get(title_id)
        return None
    
    def to_dict(self) -> dict:
        return {
            "titles": self._titles,
            "player_titles": self._player_titles,
            "next_id": self._next_id,
        }
    
    def from_dict(self, data: dict):
        self._titles = data.get("titles", {})
        self._player_titles = data.get("player_titles", {})
        self._next_id = data.get("next_id", 1)


_title_manager: TitleManager | None = None


def get_title_manager() -> TitleManager:
    global _title_manager
    if _title_manager is None:
        _title_manager = TitleManager()
    return _title_manager


def init_title_system():
    """初始化默认称号"""
    manager = get_title_manager()
    if not manager._titles:
        default_titles = [
            ("骑士", "基础骑士称号", 5, 3, 50, 0, 0),
            ("骑士长", "精英骑士称号", 10, 6, 100, 0.05, 0.05),
            ("男爵", "贵族称号", 15, 10, 150, 0.1, 0.1),
            ("子爵", "高级贵族称号", 20, 15, 200, 0.15, 0.15),
            ("伯爵", "大贵族称号", 30, 20, 300, 0.2, 0.2),
            ("侯爵", "皇室成员称号", 40, 25, 400, 0.25, 0.25),
            ("公爵", "大公爵称号", 50, 30, 500, 0.3, 0.3),
            ("领主", "领主称号", 60, 40, 600, 0.35, 0.35),
            ("大将军", "军队统帅称号", 80, 50, 800, 0.4, 0.4),
            ("国王", "一国之君称号", 100, 60, 1000, 0.5, 0.5),
            ("传奇", "传奇勇士称号", 150, 80, 1500, 0.6, 0.6),
            ("神话", "超越凡人的存在", 200, 100, 2000, 0.8, 0.8),
        ]
        
        for name, desc, atk, defense, hp, exp_b, gold_b in default_titles:
            manager.create_title(name, desc, atk, defense, hp, exp_b, gold_b)


class LevelSystem:
    """等级系统 - 处理升级逻辑"""
    
    @staticmethod
    def check_level_up(player: "Player") -> dict | None:
        """检查是否可以升级，返回升级信息或None"""
        level = player.level
        if level >= MAX_LEVEL:
            return None
        
        config = get_level_config(level)
        exp_needed = config["exp_to_next"]
        
        if player.exp >= exp_needed:
            player.exp -= exp_needed
            player.level += 1
            player.unallocated_points += config["attribute_points"]
            
            # 重新计算属性
            LevelSystem.recalculate_stats(player)
            
            return {
                "leveled_up": True,
                "new_level": player.level,
                "points_gained": config["attribute_points"],
                "total_points": player.unallocated_points,
            }
        
        return None
    
    @staticmethod
    def recalculate_stats(player: "Player"):
        """重新计算玩家属性"""
        level = player.level
        config = get_level_config(level)
        
        base_hp = 100
        base_atk = 10
        base_def = 5
        
        level_hp = config["hp_bonus"]
        level_atk = config["attack_bonus"]
        level_def = config["defense_bonus"]
        
        attr = player.attributes
        
        player.max_hp = base_hp + level_hp + attr.get_hp_bonus() + player.permanent_max_hp_bonus
        player.attack = base_atk + level_atk + attr.get_attack_bonus() + player.permanent_attack_bonus
        player.defense = base_def + level_def + attr.get_defense_bonus() + player.permanent_defense_bonus
        
        if player.hp > player.max_hp:
            player.hp = player.max_hp
    
    @staticmethod
    def allocate_point(player: "Player", attr_type: str) -> dict:
        """分配属性点"""
        if player.unallocated_points <= 0:
            return {"success": False, "message": "没有可分配的属性点"}
        
        attr_type = attr_type.lower()
        if attr_type in ("str", "strength", "力量"):
            player.attributes.strength += 1
        elif attr_type in ("agi", "agility", "敏捷"):
            player.attributes.agility += 1
        elif attr_type in ("vit", "vitality", "活力"):
            player.attributes.vitality += 1
        elif attr_type in ("lead", "leadership", "统御"):
            player.attributes.leadership += 1
        else:
            return {"success": False, "message": f"无效的属性类型: {attr_type}"}
        
        player.unallocated_points -= 1
        LevelSystem.recalculate_stats(player)
        
        return {
            "success": True,
            "message": f"分配成功！剩余 {player.unallocated_points} 点",
            "points_left": player.unallocated_points,
            "attributes": player.attributes.to_dict(),
        }
    
    @staticmethod
    def add_exp(player: "Player", amount: float) -> list[dict]:
        """添加经验值，可能触发多次升级"""
        title = get_title_manager().get_player_title(player.user_id)
        exp_multiplier = 1.0
        if title:
            exp_multiplier += title.get("exp_bonus", 0)
        
        actual_exp = int(amount * exp_multiplier)
        player.exp += actual_exp
        
        results = []
        while True:
            result = LevelSystem.check_level_up(player)
            if result:
                results.append(result)
            else:
                break
        
        return results
    
    @staticmethod
    def get_exp_progress(player: "Player") -> dict:
        """获取当前升级进度"""
        if player.level >= MAX_LEVEL:
            return {
                "level": player.level,
                "exp": 0,
                "exp_to_next": 0,
                "progress": 100,
                "is_max_level": True,
            }
        
        config = get_level_config(player.level)
        exp_to_next = config["exp_to_next"]
        progress = (player.exp / exp_to_next) * 100 if exp_to_next > 0 else 0
        
        return {
            "level": player.level,
            "exp": player.exp,
            "exp_to_next": exp_to_next,
            "progress": min(100, progress),
            "is_max_level": False,
        }


_title_system_initialized = False


def init_level_system():
    """初始化等级系统"""
    global _title_system_initialized
    if not _title_system_initialized:
        init_title_system()
        _title_system_initialized = True
