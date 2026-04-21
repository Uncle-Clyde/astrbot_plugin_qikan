"""
城市任务管理器 - 封装城市任务数据持久化

玩家通过城镇镇长接取任务，完成任务后获得奖励
"""

from __future__ import annotations

import time
from typing import Optional

from . import city_quest_system as cqs


class CityQuestManager:
    """管理城市任务的接受、进度跟踪和完成"""

    def __init__(self, data_manager):
        self._dm = data_manager
        self._schema_initialized = False

    async def initialize(self):
        """初始化数据库表"""
        await self._ensure_schema()
        self._schema_initialized = True

    async def _ensure_schema(self):
        """确保城市任务表存在"""
        if self._schema_initialized:
            return
        
        await self._dm.db.execute("""
            CREATE TABLE IF NOT EXISTS city_quests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quest_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                location_id TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                progress INTEGER DEFAULT 0,
                started_at REAL NOT NULL,
                expires_at REAL DEFAULT 0,
                UNIQUE(quest_id, user_id)
            )
        """)
        await self._dm.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_city_quests_user 
            ON city_quests(user_id, status)
        """)
        await self._dm.db.commit()
        self._schema_initialized = True

    async def get_available_quests(
        self, 
        location_id: str, 
        player_level: int, 
        player_realm: int
    ) -> list[dict]:
        """获取指定城镇可用的任务列表"""
        return cqs.get_available_quests(location_id, player_level, player_realm)

    async def accept_quest(
        self, 
        user_id: str, 
        quest_id: str, 
        location_id: str,
        expires_hours: int = 24
    ) -> bool:
        """接受城市任务"""
        await self._ensure_schema()
        
        now = time.time()
        expires_at = now + expires_hours * 3600
        
        try:
            await self._dm.db.execute(
                """INSERT OR REPLACE INTO city_quests 
                   (quest_id, user_id, location_id, status, progress, started_at, expires_at)
                   VALUES (?, ?, ?, 'active', 0, ?, ?)""",
                (quest_id, user_id, location_id, now, expires_at),
            )
            await self._dm.db.commit()
            return True
        except Exception:
            return False

    async def get_active_quests(self, user_id: str) -> list[dict]:
        """获取玩家当前进行的城市任务"""
        await self._ensure_schema()
        
        now = time.time()
        cur = await self._dm.db.execute(
            """SELECT quest_id, location_id, progress, started_at, expires_at 
               FROM city_quests 
               WHERE user_id = ? AND status = 'active' 
               AND (expires_at = 0 OR expires_at > ?)
               ORDER BY started_at DESC""",
            (user_id, now),
        )
        rows = await cur.fetchall()
        
        result = []
        for r in rows:
            quest_id = r[0]
            location_id = r[1]
            location = cqs.TOWNS.get(location_id) if location_id else None
            
            quest = cqs.get_available_quests(
                location_id, 1, 0
            )
            quest_def = None
            for q in quest:
                if q["quest_id"] == quest_id:
                    quest_def = q
                    break
            
            if quest_def:
                result.append({
                    "quest_id": quest_id,
                    "location_id": location_id,
                    "location_name": location.name if location else location_id,
                    "progress": r[2],
                    "target_count": quest_def.get("target_count", 1),
                    "started_at": r[3],
                    "expires_at": r[4],
                    "name": quest_def.get("name", ""),
                    "description": quest_def.get("description", ""),
                    "exp_reward": quest_def.get("exp_reward", 0),
                    "gold_reward": quest_def.get("gold_reward", 0),
                    "quest_type": quest_def.get("quest_type", ""),
                })
        
        return result

    async def update_progress(
        self, 
        user_id: str, 
        quest_id: str, 
        progress: int
    ) -> bool:
        """更新任务进度"""
        await self._ensure_schema()
        
        try:
            await self._dm.db.execute(
                """UPDATE city_quests SET progress = ? 
                   WHERE quest_id = ? AND user_id = ? AND status = 'active'""",
                (progress, quest_id, user_id),
            )
            await self._dm.db.commit()
            return True
        except Exception:
            return False

    async def increment_progress(
        self, 
        user_id: str, 
        quest_id: str, 
        increment: int = 1
    ) -> dict:
        """增加任务进度"""
        await self._ensure_schema()
        
        cur = await self._dm.db.execute(
            """SELECT progress FROM city_quests 
               WHERE quest_id = ? AND user_id = ? AND status = 'active'""",
            (quest_id, user_id),
        )
        row = await cur.fetchone()
        
        if not row:
            return {"success": False, "message": "任务不存在或已完成"}
        
        current = row[0]
        new_progress = current + increment
        
        await self._dm.db.execute(
            """UPDATE city_quests SET progress = ? 
               WHERE quest_id = ? AND user_id = ?""",
            (new_progress, quest_id, user_id),
        )
        await self._dm.db.commit()
        
        return {"success": True, "progress": new_progress}

    async def complete_quest(
        self, 
        user_id: str, 
        quest_id: str,
        exp_reward: int = 0,
        gold_reward: int = 0
    ) -> dict | None:
        """完成任务并发放奖励"""
        await self._ensure_schema()
        
        cur = await self._dm.db.execute(
            """SELECT quest_id FROM city_quests 
               WHERE quest_id = ? AND user_id = ? AND status = 'active'""",
            (quest_id, user_id),
        )
        row = await cur.fetchone()
        
        if not row:
            return None
        
        now = time.time()
        await self._dm.db.execute(
            """UPDATE city_quests SET status = 'completed', progress = target_count 
               WHERE quest_id = ? AND user_id = ?""",
            (quest_id, user_id),
        )
        
        await self._dm.db.execute(
            """INSERT INTO city_quests (quest_id, user_id, location_id, status, progress, started_at, expires_at)
               SELECT quest_id, user_id, location_id, 'completed', progress, started_at, ?
               FROM city_quests WHERE quest_id = ? AND user_id = ?""",
            (now, quest_id, user_id),
        )
        await self._dm.db.commit()
        
        return {
            "quest_id": quest_id,
            "exp_reward": exp_reward,
            "gold_reward": gold_reward,
        }

    async def get_quest_history(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> list[dict]:
        """获取玩家完成任务历史"""
        await self._ensure_schema()
        
        cur = await self._dm.db.execute(
            """SELECT quest_id, location_id, progress, started_at, expires_at 
               FROM city_quests 
               WHERE user_id = ? AND status = 'completed'
               ORDER BY started_at DESC LIMIT ?""",
            (user_id, limit),
        )
        rows = await cur.fetchall()
        
        return [{"quest_id": r[0], "location_id": r[1]} for r in rows]

    async def abandon_quest(
        self, 
        user_id: str, 
        quest_id: str
    ) -> bool:
        """放弃任务"""
        await self._ensure_schema()
        
        try:
            await self._dm.db.execute(
                """UPDATE city_quests SET status = 'abandoned' 
                   WHERE quest_id = ? AND user_id = ? AND status = 'active'""",
                (quest_id, user_id),
            )
            await self._dm.db.commit()
            return True
        except Exception:
            return False