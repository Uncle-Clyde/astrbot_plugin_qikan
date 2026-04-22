"""数据持久化管理：SQLite 数据库存储。"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import shutil
import time
from datetime import datetime
from typing import Optional, Any

import aiosqlite

from .models import Player

logger = logging.getLogger(__name__)

# 用于 _alter_add_column 的标识符和类型安全校验
_SAFE_IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
# DEFAULT 值仅允许：数字/小数、单引号字符串（内部无引号）、NULL
_SAFE_COL_TYPE = re.compile(
    r"^[A-Z ]+(?:\(\d+\))?"
    r"(?:\s+DEFAULT\s+(?:-?\d+(?:\.\d+)?|'[^']*'|NULL))?$",
    re.I,
)

# 玩家表所有列（与 Player 字段一一对应）
_PLAYER_COLUMNS = [
    "user_id", "name", "realm", "sub_realm", "exp",
    "hp", "max_hp", "attack", "defense", "spirit_stones",
    "lingqi", "permanent_max_hp_bonus", "permanent_attack_bonus",
    "permanent_defense_bonus", "permanent_lingqi_bonus",
    "heart_method", "weapon", "gongfa_1", "gongfa_2", "gongfa_3",
    "head", "body", "hands", "legs", "shoulders", "accessory1", "accessory2",
    "dao_yun",
    "breakthrough_bonus", "breakthrough_pill_count",
    "heart_method_mastery", "heart_method_exp", "heart_method_value", "stored_heart_methods",
    "gongfa_1_mastery", "gongfa_1_exp",
    "gongfa_2_mastery", "gongfa_2_exp",
    "gongfa_3_mastery", "gongfa_3_exp",
    "inventory", "active_buffs", "created_at", "last_cultivate_time",
    "last_checkin_date", "afk_cultivate_start", "afk_cultivate_end",
    "last_adventure_time", "death_count", "unified_msg_origin", "password_hash",
    "level", "unallocated_points", "bandit_stats",
]


class DataManager:
    """管理玩家数据的加载和保存（SQLite）。"""

    def __init__(self, data_dir: str):
        self._data_dir = data_dir
        self._db_path = os.path.join(data_dir, "qikan.db")
        self.db: Optional[aiosqlite.Connection] = None
        self._shop_purchase_lock = asyncio.Lock()
        self._sect_schema_checked = False
        self._db_lock = asyncio.Lock()
        self._warehouse_lock = asyncio.Lock()

    @staticmethod
    async def _retry_db_op(db_path, ops_fn, *, max_retries=8, base_delay=0.15):
        """在独立连接上执行可重试的数据库操作序列。"""
        last_exc = None
        for attempt in range(max_retries + 1):
            conn = await aiosqlite.connect(db_path, timeout=60.0)
            try:
                conn.row_factory = aiosqlite.Row
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA busy_timeout=60000")
                await conn.execute("BEGIN IMMEDIATE")

                result = await ops_fn(conn)

                if not getattr(result, "_rollback", False):
                    await conn.commit()
                return getattr(result, "data", None)
            except aiosqlite.OperationalError as exc:
                msg = str(exc).lower()
                if "database is locked" in msg or "busy" in msg:
                    last_exc = exc
                    delay = base_delay * (2 ** attempt) + 0.05
                    await asyncio.sleep(delay)
                else:
                    raise
            finally:
                try:
                    await conn.close()
                except Exception:
                    pass

        logger.warning("数据库忙/锁定超时（已重试 %d 次）", max_retries)
        raise aiosqlite.OperationalError(
            f"database is locked (retried {max_retries} times)"
        ) from last_exc if last_exc else None

    class TransactionAbort(Exception):
        """在事务上下文中主动中止，携带用户提示消息。"""
        pass

    @contextlib.asynccontextmanager
    async def transaction(self):
        """提供一个使用独立连接的数据库事务，异常时自动 rollback。

        独立连接确保事务内的操作与 self.db 上的普通写操作完全隔离，
        不会出现其他协程的写入被意外卷入事务的问题。

        用法::

            async with dm.transaction() as tx:
                await tx.execute("UPDATE ...", (...))
                await tx.execute("INSERT ...", (...))
            # 离开 with 块自动 commit；异常则自动 rollback
        """
        last_exc = None
        for attempt in range(8 + 1):
            conn = await aiosqlite.connect(self._db_path, timeout=60.0)
            try:
                conn.row_factory = aiosqlite.Row
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA busy_timeout=60000")
                await conn.execute("BEGIN IMMEDIATE")

                yield conn
                await conn.commit()
                return  # ← 成功后退出重试循环
            except self.TransactionAbort:
                raise
            except Exception as exc:
                await conn.rollback()
                if isinstance(exc, aiosqlite.OperationalError):
                    msg = str(exc).lower()
                    if "database is locked" in msg or "busy" in msg:
                        last_exc = exc
                        delay = 0.15 * (2 ** attempt) + 0.05
                        await asyncio.sleep(delay)
                        continue
                raise
            finally:
                try:
                    await conn.close()
                except Exception:
                    pass

        if last_exc is not None:
            logger.warning("事务操作锁定超时（已重试 %d 次）", 8)
            raise aiosqlite.OperationalError(
                f"database is locked (retried {8} times)"
            ) from last_exc

    async def initialize(self):
        """初始化数据目录、打开数据库、建表、迁移旧数据。"""
        async with self._db_lock:
            if self.db is not None:
                try:
                    await self.db.close()
                except Exception:
                    pass
            self.db = None
            os.makedirs(self._data_dir, exist_ok=True)

            db_dir = os.path.dirname(self._db_path)
            db_name = os.path.splitext(os.path.basename(self._db_path))[0]
            for suffix in (".wal", "-shm", "-journal"):
                wal_file = os.path.join(db_dir, db_name + suffix)
                try:
                    if os.path.exists(wal_file):
                        os.remove(wal_file)
                except Exception:
                    pass

            await asyncio.sleep(0.3)

            for attempt in range(10):
                try:
                    self.db = await aiosqlite.connect(self._db_path, timeout=60.0)
                    await self.db.execute("PRAGMA journal_mode=WAL")
                    await self.db.execute("PRAGMA busy_timeout=60000")
                    await self.db.execute("BEGIN IMMEDIATE")
                    await self.db.commit()
                    logger.info(f"骑砍英雄传：数据库连接成功（尝试 {attempt + 1}/10）")
                    break
                except aiosqlite.OperationalError as e:
                    msg = str(e).lower()
                    if "locked" in msg or "busy" in msg:
                        delay = 0.5 * (2 ** attempt) + 0.1 * attempt
                        logger.warning(f"骑砍英雄传：数据库被锁定，{delay:.1f}秒后重试（尝试 {attempt + 1}/10）: {e}")
                        await asyncio.sleep(delay)
                    else:
                        raise
            else:
                raise aiosqlite.OperationalError("无法打开数据库，已重试10次")

            self.db.row_factory = aiosqlite.Row
            await self.db.execute("PRAGMA read_uncommitted=1")
            await self._create_tables()
            await self._ensure_player_schema()
            await self._migrate_json_data()

    async def _create_tables(self):
        """创建数据库表。"""
        realms_table_exists = False
        async with self.db.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'realms' LIMIT 1"
        ) as cur:
            realms_table_exists = (await cur.fetchone()) is not None
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id             TEXT PRIMARY KEY,
                name                TEXT NOT NULL,
                realm               INTEGER DEFAULT 0,
                sub_realm           INTEGER DEFAULT 0,
                exp                 INTEGER DEFAULT 0,
                hp                  INTEGER DEFAULT 100,
                max_hp              INTEGER DEFAULT 100,
                attack              INTEGER DEFAULT 10,
                defense             INTEGER DEFAULT 5,
                spirit_stones       INTEGER DEFAULT 0,
                lingqi              INTEGER DEFAULT 50,
                permanent_max_hp_bonus INTEGER DEFAULT 0,
                permanent_attack_bonus INTEGER DEFAULT 0,
                permanent_defense_bonus INTEGER DEFAULT 0,
                permanent_lingqi_bonus INTEGER DEFAULT 0,
                heart_method        TEXT DEFAULT '无',
                weapon              TEXT DEFAULT '无',
                gongfa_1            TEXT DEFAULT '无',
                gongfa_2            TEXT DEFAULT '无',
                gongfa_3            TEXT DEFAULT '无',
                head                TEXT DEFAULT '无',
                body                TEXT DEFAULT '无',
                hands               TEXT DEFAULT '无',
                legs                TEXT DEFAULT '无',
                shoulders           TEXT DEFAULT '无',
                accessory1          TEXT DEFAULT '无',
                accessory2          TEXT DEFAULT '无',
                dao_yun             INTEGER DEFAULT 0,
                breakthrough_bonus  REAL DEFAULT 0.0,
                breakthrough_pill_count INTEGER DEFAULT 0,
                heart_method_mastery INTEGER DEFAULT 0,
                heart_method_exp    INTEGER DEFAULT 0,
                heart_method_value  INTEGER DEFAULT 0,
                stored_heart_methods TEXT DEFAULT '{}',
                inventory           TEXT DEFAULT '{}',
                active_buffs        TEXT DEFAULT '[]',
                created_at          REAL,
                last_cultivate_time REAL DEFAULT 0.0,
                last_checkin_date   TEXT,
                afk_cultivate_start REAL DEFAULT 0.0,
                afk_cultivate_end   REAL DEFAULT 0.0,
                last_adventure_time REAL DEFAULT 0.0,
                death_count         INTEGER DEFAULT 0,
                unified_msg_origin  TEXT,
                password_hash       TEXT,
                level             INTEGER DEFAULT 1,
                unallocated_points INTEGER DEFAULT 0,
                bandit_stats       TEXT DEFAULT '{}'
            )
        """)
        # 爵位配置表（管理员可维护）
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS realms (
                level             INTEGER PRIMARY KEY,
                name              TEXT NOT NULL,
                has_sub_realm     INTEGER DEFAULT 0,
                high_realm        INTEGER DEFAULT 0,
                exp_to_next       INTEGER DEFAULT 100,
                sub_exp_to_next   INTEGER DEFAULT 0,
                base_hp           INTEGER DEFAULT 100,
                base_attack       INTEGER DEFAULT 10,
                base_defense      INTEGER DEFAULT 5,
                base_lingqi       INTEGER DEFAULT 50,
                breakthrough_rate REAL DEFAULT 1.0,
                death_rate        REAL DEFAULT 0.0,
                sub_dao_yun_costs TEXT DEFAULT '',
                breakthrough_dao_yun_cost INTEGER DEFAULT 0
            )
        """)
        # 历练场景表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS adventure_scenes (
                id          INTEGER PRIMARY KEY,
                category    TEXT NOT NULL,
                name        TEXT NOT NULL,
                description TEXT NOT NULL
            )
        """)
        # 被动技能定义独立表（可在数据库中独立维护）
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS heart_methods (
                method_id       TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                realm           INTEGER NOT NULL,
                quality         INTEGER NOT NULL DEFAULT 0,
                exp_multiplier  REAL NOT NULL DEFAULT 0.0,
                attack_bonus    INTEGER NOT NULL DEFAULT 0,
                defense_bonus   INTEGER NOT NULL DEFAULT 0,
                dao_yun_rate    REAL NOT NULL DEFAULT 0.0,
                description     TEXT DEFAULT '',
                mastery_exp     INTEGER NOT NULL DEFAULT 100,
                enabled         INTEGER NOT NULL DEFAULT 1
            )
        """)
        # 武器/护甲定义独立表（管理员可维护）
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS weapons (
                equip_id         TEXT PRIMARY KEY,
                name             TEXT NOT NULL,
                tier             INTEGER NOT NULL,
                slot             TEXT NOT NULL,
                attack           INTEGER NOT NULL DEFAULT 0,
                defense          INTEGER NOT NULL DEFAULT 0,
                hp               INTEGER NOT NULL DEFAULT 0,
                element          TEXT DEFAULT '无',
                element_damage   INTEGER NOT NULL DEFAULT 0,
                description      TEXT DEFAULT '',
                enabled          INTEGER NOT NULL DEFAULT 1
            )
        """)
        # 坊市上架记录
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS market_listings (
                listing_id   TEXT PRIMARY KEY,
                seller_id    TEXT NOT NULL,
                item_id      TEXT NOT NULL,
                quantity     INTEGER NOT NULL,
                unit_price   INTEGER NOT NULL,
                total_price  INTEGER NOT NULL,
                fee          INTEGER NOT NULL,
                listed_at    REAL NOT NULL,
                expires_at   REAL NOT NULL,
                status       TEXT NOT NULL DEFAULT 'active',
                buyer_id     TEXT,
                sold_at      REAL
            )
        """)
        # 坊市成交记录（用于手续费计算）
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS market_history (
                history_id   TEXT PRIMARY KEY,
                item_id      TEXT NOT NULL,
                quantity     INTEGER NOT NULL,
                unit_price   INTEGER NOT NULL,
                total_price  INTEGER NOT NULL,
                fee          INTEGER NOT NULL,
                seller_id    TEXT NOT NULL,
                buyer_id     TEXT NOT NULL,
                sold_at      REAL NOT NULL
            )
        """)
        # 坊市索引
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_market_listings_status
            ON market_listings (status)
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_market_listings_seller
            ON market_listings (seller_id)
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_market_listings_expires
            ON market_listings (expires_at)
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_market_history_item
            ON market_history (item_id, sold_at)
        """)
        # 天机阁购买记录
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS shop_purchases (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      TEXT NOT NULL,
                item_id      TEXT NOT NULL,
                quantity     INTEGER NOT NULL DEFAULT 1,
                unit_price   INTEGER NOT NULL,
                purchased_at TEXT NOT NULL
            )
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_shop_date
            ON shop_purchases (purchased_at, item_id)
        """)
        # 公告表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT NOT NULL,
                content    TEXT NOT NULL,
                enabled    INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        # 关于页面表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS about_page (
                id         INTEGER PRIMARY KEY CHECK (id = 1),
                acknowledgements TEXT DEFAULT '',
                rules      TEXT DEFAULT '',
                updated_at TEXT NOT NULL
            )
        """)
        # 初始化关于页面（如果不存在）
        await self.db.execute("""
            INSERT OR IGNORE INTO about_page (id, acknowledgements, rules, updated_at)
            VALUES (1, '', '', datetime('now'))
        """)
        # 战技定义独立表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS gongfas (
                gongfa_id     TEXT PRIMARY KEY,
                name          TEXT NOT NULL,
                tier          INTEGER NOT NULL DEFAULT 0,
                attack_bonus  INTEGER DEFAULT 0,
                defense_bonus INTEGER DEFAULT 0,
                hp_regen      INTEGER DEFAULT 0,
                lingqi_regen  INTEGER DEFAULT 0,
                description   TEXT DEFAULT '',
                mastery_exp   INTEGER DEFAULT 200,
                dao_yun_cost  INTEGER DEFAULT 0,
                recycle_price INTEGER DEFAULT 1000,
                lingqi_cost   INTEGER DEFAULT 0,
                enabled       INTEGER DEFAULT 1
            )
        """)
        # 世界频道消息表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS world_chat_messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT NOT NULL,
                name       TEXT NOT NULL,
                realm      TEXT NOT NULL DEFAULT '',
                sect_name  TEXT NOT NULL DEFAULT '',
                sect_role  TEXT NOT NULL DEFAULT '',
                sect_role_name TEXT NOT NULL DEFAULT '',
                content    TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_world_chat_created
            ON world_chat_messages (created_at)
        """)
        # 家族主表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS sects (
                sect_id       TEXT PRIMARY KEY,
                name          TEXT NOT NULL UNIQUE,
                leader_id     TEXT NOT NULL,
                description   TEXT DEFAULT '',
                level         INTEGER DEFAULT 1,
                spirit_stones INTEGER DEFAULT 0,
                max_members   INTEGER DEFAULT 30,
                join_policy   TEXT DEFAULT 'open',
                min_realm     INTEGER DEFAULT 0,
                created_at    REAL NOT NULL,
                announcement  TEXT DEFAULT '',
                warehouse_capacity INTEGER DEFAULT 200
            )
        """)
        # 家族成员关系表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS sect_members (
                user_id   TEXT PRIMARY KEY,
                sect_id   TEXT NOT NULL,
                role      TEXT NOT NULL DEFAULT 'disciple',
                joined_at REAL NOT NULL,
                contribution_points INTEGER DEFAULT 0,
                FOREIGN KEY (sect_id) REFERENCES sects(sect_id)
            )
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_sect_members_sect
            ON sect_members (sect_id)
        """)
        # 家族申请表（预留）
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS sect_applications (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT NOT NULL,
                sect_id     TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'pending',
                applied_at  REAL NOT NULL,
                resolved_at REAL,
                resolved_by TEXT
            )
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_sect_applications_sect
            ON sect_applications (sect_id, status)
        """)
        # 家族仓库表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS sect_warehouse (
                sect_id   TEXT NOT NULL,
                item_id   TEXT NOT NULL,
                quantity  INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (sect_id, item_id),
                FOREIGN KEY (sect_id) REFERENCES sects(sect_id)
            )
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_sect_warehouse_sect
            ON sect_warehouse (sect_id)
        """)
        # 家族贡献点规则配置表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS sect_contribution_config (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                sect_id     TEXT NOT NULL,
                rule_type   TEXT NOT NULL,
                target_key  TEXT NOT NULL,
                points      INTEGER NOT NULL,
                UNIQUE(sect_id, rule_type, target_key),
                FOREIGN KEY (sect_id) REFERENCES sects(sect_id)
            )
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_sect_contrib_config_sect
            ON sect_contribution_config (sect_id)
        """)
        # 家族任务表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS sect_tasks (
                task_id         INTEGER PRIMARY KEY AUTOINCREMENT,
                sect_id         TEXT NOT NULL,
                creator_id      TEXT NOT NULL,
                title           TEXT NOT NULL,
                description     TEXT DEFAULT '',
                task_type       TEXT NOT NULL,
                target_count    INTEGER DEFAULT 1,
                current_count   INTEGER DEFAULT 0,
                reward_points  INTEGER DEFAULT 0,
                reward_item_id  TEXT DEFAULT '',
                reward_item_count INTEGER DEFAULT 0,
                status          TEXT DEFAULT 'active',
                created_at      REAL NOT NULL,
                expires_at      REAL DEFAULT 0,
                FOREIGN KEY (sect_id) REFERENCES sects(sect_id)
            )
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_sect_tasks_sect
            ON sect_tasks (sect_id, status)
        """)
        # 家族任务接受记录表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS sect_task_members (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id         INTEGER NOT NULL,
                user_id         TEXT NOT NULL,
                progress        INTEGER DEFAULT 0,
                status          TEXT DEFAULT 'accepted',
                accepted_at     REAL NOT NULL,
                completed_at    REAL DEFAULT 0,
                FOREIGN KEY (task_id) REFERENCES sect_tasks(task_id),
                UNIQUE(task_id, user_id)
            )
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_sect_task_members_task
            ON sect_task_members (task_id)
        """)
        # 音效配置表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS audio_config (
                id              INTEGER PRIMARY KEY CHECK (id = 1),
                enabled         INTEGER DEFAULT 0,
                music_enabled   INTEGER DEFAULT 0,
                sound_volume    REAL DEFAULT 0.7,
                music_volume    REAL DEFAULT 0.5,
                sound_coins    TEXT DEFAULT '',
                sound_button   TEXT DEFAULT '',
                sound_task     TEXT DEFAULT '',
                sound_equip    TEXT DEFAULT '',
                sound_attack   TEXT DEFAULT '',
                music_bgm      TEXT DEFAULT '',
                updated_at     TEXT NOT NULL
            )
        """)
        await self.db.execute("""
            INSERT OR IGNORE INTO audio_config (id, enabled, music_enabled, sound_coins, sound_button, updated_at)
            VALUES (1, 0, 0, '/static/audio/coins.wav', '/static/audio/button.wav', datetime('now'))
        """)
        
        # 邮件表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS mails (
                mail_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id TEXT DEFAULT 'system',
                sender_name TEXT DEFAULT '系统',
                receiver_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                attachments TEXT DEFAULT '{}',
                is_read INTEGER DEFAULT 0,
                created_at REAL NOT NULL,
                expires_at REAL,
                is_deleted_receiver INTEGER DEFAULT 0
            )
        """)
        
        # 成就定义表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                achievement_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                icon TEXT DEFAULT '🏆',
                condition_type TEXT NOT NULL,
                condition_value INTEGER,
                reward_stones INTEGER DEFAULT 0,
                reward_items TEXT DEFAULT '{}',
                reward_title TEXT,
                sort_order INTEGER DEFAULT 0
            )
        """)
        
        # 玩家成就进度表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS player_achievements (
                user_id TEXT NOT NULL,
                achievement_id TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                completed INTEGER DEFAULT 0,
                completed_at REAL,
                claimed INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, achievement_id)
            )
        """)
        
        # 称号定义表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS titles (
                title_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                icon TEXT DEFAULT '📜',
                color TEXT DEFAULT '#FFD700',
                prefix TEXT,
                bonus_attack INTEGER DEFAULT 0,
                bonus_defense INTEGER DEFAULT 0,
                bonus_hp INTEGER DEFAULT 0,
                is_system INTEGER DEFAULT 0,
                created_at REAL
            )
        """)
        
        # 玩家称号表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS player_titles (
                user_id TEXT NOT NULL,
                title_id TEXT NOT NULL,
                is_active INTEGER DEFAULT 0,
                acquired_at REAL NOT NULL,
                PRIMARY KEY (user_id, title_id)
            )
        """)
        
        # 装备强化配置表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS enhance_configs (
                equipment_type TEXT NOT NULL,
                level INTEGER NOT NULL,
                success_rate REAL DEFAULT 0.8,
                cost_stones INTEGER,
                cost_item_id TEXT,
                cost_item_count INTEGER DEFAULT 1,
                bonus_attack INTEGER DEFAULT 0,
                bonus_defense INTEGER DEFAULT 0,
                bonus_hp INTEGER DEFAULT 0,
                PRIMARY KEY (equipment_type, level)
            )
        """)
        
        # 玩家装备强化记录
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS player_enhance_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                equipment_type TEXT NOT NULL,
                equipment_name TEXT,
                from_level INTEGER,
                to_level INTEGER,
                success INTEGER NOT NULL,
                cost_stones INTEGER,
                created_at REAL NOT NULL
            )
        """)
        
        # ══════════════════════════════════════════════════════════════
        # 同伴系统表
        # ══════════════════════════════════════════════════════════════
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS player_companions (
                user_id TEXT NOT NULL,
                companion_id TEXT NOT NULL,
                loyalty INTEGER DEFAULT 50,
                gifts_given INTEGER DEFAULT 0,
                last_gift_time REAL DEFAULT 0,
                is_active INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, companion_id)
            )
        """)
        
        # ══════════════════════════════════════════════════════════════
        # 部队系统表
        # ══════════════════════════════════════════════════════════════
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS player_troops (
                user_id TEXT NOT NULL,
                troop_id TEXT NOT NULL,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, troop_id)
            )
        """)
        
        # ══════════════════════════════════════════════════════════════
        # 竞技场系统表
        # ══════════════════════════════════════════════════════════════
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS tournament_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                opponent_id TEXT NOT NULL,
                result TEXT NOT NULL,
                reward_gold INTEGER DEFAULT 0,
                reward_dao_yun INTEGER DEFAULT 0,
                win_streak INTEGER DEFAULT 0,
                streak_bonus TEXT DEFAULT '{}',
                created_at REAL NOT NULL
            )
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_tournament_user
            ON tournament_records (user_id, created_at)
        """)
        
        await self.db.commit()
        # 数据库升级：为旧表添加新列
        await self._alter_add_column("players", "last_adventure_time", "REAL DEFAULT 0.0")
        await self._alter_add_column("players", "death_count", "INTEGER DEFAULT 0")
        await self._alter_add_column("players", "lingqi", "INTEGER DEFAULT 50")
        await self._alter_add_column("players", "gold", "INTEGER DEFAULT 0")
        await self._alter_add_column("players", "permanent_max_hp_bonus", "INTEGER DEFAULT 0")
        await self._alter_add_column("players", "permanent_attack_bonus", "INTEGER DEFAULT 0")
        await self._alter_add_column("players", "permanent_defense_bonus", "INTEGER DEFAULT 0")
        await self._alter_add_column("players", "permanent_lingqi_bonus", "INTEGER DEFAULT 0")
        await self._alter_add_column("players", "heart_method", "TEXT DEFAULT '无'")
        await self._alter_add_column("players", "weapon", "TEXT DEFAULT '无'")
        await self._alter_add_column("players", "avatar_url", "TEXT DEFAULT ''")
        await self._alter_add_column("players", "last_rest_time", "REAL DEFAULT 0")
        await self._alter_add_column("players", "gongfa_1", "TEXT DEFAULT '无'")
        await self._alter_add_column("players", "gongfa_2", "TEXT DEFAULT '无'")
        await self._alter_add_column("players", "gongfa_3", "TEXT DEFAULT '无'")
        await self._alter_add_column("players", "body", "TEXT DEFAULT '无'")
        await self._alter_add_column("players", "head", "TEXT DEFAULT '无'")
        await self._alter_add_column("players", "hands", "TEXT DEFAULT '无'")
        await self._alter_add_column("players", "legs", "TEXT DEFAULT '无'")
        await self._alter_add_column("players", "shoulders", "TEXT DEFAULT '无'")
        await self._alter_add_column("players", "accessory1", "TEXT DEFAULT '无'")
        await self._alter_add_column("players", "accessory2", "TEXT DEFAULT '无'")
        await self._alter_add_column("players", "dao_yun", "INTEGER DEFAULT 0")
        await self._alter_add_column("players", "level", "INTEGER DEFAULT 1")
        await self._alter_add_column("players", "unallocated_points", "INTEGER DEFAULT 0")
        await self._alter_add_column("players", "bandit_stats", "TEXT DEFAULT '{}'")
        await self._alter_add_column("players", "breakthrough_bonus", "REAL DEFAULT 0.0")
        await self._alter_add_column("players", "breakthrough_pill_count", "INTEGER DEFAULT 0")
        await self._alter_add_column("players", "heart_method_mastery", "INTEGER DEFAULT 0")
        await self._alter_add_column("players", "heart_method_exp", "INTEGER DEFAULT 0")
        await self._alter_add_column("players", "heart_method_value", "INTEGER DEFAULT 0")
        await self._alter_add_column("players", "stored_heart_methods", "TEXT DEFAULT '{}'")
        await self._alter_add_column("players", "active_buffs", "TEXT DEFAULT '[]'")
        await self._alter_add_column("players", "gongfa_1_mastery", "INTEGER DEFAULT 0")
        await self._alter_add_column("players", "gongfa_1_exp", "INTEGER DEFAULT 0")
        await self._alter_add_column("players", "gongfa_2_mastery", "INTEGER DEFAULT 0")
        await self._alter_add_column("players", "gongfa_2_exp", "INTEGER DEFAULT 0")
        await self._alter_add_column("players", "gongfa_3_mastery", "INTEGER DEFAULT 0")
        await self._alter_add_column("players", "gongfa_3_exp", "INTEGER DEFAULT 0")
        await self._alter_add_column("gongfas", "lingqi_cost", "INTEGER DEFAULT 0")
        await self._alter_add_column("world_chat_messages", "sect_name", "TEXT DEFAULT ''")
        await self._alter_add_column("world_chat_messages", "sect_role", "TEXT DEFAULT ''")
        await self._alter_add_column("world_chat_messages", "sect_role_name", "TEXT DEFAULT ''")
        await self._ensure_sect_schema(force=True)
        # 爵位表迁移：新增声望字段
        await self._alter_add_column("realms", "sub_dao_yun_costs", "TEXT DEFAULT ''")
        await self._alter_add_column("realms", "breakthrough_dao_yun_cost", "INTEGER DEFAULT 0")
        # 爵位表首次创建时写入一份默认数据；之后完全以数据库内容为准
        if not realms_table_exists:
            await self._seed_realms()
        await self._backfill_realm_dao_yun_defaults()
        # 填充场景数据
        await self._seed_adventure_scenes()
        # 填充被动技能定义（仅补齐缺失，不覆盖已有配置）
        await self._seed_heart_methods()
        # 迁移旧版 weapons 表（添加 hp 列）
        await self._alter_add_column("weapons", "hp", "INTEGER NOT NULL DEFAULT 0")
        # 填充装备定义（仅补齐缺失，不覆盖已有配置）
        await self._seed_weapons()
        # 填充战技定义（仅补齐缺失，不覆盖已有配置）
        await self._seed_gongfas()
        await self._sync_gongfa_lingqi_costs()

    async def _migrate_json_data(self):
        """若存在旧 players.json 且数据库为空，则自动迁移。"""
        json_file = os.path.join(self._data_dir, "players.json")
        if not os.path.exists(json_file):
            return
        # 检查数据库是否已有数据
        async with self.db.execute("SELECT COUNT(*) FROM players") as cur:
            row = await cur.fetchone()
            if row[0] > 0:
                return
        # 读取旧 JSON
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                content = f.read()
            if not content.strip():
                return
            data = json.loads(content)
            for uid, d in data.items():
                d["user_id"] = uid
                player = Player.from_dict(d)
                await self._upsert_player(player)
            await self.db.commit()
            # 迁移完成后重命名旧文件作备份
            backup = json_file + ".bak"
            if not os.path.exists(backup):
                os.rename(json_file, backup)
        except Exception:
            pass

    async def load_all_players(self) -> dict[str, Player]:
        """加载所有玩家数据到内存。"""
        players = {}
        async with self.db.execute("SELECT * FROM players") as cur:
            async for row in cur:
                d = self._row_to_dict(row)
                player = Player.from_dict(d)
                players[player.user_id] = player
        return players

    async def load_heart_methods(self) -> dict:
        """加载启用的被动技能定义（独立表 -> 运行时）。"""
        from .constants import HEART_METHOD_REGISTRY, HeartMethodDef, HeartMethodQuality

        methods = {}
        try:
            async with self.db.execute(
                """
                SELECT method_id, name, realm, quality, exp_multiplier,
                       attack_bonus, defense_bonus, dao_yun_rate, description, mastery_exp
                FROM heart_methods
                WHERE enabled = 1
                ORDER BY realm ASC, quality ASC, method_id ASC
                """
            ) as cur:
                async for row in cur:
                    method_id = row["method_id"]
                    methods[method_id] = HeartMethodDef(
                        method_id=method_id,
                        name=row["name"],
                        realm=int(row["realm"]),
                        quality=HeartMethodQuality(int(row["quality"])),
                        exp_multiplier=float(row["exp_multiplier"] or 0.0),
                        attack_bonus=int(row["attack_bonus"] or 0),
                        defense_bonus=int(row["defense_bonus"] or 0),
                        dao_yun_rate=float(row["dao_yun_rate"] or 0.0),
                        description=row["description"] or "",
                        mastery_exp=int(row["mastery_exp"] or 100),
                    )
        except Exception:
            # 回退到代码内置，避免启动失败
            return dict(HEART_METHOD_REGISTRY)
        return methods

    async def load_weapons(self) -> dict:
        """加载启用的装备定义（独立表 -> 运行时）。"""
        from .constants import EQUIPMENT_REGISTRY, EquipmentDef

        equips = {}
        try:
            async with self.db.execute(
                """
                SELECT equip_id, name, tier, slot, attack, defense, hp,
                       element, element_damage, description
                FROM weapons
                WHERE enabled = 1
                ORDER BY tier ASC, slot ASC, equip_id ASC
                """
            ) as cur:
                async for row in cur:
                    equip_id = row["equip_id"]
                    equips[equip_id] = EquipmentDef(
                        equip_id=equip_id,
                        name=row["name"],
                        tier=int(row["tier"]),
                        slot=row["slot"],
                        attack=int(row["attack"] or 0),
                        defense=int(row["defense"] or 0),
                        hp=int(row["hp"] or 0),
                        element=row["element"] or "无",
                        element_damage=int(row["element_damage"] or 0),
                        description=row["description"] or "",
                    )
        except Exception:
            return dict(EQUIPMENT_REGISTRY)
        return equips

    async def save_player(self, player: Player):
        """保存单个玩家（INSERT OR REPLACE）。"""
        await self._upsert_player(player)
        await self.db.commit()

    async def save_all_players(self, players: dict[str, Player]):
        """批量保存所有玩家数据（UPSERT模式，分批提交）。"""
        batch_size = 50
        batch: list[Player] = []
        for player in players.values():
            batch.append(player)
            if len(batch) >= batch_size:
                for p in batch:
                    await self._upsert_player(p)
                await self.db.commit()
                batch.clear()
        if batch:
            for p in batch:
                await self._upsert_player(p)
            await self.db.commit()

    async def delete_player(self, user_id: str):
        """删除单个玩家。"""
        await self.db.execute("DELETE FROM players WHERE user_id = ?", (user_id,))
        await self.db.commit()

    async def clear_all_data(self, remove_dir: bool = False):
        """清理插件数据。"""
        if remove_dir:
            await self.close()
            if os.path.isdir(self._data_dir):
                await asyncio.to_thread(shutil.rmtree, self._data_dir, True)
            return
        await self.db.execute("DELETE FROM players")
        await self.db.execute("DELETE FROM web_tokens")
        await self.db.execute("DELETE FROM bind_keys")
        await self.db.execute("DELETE FROM chat_bindings")
        await self.db.commit()

    async def close(self):
        """关闭数据库连接。"""
        if self.db:
            await self.db.close()
            self.db = None

    # ==================== 数据库维护 ====================

    async def db_health_check(self) -> dict:
        """数据库健康检查，返回诊断信息。"""
        if not self.db:
            return {"healthy": False, "message": "数据库未初始化"}

        try:
            result = {"healthy": True, "checks": {}}

            async with self.db.execute("PRAGMA integrity_check") as cur:
                row = await cur.fetchone()
                result["checks"]["integrity"] = row[0] if row else "unknown"

            async with self.db.execute("PRAGMA quick_check") as cur:
                row = await cur.fetchone()
                result["checks"]["quick_check"] = row[0] if row else "unknown"

            async with self.db.execute("PRAGMA journal_mode") as cur:
                row = await cur.fetchone()
                result["checks"]["journal_mode"] = row[0] if row else "unknown"

            async with self.db.execute("PRAGMA synchronous") as cur:
                row = await cur.fetchone()
                result["checks"]["synchronous"] = row[0] if row else "unknown"

            async with self.db.execute("SELECT COUNT(*) FROM players") as cur:
                row = await cur.fetchone()
                result["player_count"] = row[0] if row else 0

            async with self.db.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()") as cur:
                row = await cur.fetchone()
                result["db_size_bytes"] = row[0] if row else 0

            return result
        except Exception as e:
            return {"healthy": False, "message": str(e)}

    async def db_vacuum(self) -> dict:
        """执行 VACUUM 优化数据库。"""
        if not self.db:
            return {"success": False, "message": "数据库未初始化"}

        try:
            await self.db.execute("VACUUM")
            return {"success": True, "message": "数据库优化完成"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def db_backup(self, backup_path: str) -> dict:
        """备份数据库到指定路径。"""
        import shutil

        if not self.db:
            return {"success": False, "message": "数据库未初始化"}

        try:
            await self.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            shutil.copy2(self._db_path, backup_path)
            wal_path = self._db_path + "-wal"
            if os.path.exists(wal_path):
                shutil.copy2(wal_path, backup_path + "-wal")
            return {"success": True, "message": f"备份成功: {backup_path}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def get_table_info(self) -> list[dict]:
        """获取所有表的信息。"""
        if not self.db:
            return []

        tables = []
        async with self.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ) as cur:
            async for row in cur:
                table_name = row[0]
                async with self.db.execute(f"SELECT COUNT(*) FROM {table_name}") as count_cur:
                    count_row = await count_cur.fetchone()
                    count = count_row[0] if count_row else 0
                tables.append({"name": table_name, "row_count": count})
        return tables

    # ==================== 内部方法 ====================

    async def _upsert_player(self, player: Player, db: aiosqlite.Connection | None = None):
        """INSERT OR REPLACE 单个玩家。"""
        d = player.to_dict(include_sensitive=True)
        # inventory 序列化为 JSON text
        inv = d.get("inventory", {})
        if isinstance(inv, dict):
            inv = json.dumps(inv, ensure_ascii=False)
        stored_heart_methods = d.get("stored_heart_methods", {})
        if isinstance(stored_heart_methods, dict):
            stored_heart_methods = json.dumps(stored_heart_methods, ensure_ascii=False)
        active_buffs = d.get("active_buffs_raw", d.get("active_buffs", []))
        if isinstance(active_buffs, list):
            active_buffs = json.dumps(active_buffs, ensure_ascii=False)
        bandit_stats = d.get("bandit_stats", {})
        if isinstance(bandit_stats, dict):
            bandit_stats = json.dumps(bandit_stats, ensure_ascii=False)
        conn = db or self.db
        if conn is None:
            raise RuntimeError("数据库连接尚未初始化")

        values = (
            player.user_id,
            d.get("name", ""),
            d.get("realm", 0),
            d.get("sub_realm", 0),
            d.get("exp", 0),
            d.get("hp", 100),
            d.get("max_hp", 100),
            d.get("attack", 10),
            d.get("defense", 5),
            d.get("spirit_stones", 0),
            d.get("lingqi", 50),
            d.get("permanent_max_hp_bonus", 0),
            d.get("permanent_attack_bonus", 0),
            d.get("permanent_defense_bonus", 0),
            d.get("permanent_lingqi_bonus", 0),
            d.get("heart_method", "无"),
            d.get("weapon", "无"),
            d.get("gongfa_1", "无"),
            d.get("gongfa_2", "无"),
            d.get("gongfa_3", "无"),
            d.get("head", "无"),
            d.get("body", "无"),
            d.get("hands", "无"),
            d.get("legs", "无"),
            d.get("shoulders", "无"),
            d.get("accessory1", "无"),
            d.get("accessory2", "无"),
            d.get("dao_yun", 0),
            d.get("breakthrough_bonus", 0.0),
            d.get("breakthrough_pill_count", 0),
            d.get("heart_method_mastery", 0),
            d.get("heart_method_exp", 0),
            d.get("heart_method_value", 0),
            stored_heart_methods,
            player.gongfa_1_mastery,
            player.gongfa_1_exp,
            player.gongfa_2_mastery,
            player.gongfa_2_exp,
            player.gongfa_3_mastery,
            player.gongfa_3_exp,
            inv,
            active_buffs,
            d.get("created_at", 0),
            d.get("last_cultivate_time", 0.0),
            d.get("last_checkin_date"),
            d.get("afk_cultivate_start", 0.0),
            d.get("afk_cultivate_end", 0.0),
            d.get("last_adventure_time", 0.0),
            d.get("death_count", 0),
            d.get("unified_msg_origin"),
            d.get("password_hash"),
            d.get("level", 1),
            d.get("unallocated_points", 0),
            bandit_stats,
        )
        placeholders = ", ".join(["?"] * len(_PLAYER_COLUMNS))
        cols = ", ".join(_PLAYER_COLUMNS)
        await conn.execute(
            f"INSERT OR REPLACE INTO players ({cols}) VALUES ({placeholders})",
            values,
        )

    @staticmethod
    def _row_to_dict(row: aiosqlite.Row) -> dict:
        """将数据库行转为 Player.from_dict 可用的字典。"""
        d = dict(row)
        # inventory 从 JSON text 反序列化
        inv = d.get("inventory", "{}")
        if isinstance(inv, str):
            try:
                d["inventory"] = json.loads(inv)
            except (json.JSONDecodeError, TypeError):
                d["inventory"] = {}
        stored_heart_methods = d.get("stored_heart_methods", "{}")
        if isinstance(stored_heart_methods, str):
            try:
                loaded = json.loads(stored_heart_methods)
                d["stored_heart_methods"] = loaded if isinstance(loaded, dict) else {}
            except (json.JSONDecodeError, TypeError):
                d["stored_heart_methods"] = {}
        active_buffs = d.get("active_buffs", "[]")
        if isinstance(active_buffs, str):
            try:
                loaded = json.loads(active_buffs)
                d["active_buffs_raw"] = loaded if isinstance(loaded, list) else []
            except (json.JSONDecodeError, TypeError):
                d["active_buffs_raw"] = []
        bandit_stats = d.get("bandit_stats", "{}")
        if isinstance(bandit_stats, str):
            try:
                d["bandit_stats"] = json.loads(bandit_stats)
            except (json.JSONDecodeError, TypeError):
                d["bandit_stats"] = {}
        return d

    async def _alter_add_column(self, table: str, column: str, col_type: str):
        """安全地为表添加新列（已存在则忽略）。"""
        if not _SAFE_IDENT.match(table) or not _SAFE_IDENT.match(column):
            raise ValueError(f"非法标识符: table={table}, column={column}")
        if not _SAFE_COL_TYPE.match(col_type):
            raise ValueError(f"非法列类型: {col_type}")
        try:
            await self.db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            await self.db.commit()
        except Exception as e:
            if "duplicate column name" not in str(e).lower():
                logger.warning("添加列失败 %s.%s: %s", table, column, e)  # 列已存在

    async def _ensure_player_schema(self, force: bool = False):
        """确保玩家相关旧表已经自动升级到当前结构。"""
        try:
            await self._alter_add_column("players", "level", "INTEGER DEFAULT 1")
            await self._alter_add_column("players", "unallocated_points", "INTEGER DEFAULT 0")
            await self._alter_add_column("players", "bandit_stats", "TEXT DEFAULT '{}'")
        except Exception:
            pass

    async def _ensure_sect_schema(self, force: bool = False):
        """确保家族相关旧表已经自动升级到当前结构。"""
        if self._sect_schema_checked and not force:
            return
        await self._alter_add_column("sects", "description", "TEXT DEFAULT ''")
        await self._alter_add_column("sects", "level", "INTEGER DEFAULT 1")
        await self._alter_add_column("sects", "spirit_stones", "INTEGER DEFAULT 0")
        await self._alter_add_column("sects", "max_members", "INTEGER DEFAULT 30")
        await self._alter_add_column("sects", "join_policy", "TEXT DEFAULT 'open'")
        await self._alter_add_column("sects", "min_realm", "INTEGER DEFAULT 0")
        await self._alter_add_column("sects", "created_at", "REAL DEFAULT 0.0")
        await self._alter_add_column("sects", "announcement", "TEXT DEFAULT ''")
        await self._alter_add_column("sect_members", "role", "TEXT DEFAULT 'disciple'")
        await self._alter_add_column("sect_members", "joined_at", "REAL DEFAULT 0.0")
        await self._alter_add_column("sect_applications", "status", "TEXT DEFAULT 'pending'")
        await self._alter_add_column("sect_applications", "applied_at", "REAL DEFAULT 0.0")
        await self._alter_add_column("sect_applications", "resolved_at", "REAL")
        await self._alter_add_column("sect_applications", "resolved_by", "TEXT")
        await self._alter_add_column("sect_members", "contribution_points", "INTEGER DEFAULT 0")
        await self._alter_add_column("sects", "warehouse_capacity", "INTEGER DEFAULT 200")
        try:
            await self.db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_sects_name_unique ON sects (name)")
            await self.db.commit()
        except Exception:
            pass
        self._sect_schema_checked = True

    async def _seed_realms(self):
        """首次创建爵位表时，写入一份内置默认爵位。"""
        import json as _json
        from .constants import REALM_CONFIG as DEFAULT_REALM_CONFIG

        rows = []
        for level, cfg in DEFAULT_REALM_CONFIG.items():
            sub_costs = cfg.get("sub_dao_yun_costs", [])
            rows.append((
                int(level),
                cfg["name"],
                1 if cfg.get("has_sub_realm") else 0,
                1 if cfg.get("high_realm") else 0,
                int(cfg.get("exp_to_next", 100)),
                int(cfg.get("sub_exp_to_next", 0)),
                int(cfg.get("base_hp", 100)),
                int(cfg.get("base_attack", 10)),
                int(cfg.get("base_defense", 5)),
                int(cfg.get("base_lingqi", 50)),
                float(cfg.get("breakthrough_rate", 1.0)),
                float(cfg.get("death_rate", 0.0)),
                _json.dumps(sub_costs) if sub_costs else "",
                int(cfg.get("breakthrough_dao_yun_cost", 0)),
            ))
        await self.db.executemany(
            """
            INSERT OR IGNORE INTO realms (
                level, name, has_sub_realm, high_realm,
                exp_to_next, sub_exp_to_next,
                base_hp, base_attack, base_defense, base_lingqi,
                breakthrough_rate, death_rate,
                sub_dao_yun_costs, breakthrough_dao_yun_cost
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        await self.db.commit()

    async def _backfill_realm_dao_yun_defaults(self):
        """为旧 realms 表补齐新增的声望字段默认值，不覆盖已编辑数据。"""
        import json as _json
        from .constants import REALM_CONFIG as DEFAULT_REALM_CONFIG

        changed = False
        for level, cfg in DEFAULT_REALM_CONFIG.items():
            default_sub_costs = cfg.get("sub_dao_yun_costs", [])
            default_bt_cost = int(cfg.get("breakthrough_dao_yun_cost", 0))
            if not default_sub_costs and default_bt_cost <= 0:
                continue
            sub_costs_text = _json.dumps(default_sub_costs) if default_sub_costs else ""
            cur = await self.db.execute(
                """
                UPDATE realms
                SET sub_dao_yun_costs = ?, breakthrough_dao_yun_cost = ?
                WHERE level = ?
                  AND COALESCE(sub_dao_yun_costs, '') = ''
                """,
                (sub_costs_text, default_bt_cost, int(level)),
            )
            if (cur.rowcount or 0) > 0:
                changed = True
        if changed:
            await self.db.commit()

    async def load_realms(self) -> dict[int, dict]:
        """加载爵位配置（独立表 -> 运行时 REALM_CONFIG）。"""
        import json as _json
        from .constants import REALM_CONFIG as DEFAULT_REALM_CONFIG

        realms = {}
        try:
            async with self.db.execute(
                """
                SELECT level, name, has_sub_realm, high_realm,
                       exp_to_next, sub_exp_to_next,
                       base_hp, base_attack, base_defense, base_lingqi,
                       breakthrough_rate, death_rate,
                       sub_dao_yun_costs, breakthrough_dao_yun_cost
                FROM realms
                ORDER BY level ASC
                """
            ) as cur:
                async for row in cur:
                    level = int(row["level"])
                    cfg: dict[str, Any] = {
                        "name": row["name"],
                        "has_sub_realm": bool(int(row["has_sub_realm"])),
                        "exp_to_next": int(row["exp_to_next"]),
                        "sub_exp_to_next": int(row["sub_exp_to_next"]),
                        "base_hp": int(row["base_hp"]),
                        "base_attack": int(row["base_attack"]),
                        "base_defense": int(row["base_defense"]),
                        "base_lingqi": int(row["base_lingqi"]),
                        "breakthrough_rate": float(row["breakthrough_rate"]),
                        "death_rate": float(row["death_rate"]),
                    }
                    if int(row["high_realm"]):
                        cfg["high_realm"] = True
                    raw_costs = str(row["sub_dao_yun_costs"] or "").strip()
                    if raw_costs:
                        try:
                            cfg["sub_dao_yun_costs"] = _json.loads(raw_costs)
                        except (ValueError, TypeError):
                            pass
                    bt_cost = int(row["breakthrough_dao_yun_cost"] or 0)
                    if bt_cost > 0:
                        cfg["breakthrough_dao_yun_cost"] = bt_cost
                    realms[level] = cfg
        except Exception:
            return dict(DEFAULT_REALM_CONFIG)
        return realms if realms else dict(DEFAULT_REALM_CONFIG)

    async def admin_list_realms(self) -> list[dict[str, Any]]:
        result = []
        async with self.db.execute(
            """
            SELECT level, name, has_sub_realm, high_realm,
                   exp_to_next, sub_exp_to_next,
                   base_hp, base_attack, base_defense, base_lingqi,
                   breakthrough_rate, death_rate,
                   sub_dao_yun_costs, breakthrough_dao_yun_cost
            FROM realms
            ORDER BY level ASC
            """
        ) as cur:
            async for row in cur:
                result.append(dict(row))
        return result

    async def admin_has_realm_name(self, name: str, exclude_level: int | None = None) -> bool:
        if exclude_level is not None:
            async with self.db.execute(
                "SELECT 1 FROM realms WHERE name = ? AND level != ? LIMIT 1",
                (name, exclude_level),
            ) as cur:
                return (await cur.fetchone()) is not None
        async with self.db.execute(
            "SELECT 1 FROM realms WHERE name = ? LIMIT 1", (name,),
        ) as cur:
            return (await cur.fetchone()) is not None

    async def admin_create_realm(self, data: dict[str, Any]) -> bool:
        cur = await self.db.execute(
            """
            INSERT OR IGNORE INTO realms (
                level, name, has_sub_realm, high_realm,
                exp_to_next, sub_exp_to_next,
                base_hp, base_attack, base_defense, base_lingqi,
                breakthrough_rate, death_rate,
                sub_dao_yun_costs, breakthrough_dao_yun_cost
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(data["level"]),
                data["name"],
                int(data.get("has_sub_realm", 0)),
                int(data.get("high_realm", 0)),
                int(data.get("exp_to_next", 100)),
                int(data.get("sub_exp_to_next", 0)),
                int(data.get("base_hp", 100)),
                int(data.get("base_attack", 10)),
                int(data.get("base_defense", 5)),
                int(data.get("base_lingqi", 50)),
                float(data.get("breakthrough_rate", 1.0)),
                float(data.get("death_rate", 0.0)),
                str(data.get("sub_dao_yun_costs", "")),
                int(data.get("breakthrough_dao_yun_cost", 0)),
            ),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def admin_update_realm(self, level: int, data: dict[str, Any]) -> bool:
        cur = await self.db.execute(
            """
            UPDATE realms
            SET name = ?, has_sub_realm = ?, high_realm = ?,
                exp_to_next = ?, sub_exp_to_next = ?,
                base_hp = ?, base_attack = ?, base_defense = ?, base_lingqi = ?,
                breakthrough_rate = ?, death_rate = ?,
                sub_dao_yun_costs = ?, breakthrough_dao_yun_cost = ?
            WHERE level = ?
            """,
            (
                data["name"],
                int(data.get("has_sub_realm", 0)),
                int(data.get("high_realm", 0)),
                int(data.get("exp_to_next", 100)),
                int(data.get("sub_exp_to_next", 0)),
                int(data.get("base_hp", 100)),
                int(data.get("base_attack", 10)),
                int(data.get("base_defense", 5)),
                int(data.get("base_lingqi", 50)),
                float(data.get("breakthrough_rate", 1.0)),
                float(data.get("death_rate", 0.0)),
                str(data.get("sub_dao_yun_costs", "")),
                int(data.get("breakthrough_dao_yun_cost", 0)),
                level,
            ),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def admin_delete_realm(self, level: int) -> bool:
        cur = await self.db.execute(
            "DELETE FROM realms WHERE level = ?",
            (level,),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def get_realm_names(self) -> dict[int, str]:
        """获取爵位等级->名称映射（公开API用）。"""
        result = {}
        async with self.db.execute(
            "SELECT level, name FROM realms ORDER BY level ASC"
        ) as cur:
            async for row in cur:
                result[int(row["level"])] = row["name"]
        return result

    async def _seed_adventure_scenes(self):
        """若场景表为空，填充40条历练场景数据。"""
        async with self.db.execute("SELECT COUNT(*) FROM adventure_scenes") as cur:
            row = await cur.fetchone()
            if row[0] > 0:
                return
        scenes = [
            # 魔兽森林
            ("魔兽森林", "幽暗密林", "古树参天，妖兽潜伏于暗处"),
            ("魔兽森林", "血月狼谷", "狼嚎震天，血月映照下凶兽成群"),
            ("魔兽森林", "毒瘴沼泽", "瘴气弥漫，毒虫遍地横行"),
            ("魔兽森林", "万蛇巢穴", "蛇影重重，巨蟒盘踞洞中"),
            ("魔兽森林", "熊罴险岭", "巨熊咆哮，山石崩裂"),
            ("魔兽森林", "灵猿古树", "灵猿据守千年古木"),
            ("魔兽森林", "火鸦荒原", "火鸦群起，烈焰灼天"),
            ("魔兽森林", "寒冰兽窟", "冰封洞窟中蛰伏着远古凶兽"),
            ("魔兽森林", "雷鹰崖壁", "崖顶雷鹰振翅带起雷暴"),
            ("魔兽森林", "九尾狐林", "迷雾中传来蛊惑人心的狐鸣"),
            # 秘境探险
            ("秘境探险", "上古遗迹", "断壁残垣中隐藏着远古秘宝"),
            ("秘境探险", "迷幻阵法", "虚实难辨，一步踏错万劫不复"),
            ("秘境探险", "地下灵脉", "体力汹涌的地底矿脉"),
            ("秘境探险", "沉没宫殿", "水下宫殿中封印着未知力量"),
            ("秘境探险", "时空裂隙", "时空紊乱的裂缝中危机四伏"),
            ("秘境探险", "藏经阁废墟", "残破典籍中暗藏逆天战技"),
            ("秘境探险", "配药古洞", "古修士遗留的配药福地"),
            ("秘境探险", "星辰迷宫", "星光指引下的层层考验"),
            ("秘境探险", "天机棋盘", "以命为棋，一局定生死"),
            ("秘境探险", "虚空秘境", "虚空中飘浮的远古修炼之地"),
            # 除魔卫道
            ("除魔卫道", "魔修巢穴", "魔修聚集的阴暗地窟"),
            ("除魔卫道", "血祭祭坛", "邪修正在进行血祭仪式"),
            ("除魔卫道", "鬼蜮幽都", "阴气冲天，厉鬼横行"),
            ("除魔卫道", "堕落仙山", "被魔气侵蚀的昔日仙门"),
            ("除魔卫道", "尸傀战场", "操控尸傀的邪修正在为祸"),
            ("除魔卫道", "妖邪峡谷", "妖邪盘踞的深幽峡谷"),
            ("除魔卫道", "噬魂阵法", "以魂为引的禁忌大阵"),
            ("除魔卫道", "天魔分身", "天魔降临世间的一缕分身"),
            ("除魔卫道", "邪道拍卖", "暗中交易违禁之物的黑市"),
            ("除魔卫道", "魔道入侵", "魔道大军入侵，需奋力抵御"),
            # 红尘历练
            ("红尘历练", "繁华集市", "凡人集市中暗流涌动"),
            ("红尘历练", "仙门试炼", "仙门弟子间的切磋比试"),
            ("红尘历练", "悬赏猎杀", "接取悬赏任务追捕通缉犯"),
            ("红尘历练", "护送商队", "护送灵材商队穿越危险地带"),
            ("红尘历练", "擂台争霸", "角斗场武斗大赛"),
            ("红尘历练", "奇遇仙缘", "偶遇高人，机缘降临"),
            ("红尘历练", "山贼劫道", "路遇山贼拦路打劫"),
            ("红尘历练", "江湖恩怨", "卷入江湖恩怨纷争"),
            ("红尘历练", "天灾降临", "天降异象，妖兽暴动"),
            ("红尘历练", "论道大会", "各路修士齐聚论道"),
        ]
        await self.db.executemany(
            "INSERT INTO adventure_scenes (category, name, description) VALUES (?, ?, ?)",
            scenes,
        )
        await self.db.commit()

    async def _seed_heart_methods(self):
        """若被动技能表为空或有缺失，按代码内置定义补齐。"""
        from .constants import HEART_METHOD_REGISTRY

        existing = set()
        async with self.db.execute("SELECT method_id FROM heart_methods") as cur:
            async for row in cur:
                existing.add(row[0])

        rows = []
        for hm in HEART_METHOD_REGISTRY.values():
            if hm.method_id in existing:
                continue
            rows.append(
                (
                    hm.method_id,
                    hm.name,
                    int(hm.realm),
                    int(hm.quality),
                    float(hm.exp_multiplier),
                    int(hm.attack_bonus),
                    int(hm.defense_bonus),
                    float(hm.dao_yun_rate),
                    hm.description,
                    int(hm.mastery_exp),
                    1,
                )
            )

        if not rows:
            return

        await self.db.executemany(
            """
            INSERT OR IGNORE INTO heart_methods (
                method_id, name, realm, quality, exp_multiplier,
                attack_bonus, defense_bonus, dao_yun_rate, description, mastery_exp, enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
rows,
        )
        await self.db.commit()

    async def _seed_weapons(self):
        """若武器表为空或有缺失，按代码内置定义补齐。"""
        from .constants import EQUIPMENT_REGISTRY

        existing = set()
        async with self.db.execute("SELECT equip_id FROM weapons") as cur:
            async for row in cur:
                existing.add(row[0])

        rows = []
        for eq in EQUIPMENT_REGISTRY.values():
            if eq.equip_id in existing:
                continue
            rows.append(
                (
                    eq.equip_id,
                    eq.name,
                    int(eq.tier),
                    eq.slot,
                    int(eq.attack),
                    int(eq.defense),
                    int(eq.hp),
                    eq.element,
                    int(eq.element_damage),
                    eq.description,
                    1,
                )
            )

        if not rows:
            return

        await self.db.executemany(
            """
            INSERT OR IGNORE INTO weapons (
                equip_id, name, tier, slot, attack, defense, hp,
                element, element_damage, description, enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        await self.db.commit()

    async def _seed_gongfas(self):
        """若战技表为空或有缺失，按代码内置定义补齐。"""
        from .constants import GONGFA_REGISTRY

        existing = set()
        async with self.db.execute("SELECT gongfa_id FROM gongfas") as cur:
            async for row in cur:
                existing.add(row[0])

        rows = []
        for gf in GONGFA_REGISTRY.values():
            if gf.gongfa_id in existing:
                continue
            rows.append(
                (
                    gf.gongfa_id,
                    gf.name,
                    int(gf.tier),
                    int(gf.attack_bonus),
                    int(gf.defense_bonus),
                    int(gf.hp_regen),
                    int(gf.lingqi_regen),
                    gf.description,
                    int(gf.mastery_exp),
                    int(gf.dao_yun_cost),
                    int(gf.recycle_price),
                    int(gf.lingqi_cost),
                    1,
                )
            )

        if not rows:
            return

        await self.db.executemany(
            """
            INSERT OR IGNORE INTO gongfas (
                gongfa_id, name, tier, attack_bonus, defense_bonus,
                hp_regen, lingqi_regen, description, mastery_exp,
                dao_yun_cost, recycle_price, lingqi_cost, enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        await self.db.commit()

    async def _sync_gongfa_lingqi_costs(self):
        """为旧数据补齐耗灵字段，避免重载后战技耗灵归零。"""
        from .constants import calc_gongfa_lingqi_cost

        rows = []
        async with self.db.execute(
            """
            SELECT gongfa_id, tier, attack_bonus, defense_bonus, hp_regen, lingqi_regen, lingqi_cost
            FROM gongfas
            """
        ) as cur:
            async for row in cur:
                current_cost = int(row["lingqi_cost"] or 0)
                if current_cost > 0:
                    continue
                rows.append((
                    calc_gongfa_lingqi_cost(
                        int(row["tier"] or 0),
                        int(row["attack_bonus"] or 0),
                        int(row["defense_bonus"] or 0),
                        int(row["hp_regen"] or 0),
                        int(row["lingqi_regen"] or 0),
                    ),
                    row["gongfa_id"],
                ))

        if not rows:
            return

        await self.db.executemany(
            "UPDATE gongfas SET lingqi_cost = ? WHERE gongfa_id = ?",
            rows,
        )
        await self.db.commit()

    async def load_gongfas(self) -> dict:
        """加载启用的战技定义（独立表 -> 运行时）。"""
        from .constants import GONGFA_REGISTRY, GongfaDef, calc_gongfa_lingqi_cost

        gongfas = {}
        try:
            async with self.db.execute(
                """
                SELECT gongfa_id, name, tier, attack_bonus, defense_bonus,
                       hp_regen, lingqi_regen, description, mastery_exp,
                       dao_yun_cost, recycle_price, lingqi_cost
                FROM gongfas
                WHERE enabled = 1
                ORDER BY tier ASC, gongfa_id ASC
                """
            ) as cur:
                async for row in cur:
                    gongfa_id = row["gongfa_id"]
                    tier = int(row["tier"] or 0)
                    attack_bonus = int(row["attack_bonus"] or 0)
                    defense_bonus = int(row["defense_bonus"] or 0)
                    hp_regen = int(row["hp_regen"] or 0)
                    lingqi_regen = int(row["lingqi_regen"] or 0)
                    gongfas[gongfa_id] = GongfaDef(
                        gongfa_id=gongfa_id,
                        name=row["name"],
                        tier=tier,
                        attack_bonus=attack_bonus,
                        defense_bonus=defense_bonus,
                        hp_regen=hp_regen,
                        lingqi_regen=lingqi_regen,
                        description=row["description"] or "",
                        mastery_exp=int(row["mastery_exp"] or 200),
                        dao_yun_cost=int(row["dao_yun_cost"] or 0),
                        recycle_price=int(row["recycle_price"] or 1000),
                        lingqi_cost=int(row["lingqi_cost"] or 0) or calc_gongfa_lingqi_cost(
                            tier,
                            attack_bonus,
                            defense_bonus,
                            hp_regen,
                            lingqi_regen,
                        ),
                    )
        except Exception:
            return dict(GONGFA_REGISTRY)
        return gongfas

    async def admin_list_gongfas(self) -> list[dict[str, Any]]:
        result = []
        async with self.db.execute(
            """
            SELECT gongfa_id, name, tier, attack_bonus, defense_bonus,
                   hp_regen, lingqi_regen, description, mastery_exp,
                   dao_yun_cost, recycle_price, lingqi_cost, enabled
            FROM gongfas
            ORDER BY tier ASC, gongfa_id ASC
            """
        ) as cur:
            async for row in cur:
                result.append(dict(row))
        return result

    async def admin_has_gongfa_name(self, name: str) -> bool:
        """检查战技名称是否已存在（不区分大小写，忽略首尾空白）。"""
        async with self.db.execute(
            """
            SELECT 1
            FROM gongfas
            WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
            LIMIT 1
            """,
            (name,),
        ) as cur:
            row = await cur.fetchone()
            return row is not None

    async def admin_create_gongfa(self, data: dict[str, Any]) -> bool:
        from .constants import calc_gongfa_lingqi_cost

        lingqi_cost = data.get("lingqi_cost")
        if lingqi_cost is None:
            lingqi_cost = calc_gongfa_lingqi_cost(
                int(data["tier"]),
                int(data.get("attack_bonus", 0)),
                int(data.get("defense_bonus", 0)),
                int(data.get("hp_regen", 0)),
                int(data.get("lingqi_regen", 0)),
            )
        cur = await self.db.execute(
            """
            INSERT OR IGNORE INTO gongfas (
                gongfa_id, name, tier, attack_bonus, defense_bonus,
                hp_regen, lingqi_regen, description, mastery_exp,
                dao_yun_cost, recycle_price, lingqi_cost, enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["gongfa_id"],
                data["name"],
                int(data["tier"]),
                int(data.get("attack_bonus", 0)),
                int(data.get("defense_bonus", 0)),
                int(data.get("hp_regen", 0)),
                int(data.get("lingqi_regen", 0)),
                str(data.get("description", "")),
                int(data.get("mastery_exp", 200)),
                int(data.get("dao_yun_cost", 0)),
                int(data.get("recycle_price", 1000)),
                int(lingqi_cost),
                int(data.get("enabled", 1)),
            ),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def admin_update_gongfa(self, gongfa_id: str, data: dict[str, Any]) -> bool:
        from .constants import calc_gongfa_lingqi_cost

        lingqi_cost = data.get("lingqi_cost")
        if lingqi_cost is None:
            lingqi_cost = calc_gongfa_lingqi_cost(
                int(data["tier"]),
                int(data.get("attack_bonus", 0)),
                int(data.get("defense_bonus", 0)),
                int(data.get("hp_regen", 0)),
                int(data.get("lingqi_regen", 0)),
            )
        cur = await self.db.execute(
            """
            UPDATE gongfas
            SET name = ?, tier = ?, attack_bonus = ?, defense_bonus = ?,
                hp_regen = ?, lingqi_regen = ?, description = ?, mastery_exp = ?,
                dao_yun_cost = ?, recycle_price = ?, lingqi_cost = ?, enabled = ?
            WHERE gongfa_id = ?
            """,
            (
                data["name"],
                int(data["tier"]),
                int(data.get("attack_bonus", 0)),
                int(data.get("defense_bonus", 0)),
                int(data.get("hp_regen", 0)),
                int(data.get("lingqi_regen", 0)),
                str(data.get("description", "")),
                int(data.get("mastery_exp", 200)),
                int(data.get("dao_yun_cost", 0)),
                int(data.get("recycle_price", 1000)),
                int(lingqi_cost),
                int(data.get("enabled", 1)),
                gongfa_id,
            ),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def admin_delete_gongfa(self, gongfa_id: str) -> bool:
        cur = await self.db.execute(
            "DELETE FROM gongfas WHERE gongfa_id = ?",
            (gongfa_id,),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def get_adventure_scenes(self) -> list[dict]:
        """获取所有历练场景。"""
        result = []
        async with self.db.execute(
            "SELECT id, category, name, description FROM adventure_scenes ORDER BY id"
        ) as cur:
            async for row in cur:
                result.append({
                    "id": row[0], "category": row[1],
                    "name": row[2], "description": row[3],
                })
        return result

    async def get_random_scene(self) -> Optional[dict]:
        """随机获取一个历练场景。"""
        async with self.db.execute(
            "SELECT id, category, name, description FROM adventure_scenes ORDER BY RANDOM() LIMIT 1"
        ) as cur:
            row = await cur.fetchone()
            if row:
                return {"id": row[0], "category": row[1], "name": row[2], "description": row[3]}
        return None

    # ==================== 管理员 CRUD：历练场景 ====================

    async def admin_list_adventure_scenes(self) -> list[dict[str, Any]]:
        return await self.get_adventure_scenes()

    async def admin_has_adventure_scene_name(self, name: str) -> bool:
        """检查历练场景名称是否已存在（不区分大小写，忽略首尾空白）。"""
        async with self.db.execute(
            """
            SELECT 1
            FROM adventure_scenes
            WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
            LIMIT 1
            """,
            (name,),
        ) as cur:
            row = await cur.fetchone()
            return row is not None

    async def admin_create_adventure_scene(self, category: str, name: str, description: str) -> int:
        cur = await self.db.execute(
            "INSERT INTO adventure_scenes (category, name, description) VALUES (?, ?, ?)",
            (category, name, description),
        )
        await self.db.commit()
        return int(cur.lastrowid or 0)

    async def admin_update_adventure_scene(self, scene_id: int, category: str, name: str, description: str) -> bool:
        cur = await self.db.execute(
            """
            UPDATE adventure_scenes
            SET category = ?, name = ?, description = ?
            WHERE id = ?
            """,
            (category, name, description, scene_id),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def admin_delete_adventure_scene(self, scene_id: int) -> bool:
        cur = await self.db.execute(
            "DELETE FROM adventure_scenes WHERE id = ?",
            (scene_id,),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    # ==================== 管理员 CRUD：被动技能 ====================

    async def admin_list_heart_methods(self) -> list[dict[str, Any]]:
        result = []
        async with self.db.execute(
            """
            SELECT method_id, name, realm, quality, exp_multiplier,
                   attack_bonus, defense_bonus, dao_yun_rate, description, mastery_exp, enabled
            FROM heart_methods
            ORDER BY realm ASC, quality ASC, method_id ASC
            """
        ) as cur:
            async for row in cur:
                result.append(dict(row))
        return result

    async def admin_has_heart_method_name(self, name: str) -> bool:
        """检查被动技能名称是否已存在（不区分大小写，忽略首尾空白）。"""
        async with self.db.execute(
            """
            SELECT 1
            FROM heart_methods
            WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
            LIMIT 1
            """,
            (name,),
        ) as cur:
            row = await cur.fetchone()
            return row is not None

    async def admin_create_heart_method(self, data: dict[str, Any]) -> bool:
        cur = await self.db.execute(
            """
            INSERT OR IGNORE INTO heart_methods (
                method_id, name, realm, quality, exp_multiplier,
                attack_bonus, defense_bonus, dao_yun_rate, description, mastery_exp, enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["method_id"],
                data["name"],
                int(data["realm"]),
                int(data["quality"]),
                float(data.get("exp_multiplier", 0.0)),
                int(data.get("attack_bonus", 0)),
                int(data.get("defense_bonus", 0)),
                float(data.get("dao_yun_rate", 0.0)),
                str(data.get("description", "")),
                int(data.get("mastery_exp", 100)),
                int(data.get("enabled", 1)),
            ),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def admin_update_heart_method(self, method_id: str, data: dict[str, Any]) -> bool:
        cur = await self.db.execute(
            """
            UPDATE heart_methods
            SET name = ?, realm = ?, quality = ?, exp_multiplier = ?,
                attack_bonus = ?, defense_bonus = ?, dao_yun_rate = ?,
                description = ?, mastery_exp = ?, enabled = ?
            WHERE method_id = ?
            """,
            (
                data["name"],
                int(data["realm"]),
                int(data["quality"]),
                float(data.get("exp_multiplier", 0.0)),
                int(data.get("attack_bonus", 0)),
                int(data.get("defense_bonus", 0)),
                float(data.get("dao_yun_rate", 0.0)),
                str(data.get("description", "")),
                int(data.get("mastery_exp", 100)),
                int(data.get("enabled", 1)),
                method_id,
            ),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def admin_delete_heart_method(self, method_id: str) -> bool:
        cur = await self.db.execute(
            "DELETE FROM heart_methods WHERE method_id = ?",
            (method_id,),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    # ==================== 管理员 CRUD：武器/护甲 ====================

    async def admin_list_weapons(self) -> list[dict[str, Any]]:
        result = []
        async with self.db.execute(
            """
            SELECT equip_id, name, tier, slot, attack, defense,
                   element, element_damage, description, enabled
            FROM weapons
            ORDER BY tier ASC, slot ASC, equip_id ASC
            """
        ) as cur:
            async for row in cur:
                result.append(dict(row))
        return result

    async def admin_has_weapon_name(self, name: str) -> bool:
        """检查装备名称是否已存在（不区分大小写，忽略首尾空白）。"""
        async with self.db.execute(
            """
            SELECT 1
            FROM weapons
            WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
            LIMIT 1
            """,
            (name,),
        ) as cur:
            row = await cur.fetchone()
            return row is not None

    async def admin_create_weapon(self, data: dict[str, Any]) -> bool:
        cur = await self.db.execute(
            """
            INSERT OR IGNORE INTO weapons (
                equip_id, name, tier, slot, attack, defense, hp,
                element, element_damage, description, enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["equip_id"],
                data["name"],
                int(data["tier"]),
                data["slot"],
                int(data.get("attack", 0)),
                int(data.get("defense", 0)),
                int(data.get("hp", 0)),
                str(data.get("element", "无") or "无"),
                int(data.get("element_damage", 0)),
                str(data.get("description", "")),
                int(data.get("enabled", 1)),
            ),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def admin_update_weapon(self, equip_id: str, data: dict[str, Any]) -> bool:
        cur = await self.db.execute(
            """
            UPDATE weapons
            SET name = ?, tier = ?, slot = ?, attack = ?, defense = ?, hp = ?,
                element = ?, element_damage = ?, description = ?, enabled = ?
            WHERE equip_id = ?
            """,
            (
                data["name"],
                int(data["tier"]),
                data["slot"],
                int(data.get("attack", 0)),
                int(data.get("defense", 0)),
                int(data.get("hp", 0)),
                str(data.get("element", "无") or "无"),
                int(data.get("element_damage", 0)),
                str(data.get("description", "")),
                int(data.get("enabled", 1)),
                equip_id,
            ),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def admin_delete_weapon(self, equip_id: str) -> bool:
        cur = await self.db.execute(
            "DELETE FROM weapons WHERE equip_id = ?",
            (equip_id,),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    # ── 坊市 (Market) CRUD ──────────────────────────────────

    async def insert_market_listing(self, listing: dict) -> None:
        """插入一条上架记录。"""
        await self.db.execute(
            """INSERT INTO market_listings
               (listing_id, seller_id, item_id, quantity, unit_price,
                total_price, fee, listed_at, expires_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                listing["listing_id"],
                listing["seller_id"],
                listing["item_id"],
                listing["quantity"],
                listing["unit_price"],
                listing["total_price"],
                listing["fee"],
                listing["listed_at"],
                listing["expires_at"],
                listing.get("status", "active"),
            ),
        )
        await self.db.commit()

    async def get_active_listings(
        self,
        page: int = 1,
        page_size: int = 20,
        item_id: str | None = None,
        seller_id: str | None = None,
    ) -> dict:
        """分页查询活跃商品。"""
        conditions = ["status = 'active'"]
        params: list = []
        if item_id:
            conditions.append("item_id = ?")
            params.append(item_id)
        if seller_id:
            conditions.append("seller_id = ?")
            params.append(seller_id)
        where = " AND ".join(conditions)

        try:
            page = int(page)
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(page_size)
        except (TypeError, ValueError):
            page_size = 20
        page = max(1, page)
        page_size = max(1, page_size)

        row = await self.db.execute(
            f"SELECT COUNT(*) FROM market_listings WHERE {where}", params,
        )
        total = (await row.fetchone())[0]
        total_pages = max(1, (total + page_size - 1) // page_size)
        page = min(page, total_pages)

        offset = (page - 1) * page_size
        params_page = list(params) + [page_size, offset]
        cur = await self.db.execute(
            f"""SELECT * FROM market_listings
                WHERE {where}
                ORDER BY listed_at DESC
                LIMIT ? OFFSET ?""",
            params_page,
        )
        rows = await cur.fetchall()
        columns = [d[0] for d in cur.description]
        listings = [dict(zip(columns, r)) for r in rows]
        return {
            "listings": listings,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    async def get_listing_by_id(self, listing_id: str) -> dict | None:
        """单条查询上架记录。"""
        cur = await self.db.execute(
            "SELECT * FROM market_listings WHERE listing_id = ?",
            (listing_id,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        columns = [d[0] for d in cur.description]
        return dict(zip(columns, row))

    async def get_listing_by_id_prefix(self, prefix: str) -> dict | None:
        """通过 listing_id 前缀模糊查询（聊天端短编号）。"""
        cur = await self.db.execute(
            "SELECT * FROM market_listings WHERE listing_id LIKE ? AND status = 'active'",
            (prefix + "%",),
        )
        rows = await cur.fetchall()
        if len(rows) != 1:
            return None
        columns = [d[0] for d in cur.description]
        return dict(zip(columns, rows[0]))

    async def update_listing_status(
        self,
        listing_id: str,
        status: str,
        buyer_id: str | None = None,
        sold_at: float | None = None,
        expected_status: str | None = None,
    ) -> int:
        """更新上架状态，返回受影响行数。"""
        if expected_status:
            cur = await self.db.execute(
                """UPDATE market_listings
                   SET status = ?, buyer_id = ?, sold_at = ?
                   WHERE listing_id = ? AND status = ?""",
                (status, buyer_id, sold_at, listing_id, expected_status),
            )
        else:
            cur = await self.db.execute(
                """UPDATE market_listings
                   SET status = ?, buyer_id = ?, sold_at = ?
                   WHERE listing_id = ?""",
                (status, buyer_id, sold_at, listing_id),
            )
        await self.db.commit()
        return cur.rowcount

    async def insert_market_history(self, record: dict) -> None:
        """插入成交记录。"""
        await self.db.execute(
            """INSERT INTO market_history
               (history_id, item_id, quantity, unit_price, total_price,
                fee, seller_id, buyer_id, sold_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record["history_id"],
                record["item_id"],
                record["quantity"],
                record["unit_price"],
                record["total_price"],
                record["fee"],
                record["seller_id"],
                record["buyer_id"],
                record["sold_at"],
            ),
        )
        await self.db.commit()

    async def get_market_stats(self, item_id: str, days: int = 7) -> dict:
        """获取指定物品近 N 天的均价和成交量。"""
        import time as _time
        cutoff = _time.time() - days * 86400
        cur = await self.db.execute(
            """SELECT COUNT(*) as cnt,
                      COALESCE(AVG(unit_price), 0) as avg_price,
                      COALESCE(SUM(quantity), 0) as total_qty
               FROM market_history
               WHERE item_id = ? AND sold_at >= ?""",
            (item_id, cutoff),
        )
        row = await cur.fetchone()
        return {
            "count": row[0],
            "avg_price": row[1],
            "total_quantity": row[2],
        }

    async def get_expired_active_listings(self, now: float) -> list[dict]:
        """查询已过期但仍为 active 的上架记录。"""
        cur = await self.db.execute(
            "SELECT * FROM market_listings WHERE status = 'active' AND expires_at <= ?",
            (now,),
        )
        rows = await cur.fetchall()
        if not rows:
            return []
        columns = [d[0] for d in cur.description]
        return [dict(zip(columns, r)) for r in rows]

    async def get_my_listings(self, seller_id: str) -> list[dict]:
        """查询某玩家的所有上架记录（按时间倒序，最多50条）。"""
        cur = await self.db.execute(
            """SELECT * FROM market_listings
               WHERE seller_id = ?
               ORDER BY listed_at DESC
               LIMIT 50""",
            (seller_id,),
        )
        rows = await cur.fetchall()
        if not rows:
            return []
        columns = [d[0] for d in cur.description]
        return [dict(zip(columns, r)) for r in rows]

    async def clear_my_listing_history(self, seller_id: str, include_expired: bool = False) -> int:
        """清理某玩家历史上架记录（已售/已下架，可选含已过期），返回删除条数。"""
        statuses = ["sold", "cancelled"]
        if include_expired:
            statuses.append("expired")
        placeholders = ",".join("?" for _ in statuses)
        params = [seller_id] + statuses
        cur = await self.db.execute(
            f"""DELETE FROM market_listings
               WHERE seller_id = ? AND status IN ({placeholders})""",
            params,
        )
        await self.db.commit()
        return int(cur.rowcount or 0)

    async def admin_list_market_listings(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str = "",
        keyword: str = "",
    ) -> dict:
        """管理员分页查询坊市记录（支持状态/关键词过滤）。"""
        try:
            page = int(page)
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(page_size)
        except (TypeError, ValueError):
            page_size = 20
        page = max(1, page)
        page_size = min(100, max(1, page_size))

        conditions = ["1=1"]
        params: list[Any] = []

        if status:
            conditions.append("status = ?")
            params.append(status)

        keyword = str(keyword or "").strip()
        if keyword:
            like_kw = f"%{keyword}%"
            conditions.append(
                "(listing_id LIKE ? OR seller_id LIKE ? OR item_id LIKE ? OR COALESCE(buyer_id, '') LIKE ?)"
            )
            params.extend([like_kw, like_kw, like_kw, like_kw])

        where = " AND ".join(conditions)

        row = await self.db.execute(
            f"SELECT COUNT(*) FROM market_listings WHERE {where}",
            params,
        )
        total = int((await row.fetchone())[0])
        total_pages = max(1, (total + page_size - 1) // page_size)
        page = min(page, total_pages)

        offset = (page - 1) * page_size
        cur = await self.db.execute(
            f"""SELECT * FROM market_listings
               WHERE {where}
               ORDER BY listed_at DESC
               LIMIT ? OFFSET ?""",
            list(params) + [page_size, offset],
        )
        rows = await cur.fetchall()
        columns = [d[0] for d in cur.description]
        listings = [dict(zip(columns, r)) for r in rows]
        return {
            "listings": listings,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    async def admin_create_market_listing(self, data: dict[str, Any]) -> bool:
        """管理员新增坊市记录。"""
        cur = await self.db.execute(
            """INSERT OR IGNORE INTO market_listings
               (listing_id, seller_id, item_id, quantity, unit_price, total_price,
                fee, listed_at, expires_at, status, buyer_id, sold_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["listing_id"],
                data["seller_id"],
                data["item_id"],
                int(data["quantity"]),
                int(data["unit_price"]),
                int(data["total_price"]),
                int(data.get("fee", 0)),
                float(data["listed_at"]),
                float(data["expires_at"]),
                str(data.get("status", "active")),
                (str(data.get("buyer_id", "")).strip() or None),
                (float(data["sold_at"]) if data.get("sold_at") is not None else None),
            ),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def admin_update_market_listing(self, listing_id: str, data: dict[str, Any]) -> bool:
        """管理员更新坊市记录。"""
        cur = await self.db.execute(
            """UPDATE market_listings
               SET seller_id = ?, item_id = ?, quantity = ?, unit_price = ?, total_price = ?,
                   fee = ?, listed_at = ?, expires_at = ?, status = ?, buyer_id = ?, sold_at = ?
               WHERE listing_id = ?""",
            (
                data["seller_id"],
                data["item_id"],
                int(data["quantity"]),
                int(data["unit_price"]),
                int(data["total_price"]),
                int(data.get("fee", 0)),
                float(data["listed_at"]),
                float(data["expires_at"]),
                str(data.get("status", "active")),
                (str(data.get("buyer_id", "")).strip() or None),
                (float(data["sold_at"]) if data.get("sold_at") is not None else None),
                listing_id,
            ),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def admin_delete_market_listing(self, listing_id: str) -> bool:
        """管理员删除坊市记录。"""
        cur = await self.db.execute(
            "DELETE FROM market_listings WHERE listing_id = ?",
            (listing_id,),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    # ── 天机阁（商店） ──────────────────────────────────────

    async def get_shop_sold_today(self, item_id: str, date_str: str) -> int:
        """获取某商品今日全服已购总数。"""
        cur = await self.db.execute(
            "SELECT COALESCE(SUM(quantity), 0) FROM shop_purchases WHERE item_id = ? AND purchased_at = ?",
            (item_id, date_str),
        )
        row = await cur.fetchone()
        return row[0] if row else 0

    async def get_player_shop_today(self, user_id: str, date_str: str) -> list[dict]:
        """获取某玩家今日购买记录。"""
        cur = await self.db.execute(
            "SELECT item_id, SUM(quantity) as qty, unit_price FROM shop_purchases WHERE user_id = ? AND purchased_at = ? GROUP BY item_id",
            (user_id, date_str),
        )
        rows = await cur.fetchall()
        return [{"item_id": r[0], "quantity": r[1], "unit_price": r[2]} for r in rows]

    async def record_shop_purchase(self, user_id: str, item_id: str, quantity: int, unit_price: int, date_str: str):
        """记录一笔天机阁购买。"""
        await self.db.execute(
            "INSERT INTO shop_purchases (user_id, item_id, quantity, unit_price, purchased_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, item_id, quantity, unit_price, date_str),
        )
        await self.db.commit()

    async def reserve_shop_purchase(
        self,
        user_id: str,
        item_id: str,
        quantity: int,
        unit_price: int,
        date_str: str,
        daily_limit: int,
    ) -> dict[str, int | bool]:
        """串行预占商店库存，避免并发下超卖。"""
        async with self._shop_purchase_lock:
            cur = await self.db.execute(
                "SELECT COALESCE(SUM(quantity), 0) FROM shop_purchases WHERE item_id = ? AND purchased_at = ?",
                (item_id, date_str),
            )
            row = await cur.fetchone()
            sold_today = int(row[0] or 0) if row else 0
            remaining = max(0, int(daily_limit) - sold_today)
            if quantity > remaining:
                return {"success": False, "remaining": remaining, "sold_today": sold_today}

            await self.db.execute(
                "INSERT INTO shop_purchases (user_id, item_id, quantity, unit_price, purchased_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, item_id, quantity, unit_price, date_str),
            )
            await self.db.commit()
            return {
                "success": True,
                "remaining": remaining - quantity,
                "sold_today": sold_today + quantity,
            }

    async def commit_shop_purchase_atomic(
        self,
        player: Player,
        item_id: str,
        quantity: int,
        unit_price: int,
        date_str: str,
        daily_limit: int = 0,
    ) -> dict[str, int | bool]:
        """以单个事务提交商店购买记录和玩家状态。"""
        conn: aiosqlite.Connection | None = None
        last_exc = None
        for attempt in range(8 + 1):
            try:
                conn = await aiosqlite.connect(self._db_path, timeout=60.0)
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA busy_timeout=60000")
                await conn.execute("BEGIN IMMEDIATE")

                sold_today = 0
                remaining = 0
                if daily_limit > 0:
                    cur = await conn.execute(
                        "SELECT COALESCE(SUM(quantity), 0) FROM shop_purchases WHERE item_id = ? AND purchased_at = ?",
                        (item_id, date_str),
                    )
                    row = await cur.fetchone()
                    sold_today = int(row[0] or 0) if row else 0
                    remaining = max(0, int(daily_limit) - sold_today)
                    if quantity > remaining:
                        await conn.rollback()
                        return {"success": False, "remaining": remaining, "sold_today": sold_today}

                await conn.execute(
                    "INSERT INTO shop_purchases (user_id, item_id, quantity, unit_price, purchased_at) VALUES (?, ?, ?, ?, ?)",
                    (player.user_id, item_id, quantity, unit_price, date_str),
                )
                await self._upsert_player(player, db=conn)
                await conn.commit()
                return {
                    "success": True,
                    "remaining": max(0, remaining - quantity) if daily_limit > 0 else 0,
                    "sold_today": sold_today + quantity,
                }
            except aiosqlite.OperationalError as exc:
                msg = str(exc).lower()
                if conn is not None:
                    try:
                        await conn.rollback()
                    except Exception:
                        pass
                if "database is locked" in msg or "busy" in msg:
                    last_exc = exc
                    delay = 0.15 * (2 ** attempt) + 0.05
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise
            finally:
                if conn is not None:
                    try:
                        await conn.close()
                    except Exception:
                        pass

        logger.warning("商店购买锁定超时（已重试 %d 次）", 8)
        raise aiosqlite.OperationalError(
            f"database is locked (retried {8} times)"
        ) from last_exc if last_exc else None

    # ── 公告管理 ────────────────────────────────────────────
    async def get_active_announcements(self) -> list[dict]:
        """获取所有启用的公告。"""
        result = []
        async with self.db.execute(
            "SELECT id, title, content, created_at, updated_at FROM announcements WHERE enabled=1 ORDER BY id DESC"
        ) as cur:
            async for row in cur:
                result.append({
                    "id": row[0], "title": row[1], "content": row[2],
                    "created_at": row[3], "updated_at": row[4],
                })
        return result

    async def admin_list_announcements(self) -> list[dict]:
        """管理员获取全量公告列表。"""
        result = []
        async with self.db.execute(
            "SELECT id, title, content, enabled, created_at, updated_at FROM announcements ORDER BY id DESC"
        ) as cur:
            async for row in cur:
                result.append({
                    "id": row[0], "title": row[1], "content": row[2],
                    "enabled": row[3], "created_at": row[4], "updated_at": row[5],
                })
        return result

    async def admin_create_announcement(self, title: str, content: str) -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = await self.db.execute(
            "INSERT INTO announcements (title, content, enabled, created_at, updated_at) VALUES (?, ?, 1, ?, ?)",
            (title, content, now, now),
        )
        await self.db.commit()
        return int(cur.lastrowid or 0)

    async def admin_update_announcement(self, ann_id: int, title: str, content: str, enabled: int) -> bool:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = await self.db.execute(
            """
            UPDATE announcements
            SET title = ?, content = ?, enabled = ?, updated_at = ?
            WHERE id = ?
            """,
            (title, content, enabled, now, ann_id),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def admin_delete_announcement(self, ann_id: int) -> bool:
        cur = await self.db.execute(
            "DELETE FROM announcements WHERE id = ?",
            (ann_id,),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    # ── 关于页面 ──────────────────────────────────────────────

    async def get_about_page(self) -> dict:
        """获取关于页面内容"""
        cur = await self.db.execute(
            "SELECT acknowledgements, rules, updated_at FROM about_page WHERE id = 1"
        )
        row = await cur.fetchone()
        if row:
            return {
                "acknowledgements": row[0] or "",
                "rules": row[1] or "",
                "updated_at": row[2] or "",
            }
        return {"acknowledgements": "", "rules": "", "updated_at": ""}

    async def admin_update_about_page(self, acknowledgements: str, rules: str) -> bool:
        """更新关于页面内容"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = await self.db.execute(
            "UPDATE about_page SET acknowledgements = ?, rules = ?, updated_at = ? WHERE id = 1",
            (acknowledgements, rules, now),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    # ── 音效配置 ──────────────────────────────────────────────

    async def get_audio_config(self) -> dict:
        """获取音效配置"""
        cur = await self.db.execute(
            """SELECT enabled, music_enabled, sound_volume, music_volume,
               sound_coins, sound_button, sound_task, sound_equip, sound_attack, music_bgm
               FROM audio_config WHERE id = 1"""
        )
        row = await cur.fetchone()
        if row:
            return {
                "enabled": bool(row[0]),
                "music_enabled": bool(row[1]),
                "sound_volume": row[2] or 0.7,
                "music_volume": row[3] or 0.5,
                "sound_coins": row[4] or "",
                "sound_button": row[5] or "",
                "sound_task": row[6] or "",
                "sound_equip": row[7] or "",
                "sound_attack": row[8] or "",
                "music_bgm": row[9] or "",
            }
        return {
            "enabled": False,
            "music_enabled": False,
            "sound_volume": 0.7,
            "music_volume": 0.5,
            "sound_coins": "",
            "sound_button": "",
            "sound_task": "",
            "sound_equip": "",
            "sound_attack": "",
            "music_bgm": "",
        }

    async def update_audio_config(
        self,
        enabled: bool = None,
        music_enabled: bool = None,
        sound_volume: float = None,
        music_volume: float = None,
    ) -> dict:
        """更新玩家音效设置"""
        updates = []
        params = []
        if enabled is not None:
            updates.append("enabled = ?")
            params.append(1 if enabled else 0)
        if music_enabled is not None:
            updates.append("music_enabled = ?")
            params.append(1 if music_enabled else 0)
        if sound_volume is not None:
            updates.append("sound_volume = ?")
            params.append(sound_volume)
        if music_volume is not None:
            updates.append("music_volume = ?")
            params.append(music_volume)
        
        if not updates:
            return {"success": False, "message": "没有要更新的设置"}
        
        params.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        cur = await self.db.execute(
            f"UPDATE audio_config SET {', '.join(updates)}, updated_at = ? WHERE id = 1",
            params,
        )
        await self.db.commit()
        return {"success": True, "message": "设置已保存"}

    async def admin_update_audio_files(self, audio_type: str, file_path: str) -> dict:
        """管理员更新音效文件配置"""
        valid_types = ["sound_coins", "sound_button", "sound_task", "sound_equip", "sound_attack", "music_bgm"]
        if audio_type not in valid_types:
            return {"success": False, "message": "无效的音效类型"}
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = await self.db.execute(
            f"UPDATE audio_config SET {audio_type} = ?, updated_at = ? WHERE id = 1",
            (file_path, now),
        )
        await self.db.commit()
        return {"success": True, "message": f"音效文件已更新: {audio_type}"}

    # ── 世界频道消息 ──────────────────────────────────────────

    async def save_chat_message(
        self,
        user_id: str,
        name: str,
        realm: str,
        content: str,
        created_at: float,
        sect_name: str = "",
        sect_role: str = "",
        sect_role_name: str = "",
    ):
        """保存一条世界频道消息到数据库。"""
        await self.db.execute(
            "INSERT INTO world_chat_messages (user_id, name, realm, content, created_at, sect_name, sect_role, sect_role_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, name, realm, content, created_at, sect_name, sect_role, sect_role_name),
        )
        await self.db.commit()

    async def load_chat_history(self, limit: int = 100, max_age_seconds: float | None = None) -> list[dict]:
        """从数据库加载最近的世界频道消息（按时间升序）。"""
        if max_age_seconds is not None:
            cutoff = time.time() - max_age_seconds
            cursor = await self.db.execute(
                "SELECT user_id, name, realm, content, created_at, sect_name, sect_role, sect_role_name "
                "FROM world_chat_messages "
                "WHERE created_at >= ? "
                "ORDER BY created_at DESC LIMIT ?",
                (cutoff, limit),
            )
        else:
            cursor = await self.db.execute(
                "SELECT user_id, name, realm, content, created_at, sect_name, sect_role, sect_role_name FROM world_chat_messages ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        rows = await cursor.fetchall()
        result = []
        for row in reversed(rows):
            result.append({
                "user_id": row[0],
                "name": row[1],
                "realm": row[2],
                "content": row[3],
                "time": row[4],
                "sect_name": row[5] if len(row) > 5 else "",
                "sect_role": row[6] if len(row) > 6 else "",
                "sect_role_name": row[7] if len(row) > 7 else "",
            })
        return result

    async def cleanup_old_chat_messages(self, max_age_seconds: float) -> int:
        """删除超过指定时间的世界频道消息，返回删除条数。"""
        cutoff = time.time() - max_age_seconds
        cur = await self.db.execute(
            "DELETE FROM world_chat_messages WHERE created_at < ?",
            (cutoff,),
        )
        await self.db.commit()
        return cur.rowcount or 0

    # ── 家族 CRUD ──────────────────────────────────────────

    async def save_sect(self, sect: dict) -> None:
        """新增家族记录。"""
        await self._ensure_sect_schema()
        await self.db.execute(
            """INSERT INTO sects
               (sect_id, name, leader_id, description, level, spirit_stones,
                max_members, join_policy, min_realm, created_at, announcement,
                warehouse_capacity)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                sect["sect_id"],
                sect["name"],
                sect["leader_id"],
                sect.get("description", ""),
                sect.get("level", 1),
                sect.get("spirit_stones", 0),
                sect.get("max_members", 30),
                sect.get("join_policy", "open"),
                sect.get("min_realm", 0),
                sect["created_at"],
                sect.get("announcement", ""),
sect.get("warehouse_capacity", 200),
            ),
        )
        await self.db.commit()

    async def create_sect_with_leader(self, sect: dict, leader_user_id: str) -> None:
        """原子创建家族及宗主成员关系。"""
        await self._ensure_sect_schema()
        try:
            await self.db.execute(
                """INSERT INTO sects
                   (sect_id, name, leader_id, description, level, spirit_stones,
                    max_members, join_policy, min_realm, created_at,
                    announcement, warehouse_capacity)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    sect["sect_id"],
                    sect["name"],
                    sect["leader_id"],
                    sect.get("description", ""),
                    sect.get("level", 1),
                    sect.get("spirit_stones", 0),
                    sect.get("max_members", 30),
                    sect.get("join_policy", "open"),
                    sect.get("min_realm", 0),
                    sect["created_at"],
                    sect.get("announcement", ""),
                    sect.get("warehouse_capacity", 200),
                ),
            )
            await self.db.execute(
                """INSERT INTO sect_members (user_id, sect_id, role, joined_at)
                   VALUES (?, ?, ?, ?)""",
                (leader_user_id, sect["sect_id"], "leader", time.time()),
            )
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

    async def delete_sect(self, sect_id: str) -> None:
        """删除家族及其所有成员关系和申请记录。"""
        await self.db.execute("DELETE FROM sect_members WHERE sect_id = ?", (sect_id,))
        await self.db.execute("DELETE FROM sect_applications WHERE sect_id = ?", (sect_id,))
        await self.db.execute("DELETE FROM sects WHERE sect_id = ?", (sect_id,))
        await self.db.commit()

    async def load_sect(self, sect_id: str) -> dict | None:
        """按 sect_id 加载家族。"""
        await self._ensure_sect_schema()
        cur = await self.db.execute("SELECT * FROM sects WHERE sect_id = ?", (sect_id,))
        row = await cur.fetchone()
        if not row:
            return None
        columns = [d[0] for d in cur.description]
        return dict(zip(columns, row))

    async def load_sect_by_name(self, name: str) -> dict | None:
        """按名称加载家族。"""
        await self._ensure_sect_schema()
        cur = await self.db.execute("SELECT * FROM sects WHERE name = ?", (name,))
        row = await cur.fetchone()
        if not row:
            return None
        columns = [d[0] for d in cur.description]
        return dict(zip(columns, row))

    async def load_sects_page(self, page: int = 1, page_size: int = 10) -> dict:
        """分页查询家族列表（含成员计数）。"""
        await self._ensure_sect_schema()
        try:
            page = int(page)
        except (TypeError, ValueError):
            page = 1
        page = max(1, page)
        page_size = max(1, min(page_size, 50))

        row = await self.db.execute("SELECT COUNT(*) FROM sects")
        total = (await row.fetchone())[0]
        total_pages = max(1, (total + page_size - 1) // page_size)
        page = min(page, total_pages)
        offset = (page - 1) * page_size

        cur = await self.db.execute(
            """SELECT s.*, COUNT(m.user_id) AS member_count
               FROM sects s
               LEFT JOIN sect_members m ON s.sect_id = m.sect_id
               GROUP BY s.sect_id
               ORDER BY s.created_at DESC
               LIMIT ? OFFSET ?""",
            (page_size, offset),
        )
        rows = await cur.fetchall()
        columns = [d[0] for d in cur.description]
        sects = [dict(zip(columns, r)) for r in rows]
        return {
            "sects": sects,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    async def update_sect_info(self, sect_id: str, data: dict) -> None:
        """更新家族可变字段（description, join_policy, min_realm, announcement）。"""
        await self._ensure_sect_schema()
        allowed = {"description", "join_policy", "min_realm", "announcement"}
        sets = []
        params = []
        for k, v in data.items():
            if k in allowed:
                sets.append(f"{k} = ?")
                params.append(v)
        if not sets:
            return
        params.append(sect_id)
        await self.db.execute(
            f"UPDATE sects SET {', '.join(sets)} WHERE sect_id = ?",
            params,
        )
        await self.db.commit()

    async def update_sect_leader(self, sect_id: str, new_leader_id: str) -> None:
        """更新家族宗主。"""
        await self._ensure_sect_schema()
        await self.db.execute(
            "UPDATE sects SET leader_id = ? WHERE sect_id = ?",
            (new_leader_id, sect_id),
        )
        await self.db.commit()

    # ── 家族成员 CRUD ──────────────────────────────────────

    async def save_sect_member(self, user_id: str, sect_id: str, role: str = "disciple") -> None:
        """添加家族成员。"""
        await self._ensure_sect_schema()
        import time as _time
        await self.db.execute(
            """INSERT OR REPLACE INTO sect_members (user_id, sect_id, role, joined_at)
               VALUES (?, ?, ?, ?)""",
            (user_id, sect_id, role, _time.time()),
        )
        await self.db.commit()

    async def delete_sect_member(self, user_id: str) -> None:
        """移除家族成员。"""
        await self.db.execute("DELETE FROM sect_members WHERE user_id = ?", (user_id,))
        await self.db.commit()

    async def load_sect_members(self, sect_id: str) -> list[dict]:
        """加载家族所有成员（含玩家名、爵位和贡献点）。"""
        await self._ensure_sect_schema()
        cur = await self.db.execute(
            """SELECT m.user_id, m.role, m.joined_at, m.contribution_points,
                      p.name AS player_name, p.realm, p.sub_realm
               FROM sect_members m
               LEFT JOIN players p ON m.user_id = p.user_id
               WHERE m.sect_id = ?
               ORDER BY
                   CASE m.role
                       WHEN 'leader' THEN 0
                       WHEN 'vice_leader' THEN 1
                       WHEN 'elder' THEN 2
                       ELSE 3
                   END,
                   m.joined_at ASC""",
            (sect_id,),
        )
        rows = await cur.fetchall()
        columns = [d[0] for d in cur.description]
        return [dict(zip(columns, r)) for r in rows]

    async def load_player_sect(self, user_id: str) -> dict | None:
        """查询玩家所在家族（返回成员记录）。"""
        await self._ensure_sect_schema()
        cur = await self.db.execute(
            "SELECT * FROM sect_members WHERE user_id = ?", (user_id,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        columns = [d[0] for d in cur.description]
        return dict(zip(columns, row))

    async def count_sect_members(self, sect_id: str) -> int:
        """统计家族成员数。"""
        await self._ensure_sect_schema()
        cur = await self.db.execute(
            "SELECT COUNT(*) FROM sect_members WHERE sect_id = ?", (sect_id,),
        )
        return (await cur.fetchone())[0]

    async def count_members_by_role(self, sect_id: str, role: str) -> int:
        """统计家族某身份的成员数。"""
        await self._ensure_sect_schema()
        cur = await self.db.execute(
            "SELECT COUNT(*) FROM sect_members WHERE sect_id = ? AND role = ?",
            (sect_id, role),
        )
        return (await cur.fetchone())[0]

    async def update_sect_member_role(self, user_id: str, role: str) -> None:
        """更新成员身份。"""
        await self._ensure_sect_schema()
        await self.db.execute(
            "UPDATE sect_members SET role = ? WHERE user_id = ?",
            (role, user_id),
        )
        await self.db.commit()

    # ── 家族仓库 ──────────────────────────────────────────

    async def get_sect_warehouse(self, sect_id: str) -> list[dict]:
        """获取家族仓库所有物品。"""
        await self._ensure_sect_schema()
        cur = await self.db.execute(
            "SELECT item_id, quantity FROM sect_warehouse WHERE sect_id = ? AND quantity > 0",
            (sect_id,),
        )
        rows = await cur.fetchall()
        return [{"item_id": r[0], "quantity": r[1]} for r in rows]

    async def get_sect_warehouse_item(self, sect_id: str, item_id: str) -> int:
        """获取家族仓库中某物品数量。"""
        await self._ensure_sect_schema()
        cur = await self.db.execute(
            "SELECT quantity FROM sect_warehouse WHERE sect_id = ? AND item_id = ?",
            (sect_id, item_id),
        )
        row = await cur.fetchone()
        return row[0] if row else 0

    async def get_sect_warehouse_slot_count(self, sect_id: str) -> int:
        """获取家族仓库已使用格数（不同物品种类数）。"""
        await self._ensure_sect_schema()
        cur = await self.db.execute(
            "SELECT COUNT(*) FROM sect_warehouse WHERE sect_id = ? AND quantity > 0",
            (sect_id,),
        )
        return (await cur.fetchone())[0]

    async def add_sect_warehouse_item(self, sect_id: str, item_id: str, quantity: int) -> None:
        """向家族仓库添加物品。"""
        await self._ensure_sect_schema()
        await self.db.execute(
            """INSERT INTO sect_warehouse (sect_id, item_id, quantity)
               VALUES (?, ?, ?)
               ON CONFLICT(sect_id, item_id) DO UPDATE SET quantity = quantity + ?""",
            (sect_id, item_id, quantity, quantity),
        )
        await self.db.commit()

    async def remove_sect_warehouse_item(self, sect_id: str, item_id: str, quantity: int) -> bool:
        """从家族仓库移除物品，返回是否成功。"""
        await self._ensure_sect_schema()
        cur = await self.db.execute(
            "SELECT quantity FROM sect_warehouse WHERE sect_id = ? AND item_id = ?",
            (sect_id, item_id),
        )
        row = await cur.fetchone()
        if not row or row[0] < quantity:
            return False
        new_qty = row[0] - quantity
        if new_qty <= 0:
            await self.db.execute(
                "DELETE FROM sect_warehouse WHERE sect_id = ? AND item_id = ?",
                (sect_id, item_id),
            )
        else:
            await self.db.execute(
                "UPDATE sect_warehouse SET quantity = ? WHERE sect_id = ? AND item_id = ?",
                (new_qty, sect_id, item_id),
            )
        await self.db.commit()
        return True

    async def delete_sect_warehouse(self, sect_id: str) -> None:
        """删除家族仓库所有物品（解散家族时调用）。"""
        await self._ensure_sect_schema()
        await self.db.execute(
            "DELETE FROM sect_warehouse WHERE sect_id = ?", (sect_id,),
        )
        await self.db.commit()

    async def warehouse_deposit_atomic(
        self, player: "Player", sect_id: str, item_id: str, quantity: int,
        contribution_delta: int,
    ) -> dict:
        """独立连接事务：仓库入库 + 贡献点增加 + 玩家落库。

        返回 {"success": True, "contribution": int}
        或 {"success": False, "reason": ...}。
        """
        last_exc = None
        for attempt in range(8 + 1):
            conn: aiosqlite.Connection | None = None
            try:
                conn = await aiosqlite.connect(self._db_path, timeout=60.0)
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA busy_timeout=60000")
                await conn.execute("BEGIN IMMEDIATE")

                # 复检仓库容量
                cur = await conn.execute(
                    "SELECT warehouse_capacity FROM sects WHERE sect_id = ?", (sect_id,),
                )
                sect_row = await cur.fetchone()
                if not sect_row:
                    await conn.rollback()
                    return {"success": False, "reason": "sect_not_found"}
                capacity = sect_row[0] if sect_row[0] is not None else 200

                cur2 = await conn.execute(
                    "SELECT quantity FROM sect_warehouse WHERE sect_id = ? AND item_id = ?",
                    (sect_id, item_id),
                )
                existing = await cur2.fetchone()
                if not existing or existing[0] == 0:
                    cur3 = await conn.execute(
                        "SELECT COUNT(*) FROM sect_warehouse WHERE sect_id = ? AND quantity > 0",
                        (sect_id,),
                    )
                    slots_used = (await cur3.fetchone())[0]
                    if slots_used >= capacity:
                        await conn.rollback()
                        return {"success": False, "reason": "warehouse_full"}

                # 写仓库
                await conn.execute(
                    """INSERT INTO sect_warehouse (sect_id, item_id, quantity)
                       VALUES (?, ?, ?)
                       ON CONFLICT(sect_id, item_id) DO UPDATE SET quantity = quantity + ?""",
                    (sect_id, item_id, quantity, quantity),
                )

                # 加贡献点（校验成员仍在该家族）
                cur_contrib = await conn.execute(
                    "UPDATE sect_members SET contribution_points = contribution_points + ? "
                    "WHERE user_id = ? AND sect_id = ?",
                    (contribution_delta, player.user_id, sect_id),
                )
                if cur_contrib.rowcount == 0:
                    await conn.rollback()
                    return {"success": False, "reason": "member_not_found"}

                # 玩家落库
                await self._upsert_player(player, db=conn)
                await conn.commit()

                # 事务完成后读贡献点（用主连接）
                new_contribution = await self.get_member_contribution(player.user_id)
                return {"success": True, "contribution": new_contribution}
            except aiosqlite.OperationalError as exc:
                msg = str(exc).lower()
                if conn is not None:
                    try:
                        await conn.rollback()
                    except Exception:
                        pass
                if "database is locked" in msg or "busy" in msg:
                    last_exc = exc
                    delay = 0.15 * (2 ** attempt) + 0.05
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise
            except Exception as e:
                if conn is not None:
                    try:
                        await conn.rollback()
                    except Exception:
                        pass
                raise e
            finally:
                if conn is not None:
                    try:
                        await conn.close()
                    except Exception:
                        pass

        logger.warning("仓库入库锁定超时（已重试 %d 次）", 8)
        raise aiosqlite.OperationalError(
            f"database is locked (retried {8} times)"
        ) from last_exc if last_exc else None

    async def warehouse_exchange_atomic(
        self, player: "Player", sect_id: str, item_id: str, quantity: int,
        contribution_cost: int,
    ) -> dict:
        """独立连接事务：条件扣贡献点 + 条件扣仓库 + 玩家落库。

        返回 {"success": True, "contribution": int}
        或 {"success": False, "reason": "insufficient_stock"|"insufficient_contribution"}。
        """
        last_exc = None
        for attempt in range(8 + 1):
            conn: aiosqlite.Connection | None = None
            try:
                conn = await aiosqlite.connect(self._db_path, timeout=60.0)
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA busy_timeout=60000")
                await conn.execute("BEGIN IMMEDIATE")

                # 条件扣贡献点
                cur = await conn.execute(
                    "UPDATE sect_members "
                    "SET contribution_points = contribution_points - ? "
                    "WHERE user_id = ? AND sect_id = ? AND contribution_points >= ?",
                    (contribution_cost, player.user_id, sect_id, contribution_cost),
                )
                if cur.rowcount == 0:
                    await conn.rollback()
                    return {"success": False, "reason": "insufficient_contribution"}

                # 条件扣仓库
                cur2 = await conn.execute(
                    "UPDATE sect_warehouse "
                    "SET quantity = quantity - ? "
                    "WHERE sect_id = ? AND item_id = ? AND quantity >= ?",
                    (quantity, sect_id, item_id, quantity),
                )
                if cur2.rowcount == 0:
                    await conn.rollback()
                    return {"success": False, "reason": "insufficient_stock"}

                # 清理零库存行
                await conn.execute(
                    "DELETE FROM sect_warehouse WHERE sect_id = ? AND item_id = ? AND quantity <= 0",
                    (sect_id, item_id),
                )

                # 玩家落库
                await self._upsert_player(player, db=conn)
                await conn.commit()

                # 事务完成后读贡献点（用主连接）
                new_contribution = await self.get_member_contribution(player.user_id)
                return {"success": True, "contribution": new_contribution}
            except aiosqlite.OperationalError as exc:
                msg = str(exc).lower()
                if conn is not None:
                    try:
                        await conn.rollback()
                    except Exception:
                        pass
                if "database is locked" in msg or "busy" in msg:
                    last_exc = exc
                    delay = 0.15 * (2 ** attempt) + 0.05
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise
            except Exception as e:
                if conn is not None:
                    try:
                        await conn.rollback()
                    except Exception:
                        pass
                raise e
            finally:
                if conn is not None:
                    try:
                        await conn.close()
                    except Exception:
                        pass

        logger.warning("仓库兑换锁定超时（已重试 %d 次）", 8)
        raise aiosqlite.OperationalError(
            f"database is locked (retried {8} times)"
        ) from last_exc if last_exc else None

    # ── 家族贡献点规则 ────────────────────────────────────

    async def get_contribution_config(self, sect_id: str) -> list[dict]:
        """获取家族全部贡献点规则。"""
        await self._ensure_sect_schema()
        cur = await self.db.execute(
            "SELECT rule_type, target_key, points FROM sect_contribution_config WHERE sect_id = ?",
            (sect_id,),
        )
        rows = await cur.fetchall()
        return [{"rule_type": r[0], "target_key": r[1], "points": r[2]} for r in rows]

    async def get_contribution_config_by_key(
        self, sect_id: str, rule_type: str, target_key: str,
    ) -> int | None:
        """获取某条具体规则的贡献点数。"""
        await self._ensure_sect_schema()
        cur = await self.db.execute(
            "SELECT points FROM sect_contribution_config WHERE sect_id = ? AND rule_type = ? AND target_key = ?",
            (sect_id, rule_type, target_key),
        )
        row = await cur.fetchone()
        return row[0] if row else None

    async def set_contribution_config(
        self, sect_id: str, rule_type: str, target_key: str, points: int,
    ) -> None:
        """设置/更新一条贡献点规则。"""
        await self._ensure_sect_schema()
        await self.db.execute(
            """INSERT INTO sect_contribution_config (sect_id, rule_type, target_key, points)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(sect_id, rule_type, target_key) DO UPDATE SET points = ?""",
            (sect_id, rule_type, target_key, points, points),
        )
        await self.db.commit()

    async def delete_contribution_config(
        self, sect_id: str, rule_type: str, target_key: str,
    ) -> None:
        """删除一条贡献点规则。"""
        await self._ensure_sect_schema()
        await self.db.execute(
            "DELETE FROM sect_contribution_config WHERE sect_id = ? AND rule_type = ? AND target_key = ?",
            (sect_id, rule_type, target_key),
        )
        await self.db.commit()

    async def delete_all_contribution_config(self, sect_id: str) -> None:
        """删除家族所有贡献点规则（解散家族时调用）。"""
        await self._ensure_sect_schema()
        await self.db.execute(
            "DELETE FROM sect_contribution_config WHERE sect_id = ?", (sect_id,),
        )
        await self.db.commit()

    # ── 成员贡献点 ────────────────────────────────────────

    async def get_member_contribution(self, user_id: str) -> int:
        """获取成员贡献点。"""
        await self._ensure_sect_schema()
        cur = await self.db.execute(
            "SELECT contribution_points FROM sect_members WHERE user_id = ?",
            (user_id,),
        )
        row = await cur.fetchone()
        return row[0] if row else 0

    async def update_member_contribution(self, user_id: str, delta: int) -> int:
        """增减成员贡献点，返回新值。"""
        await self._ensure_sect_schema()
        await self.db.execute(
            "UPDATE sect_members SET contribution_points = MAX(0, contribution_points + ?) WHERE user_id = ?",
            (delta, user_id),
        )
        await self.db.commit()
        return await self.get_member_contribution(user_id)

    # ── 家族任务 ────────────────────────────────────────────

    async def create_sect_task(
        self,
        sect_id: str,
        creator_id: str,
        title: str,
        description: str,
        task_type: str,
        target_count: int,
        reward_points: int,
        reward_item_id: str = "",
        reward_item_count: int = 0,
        expires_hours: int = 24,
    ) -> int:
        """创建家族任务。"""
        await self._ensure_sect_schema()
        now = time.time()
        expires_at = now + expires_hours * 3600 if expires_hours > 0 else 0
        cur = await self.db.execute(
            """INSERT INTO sect_tasks 
               (sect_id, creator_id, title, description, task_type, target_count, 
                reward_points, reward_item_id, reward_item_count, status, created_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
            (sect_id, creator_id, title, description, task_type, target_count,
             reward_points, reward_item_id, reward_item_count, now, expires_at),
        )
        await self.db.commit()
        return cur.lastrowid or 0

    async def get_sect_tasks(self, sect_id: str, status: str = "") -> list[dict]:
        """获取家族任务列表。"""
        await self._ensure_sect_schema()
        now = time.time()
        if status:
            cur = await self.db.execute(
                "SELECT task_id, sect_id, creator_id, title, description, task_type, target_count, "
                "current_count, reward_points, reward_item_id, reward_item_count, status, created_at, expires_at "
                "FROM sect_tasks WHERE sect_id = ? AND status = ? ORDER BY created_at DESC",
                (sect_id, status),
            )
        else:
            cur = await self.db.execute(
                "SELECT task_id, sect_id, creator_id, title, description, task_type, target_count, "
                "current_count, reward_points, reward_item_id, reward_item_count, status, created_at, expires_at "
                "FROM sect_tasks WHERE sect_id = ? AND (status = 'active' OR expires_at = 0 OR expires_at > ?) ORDER BY created_at DESC",
                (sect_id, now),
            )
        rows = await cur.fetchall()
        return [{
            "task_id": r[0],
            "sect_id": r[1],
            "creator_id": r[2],
            "title": r[3],
            "description": r[4],
            "task_type": r[5],
            "target_count": r[6],
            "current_count": r[7],
            "reward_points": r[8],
            "reward_item_id": r[9],
            "reward_item_count": r[10],
            "status": r[11],
            "created_at": r[12],
            "expires_at": r[13],
            "is_expired": r[13] > 0 and r[13] < now,
        } for r in rows]

    async def get_task_by_id(self, task_id: int) -> dict | None:
        """获取任务详情。"""
        await self._ensure_sect_schema()
        cur = await self.db.execute(
            "SELECT task_id, sect_id, creator_id, title, description, task_type, target_count, "
            "current_count, reward_points, reward_item_id, reward_item_count, status, created_at, expires_at "
            "FROM sect_tasks WHERE task_id = ?",
            (task_id,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        now = time.time()
        return {
            "task_id": row[0],
            "sect_id": row[1],
            "creator_id": row[2],
            "title": row[3],
            "description": row[4],
            "task_type": row[5],
            "target_count": row[6],
            "current_count": row[7],
            "reward_points": row[8],
            "reward_item_id": row[9],
            "reward_item_count": row[10],
            "status": row[11],
            "created_at": row[12],
            "expires_at": row[13],
            "is_expired": row[13] > 0 and row[13] < now,
        }

    async def update_task_status(self, task_id: int, status: str) -> bool:
        """更新任务状态。"""
        await self._ensure_sect_schema()
        cur = await self.db.execute(
            "UPDATE sect_tasks SET status = ? WHERE task_id = ?",
            (status, task_id),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def update_task_progress(self, task_id: int, progress: int) -> bool:
        """更新任务进度。"""
        await self._ensure_sect_schema()
        cur = await self.db.execute(
            "UPDATE sect_tasks SET current_count = ? WHERE task_id = ?",
            (progress, task_id),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def delete_sect_task(self, task_id: int) -> bool:
        """删除任务。"""
        await self._ensure_sect_schema()
        await self.db.execute("DELETE FROM sect_task_members WHERE task_id = ?", (task_id,))
        cur = await self.db.execute("DELETE FROM sect_tasks WHERE task_id = ?", (task_id,))
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    # ── 任务参与 ────────────────────────────────────────────

    async def accept_task(self, task_id: int, user_id: str) -> bool:
        """接受任务。"""
        await self._ensure_sect_schema()
        now = time.time()
        try:
            await self.db.execute(
                "INSERT INTO sect_task_members (task_id, user_id, accepted_at) VALUES (?, ?, ?)",
                (task_id, user_id, now),
            )
            await self.db.commit()
            return True
        except Exception:
            return False

    async def get_task_member(self, task_id: int, user_id: str) -> dict | None:
        """获取成员任务参与情况。"""
        await self._ensure_sect_schema()
        cur = await self.db.execute(
            "SELECT id, task_id, user_id, progress, status, accepted_at, completed_at "
            "FROM sect_task_members WHERE task_id = ? AND user_id = ?",
            (task_id, user_id),
        )
        row = await cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "task_id": row[1],
            "user_id": row[2],
            "progress": row[3],
            "status": row[4],
            "accepted_at": row[5],
            "completed_at": row[6],
        }

    async def get_task_members(self, task_id: int) -> list[dict]:
        """获取任务所有参与者。"""
        await self._ensure_sect_schema()
        cur = await self.db.execute(
            "SELECT id, task_id, user_id, progress, status, accepted_at, completed_at "
            "FROM sect_task_members WHERE task_id = ?",
            (task_id,),
        )
        rows = await cur.fetchall()
        return [{
            "id": r[0],
            "task_id": r[1],
            "user_id": r[2],
            "progress": r[3],
            "status": r[4],
            "accepted_at": r[5],
            "completed_at": r[6],
        } for r in rows]

    async def update_task_member_progress(self, task_id: int, user_id: str, progress: int) -> bool:
        """更新成员任务进度。"""
        await self._ensure_sect_schema()
        cur = await self.db.execute(
            "UPDATE sect_task_members SET progress = ?, status = 'accepted' WHERE task_id = ? AND user_id = ?",
            (progress, task_id, user_id),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def complete_task_member(self, task_id: int, user_id: str) -> bool:
        """标记成员完成任务。"""
        await self._ensure_sect_schema()
        now = time.time()
        cur = await self.db.execute(
            "UPDATE sect_task_members SET status = 'completed', completed_at = ? WHERE task_id = ? AND user_id = ?",
            (now, task_id, user_id),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    # ── 邮件系统 ──────────────────────────────────────────────

    async def send_mail(self, sender_id: str, sender_name: str, receiver_id: str, title: str, content: str, attachments: str = "{}") -> int:
        """发送邮件。"""
        now = time.time()
        expires_at = now + 7 * 24 * 3600
        cur = await self.db.execute(
            """INSERT INTO mails (sender_id, sender_name, receiver_id, title, content, attachments, created_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (sender_id, sender_name, receiver_id, title, content, attachments, now, expires_at),
        )
        await self.db.commit()
        return int(cur.lastrowid or 0)

    async def get_mails(self, user_id: str, include_deleted: bool = False) -> list[dict]:
        """获取用户邮件列表。"""
        if include_deleted:
            cur = await self.db.execute(
                "SELECT mail_id, sender_id, sender_name, title, content, attachments, is_read, created_at, expires_at FROM mails WHERE receiver_id = ? ORDER BY created_at DESC",
                (user_id,),
            )
        else:
            cur = await self.db.execute(
                "SELECT mail_id, sender_id, sender_name, title, content, attachments, is_read, created_at, expires_at FROM mails WHERE receiver_id = ? AND is_deleted_receiver = 0 ORDER BY created_at DESC",
                (user_id,),
            )
        rows = await cur.fetchall()
        now = time.time()
        result = []
        for r in rows:
            if r[8] and r[8] < now:
                continue
            result.append({
                "mail_id": r[0],
                "sender_id": r[1],
                "sender_name": r[2],
                "title": r[3],
                "content": r[4],
                "attachments": json.loads(r[5]) if r[5] else {},
                "is_read": bool(r[6]),
                "created_at": r[7],
                "expires_at": r[8],
            })
        return result

    async def get_mail(self, mail_id: int, user_id: str) -> dict | None:
        """获取单封邮件。"""
        cur = await self.db.execute(
            "SELECT mail_id, sender_id, sender_name, receiver_id, title, content, attachments, is_read, created_at, expires_at FROM mails WHERE mail_id = ? AND receiver_id = ?",
            (mail_id, user_id),
        )
        row = await cur.fetchone()
        if not row:
            return None
        return {
            "mail_id": row[0],
            "sender_id": row[1],
            "sender_name": row[2],
            "receiver_id": row[3],
            "title": row[4],
            "content": row[5],
            "attachments": json.loads(row[6]) if row[6] else {},
            "is_read": bool(row[7]),
            "created_at": row[8],
            "expires_at": row[9],
        }

    async def mark_mail_read(self, mail_id: int, user_id: str) -> bool:
        """标记邮件为已读。"""
        cur = await self.db.execute(
            "UPDATE mails SET is_read = 1 WHERE mail_id = ? AND receiver_id = ?",
            (mail_id, user_id),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def delete_mail(self, mail_id: int, user_id: str) -> bool:
        """删除邮件。"""
        cur = await self.db.execute(
            "UPDATE mails SET is_deleted_receiver = 1 WHERE mail_id = ? AND receiver_id = ?",
            (mail_id, user_id),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    # ── 成就系统 ──────────────────────────────────────────────

    async def get_all_achievements(self) -> list[dict]:
        """获取所有成就定义。"""
        cur = await self.db.execute(
            "SELECT achievement_id, name, description, icon, condition_type, condition_value, reward_stones, reward_items, reward_title, sort_order FROM achievements ORDER BY sort_order"
        )
        rows = await cur.fetchall()
        return [{
            "achievement_id": r[0],
            "name": r[1],
            "description": r[2],
            "icon": r[3],
            "condition_type": r[4],
            "condition_value": r[5],
            "reward_stones": r[6],
            "reward_items": json.loads(r[7]) if r[7] else {},
            "reward_title": r[8],
            "sort_order": r[9],
        } for r in rows]

    async def get_player_achievements(self, user_id: str) -> list[dict]:
        """获取玩家成就进度。"""
        cur = await self.db.execute(
            "SELECT achievement_id, progress, completed, completed_at, claimed FROM player_achievements WHERE user_id = ?",
            (user_id,),
        )
        rows = await cur.fetchall()
        return [{
            "achievement_id": r[0],
            "progress": r[1],
            "completed": bool(r[2]),
            "completed_at": r[3],
            "claimed": bool(r[4]),
        } for r in rows]

    async def update_achievement_progress(self, user_id: str, achievement_id: str, progress: int) -> bool:
        """更新成就进度。"""
        cur = await self.db.execute(
            """INSERT INTO player_achievements (user_id, achievement_id, progress) VALUES (?, ?, ?)
               ON CONFLICT(user_id, achievement_id) DO UPDATE SET progress = ?""",
            (user_id, achievement_id, progress, progress),
        )
        await self.db.commit()
        return True

    async def complete_achievement(self, user_id: str, achievement_id: str) -> bool:
        """完成成就。"""
        now = time.time()
        cur = await self.db.execute(
            "UPDATE player_achievements SET completed = 1, completed_at = ? WHERE user_id = ? AND achievement_id = ?",
            (now, user_id, achievement_id),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def claim_achievement_reward(self, user_id: str, achievement_id: str) -> dict | None:
        """领取成就奖励。"""
        cur = await self.db.execute(
            "SELECT reward_stones, reward_items, reward_title FROM achievements WHERE achievement_id = ?",
            (achievement_id,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        
        cur2 = await self.db.execute(
            "UPDATE player_achievements SET claimed = 1 WHERE user_id = ? AND achievement_id = ?",
            (user_id, achievement_id),
        )
        await self.db.commit()
        
        return {
            "reward_stones": row[0] or 0,
            "reward_items": json.loads(row[1]) if row[1] else {},
            "reward_title": row[2],
        }

    async def admin_create_achievement(self, achievement_id: str, name: str, description: str, icon: str, condition_type: str, condition_value: int, reward_stones: int, reward_items: str, reward_title: str, sort_order: int = 0) -> bool:
        """管理员创建成就。"""
        cur = await self.db.execute(
            """INSERT OR REPLACE INTO achievements (achievement_id, name, description, icon, condition_type, condition_value, reward_stones, reward_items, reward_title, sort_order)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (achievement_id, name, description, icon, condition_type, condition_value, reward_stones, reward_items, reward_title, sort_order),
        )
        await self.db.commit()
        return True

    async def admin_delete_achievement(self, achievement_id: str) -> bool:
        """管理员删除成就。"""
        cur = await self.db.execute("DELETE FROM achievements WHERE achievement_id = ?", (achievement_id,))
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    # ── 称号系统 ──────────────────────────────────────────────

    async def get_all_titles(self) -> list[dict]:
        """获取所有称号定义。"""
        cur = await self.db.execute(
            "SELECT title_id, name, description, icon, color, prefix, bonus_attack, bonus_defense, bonus_hp, is_system FROM titles"
        )
        rows = await cur.fetchall()
        return [{
            "title_id": r[0],
            "name": r[1],
            "description": r[2],
            "icon": r[3],
            "color": r[4],
            "prefix": r[5],
            "bonus_attack": r[6],
            "bonus_defense": r[7],
            "bonus_hp": r[8],
            "is_system": bool(r[9]),
        } for r in rows]

    async def get_player_titles(self, user_id: str) -> list[dict]:
        """获取玩家拥有的称号。"""
        cur = await self.db.execute(
            "SELECT title_id, is_active, acquired_at FROM player_titles WHERE user_id = ?",
            (user_id,),
        )
        rows = await cur.fetchall()
        return [{
            "title_id": r[0],
            "is_active": bool(r[1]),
            "acquired_at": r[2],
        } for r in rows]

    async def grant_title(self, user_id: str, title_id: str) -> bool:
        """授予玩家称号。"""
        now = time.time()
        cur = await self.db.execute(
            """INSERT OR IGNORE INTO player_titles (user_id, title_id, is_active, acquired_at) VALUES (?, ?, 0, ?)""",
            (user_id, title_id, now),
        )
        await self.db.commit()
        return True

    async def activate_title(self, user_id: str, title_id: str) -> bool:
        """激活玩家称号。"""
        cur = await self.db.execute(
            "UPDATE player_titles SET is_active = 0 WHERE user_id = ?",
            (user_id,),
        )
        cur = await self.db.execute(
            "UPDATE player_titles SET is_active = 1 WHERE user_id = ? AND title_id = ?",
            (user_id, title_id),
        )
        await self.db.commit()
        return True

    async def deactivate_title(self, user_id: str) -> bool:
        """停用玩家当前称号。"""
        cur = await self.db.execute(
            "UPDATE player_titles SET is_active = 0 WHERE user_id = ?",
            (user_id,),
        )
        await self.db.commit()
        return True

    async def admin_create_title(self, title_id: str, name: str, description: str, icon: str, color: str, prefix: str, bonus_attack: int, bonus_defense: int, bonus_hp: int, is_system: int = 0) -> bool:
        """管理员创建称号。"""
        now = time.time()
        cur = await self.db.execute(
            """INSERT OR REPLACE INTO titles (title_id, name, description, icon, color, prefix, bonus_attack, bonus_defense, bonus_hp, is_system, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (title_id, name, description, icon, color, prefix, bonus_attack, bonus_defense, bonus_hp, is_system, now),
        )
        await self.db.commit()
        return True

    async def admin_delete_title(self, title_id: str) -> bool:
        """管理员删除称号。"""
        cur = await self.db.execute("DELETE FROM titles WHERE title_id = ?", (title_id,))
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    # ── 装备强化配置 ──────────────────────────────────────────────

    async def get_enhance_configs(self) -> list[dict]:
        """获取所有强化配置。"""
        cur = await self.db.execute(
            "SELECT equipment_type, level, success_rate, cost_stones, cost_item_id, cost_item_count, bonus_attack, bonus_defense, bonus_hp FROM enhance_configs ORDER BY equipment_type, level"
        )
        rows = await cur.fetchall()
        return [{
            "equipment_type": r[0],
            "level": r[1],
            "success_rate": r[2],
            "cost_stones": r[3],
            "cost_item_id": r[4],
            "cost_item_count": r[5],
            "bonus_attack": r[6],
            "bonus_defense": r[7],
            "bonus_hp": r[8],
        } for r in rows]

    async def get_enhance_config(self, equipment_type: str, level: int) -> dict | None:
        """获取指定强化配置。"""
        cur = await self.db.execute(
            "SELECT equipment_type, level, success_rate, cost_stones, cost_item_id, cost_item_count, bonus_attack, bonus_defense, bonus_hp FROM enhance_configs WHERE equipment_type = ? AND level = ?",
            (equipment_type, level),
        )
        row = await cur.fetchone()
        if not row:
            return None
        return {
            "equipment_type": row[0],
            "level": row[1],
            "success_rate": row[2],
            "cost_stones": row[3],
            "cost_item_id": row[4],
            "cost_item_count": row[5],
            "bonus_attack": row[6],
            "bonus_defense": row[7],
            "bonus_hp": row[8],
        }

    async def admin_save_enhance_config(self, equipment_type: str, level: int, success_rate: float, cost_stones: int, cost_item_id: str, cost_item_count: int, bonus_attack: int, bonus_defense: int, bonus_hp: int) -> bool:
        """保存强化配置。"""
        cur = await self.db.execute(
            """INSERT OR REPLACE INTO enhance_configs (equipment_type, level, success_rate, cost_stones, cost_item_id, cost_item_count, bonus_attack, bonus_defense, bonus_hp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (equipment_type, level, success_rate, cost_stones, cost_item_id, cost_item_count, bonus_attack, bonus_defense, bonus_hp),
        )
        await self.db.commit()
        return True

    async def admin_delete_enhance_config(self, equipment_type: str, level: int) -> bool:
        """删除强化配置。"""
        cur = await self.db.execute(
            "DELETE FROM enhance_configs WHERE equipment_type = ? AND level = ?",
            (equipment_type, level),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def log_enhance(self, user_id: str, equipment_type: str, equipment_name: str, from_level: int, to_level: int, success: bool, cost_stones: int) -> bool:
        """记录强化日志。"""
        now = time.time()
        cur = await self.db.execute(
            """INSERT INTO player_enhance_log (user_id, equipment_type, equipment_name, from_level, to_level, success, cost_stones, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, equipment_type, equipment_name, from_level, to_level, 1 if success else 0, cost_stones, now),
        )
        await self.db.commit()
        return True

    # ══════════════════════════════════════════════════════════════
    # 同伴系统
    # ══════════════════════════════════════════════════════════════

    async def get_player_companions(self, user_id: str) -> list[dict]:
        """获取玩家所有同伴。"""
        cur = await self.db.execute(
            "SELECT companion_id, loyalty, gifts_given, last_gift_time, is_active FROM player_companions WHERE user_id = ?",
            (user_id,),
        )
        rows = await cur.fetchall()
        return [{
            "companion_id": r[0],
            "loyalty": r[1],
            "gifts_given": r[2],
            "last_gift_time": r[3],
            "is_active": bool(r[4]),
        } for r in rows]

    async def add_player_companion(self, user_id: str, companion_id: str) -> bool:
        """添加同伴。"""
        try:
            cur = await self.db.execute(
                "INSERT INTO player_companions (user_id, companion_id) VALUES (?, ?)",
                (user_id, companion_id),
            )
            await self.db.commit()
            return True
        except Exception:
            return False

    async def update_companion_loyalty(self, user_id: str, companion_id: str, loyalty_change: int, gifts_given: int = 0) -> bool:
        """更新同伴忠诚度。"""
        import time as _time
        cur = await self.db.execute(
            """UPDATE player_companions
               SET loyalty = MIN(100, MAX(0, loyalty + ?)),
                   gifts_given = gifts_given + ?,
                   last_gift_time = ?
               WHERE user_id = ? AND companion_id = ?""",
            (loyalty_change, gifts_given, _time.time(), user_id, companion_id),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def set_companion_active(self, user_id: str, companion_id: str, active: bool) -> bool:
        """设置同伴是否出战。"""
        cur = await self.db.execute(
            "UPDATE player_companions SET is_active = ? WHERE user_id = ? AND companion_id = ?",
            (1 if active else 0, user_id, companion_id),
        )
        await self.db.commit()
        return (cur.rowcount or 0) > 0

    async def has_companion(self, user_id: str, companion_id: str) -> bool:
        """检查玩家是否拥有某同伴。"""
        cur = await self.db.execute(
            "SELECT 1 FROM player_companions WHERE user_id = ? AND companion_id = ? LIMIT 1",
            (user_id, companion_id),
        )
        return (await cur.fetchone()) is not None

    # ══════════════════════════════════════════════════════════════
    # 部队系统
    # ══════════════════════════════════════════════════════════════

    async def get_player_troops(self, user_id: str) -> dict[str, int]:
        """获取玩家部队 {troop_id: count}。"""
        cur = await self.db.execute(
            "SELECT troop_id, count FROM player_troops WHERE user_id = ? AND count > 0",
            (user_id,),
        )
        rows = await cur.fetchall()
        return {r[0]: r[1] for r in rows}

    async def add_player_troops(self, user_id: str, troop_id: str, count: int) -> bool:
        """增加部队数量。"""
        cur = await self.db.execute(
            """INSERT INTO player_troops (user_id, troop_id, count)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id, troop_id) DO UPDATE SET count = count + ?""",
            (user_id, troop_id, count, count),
        )
        await self.db.commit()
        return True

    async def remove_player_troops(self, user_id: str, troop_id: str, count: int) -> int:
        """减少部队数量，返回实际减少的数量。"""
        cur = await self.db.execute(
            "SELECT count FROM player_troops WHERE user_id = ? AND troop_id = ?",
            (user_id, troop_id),
        )
        row = await cur.fetchone()
        if not row:
            return 0
        current = row[0]
        actual = min(current, count)
        new_count = current - actual
        if new_count <= 0:
            await self.db.execute(
                "DELETE FROM player_troops WHERE user_id = ? AND troop_id = ?",
                (user_id, troop_id),
            )
        else:
            await self.db.execute(
                "UPDATE player_troops SET count = ? WHERE user_id = ? AND troop_id = ?",
                (new_count, user_id, troop_id),
            )
        await self.db.commit()
        return actual

    async def get_total_troop_count(self, user_id: str) -> int:
        """获取玩家部队总数。"""
        cur = await self.db.execute(
            "SELECT COALESCE(SUM(count), 0) FROM player_troops WHERE user_id = ?",
            (user_id,),
        )
        row = await cur.fetchone()
        return row[0] if row else 0

    # ══════════════════════════════════════════════════════════════
    # 竞技场系统
    # ══════════════════════════════════════════════════════════════

    async def record_tournament_result(self, user_id: str, opponent_id: str, result: str, reward_gold: int, reward_dao_yun: int, win_streak: int, streak_bonus: str) -> bool:
        """记录竞技场战斗结果。"""
        import time as _time
        cur = await self.db.execute(
            """INSERT INTO tournament_records (user_id, opponent_id, result, reward_gold, reward_dao_yun, win_streak, streak_bonus, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, opponent_id, result, reward_gold, reward_dao_yun, win_streak, streak_bonus, _time.time()),
        )
        await self.db.commit()
        return True

    async def get_tournament_history(self, user_id: str, limit: int = 20) -> list[dict]:
        """获取竞技场历史记录。"""
        cur = await self.db.execute(
            """SELECT opponent_id, result, reward_gold, reward_dao_yun, win_streak, streak_bonus, created_at
               FROM tournament_records WHERE user_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit),
        )
        rows = await cur.fetchall()
        return [{
            "opponent_id": r[0],
            "result": r[1],
            "reward_gold": r[2],
            "reward_dao_yun": r[3],
            "win_streak": r[4],
            "streak_bonus": r[5],
            "created_at": r[6],
        } for r in rows]

    async def get_current_win_streak(self, user_id: str) -> int:
        """获取当前连胜数（从最近一次失败后计算）。"""
        cur = await self.db.execute(
            """SELECT result FROM tournament_records WHERE user_id = ?
               ORDER BY created_at DESC LIMIT 1""",
            (user_id,),
        )
        row = await cur.fetchone()
        if not row:
            return 0
        if row[0] == "win":
            cur2 = await self.db.execute(
                """SELECT win_streak FROM tournament_records WHERE user_id = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (user_id,),
            )
            row2 = await cur2.fetchone()
            return row2[0] if row2 else 0
        return 0
