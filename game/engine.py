"""战争引擎：调度所有战争操作的中心。"""

from __future__ import annotations

import asyncio
import contextlib
import datetime
import logging
import random
import re
import time
from dataclasses import fields
from typing import Awaitable, Callable, Optional

from .constants import (
    REALM_CONFIG, ITEM_REGISTRY, CHECKIN_PILL_WEIGHTS,
    EQUIPMENT_REGISTRY, EQUIPMENT_TIER_NAMES, EquipmentTier,
    HEART_METHOD_REGISTRY, HEART_METHOD_QUALITY_NAMES, MASTERY_LEVELS,
    GONGFA_REGISTRY, GONGFA_TIER_NAMES, MASTERY_MAX,
    get_heart_method_bonus, get_heart_method_manual_id, get_gongfa_scroll_id,
    get_stored_heart_method_item_id, parse_heart_method_manual_id,
    parse_stored_heart_method_item_id, parse_gongfa_scroll_id,
    get_total_gongfa_bonus, can_cultivate_gongfa,
    get_realm_name, has_sub_realm, can_equip, get_realm_heart_methods,
    get_player_base_max_lingqi, get_player_base_stats, get_realm_base_stats, calc_gongfa_lingqi_cost,
    get_max_sub_realm, get_sub_realm_dao_yun_cost, is_high_realm,
    get_nearest_realm_level,
    MOUNT_REGISTRY, MOUNT_EQUIPMENT_REGISTRY,
    RealmLevel,
)
from .spawn_system import (
    get_all_spawn_origins,
    get_all_spawn_locations,
    get_spawn_origin,
    get_spawn_location,
    validate_spawn_selection,
)
from .cultivation import attempt_breakthrough, perform_cultivate
from .data_manager import DataManager
from .auth import AuthManager
from .dungeon import DungeonManager
from .pvp import PvPManager
from .inventory import (
    add_item,
    equip_item,
    unequip_item,
    equip_mount,
    unequip_mount,
    equip_mount_item,
    unequip_mount_item,
    find_item_id_by_name,
    find_item_ids_by_name,
    get_inventory_display,
    use_item,
    recycle_item,
)
from .models import Player
from . import market as market_mod
from . import shop as shop_mod
from . import sect as sect_mod
from . import heal_skills
from . import gathering
from . import crafting
from . import trading
from . import forging
from . import hunting
from . import accessories

logger = logging.getLogger("mbwar.engine")

_BAD_NAME_KEYWORDS = (
    # 仅保留“高置信度违规词”，避免误伤正常角色名
    "色情", "淫秽", "淫荡", "约炮", "援交", "一夜情", "开房", "做爱",
    "嫖娼", "卖淫", "强奸", "轮奸",
    "鸡巴", "阴茎", "阴道", "龟头", "乳房", "大屌",
    "傻逼", "煞笔", "沙比", "脑残", "智障", "狗东西", "去死", "死妈",
    "操你妈", "cnm", "nmsl",
)


