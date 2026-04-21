"""
传奇BOSS管理器 - 封装传奇BOSS数据持久化和装备掉落

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

import time
import random
from typing import Optional

from . import legendary_system as ls
from .constants import (
    EQUIPMENT_REGISTRY, EquipmentTier,
    _LEGENDARY_VIKING, _LEGENDARY_NOMAD, _LEGENDARY_FOREST, 
    _LEGENDARY_MOUNTAIN, _LEGENDARY_LORD,
)


_SET_PIECES_MAP = {
    1: [e.equip_id for e in _LEGENDARY_VIKING],
    2: [e.equip_id for e in _LEGENDARY_NOMAD],
    3: [e.equip_id for e in _LEGENDARY_FOREST],
    4: [e.equip_id for e in _LEGENDARY_MOUNTAIN],
    5: [e.equip_id for e in _LEGENDARY_LORD],
}

_SET_NAMES = {
    1: "海盗王套装",
    2: "响马王套装",
    3: "绿林王套装",
    4: "山贼王套装",
    5: "盗圣套装",
}


class LegendaryManager:
    """管理传奇BOSS状态和玩家掉落"""

    def __init__(self, data_manager):
        self._dm = data_manager
        self._schema_initialized = False

    async def initialize(self):
        """初始化数据库表"""
        await self._ensure_schema()
        self._schema_initialized = True

    async def _ensure_schema(self):
        """确保传奇BOSS相关表存在"""
        if self._schema_initialized:
            return
        
        await self._dm.db.execute("""
            CREATE TABLE IF NOT EXISTS legendary_boss_state (
                boss_id TEXT PRIMARY KEY,
                last_respawn REAL DEFAULT 0,
                respawn_count INTEGER DEFAULT 0,
                week_start REAL DEFAULT 0,
                is_alive INTEGER DEFAULT 0,
                hp INTEGER DEFAULT 0,
                max_hp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 30
            )
        """)
        
        await self._dm.db.execute("""
            CREATE TABLE IF NOT EXISTS legendary_player_drops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                boss_id TEXT NOT NULL,
                piece_id TEXT NOT NULL,
                obtained_at REAL NOT NULL,
                UNIQUE(user_id, boss_id, piece_id)
            )
        """)
        
        await self._dm.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_legendary_drops_user 
            ON legendary_player_drops(user_id)
        """)
        
        await self._dm.db.commit()
        self._schema_initialized = True

    async def get_all_bosses_status(self) -> list[dict]:
        """获取所有BOSS状态"""
        await self._ensure_schema()
        
        cur = await self._dm.db.execute(
            "SELECT boss_id, last_respawn, respawn_count, is_alive, hp, max_hp, level FROM legendary_boss_state"
        )
        rows = await cur.fetchall()
        saved_states = {r[0]: {
            "last_respawn": r[1],
            "respawn_count": r[2],
            "is_alive": bool(r[3]),
            "hp": r[4],
            "max_hp": r[5],
            "level": r[6],
        } for r in rows}
        
        bosses = []
        for boss_id in ls.LEGENDARY_BOSSES:
            boss_def = ls.LEGENDARY_BOSSES.get(boss_id)
            saved = saved_states.get(boss_id, {})
            
            can_respawn = ls.can_legendary_boss_respawn(boss_id)
            is_alive = ls.is_legendary_boss_alive(boss_id)
            
            hp = saved.get("hp", boss_def.hp if is_alive else 0)
            max_hp = saved.get("max_hp", boss_def.hp)
            level = saved.get("level", boss_def.level)
            
            set_info = ls.LEGENDARY_SETS.get(boss_def.set_type)
            
            bosses.append({
                "boss_id": boss_id,
                "name": boss_def.name,
                "title": boss_def.title,
                "icon": boss_def.icon,
                "description": boss_def.description,
                "is_alive": is_alive,
                "can_respawn": can_respawn,
                "level": level,
                "hp": hp,
                "max_hp": max_hp,
                "attack": boss_def.attack,
                "defense": boss_def.defense,
                "bounty_gold": boss_def.bounty_gold,
                "bounty_exp": boss_def.bounty_exp,
                "set_type": boss_def.set_type,
                "set_name": set_info.name if set_info else "",
            })
        
        return bosses

    async def get_boss_status(self, boss_id: str) -> dict | None:
        """获取单个BOSS状态"""
        bosses = await self.get_all_bosses_status()
        for b in bosses:
            if b["boss_id"] == boss_id:
                return b
        return None

    async def try_spawn_boss(self, boss_id: str, player_max_level: int = 20) -> dict:
        """尝试生成BOSS"""
        if not ls.can_legendary_boss_respawn(boss_id):
            return {"success": False, "message": "BOSS尚未到达刷新时间（每周三/周日）"}
        
        stats = ls.calculate_boss_stats(player_max_level)
        
        await self._dm.db.execute("""
            INSERT OR REPLACE INTO legendary_boss_state 
            (boss_id, last_respawn, respawn_count, is_alive, hp, max_hp, level, week_start)
            VALUES (?, ?, COALESCE((SELECT respawn_count FROM legendary_boss_state WHERE boss_id = ?), 0) + 1, 1, ?, ?, ?, ?)
        """, (
            boss_id, time.time(), boss_id,
            stats["hp"], stats["hp"], stats["level"], 
            self._get_week_start(time.time())
        ))
        
        await self._dm.db.commit()
        
        return {
            "success": True,
            "message": f"{ls.LEGENDARY_BOSSES[boss_id].name} 已出现！",
            "level": stats["level"],
            "hp": stats["hp"],
        }

    def _get_week_start(self, timestamp: float) -> float:
        """获取周一开始的时间戳"""
        import time as time_module
        tm = time_module.localtime(timestamp)
        days_since_monday = tm.tm_wday
        return timestamp - days_since_monday * 86400 - tm.tm_hour * 3600 - tm.tm_min * 60 - tm.tm_sec

    async def get_player_drops(self, user_id: str) -> dict:
        """获取玩家已获得的传奇装备"""
        await self._ensure_schema()
        
        cur = await self._dm.db.execute(
            "SELECT boss_id, piece_id, obtained_at FROM legendary_player_drops WHERE user_id = ?",
            (user_id,),
        )
        rows = await cur.fetchall()
        
        drops_by_boss = {}
        all_pieces = []
        
        for row in rows:
            boss_id = row[0]
            piece_id = row[1]
            obtained_at = row[2]
            
            if boss_id not in drops_by_boss:
                drops_by_boss[boss_id] = []
            
            boss_def = ls.LEGENDARY_BOSSES.get(boss_id)
            set_def = ls.LEGENDARY_SETS.get(boss_def.set_type) if boss_def else None
            
            eq = EQUIPMENT_REGISTRY.get(piece_id)
            drops_by_boss[boss_id].append({
                "piece_id": piece_id,
                "name": eq.name if eq else piece_id,
                "slot": eq.slot if eq else "",
                "obtained_at": obtained_at,
            })
            all_pieces.append(piece_id)
        
        return drops_by_boss, all_pieces

    async def generate_drops(self, user_id: str, boss_id: str) -> list[dict]:
        """生成BOSS掉落"""
        boss_def = ls.LEGENDARY_BOSSES.get(boss_id)
        if not boss_def:
            return []
        
        set_type = boss_def.set_type
        available_pieces = _SET_PIECES_MAP.get(set_type, [])
        
        existing = await self.get_player_drops(user_id)
        existing_by_boss = existing[0].get(boss_id, [])
        existing_ids = [p["piece_id"] for p in existing_by_boss]
        
        available = [p for p in available_pieces if p not in existing_ids]
        if not available:
            return []
        
        drop_count = random.randint(boss_def.drop_count_min, boss_def.drop_count_max)
        drop_count = min(drop_count, len(available))
        
        drops = random.sample(available, drop_count)
        now = time.time()
        
        for piece_id in drops:
            try:
                await self._dm.db.execute(
                    """INSERT INTO legendary_player_drops 
                       (user_id, boss_id, piece_id, obtained_at)
                       VALUES (?, ?, ?, ?)""",
                    (user_id, boss_id, piece_id, now),
                )
            except Exception:
                pass
        
        await self._dm.db.commit()
        
        result = []
        for piece_id in drops:
            eq = EQUIPMENT_REGISTRY.get(piece_id)
            result.append({
                "piece_id": piece_id,
                "name": eq.name if eq else piece_id,
                "slot": eq.slot if eq else "",
                "tier": "LEGENDARY",
                "attack": eq.attack if eq else 0,
                "defense": eq.defense if eq else 0,
                "hp": eq.hp if eq else 0,
                "description": eq.description if eq else "",
            })
        
        return result

    async def check_set_bonus(self, user_id: str) -> dict:
        """检查玩家套装加成"""
        drops_by_boss, all_pieces = await self.get_player_drops(user_id)
        
        result = {"sets": {}, "total_bonus": {}}
        
        for set_type, set_pieces in _SET_PIECES_MAP.items():
            count = sum(1 for p in set_pieces if p in all_pieces)
            if count == 0:
                continue
            
            set_def = ls.LEGENDARY_SETS.get(set_type)
            if not set_def:
                continue
            
            bonuses = []
            if count >= 2:
                bonuses.append({"pieces": 2, "effect": set_def.set_bonus_2})
            if count >= 3:
                bonuses.append({"pieces": 3, "effect": set_def.set_bonus_3})
            if count >= 5:
                bonuses.append({"pieces": 5, "effect": set_def.set_bonus_5})
            
            player_pieces = []
            for piece_id in set_pieces:
                if piece_id in all_pieces:
                    eq = EQUIPMENT_REGISTRY.get(piece_id)
                    player_pieces.append({
                        "piece_id": piece_id,
                        "name": eq.name if eq else piece_id,
                    })
            
            result["sets"][set_def.name] = {
                "set_id": set_type,
                "count": count,
                "pieces": player_pieces,
                "bonuses": bonuses,
                "max_bonus": set_def.set_bonus_5 if count >= 5 else (
                    set_def.set_bonus_3 if count >= 3 else (
                        set_def.set_bonus_2 if count >= 2 else ""
                    )
                ),
            }
            
            if count >= 2:
                result["total_bonus"]["hp"] = result["total_bonus"].get("hp", 0) + set_def.set_hp_bonus // 2
                result["total_bonus"]["attack"] = result["total_bonus"].get("attack", 0) + set_def.set_attack_bonus // 3
                result["total_bonus"]["defense"] = result["total_bonus"].get("defense", 0) + set_def.set_defense_bonus // 3
        
        return result

    async def get_player_collection_summary(self, user_id: str) -> dict:
        """获取玩家收藏汇总"""
        drops_by_boss, all_pieces = await self.get_player_drops(user_id)
        
        total_sets = 0
        complete_sets = 0
        set_details = []
        
        for set_type, set_pieces in _SET_PIECES_MAP.items():
            count = sum(1 for p in set_pieces if p in all_pieces)
            set_def = ls.LEGENDARY_SETS.get(set_type)
            if set_def:
                set_name = _SET_NAMES.get(set_type, f"套装{set_type}")
                is_complete = count >= 5
                if count > 0:
                    total_sets += 1
                if is_complete:
                    complete_sets += 1
                
                set_details.append({
                    "set_type": set_type,
                    "set_name": set_name,
                    "count": count,
                    "is_complete": is_complete,
                })
        
        return {
            "total_pieces": len(all_pieces),
            "total_sets": total_sets,
            "complete_sets": complete_sets,
            "sets": set_details,
        }

    async def get_server_max_level(self) -> int:
        """获取服务器最高玩家等级"""
        players = self._dm._players if hasattr(self._dm, '_players') else {}
        if not players:
            return 20
        
        max_level = 20
        for player in players.values():
            level = getattr(player, 'level', 1)
            if level > max_level:
                max_level = level
        
        return max_level