class GameEngine:
    """核心游戏引擎，聊天指令和 Web 共用。"""

    def __init__(self, data_manager: DataManager, cultivate_cooldown: int = 60):
        self._data_manager = data_manager
        self._players: dict[str, Player] = {}
        self._player_locks: dict[str, asyncio.Lock] = {}
        self._name_index: dict[str, str] = {}  # {骑士名: user_id} 用于按名查找
        self._cultivate_cooldown = cultivate_cooldown
        self._checkin_config: dict = {}  # 每日签到配置，由外部设置
        self._ws_manager = None  # 由 web 层设置
        self._name_reviewer: Callable[[str], Awaitable[dict | tuple | bool]] | None = None
        self._sect_name_reviewer: Callable[[str], Awaitable[dict]] | None = None
        self._chat_reviewer: Callable[[str], Awaitable[dict]] | None = None
        self.auth: AuthManager | None = None
        self._pending_deaths: dict[str, dict] = {}
        self.dungeon = DungeonManager(self)
        self.pvp = PvPManager(self)
        self.admin_manager = None  # 分级管理员系统
        self._ui_config: dict = self._default_ui_config()
    
    def _default_ui_config(self) -> dict:
        """默认UI配置"""
        return {
            "background_color": "#0D0D0D",
            "background_gradient_start": "#1A1A1A",
            "background_gradient_end": "#151515",
            "header_color": "#1A1A1A",
            "header_border_color": "#8B0000",
            "accent_color": "#D4AF37",
            "text_color": "#F5DEB3",
            "button_color": "#8B0000",
            "enabled": False
        }
    
    def get_ui_config(self) -> dict:
        """获取UI配置"""
        return self._ui_config.copy()
    
    def set_ui_config(self, config: dict, admin_level: int) -> dict:
        """设置UI配置（需要lv4+）"""
        from .admin_system import AdminLevel
        if admin_level < AdminLevel.SUPER_ADMIN:
            return {"success": False, "message": "权限不足，需要超级管理员或更高"}
        
        valid_keys = {
            "background_color", "background_gradient_start", "background_gradient_end",
            "header_color", "header_border_color", "accent_color", "text_color", "button_color", "enabled"
        }
        for key, value in config.items():
            if key in valid_keys:
                self._ui_config[key] = value
        
        return {"success": True, "message": "UI配置已更新", "config": self._ui_config}

    async def initialize(self):
        """加载所有玩家数据到内存。"""
        from .constants import set_heart_method_registry, set_equipment_registry, set_gongfa_registry, set_realm_config
        from .pills import clean_expired_buffs
        from .map_system import init_bandit_system
        from .player_level import init_level_system
        from .admin_system import get_admin_manager
        from . import skills_simple
        from . import city_quest_system
        from . import legendary_system
        from . import random_events
        from ..web.teamspeak_middleware import TeamSpeakMiddleware

        realms = await self._data_manager.load_realms()
        set_realm_config(realms)
        equipments = await self._data_manager.load_weapons()
        set_equipment_registry(equipments)
        
        # 使用精简的骑砍技能系统
        heart_methods = await self._data_manager.load_heart_methods()
        set_heart_method_registry(heart_methods)
        gongfas = await self._data_manager.load_gongfas()
        set_gongfa_registry(gongfas)
        
        # 注册精简技能
        skills_simple.register_skills()

        # 初始化等级系统和称号系统
        init_level_system()
        
        # 初始化城市任务系统
        # city_quest_system.init_city_quest_system()  # 移除不存在的函数调用
        
        # 初始化传奇BOSS系统
        # legendary_system.init_legendary_system()  # 移除不存在的函数调用
        
        # 初始化随机事件系统
        # random_events.init_random_events()  # 移除不存在的函数调用
        
        # 初始化 TeamSpeak 中间件
        self.ts_middleware = TeamSpeakMiddleware()
        if hasattr(self, '_config') and self._config:
            await self.ts_middleware.initialize()
        
        # 初始化分级管理员系统
        self.admin_manager = get_admin_manager()

        self._players = await self._data_manager.load_all_players()
        normalized = False
        # 构建角色名索引
        for uid, player in self._players.items():
            self._name_index[player.name] = uid
            if self._normalize_player_realm_progress(player):
                normalized = True
            realm_stats = get_realm_base_stats(player.realm, player.sub_realm)
            if getattr(player, "permanent_max_hp_bonus", 0) <= 0 and player.max_hp > realm_stats["max_hp"]:
                player.permanent_max_hp_bonus = player.max_hp - realm_stats["max_hp"]
                normalized = True
            if getattr(player, "permanent_attack_bonus", 0) <= 0 and player.attack > realm_stats["attack"]:
                player.permanent_attack_bonus = player.attack - realm_stats["attack"]
                normalized = True
            if getattr(player, "permanent_defense_bonus", 0) <= 0 and player.defense > realm_stats["defense"]:
                player.permanent_defense_bonus = player.defense - realm_stats["defense"]
                normalized = True
            if getattr(player, "permanent_lingqi_bonus", 0) <= 0 and player.lingqi > realm_stats["max_lingqi"]:
                player.permanent_lingqi_bonus = player.lingqi - realm_stats["max_lingqi"]
                normalized = True

            max_lingqi = get_player_base_max_lingqi(player)
            if player.lingqi <= 0 or (player.lingqi == 50 and player.realm > 0):
                player.lingqi = max_lingqi
                normalized = True
            elif player.lingqi > max_lingqi:
                player.lingqi = max_lingqi
                normalized = True
            heart_fix = self._auto_unequip_invalid_heart_method(player, convert_ratio=0.6, force=False)
            removed_gongfas = self._auto_unequip_invalid_gongfa(player)
            if heart_fix.get("removed_name") or removed_gongfas:
                normalized = True
            if clean_expired_buffs(player):
                normalized = True
            # 清理过期被动技能道具
            if self._clean_expired_heart_methods(player):
                normalized = True
            if self._clamp_player_hp(player):
                normalized = True
        if normalized:
            await self._data_manager.save_all_players(self._players)

        # 启动定时清理任务（过期Token/绑定 + 过期集市商品）
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

    @staticmethod
    def _clamp_player_hp(player: Player) -> bool:
        """兜底确保玩家生命值始终处于合法范围内。"""
        changed = False
        max_hp = max(1, int(getattr(player, "max_hp", 1) or 1))
        if player.max_hp != max_hp:
            player.max_hp = max_hp
            changed = True

        hp = max(0, min(player.max_hp, int(getattr(player, "hp", 0) or 0)))
        if player.hp != hp:
            player.hp = hp
            changed = True
        return changed

    @staticmethod
    def _normalize_player_realm_progress(player: Player) -> bool:
        """将玩家爵位进度纠正到当前已配置的合法范围内。"""
        changed = False
        normalized_realm = get_nearest_realm_level(getattr(player, "realm", 0) or 0)
        if player.realm != normalized_realm:
            player.realm = normalized_realm
            changed = True

        current_sub = int(getattr(player, "sub_realm", 0) or 0)
        if has_sub_realm(player.realm):
            normalized_sub = max(0, min(current_sub, get_max_sub_realm(player.realm)))
        else:
            normalized_sub = 0
        if player.sub_realm != normalized_sub:
            player.sub_realm = normalized_sub
            changed = True
        return changed

    @staticmethod
    def _sync_player_base_stats(player: Player) -> bool:
        """按当前爵位重新同步玩家基础属性，不改变永久加成。"""
        changed = False
        base_stats = get_player_base_stats(player)
        new_max_hp = max(1, int(base_stats["max_hp"]))
        new_attack = max(0, int(base_stats["attack"]))
        new_defense = max(0, int(base_stats["defense"]))
        new_max_lingqi = max(0, int(base_stats["max_lingqi"]))

        if player.max_hp != new_max_hp:
            player.max_hp = new_max_hp
            changed = True
        if player.attack != new_attack:
            player.attack = new_attack
            changed = True
        if player.defense != new_defense:
            player.defense = new_defense
            changed = True

        hp = max(0, min(player.max_hp, int(getattr(player, "hp", 0) or 0)))
        if player.hp != hp:
            player.hp = hp
            changed = True

        lingqi = max(0, min(new_max_lingqi, int(getattr(player, "lingqi", 0) or 0)))
        if player.lingqi != lingqi:
            player.lingqi = lingqi
            changed = True
        return changed

    async def get_or_create_player(self, user_id: str, name: str, spawn_origin: str = "", spawn_location: str = "") -> Player:
        """获取或创建玩家。"""
        if user_id in self._players:
            return self._players[user_id]
        
        start_realm = get_nearest_realm_level(RealmLevel.MORTAL)
        realm_cfg = REALM_CONFIG.get(start_realm, {})
        
        origin = get_spawn_origin(spawn_origin) if spawn_origin else None
        location = get_spawn_location(spawn_location) if spawn_location else None
        
        base_hp = realm_cfg["base_hp"]
        base_attack = realm_cfg["base_attack"]
        base_defense = realm_cfg["base_defense"]
        base_lingqi = realm_cfg.get("base_lingqi", 50)
        
        player = Player(
            user_id=user_id,
            name=name,
            realm=start_realm,
            hp=base_hp,
            max_hp=base_hp,
            attack=base_attack,
            defense=base_defense,
            lingqi=base_lingqi,
            spawn_origin=spawn_origin,
            spawn_location=spawn_location,
        )
        
        if location:
            player.map_state.current_location = location.location_id
            player.map_state.x = location.x
            player.map_state.y = location.y
        else:
            player.map_state.x = 500.0
            player.map_state.y = 500.0
        
        player.inventory["healing_pill"] = player.inventory.get("healing_pill", 0) + 3
        player.inventory["exp_pill"] = player.inventory.get("exp_pill", 0) + 1
        
        self._players[user_id] = player
        self._name_index[name] = user_id
        await self._save_player(player)
        return player

    async def get_player(self, user_id: str) -> Optional[Player]:
        """获取玩家，不存在返回 None。"""
        return self._players.get(user_id)

    async def _auto_update_task_progress(self, user_id: str, task_type: str, count: int = 1) -> list[dict]:
        """自动更新任务进度。返回完成的任务列表。"""
        completed = []
        membership = await self._data_manager.load_player_sect(user_id)
        if not membership:
            return completed

        tasks = await self._data_manager.get_sect_tasks(membership["sect_id"], "active")
        for task in tasks:
            if task["task_type"] != task_type:
                continue
            if task.get("is_expired"):
                continue

            member_task = await self._data_manager.get_task_member(task["task_id"], user_id)
            if not member_task or member_task["status"] == "completed":
                continue

            new_progress = min(member_task["progress"] + count, task["target_count"])
            await self._data_manager.update_task_member_progress(task["task_id"], user_id, new_progress)

            if new_progress >= task["target_count"]:
                await self._data_manager.complete_task_member(task["task_id"], user_id)
                await self._data_manager.update_task_progress(task["task_id"], new_progress)

                reward_points = task["reward_points"]
                if reward_points > 0:
                    await self._data_manager.update_member_contribution(user_id, reward_points)

                if task["reward_item_id"] and task["reward_item_count"] > 0:
                    player = await self.get_player(user_id)
                    if player:
                        from .inventory import add_item
                        await add_item(player, task["reward_item_id"], task["reward_item_count"], "任务奖励")
                        await self._notify_player_update(player)

                completed.append({
                    "task_id": task["task_id"],
                    "title": task["title"],
                    "reward_points": reward_points,
                })

        return completed

    async def cultivate(self, user_id: str) -> dict:
        """训练操作。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        # 驻守训练中不可手动训练
        if player.afk_cultivate_end > time.time():
            remaining = int(player.afk_cultivate_end - time.time())
            mins = remaining // 60
            secs = remaining % 60
            return {"success": False, "message": f"正在驻守训练中，剩余{mins}分{secs}秒"}

        result = await perform_cultivate(player, self._cultivate_cooldown)
        if result["success"]:
            await self._save_player(player)
            completed_tasks = await self._auto_update_task_progress(user_id, "cultivate")
            if completed_tasks:
                task_names = "、".join([t["title"] for t in completed_tasks])
                result["task_completed"] = completed_tasks
                result["message"] = result.get("message", "") + f" 完成家族任务：{task_names}"
        return result

    async def daily_checkin(self, user_id: str) -> dict:
        """每日签到，随机获得第纳尔、药剂或经验。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        today = datetime.datetime.now().astimezone().date().isoformat()
        if player.last_checkin_date == today:
            return {"success": False, "message": "今日已签到，明天再来吧"}

        cfg = self._checkin_config or {}

        def _to_int(value, default: int) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        def _clamp(value: int, lo: int, hi: int) -> int:
            return max(lo, min(hi, value))

        prob_stones = _clamp(_to_int(cfg.get("checkin_prob_stones", 60), 60), 0, 100)
        prob_exp = _clamp(_to_int(cfg.get("checkin_prob_exp", 25), 25), 0, 100)
        if prob_stones + prob_exp > 100:
            prob_exp = max(0, 100 - prob_stones)

        realm_mult = 1.0 + player.realm * 0.3

        roll = random.randint(1, 100)

        if roll <= prob_stones:
            # 纯第纳尔
            base_min = _to_int(cfg.get("checkin_stones_min", 20), 20)
            base_max = _to_int(cfg.get("checkin_stones_max", 300), 300)
            base_min, base_max = sorted((max(0, base_min), max(0, base_max)))
            stones = random.randint(
                int(base_min * realm_mult), int(base_max * realm_mult)
            )
            player.spirit_stones += stones
            rewards = f"{stones}第纳尔"

        elif roll <= prob_stones + prob_exp:
            # 纯经验
            base_min = _to_int(cfg.get("checkin_exp_min", 500), 500)
            base_max = _to_int(cfg.get("checkin_exp_max", 5000), 5000)
            base_min, base_max = sorted((max(0, base_min), max(0, base_max)))
            exp = random.randint(
                int(base_min * realm_mult), int(base_max * realm_mult)
            )
            player.exp += exp
            rewards = f"{exp}经验"

        else:
            # 第纳尔 + 药剂
            base_min = _to_int(cfg.get("checkin_stones_with_pill_min", 10), 10)
            base_max = _to_int(cfg.get("checkin_stones_with_pill_max", 100), 100)
            base_min, base_max = sorted((max(0, base_min), max(0, base_max)))
            stones = random.randint(
                int(base_min * realm_mult), int(base_max * realm_mult)
            )
            player.spirit_stones += stones

            weighted_items = []
            for item_id, weight in CHECKIN_PILL_WEIGHTS:
                if item_id not in ITEM_REGISTRY:
                    continue
                w = _to_int(weight, 0)
                if w > 0:
                    weighted_items.append((item_id, w))
            if not weighted_items:
                weighted_items = [("healing_pill", 1)]
            pill_ids = [w[0] for w in weighted_items]
            pill_weights = [w[1] for w in weighted_items]
            pill_id = random.choices(pill_ids, weights=pill_weights, k=1)[0]
            await add_item(player, pill_id)
            pill_name = ITEM_REGISTRY[pill_id].name

            rewards = f"{stones}第纳尔和一瓶{pill_name}"

        player.last_checkin_date = today
        await self._save_player(player)
        await self._notify_player_update(player)

        return {
            "success": True,
            "message": f"签到成功！今日获取{rewards}",
            "rewards": rewards,
        }

    async def start_afk_cultivate(self, user_id: str, minutes: int) -> dict:
        """开始驻守训练。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        async with self._get_player_lock(user_id):
            if self.has_pending_death(user_id):
                return {"success": False, "message": "你已战死沙场，请先确认重生后再驻守训练"}

            try:
                max_minutes = int(self._checkin_config.get("afk_cultivate_max_minutes", 60))
            except (TypeError, ValueError):
                max_minutes = 60
            if max_minutes < 1:
                max_minutes = 60
            if minutes < 1 or minutes > max_minutes:
                return {"success": False, "message": f"驻守时长须在1~{max_minutes}分钟之间"}

            now = time.time()
            if player.afk_cultivate_end > 0:
                if player.afk_cultivate_end > now:
                    remaining = int(player.afk_cultivate_end - now)
                    mins = remaining // 60
                    secs = remaining % 60
                    return {"success": False, "message": f"正在驻守训练中，剩余{mins}分{secs}秒"}
                return {"success": False, "message": "你有已完成的驻守训练尚未结算，请先使用「结算」领取收益"}

            player.afk_cultivate_start = now
            player.afk_cultivate_end = now + minutes * 60
            await self._save_player(player)

        return {
            "success": True,
            "message": f"开始驻守训练{minutes}分钟，完成后请使用「结算」领取收益",
            "minutes": minutes,
            "end_time": player.afk_cultivate_end,
        }

    async def collect_afk_cultivate(self, user_id: str) -> dict:
        """结算驻守训练收益。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        async with self._get_player_lock(user_id):
            # 在锁内校验死亡状态，防止与 confirm_death 竞态
            if self.has_pending_death(user_id):
                return {"success": False, "message": "你已战死沙场，请先确认重生后再结算驻守收益"}

            if player.afk_cultivate_end <= 0:
                return {"success": False, "message": "当前没有驻守训练记录"}

            now = time.time()
            if now < player.afk_cultivate_end:
                remaining = int(player.afk_cultivate_end - now)
                mins = remaining // 60
                secs = remaining % 60
                return {"success": False, "message": f"驻守训练尚未完成，剩余{mins}分{secs}秒"}

            # 计算驻守时长（分钟）
            duration_sec = player.afk_cultivate_end - player.afk_cultivate_start
            duration_min = max(1, int(duration_sec / 60))

            # 经验公式：取训练单次经验的平均值 × 分钟数
            normalized_realm = get_nearest_realm_level(player.realm)
            if normalized_realm != player.realm:
                player.realm = normalized_realm
            if has_sub_realm(player.realm):
                player.sub_realm = max(0, min(int(player.sub_realm), get_max_sub_realm(player.realm)))
            else:
                player.sub_realm = 0
            realm_cfg = REALM_CONFIG.get(player.realm)
            if not realm_cfg:
                return {"success": False, "message": "当前爵位配置无效，无法结算驻守训练"}
            base_min = 10 + player.realm * 5 + player.sub_realm * 2
            base_max = 30 + player.realm * 10 + player.sub_realm * 4
            if player.realm >= RealmLevel.GOLDEN_CORE:
                base_min *= 10
                base_max *= 10
            avg_exp_per_min = (base_min + base_max) // 2
            total_exp = avg_exp_per_min * duration_min

            # 被动技能经验加成
            from .constants import get_heart_method_bonus, HEART_METHOD_REGISTRY, MASTERY_MAX
            hm_bonus = get_heart_method_bonus(player.heart_method, player.heart_method_mastery)
            if hm_bonus["exp_multiplier"] > 0:
                total_exp = int(total_exp * (1.0 + hm_bonus["exp_multiplier"]))

            player.exp += total_exp

            extra_msgs: list[str] = []

            # 驻守期间被动技能经验（每分钟1点基础）
            hm = HEART_METHOD_REGISTRY.get(player.heart_method)
            if hm and player.heart_method_mastery < MASTERY_MAX:
                hm_exp_gain = duration_min * (1 + hm.quality)
                player.heart_method_exp += hm_exp_gain
                while (player.heart_method_mastery < MASTERY_MAX
                       and player.heart_method_exp >= hm.mastery_exp):
                    player.heart_method_exp -= hm.mastery_exp
                    player.heart_method_mastery += 1
                    from .constants import MASTERY_LEVELS
                    extra_msgs.append(
                        f"技能【{hm.name}】训练至{MASTERY_LEVELS[player.heart_method_mastery]}！"
                    )

            # 驻守期间战斗技能经验（每分钟1点/技能，爵位不够则不涨）
            for slot in ("gongfa_1", "gongfa_2", "gongfa_3"):
                gongfa_id = getattr(player, slot, "无")
                if not gongfa_id or gongfa_id == "无":
                    continue
                gf = GONGFA_REGISTRY.get(gongfa_id)
                if not gf:
                    continue
                if not can_cultivate_gongfa(player.realm, gf.tier):
                    extra_msgs.append(f"技能【{gf.name}】需更高爵位方可继续训练")
                    continue
                mastery_attr = f"{slot}_mastery"
                exp_attr = f"{slot}_exp"
                mastery = getattr(player, mastery_attr, 0)
                if mastery >= MASTERY_MAX:
                    continue
                player_exp = getattr(player, exp_attr, 0) + duration_min
                while player_exp >= gf.mastery_exp and mastery < MASTERY_MAX:
                    if gf.tier >= 2 and mastery == 2 and gf.dao_yun_cost > 0:
                        if player.dao_yun < gf.dao_yun_cost:
                            player_exp = gf.mastery_exp - 1
                            break
                        player.dao_yun -= gf.dao_yun_cost
                        extra_msgs.append(f"消耗声望{gf.dao_yun_cost}，助技能【{gf.name}】晋升")
                    player_exp -= gf.mastery_exp
                    mastery += 1
                    if mastery <= MASTERY_MAX:
                        from .constants import MASTERY_LEVELS
                        extra_msgs.append(f"技能【{gf.name}】训练至{MASTERY_LEVELS[mastery]}！")
                setattr(player, mastery_attr, mastery)
                setattr(player, exp_attr, max(0, int(player_exp)))

            # 驻守期间战斗技能回血/回体力
            gf_total = get_total_gongfa_bonus(player)
            if gf_total["hp_regen"] > 0 and player.hp < player.max_hp:
                heal = min(gf_total["hp_regen"] * duration_min, player.max_hp - player.hp)
                player.hp += heal
                extra_msgs.append(f"技能恢复+{heal}")
            if gf_total["lingqi_regen"] > 0:
                regen = gf_total["lingqi_regen"] * duration_min
                max_lq = get_player_base_max_lingqi(player)
                actual = min(regen, max(0, max_lq - player.lingqi))
                if actual > 0:
                    player.lingqi += actual
                    extra_msgs.append(f"技能恢复体力+{actual}")

            # 驻守期间声望（仅领主及以上被动技能生效）
            if hm and hm.realm >= RealmLevel.DEITY_TRANSFORM and hm_bonus["dao_yun_rate"] > 0:
                dao_gain = int(duration_min * hm_bonus["dao_yun_rate"] * 0.3)
                if dao_gain > 0:
                    player.dao_yun += dao_gain
                    extra_msgs.append(f"声望提升+{dao_gain}")

            # 处理军衔自动升级
            sub_level_ups = 0
            if has_sub_realm(player.realm):
                sub_exp = realm_cfg.get("sub_exp_to_next", 0)
                max_sr = get_max_sub_realm(player.realm)
                while (sub_exp > 0
                       and player.sub_realm < max_sr
                       and player.exp >= sub_exp):
                    # 高阶爵位军衔升级需要声望
                    dao_cost = get_sub_realm_dao_yun_cost(player.realm, player.sub_realm)
                    if dao_cost > 0 and player.dao_yun < dao_cost:
                        break
                    if dao_cost > 0:
                        player.dao_yun -= dao_cost
                        extra_msgs.append(f"消耗声望{dao_cost}")
                    player.exp -= sub_exp
                    player.sub_realm += 1
                    sub_level_ups += 1
                    hp_bonus = int(realm_cfg["base_hp"] * 0.08)
                    atk_bonus = int(realm_cfg["base_attack"] * 0.06)
                    def_bonus = int(realm_cfg["base_defense"] * 0.06)
                    lingqi_bonus = max(1, int(realm_cfg.get("base_lingqi", 0) * 0.08))
                    player.max_hp += hp_bonus
                    player.hp = player.max_hp
                    player.attack += atk_bonus
                    player.defense += def_bonus
                    player.lingqi += lingqi_bonus

            # 重置驻守状态
            player.afk_cultivate_start = 0.0
            player.afk_cultivate_end = 0.0
            await self._save_player(player)

        realm_name = get_realm_name(player.realm, player.sub_realm)
        msg = f"驻守训练{duration_min}分钟完成！获得{total_exp}经验"
        if sub_level_ups > 0:
            extra_msgs.append(f"爵位提升！当前：{realm_name}")
        if extra_msgs:
            msg += "\n" + "，".join(extra_msgs)

        return {
            "success": True,
            "message": msg,
            "exp_gained": total_exp,
            "duration_min": duration_min,
            "sub_level_ups": sub_level_ups,
            "realm_name": realm_name,
        }

    async def cancel_afk_cultivate(self, user_id: str) -> dict:
        """取消驻守训练并放弃本次驻守收益。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        async with self._get_player_lock(user_id):
            if player.afk_cultivate_end <= 0:
                return {"success": False, "message": "当前没有驻守训练记录"}

            now = time.time()
            if now < player.afk_cultivate_end:
                remaining = int(player.afk_cultivate_end - now)
                mins = remaining // 60
                secs = remaining % 60
                msg = f"已取消驻守训练（原剩余{mins}分{secs}秒），本次驻守收益已放弃"
            else:
                msg = "已取消未结算的驻守训练，本次驻守收益已放弃"

            player.afk_cultivate_start = 0.0
            player.afk_cultivate_end = 0.0
            await self._save_player(player)
        return {"success": True, "message": msg}

    async def adventure(self, user_id: str) -> dict:
        """征战操作：进入副本探索。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        if player.realm < RealmLevel.QI_REFINING:
            return {"success": False, "message": "经验尚浅，至少需要新兵等级才能征战"}

        if self.dungeon.has_active_session(user_id) or self.pvp.get_session_for_player(user_id):
            return await self.dungeon.start(player)

        cfg = self._checkin_config or {}
        try:
            cooldown = int(cfg.get("adventure_cooldown", 1800))
        except (TypeError, ValueError):
            cooldown = 1800
        cooldown = max(0, cooldown)

        now = time.time()
        if cooldown > 0 and player.last_adventure_time > 0:
            remaining = cooldown - (now - player.last_adventure_time)
            if remaining > 0:
                remaining = int(remaining)
                mins = remaining // 60
                secs = remaining % 60
                if mins > 0:
                    return {"success": False, "message": f"征战冷却中，请等待{mins}分{secs}秒后再试"}
                return {"success": False, "message": f"征战冷却中，请等待{secs}秒后再试"}

        return await self.dungeon.start(player)

    async def get_adventure_scenes(self) -> list[dict]:
        """获取所有征战场景列表。"""
        return await self._data_manager.get_adventure_scenes()

    async def _reload_runtime_registries(self):
        """从数据库重载爵位、装备、被动技能、战斗技能定义到运行时注册表。"""
        from .constants import set_equipment_registry, set_heart_method_registry, set_gongfa_registry, set_realm_config

        realms = await self._data_manager.load_realms()
        set_realm_config(realms)
        equipments = await self._data_manager.load_weapons()
        set_equipment_registry(equipments)
        heart_methods = await self._data_manager.load_heart_methods()
        set_heart_method_registry(heart_methods)
        gongfas = await self._data_manager.load_gongfas()
        set_gongfa_registry(gongfas)

    async def _normalize_players_after_registry_change(self):
        """当定义表变化后，归一化玩家爵位与装备/技能状态。"""
        changed = False
        for player in self._players.values():
            realm_changed = self._normalize_player_realm_progress(player)
            stats_changed = self._sync_player_base_stats(player)
            removed = self._auto_unequip_invalid_equipment(player)
            heart_fix = self._auto_unequip_invalid_heart_method(player, convert_ratio=0.0, force=False)
            removed_gongfas = self._auto_unequip_invalid_gongfa(player)
            hp_changed = self._clamp_player_hp(player)
            if realm_changed or stats_changed or removed or heart_fix.get("removed_name") or removed_gongfas or hp_changed:
                changed = True
        if changed:
            await self._data_manager.save_all_players(self._players)

    async def admin_list_adventure_scenes(self) -> list[dict]:
        return await self._data_manager.admin_list_adventure_scenes()

    async def admin_create_adventure_scene(self, category: str, name: str, description: str) -> dict:
        category = str(category or "").strip()
        name = str(name or "").strip()
        description = str(description or "").strip()
        if not category or not name or not description:
            return {"success": False, "message": "分类、场景名、描述不能为空"}
        if await self._data_manager.admin_has_adventure_scene_name(name):
            return {"success": False, "message": f"征战场景名称「{name}」已存在，禁止重名"}
        scene_id = await self._data_manager.admin_create_adventure_scene(category, name, description)
        return {"success": True, "message": "征战场景已新增", "id": scene_id}

    async def admin_update_adventure_scene(self, scene_id: int, category: str, name: str, description: str) -> dict:
        try:
            scene_id = int(scene_id)
        except (TypeError, ValueError):
            return {"success": False, "message": "场景ID无效"}
        category = str(category or "").strip()
        name = str(name or "").strip()
        description = str(description or "").strip()
        if not category or not name or not description:
            return {"success": False, "message": "分类、场景名、描述不能为空"}
        ok = await self._data_manager.admin_update_adventure_scene(scene_id, category, name, description)
        if not ok:
            return {"success": False, "message": "场景不存在"}
        return {"success": True, "message": "征战场景已更新"}

    async def admin_delete_adventure_scene(self, scene_id: int) -> dict:
        try:
            scene_id = int(scene_id)
        except (TypeError, ValueError):
            return {"success": False, "message": "场景ID无效"}
        ok = await self._data_manager.admin_delete_adventure_scene(scene_id)
        if not ok:
            return {"success": False, "message": "场景不存在"}
        return {"success": True, "message": "征战场景已删除"}

    # ── 公告管理 ────────────────────────────────────────────
    async def get_active_announcements(self) -> list[dict]:
        return await self._data_manager.get_active_announcements()

    async def admin_list_announcements(self) -> list[dict]:
        return await self._data_manager.admin_list_announcements()

    async def admin_create_announcement(self, title: str, content: str) -> dict:
        title = str(title or "").strip()
        content = str(content or "").strip()
        if not title or not content:
            return {"success": False, "message": "标题和内容不能为空"}
        ann_id = await self._data_manager.admin_create_announcement(title, content)
        return {"success": True, "message": "公告已创建", "id": ann_id}

    async def admin_update_announcement(self, ann_id: int, title: str, content: str, enabled: int) -> dict:
        try:
            ann_id = int(ann_id)
        except (TypeError, ValueError):
            return {"success": False, "message": "公告ID无效"}
        title = str(title or "").strip()
        content = str(content or "").strip()
        if not title or not content:
            return {"success": False, "message": "标题和内容不能为空"}
        enabled = 1 if int(enabled or 0) else 0
        ok = await self._data_manager.admin_update_announcement(ann_id, title, content, enabled)
        if not ok:
            return {"success": False, "message": "公告不存在"}
        return {"success": True, "message": "公告已更新"}

    async def admin_delete_announcement(self, ann_id: int) -> dict:
        try:
            ann_id = int(ann_id)
        except (TypeError, ValueError):
            return {"success": False, "message": "公告ID无效"}
        ok = await self._data_manager.admin_delete_announcement(ann_id)
        if not ok:
            return {"success": False, "message": "公告不存在"}
        return {"success": True, "message": "公告已删除"}

    # ── 关于页面 ──────────────────────────────────────────────

    async def get_about_page(self) -> dict:
        """获取关于页面内容（公开接口）"""
        return await self._data_manager.get_about_page()

    async def admin_update_about_page(self, acknowledgements: str, rules: str) -> dict:
        """更新关于页面内容"""
        ok = await self._data_manager.admin_update_about_page(acknowledgements, rules)
        if not ok:
            return {"success": False, "message": "更新失败"}
        return {"success": True, "message": "关于页面已更新"}

    # ── 数据库维护 ───────────────────────────────────────────

    async def admin_db_health_check(self) -> dict:
        """管理员接口：数据库健康检查"""
        return await self._data_manager.db_health_check()

    async def admin_db_vacuum(self) -> dict:
        """管理员接口：数据库优化（VACUUM）"""
        return await self._data_manager.db_vacuum()

    async def admin_db_backup(self, backup_path: str) -> dict:
        """管理员接口：数据库备份"""
        return await self._data_manager.db_backup(backup_path)

    async def admin_get_table_info(self) -> list[dict]:
        """管理员接口：获取所有表的信息"""
        return await self._data_manager.get_table_info()

    # ── 音效系统 ───────────────────────────────────────────

    async def get_audio_config(self) -> dict:
        """获取音效配置"""
        return await self._data_manager.get_audio_config()

    async def update_audio_settings(
        self,
        enabled: bool = None,
        music_enabled: bool = None,
        sound_volume: float = None,
        music_volume: float = None,
    ) -> dict:
        """更新玩家音效设置"""
        return await self._data_manager.update_audio_config(
            enabled=enabled,
            music_enabled=music_enabled,
            sound_volume=sound_volume,
            music_volume=music_volume,
        )

    async def admin_update_audio_files(self, audio_type: str, file_path: str) -> dict:
        """管理员更新音效文件"""
        return await self._data_manager.admin_update_audio_files(audio_type, file_path)

    async def admin_list_heart_methods(self) -> list[dict]:
        rows = await self._data_manager.admin_list_heart_methods()
        result = []
        for row in rows:
            item = dict(row)
            quality = int(item.get("quality", 0))
            realm = int(item.get("realm", 0))
            item["quality_name"] = HEART_METHOD_QUALITY_NAMES.get(quality, str(quality))
            item["realm_name"] = get_realm_name(realm, 0)
            item["enabled"] = 1 if int(item.get("enabled", 1)) else 0
            result.append(item)
        return result

    @staticmethod
    def _normalize_enabled_flag(value) -> int:
        if isinstance(value, str):
            v = value.strip().lower()
            if v in {"0", "false", "off", "no"}:
                return 0
            return 1
        return 0 if int(value or 0) == 0 else 1

    async def admin_create_heart_method(self, payload: dict) -> dict:
        method_id = str(payload.get("method_id", "")).strip()
        if not re.fullmatch(r"[a-z0-9_]{3,64}", method_id):
            return {"success": False, "message": "被动技能ID仅支持3-64位小写字母/数字/下划线"}
        data = {
            "method_id": method_id,
            "name": str(payload.get("name", "")).strip(),
            "realm": int(payload.get("realm", 0)),
            "quality": int(payload.get("quality", 0)),
            "exp_multiplier": float(payload.get("exp_multiplier", 0.0)),
            "attack_bonus": int(payload.get("attack_bonus", 0)),
            "defense_bonus": int(payload.get("defense_bonus", 0)),
            "dao_yun_rate": float(payload.get("dao_yun_rate", 0.0)),
            "description": str(payload.get("description", "")),
            "mastery_exp": int(payload.get("mastery_exp", 100)),
            "enabled": self._normalize_enabled_flag(payload.get("enabled", 1)),
        }
        if not data["name"]:
            return {"success": False, "message": "被动技能名称不能为空"}
        if data["realm"] not in REALM_CONFIG:
            return {"success": False, "message": "爵位值无效"}
        if data["quality"] not in {0, 1, 2}:
            return {"success": False, "message": "品质值无效"}
        if data["mastery_exp"] <= 0:
            return {"success": False, "message": "修炼阶段经验阈值必须大于0"}
        if await self._data_manager.admin_has_heart_method_name(data["name"]):
            return {"success": False, "message": f"被动技能名称「{data['name']}」已存在，禁止重名"}
        ok = await self._data_manager.admin_create_heart_method(data)
        if not ok:
            return {"success": False, "message": "被动技能ID已存在"}
        await self._reload_runtime_registries()
        await self._normalize_players_after_registry_change()
        return {"success": True, "message": "被动技能已新增"}

    async def admin_update_heart_method(self, method_id: str, payload: dict) -> dict:
        method_id = str(method_id or "").strip()
        if not method_id:
            return {"success": False, "message": "缺少被动技能ID"}
        data = {
            "name": str(payload.get("name", "")).strip(),
            "realm": int(payload.get("realm", 0)),
            "quality": int(payload.get("quality", 0)),
            "exp_multiplier": float(payload.get("exp_multiplier", 0.0)),
            "attack_bonus": int(payload.get("attack_bonus", 0)),
            "defense_bonus": int(payload.get("defense_bonus", 0)),
            "dao_yun_rate": float(payload.get("dao_yun_rate", 0.0)),
            "description": str(payload.get("description", "")),
            "mastery_exp": int(payload.get("mastery_exp", 100)),
            "enabled": self._normalize_enabled_flag(payload.get("enabled", 1)),
        }
        if not data["name"]:
            return {"success": False, "message": "被动技能名称不能为空"}
        if data["realm"] not in REALM_CONFIG:
            return {"success": False, "message": "爵位值无效"}
        if data["quality"] not in {0, 1, 2}:
            return {"success": False, "message": "品质值无效"}
        if data["mastery_exp"] <= 0:
            return {"success": False, "message": "修炼阶段经验阈值必须大于0"}
        ok = await self._data_manager.admin_update_heart_method(method_id, data)
        if not ok:
            return {"success": False, "message": "被动技能不存在"}
        await self._reload_runtime_registries()
        await self._normalize_players_after_registry_change()
        return {"success": True, "message": "被动技能已更新"}

    async def admin_delete_heart_method(self, method_id: str) -> dict:
        method_id = str(method_id or "").strip()
        if not method_id:
            return {"success": False, "message": "缺少被动技能ID"}
        ok = await self._data_manager.admin_delete_heart_method(method_id)
        if not ok:
            return {"success": False, "message": "被动技能不存在"}
        await self._reload_runtime_registries()
        await self._normalize_players_after_registry_change()
        return {"success": True, "message": "被动技能已删除"}

    async def admin_list_gongfas(self) -> list[dict]:
        rows = await self._data_manager.admin_list_gongfas()
        result = []
        for row in rows:
            item = dict(row)
            tier = int(item.get("tier", 0))
            item["tier_name"] = GONGFA_TIER_NAMES.get(tier, str(tier))
            item["enabled"] = 1 if int(item.get("enabled", 1)) else 0
            result.append(item)
        return result

    async def admin_create_gongfa(self, payload: dict) -> dict:
        gongfa_id = str(payload.get("gongfa_id", "")).strip()
        if not re.fullmatch(r"[a-z0-9_]{3,64}", gongfa_id):
            return {"success": False, "message": "战技ID仅支持3-64位小写字母/数字/下划线"}
        data = {
            "gongfa_id": gongfa_id,
            "name": str(payload.get("name", "")).strip(),
            "tier": int(payload.get("tier", 0)),
            "attack_bonus": int(payload.get("attack_bonus", 0)),
            "defense_bonus": int(payload.get("defense_bonus", 0)),
            "hp_regen": int(payload.get("hp_regen", 0)),
            "lingqi_regen": int(payload.get("lingqi_regen", 0)),
            "description": str(payload.get("description", "")),
            "mastery_exp": int(payload.get("mastery_exp", 200)),
            "dao_yun_cost": int(payload.get("dao_yun_cost", 0)),
            "recycle_price": int(payload.get("recycle_price", 1000)),
            "lingqi_cost": int(payload.get("lingqi_cost", 0) or 0),
            "enabled": self._normalize_enabled_flag(payload.get("enabled", 1)),
        }
        if not data["name"]:
            return {"success": False, "message": "战技名称不能为空"}
        if data["tier"] not in {0, 1, 2, 3}:
            return {"success": False, "message": "品阶值无效（0-3）"}
        if data["mastery_exp"] <= 0:
            return {"success": False, "message": "修炼阶段经验阈值必须大于0"}
        if data["lingqi_cost"] <= 0:
            data["lingqi_cost"] = calc_gongfa_lingqi_cost(
                data["tier"],
                data["attack_bonus"],
                data["defense_bonus"],
                data["hp_regen"],
                data["lingqi_regen"],
            )
        if await self._data_manager.admin_has_gongfa_name(data["name"]):
            return {"success": False, "message": f"战技名称「{data['name']}」已存在，禁止重名"}
        ok = await self._data_manager.admin_create_gongfa(data)
        if not ok:
            return {"success": False, "message": "战技ID已存在"}
        await self._reload_runtime_registries()
        await self._normalize_players_after_registry_change()
        return {"success": True, "message": "战技已新增"}

    async def admin_update_gongfa(self, gongfa_id: str, payload: dict) -> dict:
        gongfa_id = str(gongfa_id or "").strip()
        if not gongfa_id:
            return {"success": False, "message": "缺少战技ID"}
        data = {
            "name": str(payload.get("name", "")).strip(),
            "tier": int(payload.get("tier", 0)),
            "attack_bonus": int(payload.get("attack_bonus", 0)),
            "defense_bonus": int(payload.get("defense_bonus", 0)),
            "hp_regen": int(payload.get("hp_regen", 0)),
            "lingqi_regen": int(payload.get("lingqi_regen", 0)),
            "description": str(payload.get("description", "")),
            "mastery_exp": int(payload.get("mastery_exp", 200)),
            "dao_yun_cost": int(payload.get("dao_yun_cost", 0)),
            "recycle_price": int(payload.get("recycle_price", 1000)),
            "lingqi_cost": int(payload.get("lingqi_cost", 0) or 0),
            "enabled": self._normalize_enabled_flag(payload.get("enabled", 1)),
        }
        if not data["name"]:
            return {"success": False, "message": "战技名称不能为空"}
        if data["tier"] not in {0, 1, 2, 3}:
            return {"success": False, "message": "品阶值无效（0-3）"}
        if data["mastery_exp"] <= 0:
            return {"success": False, "message": "修炼阶段经验阈值必须大于0"}
        if data["lingqi_cost"] <= 0:
            data["lingqi_cost"] = calc_gongfa_lingqi_cost(
                data["tier"],
                data["attack_bonus"],
                data["defense_bonus"],
                data["hp_regen"],
                data["lingqi_regen"],
            )
        ok = await self._data_manager.admin_update_gongfa(gongfa_id, data)
        if not ok:
            return {"success": False, "message": "战技不存在"}
        await self._reload_runtime_registries()
        await self._normalize_players_after_registry_change()
        return {"success": True, "message": "战技已更新"}

    async def admin_delete_gongfa(self, gongfa_id: str) -> dict:
        gongfa_id = str(gongfa_id or "").strip()
        if not gongfa_id:
            return {"success": False, "message": "缺少战技ID"}
        ok = await self._data_manager.admin_delete_gongfa(gongfa_id)
        if not ok:
            return {"success": False, "message": "战技不存在"}
        await self._reload_runtime_registries()
        await self._normalize_players_after_registry_change()
        return {"success": True, "message": "战技已删除"}

    # ---- 爵位管理 CRUD ----

    async def admin_list_realms(self) -> list[dict]:
        return await self._data_manager.admin_list_realms()

    async def admin_create_realm(self, payload: dict) -> dict:
        try:
            level = int(payload.get("level", -1))
        except (TypeError, ValueError):
            return {"success": False, "message": "爵位等级必须为整数"}
        if level < 0:
            return {"success": False, "message": "爵位等级不能为负数"}
        name = str(payload.get("name", "")).strip()
        if not name:
            return {"success": False, "message": "爵位名称不能为空"}
        if await self._data_manager.admin_has_realm_name(name):
            return {"success": False, "message": f"爵位名称「{name}」已存在，禁止重名"}
        data = {
            "level": level,
            "name": name,
            "has_sub_realm": self._normalize_enabled_flag(payload.get("has_sub_realm", 0)),
            "high_realm": self._normalize_enabled_flag(payload.get("high_realm", 0)),
            "exp_to_next": max(0, int(payload.get("exp_to_next", 100))),
            "sub_exp_to_next": max(0, int(payload.get("sub_exp_to_next", 0))),
            "base_hp": max(1, int(payload.get("base_hp", 100))),
            "base_attack": max(0, int(payload.get("base_attack", 10))),
            "base_defense": max(0, int(payload.get("base_defense", 5))),
            "base_lingqi": max(1, int(payload.get("base_lingqi", 50))),
            "breakthrough_rate": max(0.0, min(1.0, float(payload.get("breakthrough_rate", 1.0)))),
            "death_rate": max(0.0, min(1.0, float(payload.get("death_rate", 0.0)))),
            "sub_dao_yun_costs": str(payload.get("sub_dao_yun_costs", "")),
            "breakthrough_dao_yun_cost": max(0, int(payload.get("breakthrough_dao_yun_cost", 0))),
        }
        ok = await self._data_manager.admin_create_realm(data)
        if not ok:
            return {"success": False, "message": f"爵位等级 {level} 已存在"}
        await self._reload_runtime_registries()
        await self._normalize_players_after_registry_change()
        return {"success": True, "message": "爵位已新增"}

    async def admin_update_realm(self, level: int, payload: dict) -> dict:
        name = str(payload.get("name", "")).strip()
        if not name:
            return {"success": False, "message": "爵位名称不能为空"}
        if await self._data_manager.admin_has_realm_name(name, exclude_level=level):
            return {"success": False, "message": f"爵位名称「{name}」已存在，禁止重名"}
        data = {
            "name": name,
            "has_sub_realm": self._normalize_enabled_flag(payload.get("has_sub_realm", 0)),
            "high_realm": self._normalize_enabled_flag(payload.get("high_realm", 0)),
            "exp_to_next": max(0, int(payload.get("exp_to_next", 100))),
            "sub_exp_to_next": max(0, int(payload.get("sub_exp_to_next", 0))),
            "base_hp": max(1, int(payload.get("base_hp", 100))),
            "base_attack": max(0, int(payload.get("base_attack", 10))),
            "base_defense": max(0, int(payload.get("base_defense", 5))),
            "base_lingqi": max(1, int(payload.get("base_lingqi", 50))),
            "breakthrough_rate": max(0.0, min(1.0, float(payload.get("breakthrough_rate", 1.0)))),
            "death_rate": max(0.0, min(1.0, float(payload.get("death_rate", 0.0)))),
            "sub_dao_yun_costs": str(payload.get("sub_dao_yun_costs", "")),
            "breakthrough_dao_yun_cost": max(0, int(payload.get("breakthrough_dao_yun_cost", 0))),
        }
        ok = await self._data_manager.admin_update_realm(level, data)
        if not ok:
            return {"success": False, "message": "爵位不存在"}
        await self._reload_runtime_registries()
        await self._normalize_players_after_registry_change()
        return {"success": True, "message": "爵位已更新"}

    async def admin_delete_realm(self, level: int) -> dict:
        ok = await self._data_manager.admin_delete_realm(level)
        if not ok:
            return {"success": False, "message": "爵位不存在"}
        await self._reload_runtime_registries()
        await self._normalize_players_after_registry_change()
        return {"success": True, "message": "爵位已删除"}

    async def get_realm_names(self) -> dict[int, str]:
        """获取爵位等级→名称映射。"""
        return await self._data_manager.get_realm_names()

    async def admin_list_weapons(self) -> list[dict]:
        from .constants import EQUIPMENT_TIER_NAMES

        rows = await self._data_manager.admin_list_weapons()
        result = []
        for row in rows:
            item = dict(row)
            tier = int(item.get("tier", 0))
            item["tier_name"] = EQUIPMENT_TIER_NAMES.get(tier, str(tier))
            item["enabled"] = 1 if int(item.get("enabled", 1)) else 0
            result.append(item)
        return result

    async def admin_create_weapon(self, payload: dict) -> dict:
        equip_id = str(payload.get("equip_id", "")).strip()
        if not re.fullmatch(r"[a-z0-9_]{3,64}", equip_id):
            return {"success": False, "message": "武器ID仅支持3-64位小写字母/数字/下划线"}
        slot = str(payload.get("slot", "")).strip().lower()
        if slot not in {"weapon", "armor"}:
            return {"success": False, "message": "槽位仅支持 weapon 或 armor"}
        tier = int(payload.get("tier", 0))
        if tier not in {0, 1, 2, 3}:
            return {"success": False, "message": "品阶值无效"}
        data = {
            "equip_id": equip_id,
            "name": str(payload.get("name", "")).strip(),
            "tier": tier,
            "slot": slot,
            "attack": int(payload.get("attack", 0)),
            "defense": int(payload.get("defense", 0)),
            "element": str(payload.get("element", "无") or "无").strip(),
            "element_damage": int(payload.get("element_damage", 0)),
            "description": str(payload.get("description", "")),
            "enabled": self._normalize_enabled_flag(payload.get("enabled", 1)),
        }
        if not data["name"]:
            return {"success": False, "message": "装备名称不能为空"}
        if await self._data_manager.admin_has_weapon_name(data["name"]):
            return {"success": False, "message": f"装备名称「{data['name']}」已存在，禁止重名"}
        ok = await self._data_manager.admin_create_weapon(data)
        if not ok:
            return {"success": False, "message": "武器ID已存在"}
        await self._reload_runtime_registries()
        await self._normalize_players_after_registry_change()
        return {"success": True, "message": "装备已新增"}

    async def admin_update_weapon(self, equip_id: str, payload: dict) -> dict:
        equip_id = str(equip_id or "").strip()
        if not equip_id:
            return {"success": False, "message": "缺少武器ID"}
        slot = str(payload.get("slot", "")).strip().lower()
        if slot not in {"weapon", "armor"}:
            return {"success": False, "message": "槽位仅支持 weapon 或 armor"}
        tier = int(payload.get("tier", 0))
        if tier not in {0, 1, 2, 3}:
            return {"success": False, "message": "品阶值无效"}
        data = {
            "name": str(payload.get("name", "")).strip(),
            "tier": tier,
            "slot": slot,
            "attack": int(payload.get("attack", 0)),
            "defense": int(payload.get("defense", 0)),
            "element": str(payload.get("element", "无") or "无").strip(),
            "element_damage": int(payload.get("element_damage", 0)),
            "description": str(payload.get("description", "")),
            "enabled": self._normalize_enabled_flag(payload.get("enabled", 1)),
        }
        if not data["name"]:
            return {"success": False, "message": "装备名称不能为空"}
        ok = await self._data_manager.admin_update_weapon(equip_id, data)
        if not ok:
            return {"success": False, "message": "装备不存在"}
        await self._reload_runtime_registries()
        await self._normalize_players_after_registry_change()
        return {"success": True, "message": "装备已更新"}

    async def admin_delete_weapon(self, equip_id: str) -> dict:
        equip_id = str(equip_id or "").strip()
        if not equip_id:
            return {"success": False, "message": "缺少武器ID"}
        ok = await self._data_manager.admin_delete_weapon(equip_id)
        if not ok:
            return {"success": False, "message": "装备不存在"}
        await self._reload_runtime_registries()
        await self._normalize_players_after_registry_change()
        return {"success": True, "message": "装备已删除"}

    async def admin_list_market_listings(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str = "",
        keyword: str = "",
    ) -> dict:
        """管理员分页查询坊市记录。"""
        st = str(status or "").strip().lower()
        allowed_status = {"", "all", "active", "sold", "cancelled", "expired"}
        if st not in allowed_status:
            st = ""
        if st == "all":
            st = ""

        data = await self._data_manager.admin_list_market_listings(
            page=page,
            page_size=page_size,
            status=st,
            keyword=str(keyword or "").strip(),
        )

        for item in data.get("listings", []):
            item["item_name"] = market_mod.get_item_name(str(item.get("item_id", "")))
            seller = self._players.get(str(item.get("seller_id", "")))
            buyer = self._players.get(str(item.get("buyer_id", "")))
            item["seller_name"] = seller.name if seller else "未知"
            item["buyer_name"] = buyer.name if buyer else "--"
        return data

    async def admin_create_market_listing(self, payload: dict) -> dict:
        """管理员新增坊市记录。"""
        seller_id = str(payload.get("seller_id", "")).strip()
        if not seller_id:
            return {"success": False, "message": "卖家ID不能为空"}
        if seller_id not in self._players:
            return {"success": False, "message": "卖家ID不存在"}

        item_id = str(payload.get("item_id", "")).strip()
        if not item_id:
            return {"success": False, "message": "物品ID不能为空"}
        if item_id not in ITEM_REGISTRY and item_id not in EQUIPMENT_REGISTRY:
            return {"success": False, "message": "物品ID不存在"}

        try:
            quantity = int(payload.get("quantity", 0))
            unit_price = int(payload.get("unit_price", 0))
            fee = int(payload.get("fee", 0))
        except (TypeError, ValueError):
            return {"success": False, "message": "数量/价格/手续费必须为整数"}

        if quantity <= 0:
            return {"success": False, "message": "数量必须大于0"}
        if unit_price < market_mod.MIN_UNIT_PRICE:
            return {"success": False, "message": f"单价不能低于{market_mod.MIN_UNIT_PRICE}"}
        if fee < 0:
            return {"success": False, "message": "手续费不能小于0"}

        status = str(payload.get("status", "active")).strip().lower() or "active"
        if status not in {"active", "sold", "cancelled", "expired"}:
            return {"success": False, "message": "状态仅支持 active/sold/cancelled/expired"}

        now = time.time()
        try:
            listed_at = float(payload.get("listed_at", now))
            expires_at = float(payload.get("expires_at", listed_at + market_mod.LISTING_DURATION))
        except (TypeError, ValueError):
            return {"success": False, "message": "时间戳格式错误"}

        if expires_at <= listed_at:
            return {"success": False, "message": "过期时间必须大于上架时间"}

        buyer_id = str(payload.get("buyer_id", "")).strip()
        sold_at_raw = payload.get("sold_at")
        sold_at = None
        if sold_at_raw not in (None, ""):
            try:
                sold_at = float(sold_at_raw)
            except (TypeError, ValueError):
                return {"success": False, "message": "成交时间格式错误"}

        if status == "sold":
            if not buyer_id:
                return {"success": False, "message": "sold 状态必须提供买家ID"}
            if buyer_id not in self._players:
                return {"success": False, "message": "买家ID不存在"}
            if sold_at is None:
                sold_at = now
        else:
            buyer_id = ""
            sold_at = None

        listing_id = str(payload.get("listing_id", "")).strip().lower()
        if listing_id:
            if not re.fullmatch(r"[a-z0-9_]{6,32}", listing_id):
                return {"success": False, "message": "记录ID仅支持6-32位小写字母/数字/下划线"}
        else:
            import secrets as _s
            listing_id = _s.token_hex(6)

        total_price = quantity * unit_price
        ok = await self._data_manager.admin_create_market_listing({
            "listing_id": listing_id,
            "seller_id": seller_id,
            "item_id": item_id,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": total_price,
            "fee": fee,
            "listed_at": listed_at,
            "expires_at": expires_at,
            "status": status,
            "buyer_id": buyer_id,
            "sold_at": sold_at,
        })
        if not ok:
            return {"success": False, "message": "记录ID已存在"}

        await self._notify_market_changed("admin_create")
        return {"success": True, "message": "坊市记录已新增"}

    async def admin_update_market_listing(self, listing_id: str, payload: dict) -> dict:
        """管理员更新坊市记录。"""
        listing_id = str(listing_id or "").strip().lower()
        if not listing_id:
            return {"success": False, "message": "缺少记录ID"}

        old = await self._data_manager.get_listing_by_id(listing_id)
        if not old:
            return {"success": False, "message": "坊市记录不存在"}

        seller_id = str(payload.get("seller_id", old.get("seller_id", ""))).strip()
        if seller_id not in self._players:
            return {"success": False, "message": "卖家ID不存在"}

        item_id = str(payload.get("item_id", old.get("item_id", ""))).strip()
        if item_id not in ITEM_REGISTRY and item_id not in EQUIPMENT_REGISTRY:
            return {"success": False, "message": "物品ID不存在"}

        try:
            quantity = int(payload.get("quantity", old.get("quantity", 0)))
            unit_price = int(payload.get("unit_price", old.get("unit_price", 0)))
            fee = int(payload.get("fee", old.get("fee", 0)))
        except (TypeError, ValueError):
            return {"success": False, "message": "数量/价格/手续费必须为整数"}

        if quantity <= 0:
            return {"success": False, "message": "数量必须大于0"}
        if unit_price < market_mod.MIN_UNIT_PRICE:
            return {"success": False, "message": f"单价不能低于{market_mod.MIN_UNIT_PRICE}"}
        if fee < 0:
            return {"success": False, "message": "手续费不能小于0"}

        status = str(payload.get("status", old.get("status", "active"))).strip().lower() or "active"
        if status not in {"active", "sold", "cancelled", "expired"}:
            return {"success": False, "message": "状态仅支持 active/sold/cancelled/expired"}

        try:
            listed_at = float(payload.get("listed_at", old.get("listed_at", time.time())))
            expires_at = float(payload.get("expires_at", old.get("expires_at", listed_at + market_mod.LISTING_DURATION)))
        except (TypeError, ValueError):
            return {"success": False, "message": "时间戳格式错误"}

        if expires_at <= listed_at:
            return {"success": False, "message": "过期时间必须大于上架时间"}

        buyer_id = str(payload.get("buyer_id", old.get("buyer_id", ""))).strip()
        sold_at_raw = payload.get("sold_at", old.get("sold_at"))
        sold_at = None
        if sold_at_raw not in (None, ""):
            try:
                sold_at = float(sold_at_raw)
            except (TypeError, ValueError):
                return {"success": False, "message": "成交时间格式错误"}

        if status == "sold":
            if not buyer_id:
                return {"success": False, "message": "sold 状态必须提供买家ID"}
            if buyer_id not in self._players:
                return {"success": False, "message": "买家ID不存在"}
            if sold_at is None:
                sold_at = time.time()
        else:
            buyer_id = ""
            sold_at = None

        total_price = quantity * unit_price
        ok = await self._data_manager.admin_update_market_listing(listing_id, {
            "seller_id": seller_id,
            "item_id": item_id,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": total_price,
            "fee": fee,
            "listed_at": listed_at,
            "expires_at": expires_at,
            "status": status,
            "buyer_id": buyer_id,
            "sold_at": sold_at,
        })
        if not ok:
            return {"success": False, "message": "坊市记录不存在"}

        await self._notify_market_changed("admin_update")
        return {"success": True, "message": "坊市记录已更新"}

    async def admin_delete_market_listing(self, listing_id: str) -> dict:
        """管理员删除坊市记录。"""
        listing_id = str(listing_id or "").strip().lower()
        if not listing_id:
            return {"success": False, "message": "缺少记录ID"}
        ok = await self._data_manager.admin_delete_market_listing(listing_id)
        if not ok:
            return {"success": False, "message": "坊市记录不存在"}
        await self._notify_market_changed("admin_delete")
        return {"success": True, "message": "坊市记录已删除"}

    async def breakthrough(self, user_id: str) -> dict:
        """晋升操作。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        # 检查是否有已使用的晋级证书
        bonus = 0.0
        if getattr(player, 'breakthrough_pill_count', 0) > 0:
            bonus = 0.2
            player.breakthrough_pill_count -= 1

        # 检查是否有护身符
        prevent_death = False
        if player.inventory.get("life_talisman", 0) > 0:
            player.inventory["life_talisman"] -= 1
            if player.inventory["life_talisman"] <= 0:
                del player.inventory["life_talisman"]
            prevent_death = True

        result = await attempt_breakthrough(player, bonus, prevent_death)

        # 处理死亡
        if result.get("died"):
            death_items = await self.prepare_death(user_id)
            result["death_items"] = death_items
        else:
            await self._save_player(player)
        return result

    async def use_item_action(self, user_id: str, item_id: str, count: int = 1) -> dict:
        """使用物品。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        result = await use_item(player, item_id, count)
        if result["success"]:
            await self._save_player(player)
        return result

    async def use_item_by_name(self, user_id: str, item_name: str) -> dict:
        """通过物品名使用物品（聊天指令用）。"""
        item_id = find_item_id_by_name(item_name)
        if not item_id:
            return {"success": False, "message": f"找不到物品：{item_name}"}
        return await self.use_item_action(user_id, item_id)

    async def recycle_action(self, user_id: str, item_id: str, count: int = 1) -> dict:
        """回收物品（Web 端使用，传 item_id）。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        result = await recycle_item(player, item_id, count)
        if result["success"]:
            await self._save_player(player)
        return result

    async def recycle_by_name(
        self,
        user_id: str,
        item_name: str,
        count: int = 1,
        query_type: str | None = None,
    ) -> dict:
        """通过物品名回收物品（聊天指令用，可按类型精确匹配）。"""
        target_name = str(item_name or "").strip()
        if not target_name:
            return {"success": False, "message": "物品名不能为空"}

        matches = find_item_ids_by_name(target_name, query_type=query_type)
        if not matches:
            return {"success": False, "message": f"找不到物品：{target_name}"}
        if len(matches) > 1:
            return {
                "success": False,
                "message": f"存在重名物品「{target_name}」，请使用：回收 装备/物品/被动技能/战技 {target_name} [数量]",
            }
        return await self.recycle_action(user_id, matches[0], count)

    async def equip_action(self, user_id: str, equip_id: str) -> dict:
        """装备物品。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        result = await equip_item(player, equip_id)
        if result["success"]:
            await self._save_player(player)
        return result

    async def equip_by_name(self, user_id: str, item_name: str) -> dict:
        """通过物品名装备（聊天指令用）。"""
        item_id = find_item_id_by_name(item_name)
        if not item_id:
            return {"success": False, "message": f"找不到装备：{item_name}"}
        if item_id not in EQUIPMENT_REGISTRY:
            return {"success": False, "message": f"{item_name}不是装备"}
        return await self.equip_action(user_id, item_id)

    async def unequip_action(self, user_id: str, slot: str) -> dict:
        """卸下装备。slot: 'weapon' | 'armor'。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        result = await unequip_item(player, slot)
        if result["success"]:
            await self._save_player(player)
        return result

    # ── 坐骑系统 ─────────────────────────────────────────────
    async def equip_mount_action(self, user_id: str, mount_id: str) -> dict:
        """装备坐骑。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        result = await equip_mount(player, mount_id)
        if result["success"]:
            await self._save_player(player)
        return result

    async def unequip_mount_action(self, user_id: str) -> dict:
        """卸下坐骑。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        result = await unequip_mount(player)
        if result["success"]:
            await self._save_player(player)
        return result

    async def equip_mount_item_action(self, user_id: str, equip_id: str) -> dict:
        """装备坐骑装备。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        result = await equip_mount_item(player, equip_id)
        if result["success"]:
            await self._save_player(player)
        return result

    async def unequip_mount_item_action(self, user_id: str, slot: str) -> dict:
        """卸下坐骑装备。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        result = await unequip_mount_item(player, slot)
        if result["success"]:
            await self._save_player(player)
        return result

    # ── 战技遗忘 ─────────────────────────────────────────
    async def forget_gongfa(self, user_id: str, slot: str) -> dict:
        """遗忘指定槽位的战斗技能，返回技能卷轴。slot: 'gongfa_1' | 'gongfa_2' | 'gongfa_3'。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        if slot not in ("gongfa_1", "gongfa_2", "gongfa_3"):
            return {"success": False, "message": "无效的战斗技能槽位"}

        gongfa_id = getattr(player, slot, "无")
        if not gongfa_id or gongfa_id == "无":
            return {"success": False, "message": "该槽位没有装备战斗技能"}

        gf = GONGFA_REGISTRY.get(gongfa_id)
        name = gf.name if gf else gongfa_id

        # 返回技能卷轴到背包
        scroll_id = get_gongfa_scroll_id(gongfa_id)
        await add_item(player, scroll_id, 1, "遗忘战技")

        # 重置技能槽位和熟练度
        setattr(player, slot, "无")
        setattr(player, f"{slot}_mastery", 0)
        setattr(player, f"{slot}_exp", 0)
        await self._save_player(player)
        await self._notify_player_update(player)
        return {"success": True, "message": f"你已遗忘技能【{name}】，获得技能卷轴"}

    def _auto_unequip_invalid_gongfa(self, player) -> list[str]:
        """自动卸下不在注册表中的战斗技能，返回被卸下的技能名列表。"""
        removed = []
        for slot in ("gongfa_1", "gongfa_2", "gongfa_3"):
            gid = getattr(player, slot, "无")
            if gid and gid != "无" and gid not in GONGFA_REGISTRY:
                removed.append(gid)
                setattr(player, slot, "无")
                setattr(player, f"{slot}_mastery", 0)
                setattr(player, f"{slot}_exp", 0)
        return removed

    def _clean_expired_heart_methods(self, player: Player) -> bool:
        """清理过期的技能道具，返回是否有清理。"""
        if not hasattr(player, "stored_heart_methods") or not isinstance(player.stored_heart_methods, dict):
            player.stored_heart_methods = {}
            return False
        current_time = time.time()
        changed = False
        kept: dict[str, float] = {}
        for mid, expire_time in player.stored_heart_methods.items():
            try:
                expire_at = float(expire_time)
            except (TypeError, ValueError):
                expire_at = 0.0
            item_id = get_stored_heart_method_item_id(mid)
            if current_time > expire_at:
                if item_id in player.inventory:
                    player.inventory.pop(item_id, None)
                    changed = True
                changed = True
                continue
            kept[mid] = expire_at
            if player.inventory.get(item_id, 0) <= 0:
                player.inventory[item_id] = 1
                changed = True
        if kept != player.stored_heart_methods:
            player.stored_heart_methods = kept
            changed = True
        return changed

    async def learn_heart_method(self, user_id: str, method_id: str) -> dict:
        """学习被动技能。更改技能时若达到小成以上需用户确认。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        hm = HEART_METHOD_REGISTRY.get(method_id)
        if not hm:
            return {"success": False, "message": "无效的被动技能"}

        # 爵位限制
        if hm.realm > player.realm:
            realm_name = REALM_CONFIG.get(hm.realm, {}).get("name", "未知")
            return {"success": False, "message": f"【{hm.name}】为{realm_name}被动技能，当前爵位不足"}

        # 已经在学习同一被动技能
        if player.heart_method == method_id:
            mastery_name = MASTERY_LEVELS[min(player.heart_method_mastery, len(MASTERY_LEVELS) - 1)]
            return {"success": False, "message": f"你已在学习【{hm.name}】（{mastery_name}）"}

        old_hm = HEART_METHOD_REGISTRY.get(player.heart_method)

        # 若旧技能达到小成以上，需要用户确认
        if old_hm and player.heart_method_mastery >= 1:
            mastery_name = MASTERY_LEVELS[min(player.heart_method_mastery, len(MASTERY_LEVELS) - 1)]
            return {
                "success": False,
                "needs_confirmation": True,
                "old_method_id": old_hm.method_id,
                "old_method_name": old_hm.name,
                "old_mastery": player.heart_method_mastery,
                "old_mastery_name": mastery_name,
                "new_method_id": method_id,
                "new_method_name": hm.name,
                "message": f"你当前学习的【{old_hm.name}】已达{mastery_name}，是否转换为技能点？"
            }

        # 直接替换（旧技能未达小成或无旧技能）
        old_name = old_hm.name if old_hm else None
        player.heart_method = method_id
        player.heart_method_mastery = 0
        player.heart_method_exp = 0
        await self._save_player(player)

        quality_name = HEART_METHOD_QUALITY_NAMES.get(hm.quality, "")
        msg = f"开始学习{quality_name}被动技能【{hm.name}】（入门）"
        if old_name:
            msg += f"\n（放弃了【{old_name}】的学习进度）"
        return {"success": True, "message": msg}

    async def confirm_replace_heart_method(
        self,
        user_id: str,
        new_method_id: str,
        convert_to_value: bool,
        source_item_id: str,
    ) -> dict:
        """确认替换被动技能。convert_to_value=True转换为技能点，False保留为技能道具。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        new_hm = HEART_METHOD_REGISTRY.get(new_method_id)
        if not new_hm:
            return {"success": False, "message": "无效的被动技能"}
        if new_hm.realm > player.realm:
            realm_name = REALM_CONFIG.get(new_hm.realm, {}).get("name", "未知爵位")
            return {"success": False, "message": f"【{new_hm.name}】需达到{realm_name}方可学习，当前爵位不足"}
        if player.heart_method == new_method_id:
            return {"success": False, "message": f"你已在学习【{new_hm.name}】"}

        item = ITEM_REGISTRY.get(source_item_id)
        if not item or item.item_type not in ("consumable", "heart_method"):
            return {"success": False, "message": "技能秘籍不存在或已失效"}
        item_method_id = str(item.effect.get("learn_heart_method", ""))
        if item_method_id != new_method_id:
            return {"success": False, "message": "确认数据已失效，请重新使用秘籍"}
        if player.inventory.get(source_item_id, 0) <= 0:
            return {"success": False, "message": "技能秘籍已不存在，请重新检查背包"}

        old_hm = HEART_METHOD_REGISTRY.get(player.heart_method)
        if not old_hm or old_hm.method_id == new_method_id or player.heart_method_mastery < 1:
            return {"success": False, "message": "当前技能未达小成，无需确认"}

        old_name = old_hm.name
        old_mastery = player.heart_method_mastery
        old_exp = player.heart_method_exp
        old_method_id = old_hm.method_id
        stored_source_method_id = parse_stored_heart_method_item_id(source_item_id)

        player.inventory[source_item_id] -= 1
        if player.inventory[source_item_id] <= 0:
            del player.inventory[source_item_id]
        if stored_source_method_id:
            player.stored_heart_methods.pop(stored_source_method_id, None)

        from .inventory import _calc_heart_method_convert_points

        player.heart_method_value = max(0, int(getattr(player, "heart_method_value", 0)))
        messages: list[str] = []

        if convert_to_value:
            convert_points = _calc_heart_method_convert_points(old_hm, old_mastery, old_exp, new_hm)
            player.heart_method_value += convert_points
            if convert_points > 0:
                messages.append(f"转化【{old_name}】为{convert_points}点技能点")
            else:
                messages.append(f"转化【{old_name}】未获得可用技能点")
        else:
            expire_time = time.time() + 3 * 24 * 3600
            stored_item_id = get_stored_heart_method_item_id(old_method_id)
            if old_method_id not in player.stored_heart_methods:
                player.stored_heart_methods[old_method_id] = expire_time
                await add_item(player, stored_item_id, 1, "保留被动技能")
                messages.append(f"保留【{old_name}】为技能道具（三天期限）")
            else:
                if player.inventory.get(stored_item_id, 0) <= 0:
                    await add_item(player, stored_item_id, 1, "保留被动技能")
                messages.append(f"保留【{old_name}】为技能道具（沿用原过期时间）")

        player.heart_method = new_method_id
        player.heart_method_mastery = 0
        player.heart_method_exp = 0

        absorbed_value = 0
        if new_hm.realm == player.realm and player.heart_method_value > 0:
            absorb_cap = max(1, int(new_hm.mastery_exp * 0.6))
            absorbed_value = min(player.heart_method_value, absorb_cap)
            player.heart_method_exp = min(new_hm.mastery_exp - 1, player.heart_method_exp + absorbed_value)
            player.heart_method_value -= absorbed_value

        await self._save_player(player)

        quality_name = HEART_METHOD_QUALITY_NAMES.get(new_hm.quality, "")
        messages.append(f"开始学习{quality_name}被动技能【{new_hm.name}】（入门）")
        if absorbed_value > 0:
            messages.append(
                f"吸收预存技能点{absorbed_value}，当前进度{player.heart_method_exp}/{new_hm.mastery_exp}"
                f"（剩余技能点{player.heart_method_value}）"
            )
        return {"success": True, "message": "，".join(messages)}

    async def learn_heart_method_by_name(self, user_id: str, name: str) -> dict:
        """通过技能名学习（聊天指令用）。"""
        for mid, hm in HEART_METHOD_REGISTRY.items():
            if hm.name == name:
                return await self.learn_heart_method(user_id, mid)
        return {"success": False, "message": f"找不到被动技能：{name}"}

    async def get_available_heart_methods(self, user_id: str) -> dict:
        """获取当前爵位可学习的被动技能列表。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色", "methods": []}

        methods = get_realm_heart_methods(player.realm)
        result = []
        for hm in methods:
            is_current = (player.heart_method == hm.method_id)
            result.append({
                "method_id": hm.method_id,
                "name": hm.name,
                "quality": hm.quality,
                "quality_name": HEART_METHOD_QUALITY_NAMES.get(hm.quality, ""),
                "exp_multiplier": hm.exp_multiplier,
                "attack_bonus": hm.attack_bonus,
                "defense_bonus": hm.defense_bonus,
                "dao_yun_rate": hm.dao_yun_rate,
                "description": hm.description,
                "is_current": is_current,
            })
        return {"success": True, "methods": result}

    async def get_panel(self, user_id: str) -> Optional[dict]:
        """获取角色面板数据。"""
        player = self._players.get(user_id)
        if not player:
            return None
        self._clamp_player_hp(player)
        panel = player.to_dict()
        pending = self._pending_deaths.get(user_id)
        if pending:
            panel["pending_death_items"] = pending.get("items", [])
        return panel

    def has_pending_death(self, user_id: str) -> bool:
        """是否存在待确认的战死重生选择。"""
        return user_id in self._pending_deaths

    async def get_inventory(self, user_id: str) -> list[dict]:
        """获取背包展示数据。"""
        player = self._players.get(user_id)
        if not player:
            return []
        return await get_inventory_display(player)

    def get_item_detail(self, item_name: str, query_type: str | None = None) -> dict | None:
        """根据物品名查询物品详情（静态数据查询，不需要 player_id）。

        支持三种类型：消耗品/材料、装备、被动技能秘籍。
        当出现重名条目时按优先级自动返回一个结果：
        装备 > 被动技能秘籍 > 普通物品。
        """
        target_name = str(item_name or "").strip()
        if not target_name:
            return None

        target_type = str(query_type or "").strip()
        candidates: list[dict] = []

        # 1) 在 EQUIPMENT_REGISTRY 中查找装备
        for eq in EQUIPMENT_REGISTRY.values():
            if target_type and target_type != "equipment":
                continue
            if eq.name != target_name:
                continue
            candidates.append({
                "type": "equipment",
                "name": eq.name,
                "tier_name": EQUIPMENT_TIER_NAMES.get(eq.tier, "未知"),
                "slot": "武器" if eq.slot == "weapon" else "护甲",
                "attack": eq.attack,
                "defense": eq.defense,
                "element": eq.element,
                "element_damage": eq.element_damage,
                "description": eq.description,
            })

        # 2) 在 ITEM_REGISTRY 中查找
        for item in ITEM_REGISTRY.values():
            if item.name != target_name:
                continue
            # 检查是否是被动技能秘籍
            method_id = parse_heart_method_manual_id(item.item_id)
            if not method_id:
                method_id = parse_stored_heart_method_item_id(item.item_id)
            if method_id:
                hm = HEART_METHOD_REGISTRY.get(method_id)
                if hm:
                    if target_type and target_type != "heart_method":
                        continue
                    realm_name = REALM_CONFIG.get(hm.realm, {}).get("name", "未知爵位")
                    candidates.append({
                        "type": "heart_method",
                        "name": item.name,
                        "quality_name": HEART_METHOD_QUALITY_NAMES.get(hm.quality, "未知"),
                        "realm_name": realm_name,
                        "attack_bonus": hm.attack_bonus,
                        "defense_bonus": hm.defense_bonus,
                        "exp_multiplier": hm.exp_multiplier,
                        "dao_yun_rate": hm.dao_yun_rate,
                        "description": hm.description,
                    })
                    continue
            # 检查是否是战技卷轴
            gf_id = parse_gongfa_scroll_id(item.item_id)
            if gf_id:
                gf = GONGFA_REGISTRY.get(gf_id)
                if gf:
                    if target_type and target_type != "gongfa":
                        continue
                    candidates.append({
                        "type": "gongfa",
                        "name": item.name,
                        "tier_name": GONGFA_TIER_NAMES.get(gf.tier, "未知"),
                        "attack_bonus": gf.attack_bonus,
                        "defense_bonus": gf.defense_bonus,
                        "hp_regen": gf.hp_regen,
                        "lingqi_regen": gf.lingqi_regen,
                        "description": item.description,
                    })
                    continue
            # 普通消耗品/材料
            if target_type and target_type != "item":
                continue
            candidates.append({
                "type": "item",
                "name": item.name,
                "item_type": item.item_type,
                "description": item.description,
                "effect": item.effect,
            })

        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        type_priority = {
            "equipment": 0,
            "heart_method": 1,
            "gongfa": 2,
            "item": 3,
        }
        candidates.sort(key=lambda c: type_priority.get(str(c.get("type", "")), 9))
        return candidates[0]

    async def _random_drop(self, player: Player):
        """保留兼容：修炼/挂机修炼不再产出任何掉落。"""
        return

    async def _random_equip_drop(self, player: Player):
        """保留兼容：装备掉落已迁移到历练逻辑。"""
        return

    async def _save_player(self, player: Player):
        """保存玩家数据并通知 WebSocket。"""
        # 兜底：若被动技能爵位不符则自动卸下为秘籍，并结转60%被动技能值
        self._auto_unequip_invalid_heart_method(player, convert_ratio=0.6, force=False)
        player.heart_method_value = max(0, int(getattr(player, "heart_method_value", 0)))
        self._clamp_player_hp(player)
        await self._data_manager.save_player(player)
        try:
            await self._notify_player_update(player)
        except Exception:
            logger.exception("战争大陆：玩家状态推送失败 user_id=%s", player.user_id)

    async def _notify_player_update(self, player: Player):
        """向前端推送玩家面板、背包与排行榜变化。"""
        if self._ws_manager:
            await self._ws_manager.notify_player_update(player)
            inv = await get_inventory_display(player)
            await self._ws_manager.send_to_player(player.user_id, {
                "type": "inventory",
                "data": inv,
            })
            if hasattr(self._ws_manager, "queue_rankings_refresh"):
                self._ws_manager.queue_rankings_refresh(self)
            elif hasattr(self._ws_manager, "broadcast"):
                await self._ws_manager.broadcast({
                    "type": "rankings_changed",
                    "data": {"user_id": player.user_id},
                })

    @staticmethod
    def _apply_player_snapshot(player: Player, snapshot: Player):
        """将快照状态覆盖回内存玩家对象。"""
        for field in fields(Player):
            value = getattr(snapshot, field.name)
            if isinstance(value, dict):
                value = dict(value)
            setattr(player, field.name, value)
        GameEngine._clamp_player_hp(player)

    def _get_player_lock(self, user_id: str) -> asyncio.Lock:
        """获取玩家级锁（按需创建），用于保护需要原子修改玩家状态的操作。"""
        return self._player_locks.setdefault(user_id, asyncio.Lock())

    @staticmethod
    def _snapshot_player(player: Player) -> Player:
        """创建玩家对象的深拷贝快照，用于在事务中操作而不影响共享内存。"""
        return Player.from_dict(player.to_dict(include_sensitive=True))

    async def _notify_market_changed(self, action: str, count: int = 0):
        """广播坊市列表变更，驱动前端实时刷新。"""
        if self._ws_manager and hasattr(self._ws_manager, "queue_market_refresh"):
            self._ws_manager.queue_market_refresh(self)
        elif self._ws_manager and hasattr(self._ws_manager, "broadcast"):
            await self._ws_manager.broadcast({
                "type": "market_changed",
                "data": {
                    "action": action,
                    "count": int(count or 0),
                    "ts": time.time(),
                },
            })

    async def _process_market_cleanup(self):
        """清理过期集市商品：逐条在持锁事务内原子完成标记+退物。"""
        expired = await market_mod.cleanup_expired(self._data_manager)
        cleaned_count = 0

        for listing in expired:
            sid = listing["seller_id"]
            seller = self._players.get(sid)
            if not seller:
                # 卖家不在线/已删除，仅标记过期，物品无法退回
                await self._data_manager.update_listing_status(
                    listing["listing_id"], "expired", expected_status="active",
                )
                cleaned_count += 1
                continue

            async with self._get_player_lock(sid):
                snapshot = self._snapshot_player(seller)
                item_id = listing["item_id"]
                snapshot.inventory[item_id] = (
                    snapshot.inventory.get(item_id, 0) + listing["quantity"]
                )
                try:
                    async with self._data_manager.transaction() as tx:
                        cur = await tx.execute(
                            """UPDATE market_listings SET status = ?
                               WHERE listing_id = ? AND status = ?""",
                            ("expired", listing["listing_id"], "active"),
                        )
                        if cur.rowcount <= 0:
                            # 已被并发处理（购买/取消），跳过
                            continue
                        await self._data_manager._upsert_player(snapshot, db=tx)
                except Exception:
                    logger.exception(
                        "战争大陆：过期清理事务失败 listing=%s seller=%s",
                        listing["listing_id"], sid,
                    )
                    continue

                self._apply_player_snapshot(seller, snapshot)
                try:
                    await self._notify_player_update(seller)
                except Exception:
                    logger.exception("战争大陆：玩家状态推送失败 user_id=%s", sid)
                cleaned_count += 1

        if cleaned_count > 0:
            await self._notify_market_changed("cleanup", cleaned_count)

    async def _periodic_cleanup(self):
        """每5分钟清理过期数据（Token/绑定 + 坊市过期商品）。"""
        while True:
            await asyncio.sleep(300)
            try:
                if self.auth:
                    await self.auth.save()
            except Exception:
                logger.exception("战争大陆：定时清理认证数据异常")
            try:
                await self._process_market_cleanup()
            except Exception:
                logger.exception("战争大陆：定时清理集市过期商品异常")

def _auto_unequip_invalid_equipment(self, player: Player) -> list[str]:
        """自动卸下当前爵位无法装备的物品并放回背包。"""
        removed: list[str] = []
        for slot in ("weapon", "armor"):
            equip_id = getattr(player, slot, "无")
            eq = EQUIPMENT_REGISTRY.get(equip_id)
            if not eq:
                if equip_id and equip_id != "无":
                    player.inventory[equip_id] = player.inventory.get(equip_id, 0) + 1
                    setattr(player, slot, "无")
                    removed.append(equip_id)
                continue
            if can_equip(player.realm, eq.tier):
                continue
            player.inventory[equip_id] = player.inventory.get(equip_id, 0) + 1
            setattr(player, slot, "无")
            removed.append(eq.name)
        return removed

    def _auto_unequip_invalid_heart_method(
        self, player: Player, convert_ratio: float = 0.0, force: bool = False
    ) -> dict:
        """自动卸下不符合条件的被动技能，并可按比例结转为技能点。"""
        method_id = getattr(player, "heart_method", "无")
        if not method_id or method_id == "无":
            return {"removed_name": "", "manual_name": "", "converted": 0}

        hm = HEART_METHOD_REGISTRY.get(method_id)
        if not hm:
            player.heart_method = "无"
            player.heart_method_mastery = 0
            player.heart_method_exp = 0
            return {"removed_name": method_id, "manual_name": "", "converted": 0}

        if not force and hm.realm <= player.realm:
            return {"removed_name": "", "manual_name": "", "converted": 0}

        mastery = max(0, min(int(getattr(player, "heart_method_mastery", 0)), len(MASTERY_LEVELS) - 1))
        exp = max(0, int(getattr(player, "heart_method_exp", 0)))
        raw_value = max(0, int(hm.mastery_exp) * mastery + exp)
        converted = max(0, int(raw_value * max(0.0, convert_ratio)))
        if converted > 0:
            player.heart_method_value = max(0, int(getattr(player, "heart_method_value", 0))) + converted

        manual_id = get_heart_method_manual_id(hm.method_id)
        manual = ITEM_REGISTRY.get(manual_id)
        manual_name = f"{hm.name}秘籍"
        if manual:
            player.inventory[manual_id] = player.inventory.get(manual_id, 0) + 1
            manual_name = manual.name

        player.heart_method = "无"
        player.heart_method_mastery = 0
        player.heart_method_exp = 0
        return {"removed_name": hm.name, "manual_name": manual_name, "converted": converted}

    async def _handle_player_death(self, user_id: str, player: Player):
        """处理角色战死：重置为平民，清空背包和金币。"""
        player.death_count += 1
        player.realm = 0
        player.sub_realm = 0
        player.exp = 0
        base_stats = get_player_base_stats(player)
        player.hp = base_stats["max_hp"]
        player.max_hp = base_stats["max_hp"]
        player.attack = base_stats["attack"]
        player.defense = base_stats["defense"]
        player.lingqi = base_stats["max_lingqi"]
        player.dao_yun = 0
        player.spirit_stones = 0
        player.heart_method = "无"
        player.heart_method_mastery = 0
        player.heart_method_exp = 0
        player.heart_method_value = 0
        # 战死后清空驻守训练记录
        player.afk_cultivate_start = 0.0
        player.afk_cultivate_end = 0.0
        # 战落后重置征战冷却，允许重新出发
        player.last_adventure_time = 0.0
        player.weapon = "无"
        player.head = "无"
        player.body = "无"
        player.hands = "无"
        player.legs = "无"
        player.shoulders = "无"
        player.accessory1 = "无"
        player.accessory2 = "无"
        player.gongfa_1 = "无"
        player.gongfa_2 = "无"
        player.gongfa_3 = "无"
        player.gongfa_1_mastery = 0
        player.gongfa_1_exp = 0
        player.gongfa_2_mastery = 0
        player.gongfa_2_exp = 0
        player.gongfa_3_mastery = 0
        player.gongfa_3_exp = 0
        player.inventory.clear()
        # 赠送一点基础物品以便重新开始
        player.inventory["healing_pill"] = 1
        await self._save_player(player)

    async def prepare_death(self, user_id: str) -> list[dict]:
        """收集死亡快照（被动技能、武器、护甲、背包物品），存入 _pending_deaths，返回快照列表。"""
        player = self._players.get(user_id)
        if not player:
            return []

        async with self._get_player_lock(user_id):
            # 已有快照则直接返回，禁止覆盖（防止选择性保留漏洞）
            existing = self._pending_deaths.get(user_id)
            if existing:
                return existing["items"]

            items: list[dict] = []
            snapshot_index = 0

            def make_snapshot_item(item_id: str, item_type: str, **extra) -> dict:
                nonlocal snapshot_index
                snapshot_index += 1
                return {
                    "id": f"death:{snapshot_index}:{item_type}:{item_id}",
                    "item_id": item_id,
                    "type": item_type,
                    **extra,
                }

            # 已学习的被动技能
            if player.heart_method and player.heart_method != "无":
                hm = HEART_METHOD_REGISTRY.get(player.heart_method)
                if hm:
                    items.append(make_snapshot_item(
                        player.heart_method,
                        "heart_method",
                        name=hm.name,
                        count=1,
                        description=hm.description,
                        quality_name=HEART_METHOD_QUALITY_NAMES.get(hm.quality, "普通"),
                    ))

            # 已装备的武器
            if player.weapon and player.weapon != "无":
                eq = EQUIPMENT_REGISTRY.get(player.weapon)
                if eq:
                    items.append(make_snapshot_item(
                        player.weapon,
                        "weapon",
                        name=eq.name,
                        count=1,
                        description=eq.description,
                        tier_name=EQUIPMENT_TIER_NAMES.get(eq.tier, "未知"),
                        slot=eq.slot,
                    ))

            # 已装备的所有装备（武器已在上面单独处理）
            equip_slots = ["head", "body", "hands", "legs", "shoulders", "accessory1", "accessory2"]
            for slot in equip_slots:
                equip_id = getattr(player, slot, "无")
                if equip_id and equip_id != "无":
                    eq = EQUIPMENT_REGISTRY.get(equip_id)
                    if eq:
                        items.append(make_snapshot_item(
                            equip_id,
                            "equipment",
                            name=eq.name,
                            count=1,
                            description=eq.description,
                            tier_name=EQUIPMENT_TIER_NAMES.get(eq.tier, "未知"),
                            slot=eq.slot,
                        ))

            # 已装备的战斗技能
            for gf_slot in ("gongfa_1", "gongfa_2", "gongfa_3"):
                gongfa_id = getattr(player, gf_slot, "无")
                if gongfa_id and gongfa_id != "无":
                    gf = GONGFA_REGISTRY.get(gongfa_id)
                    if gf:
                        items.append(make_snapshot_item(
                            gongfa_id,
                            "gongfa",
                            name=gf.name,
                            count=1,
                            description=gf.description,
                            tier_name=GONGFA_TIER_NAMES.get(gf.tier, "未知"),
                            gongfa_slot=gf_slot,
                        ))

            # 背包物品
            for item_id, count in player.inventory.items():
                item_def = ITEM_REGISTRY.get(item_id)
                if not item_def:
                    continue
                entry = make_snapshot_item(
                    item_id,
                    "item",
                    name=item_def.name,
                    count=count,
                    description=item_def.description,
                )
                eq = EQUIPMENT_REGISTRY.get(item_id)
                if eq:
                    entry["tier_name"] = EQUIPMENT_TIER_NAMES.get(eq.tier, "未知")
                    entry["slot"] = eq.slot
                items.append(entry)

            self._pending_deaths[user_id] = {"items": items}
            return items

    async def confirm_death(self, user_id: str, kept_ids: list[str]) -> dict:
        """校验 kept_ids ≤ 3，执行死亡重置后把保留的物品/装备/被动技能还给玩家。"""
        async with self._get_player_lock(user_id):
            snapshot = self._pending_deaths.pop(user_id, None)
            if not snapshot:
                return {"success": False, "message": "没有待确认的死亡记录"}

            player = self._players.get(user_id)
            if not player:
                return {"success": False, "message": "角色不存在"}

            if len(kept_ids) > 3:
                self._pending_deaths[user_id] = snapshot  # 放回
                return {"success": False, "message": "最多只能保留3样物品"}

            # 从快照中找到要保留的物品
            snapshot_items = snapshot["items"]
            snapshot_map = {item["id"]: item for item in snapshot_items}
            invalid_ids = [snapshot_id for snapshot_id in kept_ids if snapshot_id not in snapshot_map]
            if invalid_ids:
                self._pending_deaths[user_id] = snapshot
                return {"success": False, "message": "存在无效的保留物品，请重新选择"}

            kept_items: list[dict] = []
            seen_ids: set[str] = set()
            for snapshot_id in kept_ids:
                if snapshot_id in seen_ids:
                    continue
                seen_ids.add(snapshot_id)
                kept_items.append(snapshot_map[snapshot_id])

            # 执行原有死亡重置
            await self._handle_player_death(user_id, player)

            # 把保留的物品还给玩家
            for ki in kept_items:
                item_id = ki.get("item_id", ki["id"])
                ktype = ki["type"]
                if ktype == "heart_method":
                    hm = HEART_METHOD_REGISTRY.get(item_id)
                    if hm:
                        player.heart_method = item_id
                        player.heart_method_mastery = 0
                        player.heart_method_exp = 0
                        player.heart_method_value = 0
                elif ktype == "gongfa":
                    # 恢复战斗技能到原槽位（若槽位已被占用则找第一个空槽）
                    target_slot = str(ki.get("gongfa_slot", "")).strip() or "gongfa_1"
                    if target_slot not in {"gongfa_1", "gongfa_2", "gongfa_3"}:
                        target_slot = "gongfa_1"
                    if getattr(player, target_slot, "无") != "无":
                        for s in ("gongfa_1", "gongfa_2", "gongfa_3"):
                            if getattr(player, s, "无") == "无":
                                target_slot = s
                                break
                    if getattr(player, target_slot, "无") == "无" and item_id in GONGFA_REGISTRY:
                        setattr(player, target_slot, item_id)
                        setattr(player, f"{target_slot}_mastery", 0)
                        setattr(player, f"{target_slot}_exp", 0)
                elif ktype in ("weapon", "armor"):
                    # 装备放入背包（死亡后爵位归零，可能无法穿戴）
                    player.inventory[item_id] = player.inventory.get(item_id, 0) + 1
                else:
                    player.inventory[item_id] = player.inventory.get(item_id, 0) + ki.get("count", 1)

            await self._save_player(player)
            await self._notify_player_update(player)
            return {"success": True, "message": "携宝重生成功"}

    async def shutdown(self):
        """关闭时保存所有数据并关闭数据库。"""
        # 取消定时清理任务
        if hasattr(self, "_cleanup_task"):
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        if self._ws_manager and hasattr(self._ws_manager, "stop_chat_cleanup_task"):
            await self._ws_manager.stop_chat_cleanup_task()
        for player in self._players.values():
            self._clamp_player_hp(player)
        await self._data_manager.save_all_players(self._players)
        if self.auth:
            await self.auth.save()
        await self._data_manager.close()

    async def clear_all_data(self, remove_dir: bool = False):
        """清空游戏数据并清理持久化文件。"""
        if self.auth:
            await self.auth.clear_all()
        if self._ws_manager and hasattr(self._ws_manager, "_connections"):
            self._ws_manager._connections.clear()
        self._players.clear()
        self._name_index.clear()
        await self._data_manager.clear_all_data(remove_dir=remove_dir)

    # ==================== 出身选择相关 ====================

    def _apply_origin_bonuses(self, player: Player, origin) -> dict:
        """统一发放出身奖励（属性+物品+装备+技能+第纳尔）。"""
        reward_details = {
            "attributes": [],
            "combat_stats": [],
            "items": [],
            "equipment": [],
            "skills": [],
            "spirit_stones": 0,
        }

        # 发放属性点
        player.strength += origin.bonus_strength
        player.agility += origin.bonus_agility
        player.intelligence += origin.bonus_intelligence
        if origin.bonus_strength:
            reward_details["attributes"].append(f"力量+{origin.bonus_strength}")
        if origin.bonus_agility:
            reward_details["attributes"].append(f"敏捷+{origin.bonus_agility}")
        if origin.bonus_intelligence:
            reward_details["attributes"].append(f"智力+{origin.bonus_intelligence}")

        # 发放战斗属性
        player.hp += origin.bonus_hp
        player.max_hp += origin.bonus_hp
        player.attack += origin.bonus_attack
        player.defense += origin.bonus_defense
        player.lingqi += origin.bonus_lingqi
        player.spirit_stones += origin.bonus_spirit_stones
        if origin.bonus_hp:
            reward_details["combat_stats"].append(f"HP+{origin.bonus_hp}")
        if origin.bonus_attack:
            reward_details["combat_stats"].append(f"攻击+{origin.bonus_attack}")
        if origin.bonus_defense:
            reward_details["combat_stats"].append(f"防御+{origin.bonus_defense}")
        if origin.bonus_lingqi:
            reward_details["combat_stats"].append(f"体力+{origin.bonus_lingqi}")
        if origin.bonus_spirit_stones:
            reward_details["spirit_stones"] = origin.bonus_spirit_stones
            reward_details["combat_stats"].append(f"第纳尔+{origin.bonus_spirit_stones}")

        # 发放物品并自动穿戴装备
        for item_id, count in origin.bonus_items.items():
            player.inventory[item_id] = player.inventory.get(item_id, 0) + count
            eq = EQUIPMENT_REGISTRY.get(item_id)
            if eq and count > 0:
                current = getattr(player, eq.slot, "无")
                if current == "无":
                    setattr(player, eq.slot, item_id)
                    player.inventory[item_id] -= 1
                    if player.inventory[item_id] <= 0:
                        del player.inventory[item_id]
                    reward_details["equipment"].append(f"{eq.name}（已装备）")
                else:
                    reward_details["items"].append(f"{eq.name} x{count}")
            else:
                item_def = ITEM_REGISTRY.get(item_id)
                item_name = item_def.name if item_def else item_id
                reward_details["items"].append(f"{item_name} x{count}")

        # 发放技能
        for skill_id, level in (origin.bonus_skills or {}).items():
            player.skills = player.skills or {}
            player.skills[skill_id] = player.skills.get(skill_id, 0) + level
            reward_details["skills"].append(f"{skill_id} +{level}")

        return reward_details

    async def set_spawn_origin(self, user_id: str, spawn_origin: str, spawn_location: str) -> dict:
        """设置玩家出身和出生地点（一次性）。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "角色不存在"}
        
        if player.spawn_origin:
            return {"success": False, "message": "您已选择过出身，无法更改"}
        
        if spawn_origin:
            valid, msg = validate_spawn_selection(spawn_origin, spawn_location)
            if not valid:
                return {"success": False, "message": msg}
            
            origin = get_spawn_origin(spawn_origin)
            location = get_spawn_location(spawn_location)
            
            player.spawn_origin = spawn_origin
            player.spawn_location = spawn_location
            
            logger.info(f"[set_spawn_origin] 玩家 {player.name} 选择出身 {spawn_origin}，开始发放奖励...")
            
            reward_details = {
                "attributes": [],
                "combat_stats": [],
                "items": [],
                "equipment": [],
                "skills": [],
                "spirit_stones": 0,
            }
            
            if origin:
                reward_details = self._apply_origin_bonuses(player, origin)
                logger.info(f"[set_spawn_origin] 属性点: 力量+{origin.bonus_strength}, 敏捷+{origin.bonus_agility}, 智力+{origin.bonus_intelligence}")
                logger.info(f"[set_spawn_origin] 战斗属性: HP+{origin.bonus_hp}, 攻击+{origin.bonus_attack}, 防御+{origin.bonus_defense}, 体力+{origin.bonus_lingqi}, 第纳尔+{origin.bonus_spirit_stones}")
            
            if location:
                player.map_state.current_location = location.location_id
                player.map_state.x = location.x
                player.map_state.y = location.y
                logger.info(f"[set_spawn_origin] 设置出生地点: {location.name}")
        
        await self._save_player(player)
        
        # 构建详细消息
        lines = [f"🎉 出身选择成功！"]
        if reward_details["attributes"]:
            lines.append(f"📊 属性：{', '.join(reward_details['attributes'])}")
        if reward_details["combat_stats"]:
            lines.append(f"⚔️ 战斗：{', '.join(reward_details['combat_stats'])}")
        if reward_details["equipment"]:
            lines.append(f"🛡️ 装备：{', '.join(reward_details['equipment'])}")
        if reward_details["items"]:
            lines.append(f"🎒 物品：{', '.join(reward_details['items'])}")
        if reward_details["skills"]:
            lines.append(f"✨ 技能：{', '.join(reward_details['skills'])}")
        
        return {
            "success": True,
            "message": "\n".join(lines),
            "rewards": reward_details,
        }

    # ==================== 认证相关 ====================

    def get_player_by_name(self, name: str) -> Optional[Player]:
        """通过骑士名查找玩家。"""
        uid = self._name_index.get(name)
        if uid:
            return self._players.get(uid)
        return None

    def is_name_taken(self, name: str) -> bool:
        """检查骑士名是否已被使用。"""
        return name in self._name_index

    def set_name_reviewer(self, reviewer: Callable[[str], Awaitable[dict | tuple | bool]] | None):
        """设置骑士名审核器（由插件层注入 AI 审核实现）。"""
        self._name_reviewer = reviewer

    def set_chat_reviewer(self, reviewer: Callable[[str], Awaitable[dict]] | None):
        """设置世界频道消息审核器（由插件层注入 AI 审核实现）。"""
        self._chat_reviewer = reviewer

    def set_sect_name_reviewer(self, reviewer: Callable[[str], Awaitable[dict]] | None):
        """设置家族名称审核器（由插件层注入 AI 审核实现）。"""
        self._sect_name_reviewer = reviewer

    def _local_name_risk_check(self, name: str) -> tuple[bool, str]:
        """本地敏感词兜底检测。"""
        # 基础字符校验：只允许中文、英文、数字、部分符号，长度1-12
        if not re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9_·\-]{1,12}$', name or ""):
            return False, "角色名仅允许中文、英文、数字，长度1-12"
        normalized = re.sub(r"[\s·•・_\-]", "", str(name or "")).lower()
        for kw in _BAD_NAME_KEYWORDS:
            if kw and kw in normalized:
                return False, "角色名包含违规词汇"
        return True, ""

    async def _review_registration_name(self, name: str) -> tuple[bool, str]:
        """注册骑士名审核：本地拦截 + AI 审核。"""
        ok, reason = self._local_name_risk_check(name)
        if not ok:
            return False, reason

        if not self._name_reviewer:
            # AI 审核器未配置时，使用本地兜底规则即可
            return True, ""

        try:
            import asyncio
            review = await asyncio.wait_for(
                self._name_reviewer(name),
                timeout=5.0  # AI审核超时5秒
            )
        except asyncio.TimeoutError:
            # 审核超时，放行避免阻塞注册
            return True, ""
        except Exception:
            # 审核服务异常时放行，避免误伤正常注册
            return True, ""

        allow = False
        ai_reason = ""
        if isinstance(review, bool):
            allow = review
        elif isinstance(review, dict):
            allow = bool(review.get("allow", review.get("ok", False)))
            ai_reason = str(review.get("reason", "")).strip()
        elif isinstance(review, (tuple, list)) and review:
            allow = bool(review[0])
            if len(review) > 1:
                ai_reason = str(review[1]).strip()
        else:
            ai_reason = str(review).strip()

        if allow:
            return True, ""
        return False, ai_reason or "角色名包含不当内容"

    async def register_with_password(self, name: str, password: str, spawn_origin: str = "", spawn_location: str = "") -> dict:
        """Web 端注册：创建角色并设置密码。可选出身和出生地点。"""
        name = name.strip()
        if not name:
            return {"success": False, "message": "角色名不能为空"}
        if not re.fullmatch(r"[\u4e00-\u9fa5a-zA-Z0-9]{2,12}", name):
            return {"success": False, "message": "角色名仅支持2-12位中英文、数字"}

        ok, reason = await self._review_registration_name(name)
        if not ok:
            return {"success": False, "message": reason}

        if self.is_name_taken(name):
            return {"success": False, "message": f"角色名「{name}」已被使用"}
        if not re.fullmatch(r"\d{4,32}", password or ""):
            return {"success": False, "message": "密码仅支持数字，长度4-32位"}

        if spawn_origin or spawn_location:
            valid, msg = validate_spawn_selection(spawn_origin, spawn_location)
            if not valid:
                return {"success": False, "message": msg}

        import secrets as _s
        user_id = "u_" + _s.token_hex(8)

        player = await self.get_or_create_player(user_id, name, spawn_origin, spawn_location)
        player.password_hash = AuthManager.hash_password(password)
        await self._save_player(player)
        
        origin_name = spawn_origin or "平民"
        location_name = spawn_location or "中央平原"
        return {"success": True, "user_id": user_id, "message": f"注册成功，欢迎{origin_name}出身的{name}"}

    async def set_password(self, user_id: str, password: str) -> dict:
        """为已有角色设置密码。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "角色不存在"}
        if not re.fullmatch(r"\d{4,32}", password or ""):
            return {"success": False, "message": "密码仅支持数字，长度4-32位"}
        player.password_hash = AuthManager.hash_password(password)
        await self._save_player(player)
        return {"success": True, "message": "密码设置成功"}

    def verify_login(self, name: str, password: str) -> Optional[Player]:
        """验证骑士名+密码登录，返回 Player 或 None。"""
        player = self.get_player_by_name(name)
        if not player:
            return None
        if not player.password_hash:
            return None
        if not AuthManager.verify_password(password, player.password_hash):
            return None
        return player

    # ==================== 管理员操作 ====================

    async def delete_player(self, user_id: str) -> dict:
        """删除玩家。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "玩家不存在"}
        name = player.name

        # 清理家族成员记录
        try:
            sect_info = await self._data_manager.load_player_sect(user_id)
            if sect_info:
                sect_id = sect_info["sect_id"]
                await self._data_manager.delete_sect_member(user_id)
                # 若是族长且无其他成员，解散家族
                if sect_info.get("role") == "leader":
                    members = await self._data_manager.load_sect_members(sect_id)
                    remaining = [m for m in members if m.get("user_id") != user_id]
                    if not remaining:
                        await self._data_manager.delete_sect(sect_id)
        except Exception:
            logger.exception("战争大陆：删除玩家时清理家族数据异常 user_id=%s", user_id)

        if self.auth:
            await self.auth.revoke_user(user_id)
        if self._ws_manager and hasattr(self._ws_manager, "disconnect"):
            self._ws_manager.disconnect(user_id)
        self._name_index.pop(name, None)
        del self._players[user_id]
        await self._data_manager.delete_player(user_id)
        return {"success": True, "message": f"已删除玩家「{name}」"}

    async def batch_delete_players(self, user_ids: list[str]) -> dict:
        """批量删除玩家。"""
        deleted = 0
        deleted_ids: list[str] = []
        for uid in user_ids:
            player = self._players.get(uid)
            if player:
                self._name_index.pop(player.name, None)
                del self._players[uid]
                deleted_ids.append(uid)
                if self._ws_manager and hasattr(self._ws_manager, "disconnect"):
                    self._ws_manager.disconnect(uid)
                deleted += 1
        if deleted_ids and self.auth:
            await self.auth.revoke_users(deleted_ids)
        for uid in deleted_ids:
            await self._data_manager.delete_player(uid)
        return {"success": True, "message": f"已删除 {deleted} 名玩家", "deleted": deleted}

    async def reset_player(self, user_id: str) -> dict:
        """重置玩家角色数据到初始状态（重新选择出身）。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "玩家不存在"}

        player.spawn_origin = ""
        player.spawn_location = ""
        player.realm = RealmLevel.MORTAL
        player.sub_realm = 0
        player.exp = 0
        player.hp = 100
        player.max_hp = 100
        player.attack = 10
        player.defense = 5
        player.spirit_stones = 0
        player.lingqi = 50
        player.strength = 5
        player.agility = 5
        player.intelligence = 5
        player.skill_points = 0
        player.attribute_points = 0
        player.skills = {}
        player.permanent_max_hp_bonus = 0
        player.permanent_attack_bonus = 0
        player.permanent_defense_bonus = 0
        player.permanent_lingqi_bonus = 0
        player.heart_method = "无"
        player.weapon = "无"
        player.gongfa_1 = "无"
        player.gongfa_2 = "无"
        player.gongfa_3 = "无"
        player.head = "无"
        player.body = "无"
        player.hands = "无"
        player.legs = "无"
        player.shoulders = "无"
        player.accessory1 = "无"
        player.accessory2 = "无"
        player.mount = "无"
        player.mount_armor = "无"
        player.mount_weapon = "无"
        player.horse_armament = "无"
        player.dao_yun = 0
        player.breakthrough_bonus = 0.0
        player.breakthrough_pill_count = 0
        player.heart_method_mastery = 0
        player.heart_method_exp = 0
        player.heart_method_value = 0
        player.gongfa_1_mastery = 0
        player.gongfa_1_exp = 0
        player.gongfa_2_mastery = 0
        player.gongfa_2_exp = 0
        player.gongfa_3_mastery = 0
        player.gongfa_3_exp = 0
        player.inventory = {}
        player.inventory["healing_pill"] = 3
        player.inventory["exp_pill"] = 1
        player.stored_heart_methods = {}
        player.last_cultivate_time = 0.0
        player.last_checkin_date = None
        player.afk_cultivate_start = 0.0
        player.afk_cultivate_end = 0.0
        player.last_adventure_time = 0.0
        player.death_count = 0
        player.active_buffs = []
        player.map_state = PlayerMapState()
        player.active_quests = []
        player.level = 1
        player.unallocated_points = 0
        player.bandit_stats = {}
        player.is_injured = False
        player.injured_until = 0.0

        await self._save_player(player)
        return {"success": True, "message": "角色已重置，请重新选择出身"}

    async def update_player_data(self, user_id: str, updates: dict) -> dict:
        """管理员修改玩家数据。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "玩家不存在"}
        allowed = {"realm", "sub_realm", "exp", "hp", "max_hp", "attack", "defense", "spirit_stones", "lingqi", "dao_yun", "name"}
        realm_changed = False
        old_realm = int(player.realm)
        for key, value in updates.items():
            if key not in allowed:
                continue
            if key == "name":
                new_name = str(value).strip()
                if not new_name:
                    continue
                if new_name != player.name and self.is_name_taken(new_name):
                    return {"success": False, "message": f"角色名「{new_name}」已被使用"}
                self._name_index.pop(player.name, None)
                player.name = new_name
                self._name_index[new_name] = user_id
            else:
                try:
                    setattr(player, key, int(value))
                    if key in {"realm", "sub_realm"}:
                        realm_changed = True
                except (ValueError, TypeError):
                    pass
        removed = self._auto_unequip_invalid_equipment(player) if realm_changed else []
        heart_fix = {"removed_name": "", "manual_name": "", "converted": 0}
        if realm_changed:
            major_drop = int(player.realm) < old_realm
            heart_fix = self._auto_unequip_invalid_heart_method(
                player, convert_ratio=0.6 if major_drop else 0.0, force=major_drop
            )
        await self._save_player(player)
        msg_parts = [f"已更新玩家「{player.name}」的数据"]
        if removed:
            msg_parts.append(f"自动卸下装备：{'、'.join(removed)}")
        if heart_fix.get("removed_name"):
            msg_parts.append(f"自动卸下被动技能：{heart_fix['removed_name']}（已返还{heart_fix['manual_name']}）")
            if heart_fix.get("converted", 0) > 0:
                msg_parts.append(f"结转技能点+{heart_fix['converted']}")
        return {"success": True, "message": "；".join(msg_parts)}

    def get_player_detail(self, user_id: str) -> Optional[dict]:
        """获取玩家详细数据（含背包内容，供管理员查看）。"""
        player = self._players.get(user_id)
        if not player:
            return None
        self._clamp_player_hp(player)
        from .inventory import get_inventory_display_sync
        d = player.to_dict()
        d["inventory_detail"] = get_inventory_display_sync(player)
        d["user_id"] = user_id
        return d

    def get_online_user_ids(self) -> set[str]:
        """获取当前 WebSocket 在线的 user_id 集合。"""
        if self._ws_manager and hasattr(self._ws_manager, "_connections"):
            return set(self._ws_manager._connections.keys())
        return set()

    def get_rankings(self, limit: int = 50) -> list[dict]:
        """获取排行榜（按爵位+经验排序）。"""
        players = list(self._players.values())
        players.sort(key=lambda p: (p.realm, p.sub_realm, p.exp), reverse=True)
        result = []
        for i, p in enumerate(players[:limit]):
            result.append({
                "rank": i + 1,
                "name": p.name,
                "realm": p.realm,
                "realm_name": get_realm_name(p.realm, p.sub_realm),
                "exp": p.exp,
                "attack": p.attack,
                "defense": p.defense,
                "spirit_stones": p.spirit_stones,
            })
        return result

    def get_death_rankings(self, limit: int = 50) -> list[dict]:
        """获取死亡排行榜（按死亡次数降序）。"""
        players = [p for p in self._players.values() if p.death_count > 0]
        players.sort(
            key=lambda p: (p.death_count, p.realm, p.sub_realm, p.exp),
            reverse=True,
        )
        result = []
        for i, p in enumerate(players[:limit]):
            result.append({
                "rank": i + 1,
                "name": p.name,
                "death_count": p.death_count,
                "realm": p.realm,
                "realm_name": get_realm_name(p.realm, p.sub_realm),
            })
        return result

    def get_online_rankings(self, limit: int = 50) -> list[dict]:
        """获取在线排行榜（仅在线玩家，按爵位+经验排序）。"""
        online_ids = self.get_online_user_ids()
        players = [p for uid, p in self._players.items() if uid in online_ids]
        players.sort(key=lambda p: (p.realm, p.sub_realm, p.exp), reverse=True)
        result = []
        for i, p in enumerate(players[:limit]):
            result.append({
                "rank": i + 1,
                "name": p.name,
                "realm": p.realm,
                "realm_name": get_realm_name(p.realm, p.sub_realm),
                "exp": p.exp,
            })
        return result

    # ── 坊市 (Market) ───────────────────────────────────────

    async def market_list(
        self, user_id: str, item_id: str, quantity: int, unit_price: int,
    ) -> dict:
        """上架物品到集市（Web 端使用，传 item_id）。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        async with self._get_player_lock(user_id):
            snapshot = self._snapshot_player(player)
            result = await market_mod.list_item(
                snapshot, item_id, quantity, unit_price, self._data_manager,
            )
            if result["success"]:
                self._apply_player_snapshot(player, snapshot)
                try:
                    await self._notify_player_update(player)
                except Exception:
                    logger.exception("骑砍世界：玩家状态推送失败 user_id=%s", player.user_id)
                await self._notify_market_changed("list")
        return result

    async def market_list_by_name(
        self,
        user_id: str,
        item_name: str,
        quantity: int,
        unit_price: int,
        query_type: str | None = None,
    ) -> dict:
        """上架物品到集市（聊天端使用，传物品名）。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        matches = find_item_ids_by_name(item_name, query_type=query_type)
        if not matches:
            return {"success": False, "message": f"找不到物品：{item_name}"}
        if len(matches) > 1:
            return {
                "success": False,
                "message": f"存在重名物品「{item_name}」，请指定类型",
            }
        return await self.market_list(user_id, matches[0], quantity, unit_price)

    async def market_buy(self, user_id: str, listing_id: str) -> dict:
        """从集市购买物品。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        await self._process_market_cleanup()

        # 预查 listing 以确定卖家 ID，用于加锁
        listing = await self._data_manager.get_listing_by_id(listing_id)
        if not listing:
            return {"success": False, "message": "该商品不存在"}

        seller_id = listing["seller_id"]
        if seller_id == user_id:
            return {"success": False, "message": "不能购买自己的商品"}

        seller = self._players.get(seller_id)
        if not seller:
            return {"success": False, "message": "卖家信息异常，请稍后重试"}

        # 按 user_id 排序获取双方锁，避免死锁
        lock_ids = sorted({user_id, seller_id})
        lock_first = self._get_player_lock(lock_ids[0])
        lock_second = self._get_player_lock(lock_ids[1]) if len(lock_ids) > 1 else None

        async with lock_first:
            ctx = lock_second if lock_second else contextlib.nullcontext()
            async with ctx:
                buyer_snapshot = self._snapshot_player(player)
                seller_snapshot = self._snapshot_player(seller)
                result = await market_mod.buy_item(
                    buyer_snapshot, seller_snapshot, listing_id, self._data_manager,
                )
                if result["success"]:
                    self._apply_player_snapshot(player, buyer_snapshot)
                    self._apply_player_snapshot(seller, seller_snapshot)
                    try:
                        await self._notify_player_update(player)
                    except Exception:
                        logger.exception("骑砍世界：玩家状态推送失败 user_id=%s", player.user_id)
                    try:
                        await self._notify_player_update(seller)
                    except Exception:
                        logger.exception("骑砍世界：玩家状态推送失败 user_id=%s", seller_id)
                    await self._notify_market_changed("buy")
        return result

    async def market_buy_by_prefix(self, user_id: str, prefix: str) -> dict:
        """通过短编号购买（聊天端用）。"""
        listing = await self._data_manager.get_listing_by_id_prefix(prefix)
        if not listing:
            return {"success": False, "message": f"找不到编号为 {prefix} 的商品"}
        return await self.market_buy(user_id, listing["listing_id"])

    async def market_cancel(self, user_id: str, listing_id: str) -> dict:
        """下架商品。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        async with self._get_player_lock(user_id):
            snapshot = self._snapshot_player(player)
            result = await market_mod.cancel_listing(
                snapshot, listing_id, self._data_manager,
            )
            if result["success"]:
                self._apply_player_snapshot(player, snapshot)
                try:
                    await self._notify_player_update(player)
                except Exception:
                    logger.exception("骑砍世界：玩家状态推送失败 user_id=%s", player.user_id)
                await self._notify_market_changed("cancel")
        return result

    async def market_cancel_by_prefix(self, user_id: str, prefix: str) -> dict:
        """通过短编号下架（聊天端用）。"""
        listing = await self._data_manager.get_listing_by_id_prefix(prefix)
        if not listing:
            return {"success": False, "message": f"找不到编号为 {prefix} 的商品"}
        return await self.market_cancel(user_id, listing["listing_id"])

    @staticmethod
    def _build_listing_detail(item_id: str) -> dict | None:
        """从注册表构建坊市商品详情 dict，用于前端弹窗展示。"""
        eq = EQUIPMENT_REGISTRY.get(item_id)
        if eq:
            return {
                "kind": "equipment",
                "name": eq.name,
                "tier": eq.tier,
                "tier_name": EQUIPMENT_TIER_NAMES.get(eq.tier, str(eq.tier)),
                "slot": eq.slot,
                "attack": eq.attack,
                "defense": eq.defense,
                "element": eq.element,
                "element_damage": eq.element_damage,
                "description": eq.description,
            }
        item_def = ITEM_REGISTRY.get(item_id)
        if item_def:
            # 被动技能秘籍
            hm_id = parse_heart_method_manual_id(item_id)
            if hm_id:
                hm = HEART_METHOD_REGISTRY.get(hm_id)
                if hm:
                    bonus = get_heart_method_bonus(hm.method_id, 0)
                    return {
                        "kind": "heart_method",
                        "method_id": hm.method_id,
                        "name": item_def.name,
                        "quality": hm.quality,
                        "quality_name": HEART_METHOD_QUALITY_NAMES.get(hm.quality, "普通"),
                        "realm_name": get_realm_name(hm.realm, 0),
                        "mastery": 0,
                        "mastery_name": bonus.get("mastery_name", MASTERY_LEVELS[0]),
                        "mastery_exp": 0,
                        "mastery_exp_max": hm.mastery_exp,
                        "bonus": bonus,
                        "description": hm.description or item_def.description,
                    }
            # 战技卷轴
            gf_id = parse_gongfa_scroll_id(item_id)
            if gf_id:
                gf = GONGFA_REGISTRY.get(gf_id)
                if gf:
                    return {
                        "kind": "gongfa",
                        "gongfa_id": gf.gongfa_id,
                        "name": item_def.name,
                        "tier": gf.tier,
                        "tier_name": GONGFA_TIER_NAMES.get(gf.tier, "未知"),
                        "attack_bonus": gf.attack_bonus,
                        "defense_bonus": gf.defense_bonus,
                        "hp_regen": gf.hp_regen,
                        "lingqi_regen": gf.lingqi_regen,
                        "description": item_def.description,
                    }
            # 普通消耗品
            return {
                "kind": "consumable",
                "name": item_def.name,
                "description": item_def.description,
            }
        return None

    async def market_get_listings(
        self,
        page: int = 1,
        page_size: int = 20,
        cleanup_expired: bool = True,
    ) -> dict:
        """浏览集市商品（含过期清理 + 卖家名称补充）。"""
        if cleanup_expired:
            await self._process_market_cleanup()

        data = await market_mod.get_listings(self._data_manager, page, page_size)

        # 补充物品名称、卖家名称和物品详情
        for listing in data["listings"]:
            listing["item_name"] = market_mod.get_item_name(listing["item_id"])
            seller = self._players.get(listing["seller_id"])
            listing["seller_name"] = seller.name if seller else "未知"
            listing["item_detail"] = self._build_listing_detail(listing["item_id"])
        return data

    async def market_get_my_listings(self, user_id: str, cleanup_expired: bool = True) -> list[dict]:
        """获取我的上架记录。"""
        player = self._players.get(user_id)
        if not player:
            return []

        if cleanup_expired:
            await self._process_market_cleanup()

        listings = await market_mod.get_my_listings(player, self._data_manager)
        for listing in listings:
            listing["item_name"] = market_mod.get_item_name(listing["item_id"])
        return listings

    async def market_clear_my_history(self, user_id: str, include_expired: bool = False) -> dict:
        """清理我的历史上架记录（已售/已下架，可选含已过期）。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}
        result = await market_mod.clear_my_history(
            player,
            self._data_manager,
            include_expired=bool(include_expired),
        )
        if result.get("success"):
            await self._notify_market_changed("clear_history", int(result.get("deleted", 0)))
        return result

    async def market_fee_preview(
        self, item_id: str, quantity: int, unit_price: int,
    ) -> dict:
        """手续费预览。"""
        stats = await self._data_manager.get_market_stats(item_id)
        fee, rate = market_mod.calculate_listing_fee(unit_price, quantity, stats)
        total_price = unit_price * quantity
        return {
            "fee": fee,
            "rate": rate,
            "total_price": total_price,
            "stats": stats,
        }

    # ── 军需商店 ──────────────────────────────────────

    async def shop_get_items(self, user_id: str) -> dict:
        """获取今日军需商店商品列表。"""
        from datetime import date as _date
        today = _date.today()
        items = shop_mod.generate_daily_items(today)
        today_str = today.isoformat()
        for it in items:
            limit = it.get("daily_limit", 0)
            if limit > 0:
                sold = await self._data_manager.get_shop_sold_today(it["item_id"], today_str)
                it["sold_today"] = sold
        return {"items": items, "date": today_str}

    async def shop_buy(self, user_id: str, item_id: str, quantity: int = 1) -> dict:
        """从军需商店购买物品。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}
        async with self._get_player_lock(user_id):
            snapshot = self._snapshot_player(player)
            result = await shop_mod.buy_from_shop(snapshot, item_id, quantity)
            if not result["success"]:
                return result

            purchase_meta = result.pop("_purchase_meta", None)
            if not purchase_meta:
                return {"success": False, "message": "购买失败，订单信息缺失"}

            try:
                committed = await self._data_manager.commit_shop_purchase_atomic(
                    snapshot,
                    purchase_meta["item_id"],
                    purchase_meta["quantity"],
                    purchase_meta["unit_price"],
                    purchase_meta["purchased_at"],
                    purchase_meta.get("daily_limit", 0),
                )
            except Exception:
                return {"success": False, "message": "购买失败，数据保存异常，请稍后再试"}

            if not committed["success"]:
                daily_limit = int(purchase_meta.get("daily_limit", 0) or 0)
                remaining = int(committed.get("remaining", 0) or 0)
                return {
                    "success": False,
                    "message": f"【{purchase_meta['item_name']}】今日全服限购{daily_limit}个，剩余{remaining}个",
                }

            self._apply_player_snapshot(player, snapshot)
            await self._notify_player_update(player)
            return result

    # ── 铁匠铺系统 ─────────────────────────────────────────

    async def get_item_prefix_info(self, user_id: str, item_id: str) -> dict:
        """获取装备前缀信息"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}
        return await shop_mod.get_item_prefix_info(player, item_id)

    async def blacksmith_repair_prefix(self, user_id: str, item_id: str) -> dict:
        """铁匠铺修复装备前缀"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}
        
        snapshot = self._snapshot_player(player)
        result = await shop_mod.blacksmith_repair_prefix(snapshot, item_id)
        
        if result.get("success"):
            self._apply_player_snapshot(player, snapshot)
            await self._notify_player_update(player)
        
        return result

    async def blacksmith_enhance_prefix(self, user_id: str, item_id: str, target_quality: str = "good") -> dict:
        """铁匠铺强化装备前缀"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}
        
        snapshot = self._snapshot_player(player)
        result = await shop_mod.blacksmith_enhance_prefix(snapshot, item_id, target_quality)
        
        if result.get("success"):
            self._apply_player_snapshot(player, snapshot)
            await self._notify_player_update(player)
        
        return result

    # ── 家族系统 ─────────────────────────────────────────

    async def sect_create(self, user_id: str, name: str, description: str = "") -> dict:
        """创建家族。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}
        reviewer = self._sect_name_reviewer or self._name_reviewer
        result = await sect_mod.create_sect(
            player, name, description, self._data_manager,
            name_reviewer=reviewer,
        )
        if result["success"]:
            await self._save_player(player)
        return result

    async def sect_disband(self, user_id: str) -> dict:
        """解散家族。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}
        return await sect_mod.disband_sect(player, self._data_manager)

    async def sect_list(self, page: int = 1, page_size: int = 10) -> dict:
        """获取家族列表。"""
        return await sect_mod.get_sect_list(self._data_manager, page, page_size)

    async def sect_detail(self, sect_id: str) -> dict:
        """获取家族详情。"""
        return await sect_mod.get_sect_detail(sect_id, self._data_manager)

    async def sect_my(self, user_id: str) -> dict:
        """获取我的家族信息。"""
        return await sect_mod.get_my_sect(user_id, self._data_manager)

    async def sect_join(self, user_id: str, sect_id: str) -> dict:
        """加入家族。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}
        return await sect_mod.join_sect(player, sect_id, self._data_manager)

    async def sect_leave(self, user_id: str) -> dict:
        """退出家族。"""
        return await sect_mod.leave_sect(user_id, self._data_manager)

    async def sect_kick(self, operator_id: str, target_id: str) -> dict:
        """踢出成员。"""
        return await sect_mod.kick_member(operator_id, target_id, self._data_manager)

    async def sect_set_role(self, operator_id: str, target_id: str, role: str) -> dict:
        """设置成员身份。"""
        return await sect_mod.set_member_role(
            operator_id, target_id, role, self._data_manager,
        )

    async def sect_update_info(self, operator_id: str, data: dict) -> dict:
        """修改家族信息。"""
        return await sect_mod.update_sect_info(operator_id, data, self._data_manager)

    async def sect_transfer(self, leader_id: str, target_id: str) -> dict:
        """转让族长。"""
        return await sect_mod.transfer_leader(leader_id, target_id, self._data_manager)

    # ── 家族仓库 ──────────────────────────────────────────

    async def sect_warehouse_deposit(self, user_id: str, item_id: str, count: int = 1) -> dict:
        """上交物品到家族仓库。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        def _normalize(p: Player) -> None:
            self._auto_unequip_invalid_heart_method(p, convert_ratio=0.6, force=False)
            p.heart_method_value = max(0, int(getattr(p, "heart_method_value", 0)))
            self._clamp_player_hp(p)

        result = await sect_mod.warehouse_deposit(
            player, item_id, count, self._data_manager,
            pre_commit=_normalize,
        )
        if result["success"]:
            try:
                await self._notify_player_update(player)
            except Exception:
                logger.exception("骑砍世界：玩家状态推送失败 user_id=%s", user_id)
        return result

    async def sect_warehouse_exchange(self, user_id: str, item_id: str, count: int = 1) -> dict:
        """从家族仓库兑换物品。"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        def _normalize(p: Player) -> None:
            self._auto_unequip_invalid_heart_method(p, convert_ratio=0.6, force=False)
            p.heart_method_value = max(0, int(getattr(p, "heart_method_value", 0)))
            self._clamp_player_hp(p)

        result = await sect_mod.warehouse_exchange(
            player, item_id, count, self._data_manager,
            pre_commit=_normalize,
        )
        if result["success"]:
            try:
                await self._notify_player_update(player)
            except Exception:
                logger.exception("骑砍世界：玩家状态推送失败 user_id=%s", user_id)
        return result

    async def sect_warehouse_list(self, user_id: str) -> dict:
        """查看家族仓库。"""
        return await sect_mod.warehouse_list(user_id, self._data_manager)

    async def sect_set_submit_rule(self, user_id: str, quality_key: str, points: int) -> dict:
        """设置上交声望规则。"""
        return await sect_mod.set_submit_rule(user_id, quality_key, points, self._data_manager)

    async def sect_set_exchange_rule(
        self, user_id: str, target_key: str, points: int, *, is_item: bool = False,
    ) -> dict:
        """设置兑换声望规则。"""
        return await sect_mod.set_exchange_rule(
            user_id, target_key, points, self._data_manager, is_item=is_item,
        )

    async def sect_get_contribution_rules(self, user_id: str) -> dict:
        """获取家族声望规则。"""
        return await sect_mod.get_contribution_rules(user_id, self._data_manager)

    # ── 家族任务 ────────────────────────────────────────────

    async def sect_create_task(
        self,
        user_id: str,
        title: str,
        description: str,
        task_type: str,
        target_count: int,
        reward_points: int,
        reward_item_id: str = "",
        reward_item_count: int = 0,
        expires_hours: int = 24,
    ) -> dict:
        """创建家族任务（仅头人）。"""
        membership = await self._data_manager.load_player_sect(user_id)
        if not membership:
            return {"success": False, "message": "你尚未加入任何家族"}

        if membership["role"] not in ("leader", "elder"):
            return {"success": False, "message": "只有头人和长老可以发布任务"}

        sect = await self._data_manager.load_sect(membership["sect_id"])
        if not sect:
            return {"success": False, "message": "家族不存在"}

        task_id = await self._data_manager.create_sect_task(
            sect_id=membership["sect_id"],
            creator_id=user_id,
            title=title,
            description=description,
            task_type=task_type,
            target_count=target_count,
            reward_points=reward_points,
            reward_item_id=reward_item_id,
            reward_item_count=reward_item_count,
            expires_hours=expires_hours,
        )

        if not task_id:
            return {"success": False, "message": "创建任务失败"}

        return {"success": True, "message": f"任务「{title}」已发布", "task_id": task_id}

    async def sect_get_tasks(self, user_id: str, status: str = "") -> dict:
        """获取家族任务列表。"""
        membership = await self._data_manager.load_player_sect(user_id)
        if not membership:
            return {"success": False, "message": "你尚未加入任何家族", "tasks": []}

        tasks = await self._data_manager.get_sect_tasks(membership["sect_id"], status)
        return {"success": True, "tasks": tasks}

    async def sect_accept_task(self, user_id: str, task_id: int) -> dict:
        """接受家族任务。"""
        membership = await self._data_manager.load_player_sect(user_id)
        if not membership:
            return {"success": False, "message": "你尚未加入任何家族"}

        task = await self._data_manager.get_task_by_id(task_id)
        if not task:
            return {"success": False, "message": "任务不存在"}

        if task["sect_id"] != membership["sect_id"]:
            return {"success": False, "message": "该任务不属于你的家族"}

        if task["status"] != "active":
            return {"success": False, "message": "任务已结束"}

        if task.get("is_expired"):
            return {"success": False, "message": "任务已过期"}

        existing = await self._data_manager.get_task_member(task_id, user_id)
        if existing:
            return {"success": False, "message": "你已接受过此任务"}

        ok = await self._data_manager.accept_task(task_id, user_id)
        if not ok:
            return {"success": False, "message": "接受任务失败"}

        return {"success": True, "message": f"已接受任务「{task['title']}」"}

    async def sect_update_task_progress(self, user_id: str, task_id: int, progress: int) -> dict:
        """更新任务进度。"""
        membership = await self._data_manager.load_player_sect(user_id)
        if not membership:
            return {"success": False, "message": "你尚未加入任何家族"}

        task = await self._data_manager.get_task_by_id(task_id)
        if not task:
            return {"success": False, "message": "任务不存在"}

        member_task = await self._data_manager.get_task_member(task_id, user_id)
        if not member_task:
            return {"success": False, "message": "你未接受此任务"}

        if member_task["status"] == "completed":
            return {"success": False, "message": "任务已完成"}

        new_progress = min(member_task["progress"] + progress, task["target_count"])
        await self._data_manager.update_task_member_progress(task_id, user_id, new_progress)

        if new_progress >= task["target_count"]:
            await self._data_manager.complete_task_member(task_id, user_id)
            await self._data_manager.update_task_progress(task_id, new_progress)

            reward_msg = f" 奖励：{task['reward_points']} 贡献点"
            if task["reward_item_id"] and task["reward_item_count"] > 0:
                from .inventory import add_item
                player = await self.get_player(user_id)
                if player:
                    await add_item(player, task["reward_item_id"], task["reward_item_count"], "家族任务奖励")
                    await self._notify_player_update(player)
                    item_name = task.get("reward_item_name", task["reward_item_id"])
                    reward_msg = reward_msg + f"、{task['reward_item_count']}个{item_name}"

            return {
                "success": True,
                "message": f"任务已完成！{reward_msg}",
                "completed": True,
                "reward_points": task["reward_points"],
            }

        return {
            "success": True,
            "message": f"进度：{new_progress}/{task['target_count']}",
            "completed": False,
            "progress": new_progress,
        }

    async def sect_cancel_task(self, user_id: str, task_id: int) -> dict:
        """取消/删除任务（仅发布者或头人）。"""
        membership = await self._data_manager.load_player_sect(user_id)
        if not membership:
            return {"success": False, "message": "你尚未加入任何家族"}

        task = await self._data_manager.get_task_by_id(task_id)
        if not task:
            return {"success": False, "message": "任务不存在"}

        if task["sect_id"] != membership["sect_id"]:
            return {"success": False, "message": "该任务不属于你的家族"}

        if membership["role"] != "leader" and task["creator_id"] != user_id:
            return {"success": False, "message": "只有任务发布者和头人可以取消任务"}

        ok = await self._data_manager.delete_sect_task(task_id)
        if not ok:
            return {"success": False, "message": "删除任务失败"}

        return {"success": True, "message": f"任务「{task['title']}」已删除"}

    # ── 医疗系统 ──────────────────────────────────────────────

    async def gather_herbs(self, user_id: str) -> dict:
        """采集草药"""
        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}

        result = gathering.gather_herbs(player)
        if result["success"]:
            for herb in result.get("herbs", []):
                await add_item(player, herb["herb_id"], 1, "采集")
            await self._save_player(player)
            await self._notify_player_update(player)
        return result

    async def craft_item(self, user_id: str, recipe_id: str) -> dict:
        """制作物品"""
        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}
        
        result = crafting.craft_item(player, recipe_id)
        if result["success"]:
            await self._save_player(player)
        return result

    async def use_medical_item(self, user_id: str, item_id: str) -> dict:
        """使用医疗物品"""
        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}
        
        result = crafting.use_medical_item(player, item_id)
        if result["success"]:
            await self._save_player(player)
        return result

    async def use_heal_skill(self, user_id: str, skill_id: str) -> dict:
        """使用医疗技能"""
        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色，请先创建"}
        
        result = heal_skills.use_heal_skill(player, skill_id)
        if result.get("success"):
            await self._save_player(player)
        return result

    def get_gather_info(self, user_id: str) -> dict:
        """获取采集信息"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}
        return gathering.get_gather_info(player)

    def get_medical_info(self, user_id: str) -> dict:
        """获取医疗系统信息"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}
        
        first_aid_level = player.skills.get(30, 0)
        surgery_level = player.skills.get(32, 0)
        herbalism_level = player.skills.get(31, 0)
        
        return {
            "success": True,
            "first_aid_level": first_aid_level,
            "surgery_level": surgery_level,
            "herbalism_level": herbalism_level,
            "gather_info": gathering.get_gather_info(player),
            "recipes": crafting.get_available_recipes(herbalism_level),
            "inventory": player.inventory if hasattr(player, 'inventory') else {},
        }

    # ── 跑商系统 ──────────────────────────────────────────────

    async def trade_buy(self, user_id: str, good_id: str, count: int = 1, location_id: str = None) -> dict:
        """购买商品"""
        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}
        
        if not hasattr(player, 'map_state') or not player.map_state:
            return {"success": False, "message": "无法获取位置信息"}
        
        loc = location_id or player.map_state.current_location
        if not loc:
            return {"success": False, "message": "你不在任何城镇或村庄"}
        
        result = trading.buy_good(player, loc, good_id, count)
        if result.get("success"):
            await self._save_player(player)
        return result

    async def trade_sell(self, user_id: str, good_id: str, count: int = 1, location_id: str = None) -> dict:
        """出售商品"""
        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}
        
        if not hasattr(player, 'map_state') or not player.map_state:
            return {"success": False, "message": "无法获取位置信息"}
        
        loc = location_id or player.map_state.current_location
        if not loc:
            return {"success": False, "message": "你不在任何城镇或村庄"}
        
        result = trading.sell_good(player, loc, good_id, count)
        if result.get("success"):
            await self._save_player(player)
        return result

    def get_trade_list(self, user_id: str, location_id: str = None, is_buying: bool = True) -> dict:
        """获取商品列表"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}
        
        if not hasattr(player, 'map_state') or not player.map_state:
            return {"success": False, "message": "无法获取位置信息"}
        
        loc = location_id or player.map_state.current_location
        if not loc:
            return {"success": False, "message": "你不在任何城镇或村庄"}
        
        goods_list = trading.get_location_goods(loc, is_buying)
        return {
            "success": True,
            "location_id": loc,
            "is_buying": is_buying,
            "goods": goods_list,
        }

    def get_trade_inventory(self, user_id: str) -> dict:
        """获取玩家背包商品"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}
        
        if not hasattr(player, 'trade_inventory'):
            return {"success": True, "goods": {}}
        
        inventory = player.trade_inventory
        goods = {}
        for good_id, count in inventory.goods.items():
            good = trading.get_good(good_id)
            if good:
                goods[good_id] = {
                    "name": good.name,
                    "count": count,
                }
        
        return {"success": True, "goods": goods}

    # ── 锻造系统 ──────────────────────────────────────────────

    async def forge_item(self, user_id: str, recipe_id: str) -> dict:
        """锻造装备"""
        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}
        
        result = forging.forge_item(player, recipe_id)
        if result.get("success"):
            await self._save_player(player)
        return result

    def get_forging_materials(self, user_id: str) -> dict:
        """获取锻造材料"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}
        
        materials = {}
        if hasattr(player, 'forging_materials'):
            for mat_id, count in player.forging_materials.items():
                mat = forging.get_material(mat_id)
                if mat:
                    materials[mat_id] = {
                        "name": mat.name,
                        "count": count,
                    }
        
        return {"success": True, "materials": materials}

    def get_forging_recipes(self, user_id: str) -> dict:
        """获取锻造配方"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}
        
        skill_level = getattr(player, 'smithing_level', 0)
        recipes = forging.get_available_recipes(skill_level)
        
        recipe_list = []
        for r in recipes:
            fuel = forging.get_material(r.fuel_required)
            metal = forging.get_material(r.metal_required)
            acc = forging.get_material(r.accessory_required) if r.accessory_required else None
            
            recipe_list.append({
                "recipe_id": r.recipe_id,
                "name": r.name,
                "result": r.result_item_id,
                "fuel": fuel.name if fuel else r.fuel_required,
                "metal": metal.name if metal else r.metal_required,
                "accessory": acc.name if acc else "",
                "skill_req": r.skill_level_req,
            })
        
        return {"success": True, "recipes": recipe_list, "skill_level": skill_level}

    async def buy_forging_material(self, user_id: str, material_id: str, count: int = 1) -> dict:
        """购买锻造材料"""
        from .map_system import TOWNS, VILLAGES
        
        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}
        
        if not hasattr(player, 'map_state') or not player.map_state:
            return {"success": False, "message": "无法获取位置信息"}
        
        loc = player.map_state.current_location
        if not loc:
            return {"success": False, "message": "你不在任何城镇"}
        
        can_buy = False
        if loc in TOWNS and TOWNS[loc].has_blacksmith:
            can_buy = True
        elif loc in VILLAGES and VILLAGES[loc].has_blacksmith:
            can_buy = True
        
        if not can_buy:
            return {"success": False, "message": "你不在有铁匠铺的城镇或村庄"}
        
        shop_mats = forging.get_shop_materials(loc)
        shop_mat = None
        for m in shop_mats:
            if m["material_id"] == material_id:
                shop_mat = m
                break
        
        if not shop_mat:
            return {"success": False, "message": "该城镇不出售此材料"}
        
        total_cost = shop_mat["price"] * count
        
        if player.spirit_stones < total_cost:
            return {"success": False, "message": f"第纳尔不足，需要{total_cost}第纳尔"}
        
        player.spirit_stones -= total_cost
        forging.add_material(player, material_id, count)
        
        await self._save_player(player)
        
        return {
            "success": True,
            "message": f"购买了{count}个{shop_mat['name']}，花费{total_cost}第纳尔",
            "cost": total_cost,
        }

    # ── 狩猎系统 ──────────────────────────────────────────────

    def get_hunting_info(self, user_id: str) -> dict:
        """获取狩猎信息"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}
        
        return {
            "success": True,
            "materials": accessories.format_hunting_materials(player),
        }

    async def hunt_wildlife(self, user_id: str, wildlife_id: str = None) -> dict:
        """狩猎野生动物"""
        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        HUNT_LINGQI_COST = 15

        if player.lingqi < HUNT_LINGQI_COST:
            return {"success": False, "message": f"体力不足，需要 {HUNT_LINGQI_COST} 点体力"}

        if wildlife_id and wildlife_id in hunting.WILDLIFE:
            wildlife = hunting.WILDLIFE[wildlife_id]
        else:
            import random
            wildlife_list = list(hunting.WILDLIFE.values())
            wildlife = random.choice(wildlife_list)

        exp_reward = wildlife.exp_reward
        gold_reward = wildlife.gold_reward

        drops = hunting.calculate_hunt_drops(wildlife)

        player.exp = getattr(player, 'exp', 0) + exp_reward
        player.spirit_stones = getattr(player, 'spirit_stones', 0) + gold_reward
        player.lingqi -= HUNT_LINGQI_COST

        if not hasattr(player, 'hunting_materials'):
            player.hunting_materials = {}

        drop_texts = []
        for item_id, count in drops.items():
            result = await add_item(player, item_id, count, "狩猎")
            player.hunting_materials[item_id] = player.hunting_materials.get(item_id, 0) + count
            item_info = hunting.HUNT_DROPS.get(item_id, {})
            drop_texts.append(f"{item_info.get('name', item_id)}x{count}")

        await self._save_player(player)
        await self._notify_player_update(player)

        drops_str = "、".join(drop_texts) if drop_texts else "无"

        return {
            "success": True,
            "message": f"消耗{HUNT_LINGQI_COST}点体力，猎杀了{wildlife.name}！获得经验{exp_reward}，金币{gold_reward}，掉落：{drops_str}",
            "exp": exp_reward,
            "gold": gold_reward,
            "drops": drops,
            "lingqi_remaining": player.lingqi,
        }

    # ── 饰品制作系统 ──────────────────────────────────────────────

    async def craft_accessory(self, user_id: str, accessory_id: str) -> dict:
        """制作饰品"""
        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}
        
        result = accessories.craft_accessory(player, accessory_id)
        if result.get("success"):
            await self._save_player(player)
        return result

    def get_accessory_recipes(self, user_id: str) -> dict:
        """获取饰品配方"""
        player = self._players.get(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}
        
        return {
            "success": True,
            "recipes": accessories.format_accessory_recipes(player),
        }

    # ── 地点与NPC系统 ──────────────────────────────────────────────

    async def enter_location(self, user_id: str, location_id: str) -> dict:
        """进入城镇或村庄"""
        from .map_system import ALL_LOCATIONS, LocationType, arrive_at_location
        from .npc_system import get_npcs_for_location, get_dialog_for_npc, get_favor_level, FAVOR_LEVELS

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        loc = ALL_LOCATIONS.get(location_id)
        if not loc:
            return {"success": False, "message": "地点不存在"}

        async with self._get_player_lock(user_id):
            result = arrive_at_location(player.map_state, location_id)
            if not result.get("success"):
                return result
            await self._save_player(player)

        npcs = get_npcs_for_location(location_id)
        npc_data = []
        from .npc_system import get_npc_favor_state, _npc_favor_states
        for npc in npcs:
            favor_state = get_npc_favor_state(_npc_favor_states, user_id, npc.npc_id)
            npc_data.append({
                "npc_id": npc.npc_id,
                "name": npc.name,
                "title": npc.title,
                "icon": npc.icon,
                "description": npc.description,
                "npc_type": npc.npc_type,
                "favor": favor_state.favor,
                "favor_level": get_favor_level(favor_state.favor),
                "total_gifts_given": favor_state.total_gifts_given,
            })

        loc_type_name = LocationType(int(loc.location_type)).name
        from .map_system import get_location_icon
        loc_icon = get_location_icon(int(loc.location_type))

        return {
            "success": True,
            "message": f"你进入了{loc.name}",
            "location": {
                "location_id": loc.location_id,
                "name": loc.name,
                "type": loc_type_name,
                "icon": loc_icon,
                "description": loc.description,
                "faction": loc.faction,
                "has_blacksmith": getattr(loc, 'has_blacksmith', False),
            },
            "npcs": npc_data,
        }

    async def get_town_menu(self, user_id: str, location_id: str) -> dict:
        """获取城镇菜单（骑砍风格设施列表）。"""
        from .map_system import ALL_LOCATIONS, LocationType
        from .npc_system import get_npcs_for_location

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        loc = ALL_LOCATIONS.get(location_id)
        if not loc:
            return {"success": False, "message": "地点不存在"}

        loc_type = int(loc.location_type)
        npcs = get_npcs_for_location(location_id)
        npc_by_type = {}
        for npc in npcs:
            npc_by_type[npc.npc_type] = npc

        menu_items = []

        if loc_type == LocationType.TOWN:
            tavern_npc = npc_by_type.get("tavern_keeper")
            menu_items.append({
                "id": "tavern",
                "name": "酒馆",
                "icon": "🍺",
                "description": "休息、打听消息",
                "available": bool(tavern_npc),
                "npc_id": tavern_npc.npc_id if tavern_npc else None,
                "npc_name": tavern_npc.name if tavern_npc else None,
            })
            menu_items.append({
                "id": "arena",
                "name": "竞技场",
                "icon": "🏟️",
                "description": "参加比武大赛",
                "available": True,
                "npc_id": None,
                "npc_name": None,
            })
            merchant_npc = npc_by_type.get("merchant")
            menu_items.append({
                "id": "shop",
                "name": "商店",
                "icon": "🏪",
                "description": "买卖商品",
                "available": bool(merchant_npc),
                "npc_id": merchant_npc.npc_id if merchant_npc else None,
                "npc_name": merchant_npc.name if merchant_npc else None,
            })
            blacksmith_npc = npc_by_type.get("blacksmith")
            menu_items.append({
                "id": "blacksmith",
                "name": "铁匠铺",
                "icon": "🔨",
                "description": "修理、强化装备",
                "available": bool(blacksmith_npc),
                "npc_id": blacksmith_npc.npc_id if blacksmith_npc else None,
                "npc_name": blacksmith_npc.name if blacksmith_npc else None,
            })
            mayor_npc = npc_by_type.get("mayor")
            menu_items.append({
                "id": "castle",
                "name": "城堡",
                "icon": "🏰",
                "description": "与城镇长对话、接取任务",
                "available": bool(mayor_npc),
                "npc_id": mayor_npc.npc_id if mayor_npc else None,
                "npc_name": mayor_npc.name if mayor_npc else None,
            })
            menu_items.append({
                "id": "quests",
                "name": "任务板",
                "icon": "📋",
                "description": "查看可接任务",
                "available": True,
                "npc_id": None,
                "npc_name": None,
            })

        elif loc_type == LocationType.VILLAGE:
            elder_npc = npc_by_type.get("village_elder")
            menu_items.append({
                "id": "elder",
                "name": "村长家",
                "icon": "👴",
                "description": "与村长对话、接取任务",
                "available": bool(elder_npc),
                "npc_id": elder_npc.npc_id if elder_npc else None,
                "npc_name": elder_npc.name if elder_npc else None,
            })
            menu_items.append({
                "id": "industry",
                "name": "产业管理",
                "icon": "🏗️",
                "description": "建造和管理村庄产业",
                "available": True,
                "npc_id": None,
                "npc_name": None,
            })
            menu_items.append({
                "id": "quests",
                "name": "委托",
                "icon": "📋",
                "description": "查看村庄委托",
                "available": True,
                "npc_id": None,
                "npc_name": None,
            })
            menu_items.append({
                "id": "rest",
                "name": "借宿",
                "icon": "🛏️",
                "description": "在村民家中休息",
                "available": True,
                "npc_id": None,
                "npc_name": None,
            })

        elif loc_type == LocationType.CASTLE:
            menu_items.append({
                "id": "castle",
                "name": "城堡大厅",
                "icon": "🏰",
                "description": "城堡内部",
                "available": True,
                "npc_id": None,
                "npc_name": None,
            })
            menu_items.append({
                "id": "quests",
                "name": "任务板",
                "icon": "📋",
                "description": "查看可接任务",
                "available": True,
                "npc_id": None,
                "npc_name": None,
            })

        elif loc_type == LocationType.BANDIT_CAMP:
            menu_items.append({
                "id": "raid",
                "name": "清剿匪窝",
                "icon": "⚔️",
                "description": "与匪徒战斗",
                "available": True,
                "npc_id": None,
                "npc_name": None,
            })

        loc_type_name = LocationType(loc_type).name
        from .map_system import get_location_icon
        loc_icon = get_location_icon(loc_type)

        faction_names = {
            0: "斯瓦迪亚王国", 1: "维吉亚王国", 2: "诺德王国",
            3: "罗多克王国", 4: "库吉特汗国", 5: "萨兰德苏丹国",
        }
        faction_name = faction_names.get(getattr(loc, 'faction', -1), "")

        return {
            "success": True,
            "location": {
                "location_id": loc.location_id,
                "name": loc.name,
                "type": loc_type_name,
                "icon": loc_icon,
                "description": loc.description,
                "faction_name": faction_name,
            },
            "menu_items": menu_items,
        }

    async def town_menu_action(self, user_id: str, action_id: str, location_id: str, npc_id: str = "") -> dict:
        """处理城镇菜单项点击。"""
        from .map_system import ALL_LOCATIONS, LocationType
        from .npc_system import get_npcs_for_location

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        loc = ALL_LOCATIONS.get(location_id)
        if not loc:
            return {"success": False, "message": "地点不存在"}

        loc_type = int(loc.location_type)
        npcs = get_npcs_for_location(location_id)
        npc_by_type = {}
        for npc in npcs:
            npc_by_type[npc.npc_type] = npc

        if action_id in ("tavern", "castle", "elder", "shop", "blacksmith"):
            target_npc = None
            if npc_id:
                for npc in npcs:
                    if npc.npc_id == npc_id:
                        target_npc = npc
                        break
            else:
                type_map = {
                    "tavern": "tavern_keeper",
                    "castle": "mayor",
                    "elder": "village_elder",
                    "shop": "merchant",
                    "blacksmith": "blacksmith",
                }
                target_npc = npc_by_type.get(type_map.get(action_id, ""))

            if target_npc:
                return {
                    "success": True,
                    "action": "open_npc_dialog",
                    "npc_id": target_npc.npc_id,
                    "npc_name": target_npc.name,
                    "message": f"你走向了{target_npc.name}",
                }
            return {"success": False, "message": "该设施暂无NPC"}

        elif action_id == "arena":
            if loc_type != LocationType.TOWN:
                return {"success": False, "message": "只有城镇才有竞技场"}
            return {
                "success": True,
                "action": "navigate",
                "route": "/tournament",
                "query": {"location_id": location_id},
                "message": "你来到了竞技场",
            }

        elif action_id == "shop":
            merchant = npc_by_type.get("merchant")
            if merchant:
                return {
                    "success": True,
                    "action": "navigate",
                    "route": "/trade",
                    "query": {"location_id": location_id},
                    "message": "你来到了商店",
                }
            return {"success": False, "message": "该地点没有商店"}

        elif action_id == "blacksmith":
            blacksmith = npc_by_type.get("blacksmith")
            if blacksmith:
                return {
                    "success": True,
                    "action": "navigate",
                    "route": "/blacksmith",
                    "query": {"location_id": location_id},
                    "message": "你来到了铁匠铺",
                }
            return {"success": False, "message": "该地点没有铁匠铺"}

        elif action_id == "rest":
            return {
                "success": True,
                "action": "rest",
                "message": "你找了一处安静的地方休息",
            }

        elif action_id == "raid":
            return {
                "success": True,
                "action": "navigate",
                "route": "/bandits",
                "query": {"location_id": location_id},
                "message": "你准备清剿匪窝",
            }

        elif action_id == "quests":
            return {
                "success": True,
                "action": "show_message",
                "message": "任务系统开发中...",
            }

        elif action_id == "industry":
            return {
                "success": True,
                "action": "navigate",
                "route": "/industry",
                "query": {"village_id": location_id, "location_id": location_id},
                "message": "你打开了产业管理",
            }

        return {"success": False, "message": "未知的菜单操作"}

    async def get_village_industries(self, user_id: str, village_id: str) -> dict:
        """获取村庄产业状态。"""
        from .map_system import ALL_LOCATIONS
        from .industry_system import (
            INDUSTRIES, get_available_industries, get_industry_status_detail,
            get_npc_bonus_for_industry, INDUSTRY_MAX_PER_VILLAGE,
        )

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        loc = ALL_LOCATIONS.get(village_id)
        if not loc:
            return {"success": False, "message": "地点不存在"}

        village_type = getattr(loc, 'village_type', '')
        village_production = getattr(loc, 'production', '')
        village_prosperity = getattr(loc, 'prosperity', 0)
        favor = player.village_favor.get(village_id, 0)

        npc_bonuses = get_npc_bonus_for_industry({}, user_id, village_type)
        available = get_available_industries(
            village_id, village_type, village_production,
            village_prosperity, favor,
            player.village_industries.get(village_id, {}).get("total_count", 0),
        )
        status = get_industry_status_detail(
            player.village_industries, village_id, npc_bonuses,
        )

        return {
            "success": True,
            "village": {
                "village_id": village_id,
                "name": loc.name,
                "type": village_type,
                "production": village_production,
                "prosperity": village_prosperity,
            },
            "player_favor": favor,
            "available_industries": available,
            "built_industries": status,
            "npc_bonuses": npc_bonuses,
        }

    async def build_village_industry(self, user_id: str, village_id: str, industry_id: str) -> dict:
        """建造村庄产业。"""
        from .map_system import ALL_LOCATIONS
        from .industry_system import (
            INDUSTRIES, build_industry, get_npc_bonus_for_industry,
        )

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        loc = ALL_LOCATIONS.get(village_id)
        if not loc:
            return {"success": False, "message": "地点不存在"}

        village_type = getattr(loc, 'village_type', '')
        village_production = getattr(loc, 'production', '')
        village_prosperity = getattr(loc, 'prosperity', 0)
        favor = player.village_favor.get(village_id, 0)
        npc_bonuses = get_npc_bonus_for_industry({}, user_id, village_type)

        async with self._get_player_lock(user_id):
            result = build_industry(
                player.village_industries, user_id, village_id, industry_id,
                village_type, village_production, village_prosperity,
                favor, player.spirit_stones, npc_bonuses,
            )
            if result.get("success"):
                player.spirit_stones -= result["cost"]
                await self._save_player(player)

        return result

    async def upgrade_village_industry(self, user_id: str, village_id: str, industry_id: str) -> dict:
        """升级村庄产业。"""
        from .map_system import ALL_LOCATIONS
        from .industry_system import (
            INDUSTRIES, upgrade_industry, get_npc_bonus_for_industry,
        )

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        loc = ALL_LOCATIONS.get(village_id)
        if not loc:
            return {"success": False, "message": "地点不存在"}

        village_type = getattr(loc, 'village_type', '')
        village_production = getattr(loc, 'production', '')
        village_prosperity = getattr(loc, 'prosperity', 0)
        favor = player.village_favor.get(village_id, 0)
        npc_bonuses = get_npc_bonus_for_industry({}, user_id, village_type)

        async with self._get_player_lock(user_id):
            result = upgrade_industry(
                player.village_industries, user_id, village_id, industry_id,
                player.spirit_stones, npc_bonuses,
            )
            if result.get("success"):
                player.spirit_stones -= result["cost"]
                await self._save_player(player)

        return result

    async def collect_industry_income(self, user_id: str, village_id: str) -> dict:
        """收取村庄产业产出。"""
        from .map_system import ALL_LOCATIONS
        from .industry_system import (
            collect_industry_income as _collect, get_npc_bonus_for_industry,
        )

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        loc = ALL_LOCATIONS.get(village_id)
        if not loc:
            return {"success": False, "message": "地点不存在"}

        village_type = getattr(loc, 'village_type', '')
        village_production = getattr(loc, 'production', '')
        village_prosperity = getattr(loc, 'prosperity', 0)
        favor = player.village_favor.get(village_id, 0)
        npc_bonuses = get_npc_bonus_for_industry({}, user_id, village_type)

        async with self._get_player_lock(user_id):
            result = _collect(
                player.village_industries, user_id, village_id, npc_bonuses,
            )
            if result.get("success"):
                player.spirit_stones += result.get("total_income", 0)
                await self._save_player(player)

        return result

    async def repair_industry_action(self, user_id: str, village_id: str, industry_id: str) -> dict:
        """修复村庄产业。"""
        from .map_system import ALL_LOCATIONS
        from .industry_system import repair_industry

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        loc = ALL_LOCATIONS.get(village_id)
        if not loc:
            return {"success": False, "message": "地点不存在"}

        async with self._get_player_lock(user_id):
            result = repair_industry(
                player.village_industries, user_id, village_id, industry_id,
                player.spirit_stones,
            )
            if result.get("success"):
                player.spirit_stones -= result["cost"]
                await self._save_player(player)

        return result

    async def leave_location(self, user_id: str) -> dict:
        """离开当前地点，返回大地图"""
        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        if not player.map_state.current_location:
            return {"success": False, "message": "你不在任何地点"}

        current_loc = player.map_state.current_location
        player.map_state.current_location = ""

        await self._save_player(player)

        return {
            "success": True,
            "message": f"你离开了{current_loc}",
        }

    async def rest_at_settlement(self, user_id: str) -> dict:
        """在定居点休息，恢复HP和体力。"""
        import time
        from .map_system import ALL_LOCATIONS, LocationType
        from .npc_system import get_npcs_for_location

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        loc_id = player.map_state.current_location
        if not loc_id:
            return {"success": False, "message": "你不在任何定居点，无法休息"}

        loc = ALL_LOCATIONS.get(loc_id)
        if not loc:
            return {"success": False, "message": "地点不存在"}

        # 检查是否有酒馆老板NPC
        npcs = get_npcs_for_location(loc_id)
        has_tavern = any(n.npc_type == "tavern_keeper" for n in npcs)
        if not has_tavern:
            return {"success": False, "message": "这里没有酒馆，无法休息"}

        # 计算休息费用
        loc_type = int(loc.location_type)
        if loc_type == 1:  # TOWN
            cost = 20
        elif loc_type == 0:  # VILLAGE
            cost = 10
        elif loc_type == 2:  # CASTLE
            cost = 15
        else:
            cost = 10

        if player.spirit_stones < cost:
            return {"success": False, "message": f"第纳尔不足，休息需要{cost}第纳尔"}

        # 冷却检查（5分钟）
        now = time.time()
        if player.last_rest_time and (now - player.last_rest_time) < 300:
            remaining = int(300 - (now - player.last_rest_time))
            return {"success": False, "message": f"你刚休息过，还需等待{remaining}秒"}

        # 执行休息
        hp_recovered = player.max_hp - player.hp
        lingqi_recovered = player.max_lingqi - player.lingqi
        player.hp = player.max_hp
        player.lingqi = player.max_lingqi
        player.spirit_stones -= cost
        player.last_rest_time = now

        await self._save_player(player)

        msg = f"在{loc.name}的酒馆休息，花费{cost}第纳尔"
        if hp_recovered > 0:
            msg += f"，恢复{hp_recovered}点HP"
        if lingqi_recovered > 0:
            msg += f"，恢复{lingqi_recovered}点体力"
        if hp_recovered == 0 and lingqi_recovered == 0:
            msg += "，状态已满"

        return {
            "success": True,
            "message": msg,
            "cost": cost,
            "hp_recovered": hp_recovered,
            "lingqi_recovered": lingqi_recovered,
        }

    async def heal_troops(self, user_id: str) -> dict:
        """在定居点进行部队医疗，免费，取决于统御技能等级。"""
        from .map_system import ALL_LOCATIONS
        from .npc_system import get_npcs_for_location
        from .troops import calc_max_troops

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        loc_id = player.map_state.current_location
        if not loc_id:
            return {"success": False, "message": "你不在任何定居点，无法进行部队医疗"}

        loc = ALL_LOCATIONS.get(loc_id)
        if not loc:
            return {"success": False, "message": "地点不存在"}

        # 获取统御技能等级
        leadership_level = player.skills.get(33, player.skills.get("33", 0))
        # 医疗速度 = 1 + 统御等级 * 0.2
        medical_speed = 1.0 + leadership_level * 0.2
        # 可恢复的部队数量 = 基础3 + 统御等级 * 2
        heal_count = 3 + leadership_level * 2

        # 获取当前部队
        player_troops = await self._data_manager.get_player_troops(user_id)
        total_troops = sum(player_troops.values())

        if total_troops == 0:
            return {"success": False, "message": "你没有部队需要医疗"}

        # 计算因军饷不足可能损失的部队，进行补充
        # 医疗效果：恢复一定比例的部队（模拟逃兵回归）
        recovered = min(heal_count, total_troops // 2)

        msg = f"在{loc.name}进行部队医疗"
        msg += f"（统御{leadership_level}级，医疗速度{medical_speed:.1f}x）"
        msg += f"，可恢复{recovered}名士兵"

        # 如果有实际部队系统，这里可以恢复逃兵
        # 当前简化版：返回医疗信息
        return {
            "success": True,
            "message": msg,
            "leadership_level": leadership_level,
            "medical_speed": round(medical_speed, 1),
            "heal_count": recovered,
            "total_troops": total_troops,
            "max_troops": calc_max_troops(leadership_level),
        }

    async def start_npc_dialog(self, user_id: str, npc_id: str) -> dict:
        """开始与NPC对话"""
        from .npc_system import (
            get_npcs_for_location, get_dialog_for_npc, get_npc_favor_state,
            get_favor_level, TOWN_NPCS, VILLAGE_NPCS, _npc_favor_states
        )
        from .map_system import ALL_LOCATIONS

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        npc = None
        location_name = ""
        all_npcs = list(TOWN_NPCS.values()) + list(VILLAGE_NPCS.values())
        for n in all_npcs:
            if n.npc_id == npc_id:
                npc = n
                loc_id = n.location_ids[0] if n.location_ids else ""
                loc = ALL_LOCATIONS.get(loc_id)
                location_name = loc.name if loc else "未知"
                break

        if not npc:
            return {"success": False, "message": "NPC不存在"}

        favor_state = get_npc_favor_state(_npc_favor_states, user_id, npc_id)
        dialogs = get_dialog_for_npc(npc, location_name, favor_state.favor)

        greeting_node = dialogs.get("greeting")
        if not greeting_node:
            return {"success": False, "message": "对话初始化失败"}

        return {
            "success": True,
            "npc": {
                "npc_id": npc.npc_id,
                "name": npc.name,
                "title": npc.title,
                "icon": npc.icon,
                "description": npc.description,
                "npc_type": npc.npc_type,
                "favor": favor_state.favor,
                "favor_level": get_favor_level(favor_state.favor),
            },
            "dialog": {
                "node_id": greeting_node.node_id,
                "text": greeting_node.text,
                "options": [
                    {
                        "option_id": opt.option_id,
                        "text": opt.text,
                        "next_node": opt.next_node,
                        "action": opt.action,
                        "action_data": opt.action_data,
                    }
                    for opt in greeting_node.options
                ],
            },
            "all_dialogs": {
                node_id: {
                    "node_id": node.node_id,
                    "text": node.text,
                    "options": [
                        {
                            "option_id": opt.option_id,
                            "text": opt.text,
                            "next_node": opt.next_node,
                            "action": opt.action,
                            "action_data": opt.action_data,
                        }
                        for opt in node.options
                    ],
                }
                for node_id, node in dialogs.items()
            },
        }

    async def give_gift(self, user_id: str, npc_id: str, gift_id: str) -> dict:
        """赠送礼物给NPC"""
        from .npc_system import give_gift_to_npc, get_npc_favor_state, get_favor_level
        from .village_system import GIFT_ITEMS

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        gift = GIFT_ITEMS.get(gift_id)
        if not gift:
            return {"success": False, "message": "礼物不存在"}

        async with self._get_player_lock(user_id):
            result = give_gift_to_npc(user_id, npc_id, gift_id, gift.value)
            if result.get("success"):
                await self._save_player(player)

        return result

    async def get_gift_list(self, user_id: str) -> dict:
        """获取所有礼物列表"""
        from .village_system import GIFT_ITEMS

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        gifts = []
        for item_id, gift in GIFT_ITEMS.items():
            gifts.append({
                "id": item_id,
                "name": gift.name,
                "value": gift.value,
                "can_unlock_legendary": gift.can_unlock_legendary,
            })

        gifts.sort(key=lambda x: x["value"])

        return {
            "success": True,
            "gifts": gifts,
            "categories": {
                "common": [1, 30],
                "medium": [31, 80],
                "advanced": [81, 150],
                "rare": [151, 999],
            }
        }

    # ══════════════════════════════════════════════════════════════
    # 同伴系统
    # ══════════════════════════════════════════════════════════════

    async def get_companions(self, user_id: str) -> dict:
        """获取同伴列表。"""
        from .companions import (
            get_all_companions, get_companion, get_companion_buff,
            COMPANION_REGISTRY, GIFT_REGISTRY,
        )

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        owned = await self._data_manager.get_player_companions(user_id)
        owned_map = {c["companion_id"]: c for c in owned}

        companions = []
        for comp_def in get_all_companions():
            is_owned = comp_def.companion_id in owned_map
            companion_data = {
                "companion_id": comp_def.companion_id,
                "name": comp_def.name,
                "title": comp_def.title,
                "recruit_location": comp_def.recruit_location,
                "recruit_cost": comp_def.recruit_cost,
                "attack": comp_def.attack,
                "defense": comp_def.defense,
                "hp": comp_def.hp,
                "buff_type": comp_def.buff_type,
                "buff_value": comp_def.buff_value,
                "description": comp_def.description,
                "gift_preferences": comp_def.gift_preferences,
                "is_owned": is_owned,
            }
            if is_owned:
                oc = owned_map[comp_def.companion_id]
                companion_data["loyalty"] = oc["loyalty"]
                companion_data["gifts_given"] = oc["gifts_given"]
                companion_data["is_active"] = oc["is_active"]
                buff = get_companion_buff(type("C", (), oc)())
                companion_data["buff"] = buff
            companions.append(companion_data)

        return {"success": True, "companions": companions, "gifts": GIFT_REGISTRY}

    async def recruit_companion(self, user_id: str, companion_id: str) -> dict:
        """招募同伴。"""
        from .companions import get_companion, calculate_recruit_cost

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        comp_def = get_companion(companion_id)
        if not comp_def:
            return {"success": False, "message": "同伴不存在"}

        if await self._data_manager.has_companion(user_id, companion_id):
            return {"success": False, "message": "你已招募该同伴"}

        cost = calculate_recruit_cost(companion_id)
        if player.spirit_stones < cost:
            return {"success": False, "message": f"第纳尔不足，需要{cost}第纳尔"}

        player.spirit_stones -= cost
        await self._data_manager.add_player_companion(user_id, companion_id)
        await self._save_player(player)

        return {
            "success": True,
            "message": f"成功招募【{comp_def.title}】{comp_def.name}！",
            "companion": {
                "name": comp_def.name,
                "title": comp_def.title,
                "description": comp_def.description,
            },
        }

    async def give_companion_gift(self, user_id: str, companion_id: str, gift_id: str) -> dict:
        """赠送礼物给同伴提升忠诚度。"""
        from .companions import get_companion, calculate_gift_loyalty_gain, GIFT_REGISTRY

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        comp_def = get_companion(companion_id)
        if not comp_def:
            return {"success": False, "message": "同伴不存在"}

        if not await self._data_manager.has_companion(user_id, companion_id):
            return {"success": False, "message": "你尚未招募该同伴"}

        gift = GIFT_REGISTRY.get(gift_id)
        if not gift:
            return {"success": False, "message": "礼物不存在"}

        if player.spirit_stones < gift["base_price"]:
            return {"success": False, "message": f"第纳尔不足，需要{gift['base_price']}第纳尔"}

        loyalty_gain = calculate_gift_loyalty_gain(companion_id, gift_id)
        is_preferred = gift_id in comp_def.gift_preferences

        player.spirit_stones -= gift["base_price"]
        await self._data_manager.update_companion_loyalty(user_id, companion_id, loyalty_gain, 1)
        await self._save_player(player)

        msg = f"赠送【{gift['description']}】给{comp_def.name}"
        if is_preferred:
            msg += f"（{comp_def.name}非常喜欢！）"
        msg += f"，忠诚度+{loyalty_gain}"

        return {"success": True, "message": msg, "loyalty_gain": loyalty_gain}

    async def toggle_companion_active(self, user_id: str, companion_id: str, active: bool) -> dict:
        """切换同伴出战状态。"""
        from .companions import get_companion

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        comp_def = get_companion(companion_id)
        if not comp_def:
            return {"success": False, "message": "同伴不存在"}

        if not await self._data_manager.has_companion(user_id, companion_id):
            return {"success": False, "message": "你尚未招募该同伴"}

        await self._data_manager.set_companion_active(user_id, companion_id, active)
        status = "出战" if active else "休息"
        return {"success": True, "message": f"{comp_def.name}已设为{status}状态"}

    # ══════════════════════════════════════════════════════════════
    # 部队系统
    # ══════════════════════════════════════════════════════════════

    async def get_troops(self, user_id: str) -> dict:
        """获取部队信息。"""
        from .troops import (
            get_all_troops, get_troop, calc_total_wage, calc_max_troops,
            TROOP_REGISTRY, FACTION_NAMES,
        )

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        troops = await self._data_manager.get_player_troops(user_id)
        leadership = player.skills.get("leadership", 0)
        max_troops = calc_max_troops(leadership)
        total_count = sum(troops.values())
        total_wage = calc_total_wage(troops)

        troop_list = []
        for troop_id, count in troops.items():
            if count <= 0:
                continue
            troop_def = get_troop(troop_id)
            if troop_def:
                troop_list.append({
                    "troop_id": troop_id,
                    "name": troop_def.name,
                    "faction": troop_def.faction,
                    "faction_name": FACTION_NAMES.get(troop_def.faction, troop_def.faction),
                    "count": count,
                    "attack": troop_def.attack,
                    "defense": troop_def.defense,
                    "hp": troop_def.hp,
                    "wage": troop_def.wage,
                    "total_wage": troop_def.wage * count,
                })

        return {
            "success": True,
            "troops": troop_list,
            "total_count": total_count,
            "max_troops": max_troops,
            "total_wage": total_wage,
            "leadership_level": leadership,
            "all_troops": [
                {
                    "troop_id": t.troop_id,
                    "name": t.name,
                    "faction": t.faction,
                    "faction_name": FACTION_NAMES.get(t.faction, t.faction),
                    "cost": t.cost,
                    "wage": t.wage,
                    "attack": t.attack,
                    "defense": t.defense,
                    "hp": t.hp,
                    "description": t.description,
                }
                for t in get_all_troops()
            ],
        }

    async def recruit_troops(self, user_id: str, troop_id: str, count: int) -> dict:
        """招募部队。"""
        from .troops import get_troop, calc_max_troops

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        troop_def = get_troop(troop_id)
        if not troop_def:
            return {"success": False, "message": "兵种不存在"}

        if count <= 0:
            return {"success": False, "message": "招募数量必须大于0"}

        cost = troop_def.cost * count
        if player.spirit_stones < cost:
            return {"success": False, "message": f"第纳尔不足，需要{cost}第纳尔"}

        leadership = player.skills.get("leadership", 0)
        max_troops = calc_max_troops(leadership)
        current_count = await self._data_manager.get_total_troop_count(user_id)
        if current_count + count > max_troops:
            return {"success": False, "message": f"部队已满，最多{max_troops}人（统御{leadership}级）"}

        player.spirit_stones -= cost
        await self._data_manager.add_player_troops(user_id, troop_id, count)
        await self._save_player(player)

        return {
            "success": True,
            "message": f"成功招募{count}名{troop_def.name}！",
            "cost": cost,
            "count": count,
        }

    async def dismiss_troops(self, user_id: str, troop_id: str, count: int) -> dict:
        """解散部队。"""
        from .troops import get_troop

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        troop_def = get_troop(troop_id)
        if not troop_def:
            return {"success": False, "message": "兵种不存在"}

        if count <= 0:
            return {"success": False, "message": "解散数量必须大于0"}

        actual = await self._data_manager.remove_player_troops(user_id, troop_id, count)
        if actual <= 0:
            return {"success": False, "message": "没有该兵种可解散"}

        await self._save_player(player)
        return {"success": True, "message": f"解散了{actual}名{troop_def.name}", "actual": actual}

    # ══════════════════════════════════════════════════════════════
    # 竞技场系统
    # ══════════════════════════════════════════════════════════════

    async def get_tournament(self, user_id: str) -> dict:
        """获取竞技场信息。"""
        from .tournament import (
            get_tournament_opponents, generate_daily_opponents,
            get_opponent, ENTRY_FEE, WIN_STREAK_REWARDS,
        )

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        opponents = generate_daily_opponents(player.level)
        opponent_list = []
        for opp_id in opponents:
            opp = get_opponent(opp_id)
            if opp:
                opponent_list.append({
                    "opponent_id": opp.opponent_id,
                    "name": opp.name,
                    "title": opp.title,
                    "level": opp.level,
                    "attack": opp.attack,
                    "defense": opp.defense,
                    "hp": opp.hp,
                    "reward_gold": opp.reward_gold,
                    "reward_dao_yun": opp.reward_dao_yun,
                    "description": opp.description,
                })

        history = await self._data_manager.get_tournament_history(user_id, limit=10)

        return {
            "success": True,
            "opponents": opponent_list,
            "entry_fee": ENTRY_FEE,
            "streak_rewards": WIN_STREAK_REWARDS,
            "history": history,
        }

    async def start_tournament_battle(self, user_id: str, opponent_id: str) -> dict:
        """开始竞技场战斗。"""
        from .tournament import get_opponent, ENTRY_FEE
        from .combat import CombatState, CombatEngine
        from .constants import get_equip_bonus, get_heart_method_bonus, get_total_gongfa_bonus
        from .pills import get_effective_combat_stats

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        opp = get_opponent(opponent_id)
        if not opp:
            return {"success": False, "message": "对手不存在"}

        if player.spirit_stones < ENTRY_FEE:
            return {"success": False, "message": f"报名费不足，需要{ENTRY_FEE}第纳尔"}

        player.spirit_stones -= ENTRY_FEE
        await self._save_player(player)

        # 计算玩家真实战斗属性
        effective_stats = get_effective_combat_stats(player)
        equip_bonus = get_equip_bonus(player)
        heart_bonus = get_heart_method_bonus(player.heart_method, player.heart_method_mastery)
        gongfa_bonus = get_total_gongfa_bonus(player)
        max_lingqi = max(player.lingqi, 50)

        p_atk = max(1, effective_stats["attack"] + equip_bonus["attack"] + heart_bonus["attack_bonus"] + gongfa_bonus["attack_bonus"])
        p_def = max(1, effective_stats["defense"] + equip_bonus["defense"] + heart_bonus["defense_bonus"] + gongfa_bonus["defense_bonus"])

        state = CombatState(
            player_hp=effective_stats["hp"],
            player_max_hp=effective_stats["max_hp"],
            player_attack=p_atk,
            player_defense=p_def,
            player_lingqi=min(effective_stats["lingqi"], max_lingqi),
            player_max_lingqi=max_lingqi,
            enemy_name=f"{opp.title}{opp.name}",
            enemy_type="tournament",
            enemy_hp=opp.hp,
            enemy_max_hp=opp.hp,
            enemy_attack=opp.attack,
            enemy_defense=opp.defense,
        )

        # 存储竞技场战斗状态
        if not hasattr(self, '_tournament_combats'):
            self._tournament_combats = {}
        self._tournament_combats[user_id] = {
            "state": state,
            "opponent_id": opponent_id,
            "opponent": opp,
        }

        return {
            "success": True,
            "combat_state": state.to_dict(),
            "opponent": {
                "opponent_id": opp.opponent_id,
                "name": opp.name,
                "title": opp.title,
                "level": opp.level,
                "hp": opp.hp,
                "attack": opp.attack,
                "defense": opp.defense,
                "reward_gold": opp.reward_gold,
                "reward_dao_yun": opp.reward_dao_yun,
            },
        }

    async def tournament_combat_action(self, user_id: str, action: str, data: dict | None = None) -> dict:
        """处理竞技场战斗动作。"""
        from .combat import CombatEngine

        if not hasattr(self, '_tournament_combats') or user_id not in self._tournament_combats:
            return {"success": False, "message": "当前没有进行中的竞技场战斗"}

        battle = self._tournament_combats[user_id]
        state = battle["state"]
        player = await self.get_player(user_id)

        # 处理玩家动作
        player_result = CombatEngine.resolve_player_action(state, action, player, data)
        if not player_result["success"]:
            return player_result

        # 检查是否战斗结束
        if player_result.get("combat_end"):
            return await self._end_tournament_battle(user_id, player_result)

        # 处理敌人回合
        enemy_result = CombatEngine.resolve_enemy_turn(state)
        if enemy_result.get("combat_end"):
            player_result["combat_end"] = True
            player_result["outcome"] = "lose"
            return await self._end_tournament_battle(user_id, player_result)

        player_result["enemy_result"] = enemy_result
        player_result["combat_state"] = state.to_dict()
        return player_result

    async def _end_tournament_battle(self, user_id: str, combat_result: dict) -> dict:
        """结算竞技场战斗。"""
        import json
        from .tournament import get_opponent, get_win_streak_reward

        battle = self._tournament_combats.pop(user_id, None)
        if not battle:
            return {"success": False, "message": "战斗数据丢失"}

        opp = battle["opponent"]
        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        won = combat_result.get("outcome") == "win"

        if won:
            gold_reward = opp.reward_gold
            dao_yun_reward = opp.reward_dao_yun

            history = await self._data_manager.get_tournament_history(user_id, limit=1)
            current_streak = 1
            if history and history[0]["result"] == "win":
                current_streak = history[0]["win_streak"] + 1

            streak_bonus = get_win_streak_reward(current_streak)
            streak_bonus_json = json.dumps(streak_bonus, ensure_ascii=False) if streak_bonus else "{}"

            if streak_bonus:
                gold_reward += streak_bonus["gold"]
                dao_yun_reward += streak_bonus["dao_yun"]

            player.spirit_stones += gold_reward
            player.dao_yun += dao_yun_reward

            await self._data_manager.record_tournament_result(
                user_id, battle["opponent_id"], "win", gold_reward, dao_yun_reward,
                current_streak, streak_bonus_json,
            )
            await self._save_player(player)

            msg = f"胜利！获得{gold_reward}第纳尔，{dao_yun_reward}声望"
            if streak_bonus:
                msg += f"\n🔥 {streak_bonus['title']}！额外奖励{streak_bonus['gold']}第纳尔，{streak_bonus['dao_yun']}声望"

            return {
                "success": True,
                "message": msg,
                "result": "win",
                "gold_reward": gold_reward,
                "dao_yun_reward": dao_yun_reward,
                "win_streak": current_streak,
                "streak_bonus": streak_bonus,
                "combat_state": combat_result.get("combat_state"),
            }
        else:
            await self._data_manager.record_tournament_result(
                user_id, battle["opponent_id"], "lose", 0, 0, 0, "{}",
            )
            await self._save_player(player)

            return {
                "success": True,
                "message": "战败了……再接再厉！",
                "result": "lose",
                "combat_state": combat_result.get("combat_state"),
            }

    async def end_tournament_battle(self, user_id: str, opponent_id: str, won: bool) -> dict:
        """结束竞技场战斗并结算。"""
        import json
        from .tournament import get_opponent, get_win_streak_reward

        player = await self.get_player(user_id)
        if not player:
            return {"success": False, "message": "你还没有角色"}

        opp = get_opponent(opponent_id)
        if not opp:
            return {"success": False, "message": "对手不存在"}

        if won:
            gold_reward = opp.reward_gold
            dao_yun_reward = opp.reward_dao_yun

            history = await self._data_manager.get_tournament_history(user_id, limit=1)
            current_streak = 1
            if history and history[0]["result"] == "win":
                current_streak = history[0]["win_streak"] + 1

            streak_bonus = get_win_streak_reward(current_streak)
            streak_bonus_json = json.dumps(streak_bonus, ensure_ascii=False) if streak_bonus else "{}"

            if streak_bonus:
                gold_reward += streak_bonus["gold"]
                dao_yun_reward += streak_bonus["dao_yun"]

            player.spirit_stones += gold_reward
            player.dao_yun += dao_yun_reward

            await self._data_manager.record_tournament_result(
                user_id, opponent_id, "win", gold_reward, dao_yun_reward,
                current_streak, streak_bonus_json,
            )
            await self._save_player(player)

            msg = f"胜利！获得{gold_reward}第纳尔，{dao_yun_reward}声望"
            if streak_bonus:
                msg += f"\n🔥 {streak_bonus['title']}！额外奖励{streak_bonus['gold']}第纳尔，{streak_bonus['dao_yun']}声望"

            return {
                "success": True,
                "message": msg,
                "result": "win",
                "gold_reward": gold_reward,
                "dao_yun_reward": dao_yun_reward,
                "win_streak": current_streak,
                "streak_bonus": streak_bonus,
            }
        else:
            await self._data_manager.record_tournament_result(
                user_id, opponent_id, "lose", 0, 0, 0, "{}",
            )
            await self._save_player(player)

            return {
                "success": True,
                "message": "战败了……再接再厉！",
                "result": "lose",
            }
