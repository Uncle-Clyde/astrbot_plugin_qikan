"""WebSocket 连接管理与消息协议 - 骑砍风格。"""

from __future__ import annotations

import asyncio
import logging
import re
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..game.constants import get_realm_name
from ..game.engine import GameEngine
from ..game.models import Player
from ..game.sect import ROLE_NAMES
from ..game.spawn_system import (
    get_all_spawn_origins,
    get_all_spawn_locations,
    get_spawn_locations_by_faction,
)
from ..game import mb_skills
from .access_guard import get_access_guard

ws_logger = logging.getLogger("qikan.websocket")

RANKINGS_PUSH_DELAY = 0.6
MARKET_PUSH_DELAY = 0.4
MARKET_PAGE_SIZE = 9

# ── 世界频道常量 ────────────────────────────────────────
WORLD_CHAT_MAX_HISTORY = 100
WORLD_CHAT_MAX_LEN = 100
WORLD_CHAT_COOLDOWN = 3.0  # 秒
WORLD_CHAT_MAX_AGE = 30 * 24 * 3600  # 1个月（秒）
WORLD_CHAT_CLEANUP_INTERVAL = 6 * 3600  # 每6小时清理一次
_RE_CHINESE_ONLY = re.compile(
    r"^[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\u2000-\u206f\u0020-\u0040\u005b-\u0060\u007b-\u007e"
    r"\u3400-\u4dbf\U00020000-\U0002a6df\U0002a700-\U0002b73f"
    r"0-9a-zA-Z]+$"
)
_PENDING_DEATH_ALLOWED_TYPES = {
    "death_confirm_keep",
    "get_announcements",
    "get_inventory",
    "get_market",
    "get_my_listings",
    "get_panel",
    "get_rankings",
    "get_scenes",
    "get_shop",
    "get_world_chat_history",
    "get_town_menu",
    "dungeon_state",
    "market_fee_preview",
    "pvp_state",
}


class ConnectionManager:
    """管理 WebSocket 连接。"""

    def __init__(self, engine: GameEngine):
        self._engine = engine
        self._connections: dict[str, WebSocket] = {}  # user_id -> websocket
        self._market_pages: dict[str, int] = {}
        self._market_my_watchers: set[str] = set()
        self._rankings_dirty = False
        self._rankings_flush_task: asyncio.Task | None = None
        self._market_dirty = False
        self._market_flush_task: asyncio.Task | None = None
        # 世界频道
        self._world_chat_cooldowns: dict[str, float] = {}  # user_id -> last_send_ts
        self._chat_cleanup_task: asyncio.Task | None = None
        # 玩家位置管理
        from ..game.map_system import get_position_manager
        self._position_manager = get_position_manager()
        self._position_update_cooldowns: dict[str, float] = {}  # user_id -> last_update_ts
        self._position_throttle = 0.5  # 位置更新节流: 0.5秒

    async def connect(self, user_id: str, websocket: WebSocket):
        self._connections[user_id] = websocket

    def disconnect(self, user_id: str):
        self._connections.pop(user_id, None)
        self._market_pages.pop(user_id, None)
        self._market_my_watchers.discard(user_id)
        # 移除玩家位置缓存
        self._position_manager.remove_player(user_id)
        self._position_update_cooldowns.pop(user_id, None)
        
        # 广播玩家离开给附近的人
        nearby_users = self._position_manager.broadcast_to_nearby(user_id, 150)
        for uid in nearby_users:
            if uid != user_id:
                import asyncio
                asyncio.create_task(self.send_to_player(uid, {
                    "type": "player_left",
                    "data": {"user_id": user_id}
                }))

    def online_count(self) -> int:
        return len(self._connections)

    async def send_to_player(self, user_id: str, data: dict):
        ws = self._connections.get(user_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(user_id)

    async def broadcast(self, data: dict, exclude_user_id: str | None = None):
        """向所有在线连接广播消息。"""
        dead_users: list[str] = []
        for uid, ws in list(self._connections.items()):
            if exclude_user_id and uid == exclude_user_id:
                continue
            try:
                await ws.send_json(data)
            except Exception:
                dead_users.append(uid)
        for uid in dead_users:
            self.disconnect(uid)

    async def notify_player_update(self, player: Player):
        """游戏引擎调用：玩家状态变化时推送。"""
        await self.send_to_player(player.user_id, {
            "type": "state_update",
            "data": player.to_dict(),
        })

    def set_market_watch(self, user_id: str, *, enabled: bool, tab: str = "", page: int = 1):
        """记录当前连接关注的坊市视图，便于服务端合并推送。"""
        self._market_pages.pop(user_id, None)
        self._market_my_watchers.discard(user_id)
        if not enabled:
            return

        normalized_tab = str(tab or "").strip().lower()
        if normalized_tab == "browse":
            try:
                page_num = int(page)
            except (TypeError, ValueError):
                page_num = 1
            self._market_pages[user_id] = max(1, page_num)
        elif normalized_tab == "my":
            self._market_my_watchers.add(user_id)

    def queue_rankings_refresh(self, engine: GameEngine):
        """合并多个排行榜刷新请求，避免全员回拉。"""
        if not self._connections:
            return
        self._rankings_dirty = True
        if self._rankings_flush_task and not self._rankings_flush_task.done():
            return
        self._rankings_flush_task = asyncio.create_task(self._flush_rankings(engine))

    async def _flush_rankings(self, engine: GameEngine):
        try:
            while True:
                self._rankings_dirty = False
                await asyncio.sleep(RANKINGS_PUSH_DELAY)
                if self._connections:
                    await self.push_rankings_data(engine)
                if not self._rankings_dirty:
                    break
        finally:
            self._rankings_flush_task = None

    async def push_rankings_data(self, engine: GameEngine):
        base_payload, my_rank_map = _build_rankings_snapshot(engine)
        for user_id in list(self._connections.keys()):
            payload = dict(base_payload)
            payload["my_rank"] = my_rank_map.get(user_id)
            await self.send_to_player(user_id, {
                "type": "rankings_data",
                "data": payload,
            })

    def queue_market_refresh(self, engine: GameEngine):
        """合并坊市刷新并由服务端主动推送当前视图。"""
        if not self._connections or (not self._market_pages and not self._market_my_watchers):
            return
        self._market_dirty = True
        if self._market_flush_task and not self._market_flush_task.done():
            return
        self._market_flush_task = asyncio.create_task(self._flush_market(engine))

    async def _flush_market(self, engine: GameEngine):
        try:
            while True:
                self._market_dirty = False
                await asyncio.sleep(MARKET_PUSH_DELAY)
                if self._connections:
                    await self.push_market_data(engine)
                if not self._market_dirty:
                    break
        finally:
            self._market_flush_task = None

    async def push_market_data(self, engine: GameEngine):
        page_watchers: dict[int, list[str]] = {}
        for user_id, page in list(self._market_pages.items()):
            if user_id not in self._connections:
                continue
            page_watchers.setdefault(page, []).append(user_id)

        for page, user_ids in page_watchers.items():
            data = await engine.market_get_listings(
                page,
                page_size=MARKET_PAGE_SIZE,
                cleanup_expired=False,
            )
            for user_id in user_ids:
                await self.send_to_player(user_id, {
                    "type": "market_data",
                    "data": data,
                })

        for user_id in list(self._market_my_watchers):
            if user_id not in self._connections:
                continue
            listings = await engine.market_get_my_listings(
                user_id,
                cleanup_expired=False,
            )
            await self.send_to_player(user_id, {
                "type": "my_listings",
                "data": {"listings": listings},
            })

    # ── 世界频道 ──────────────────────────────────────────
    async def get_world_chat_history(self) -> list[dict]:
        """从数据库获取世界频道历史消息（最新在后）。"""
        return await self._engine._data_manager.load_chat_history(
            WORLD_CHAT_MAX_HISTORY,
            max_age_seconds=WORLD_CHAT_MAX_AGE,
        )

    def check_chat_cooldown(self, user_id: str) -> tuple[bool, float]:
        """检查发言冷却，返回 (ok, remaining_seconds)。"""
        now = time.time()
        last = self._world_chat_cooldowns.get(user_id, 0)
        remaining = WORLD_CHAT_COOLDOWN - (now - last)
        if remaining > 0:
            return False, remaining
        return True, 0

    def record_chat_send(self, user_id: str):
        self._world_chat_cooldowns[user_id] = time.time()

    async def add_chat_message(self, msg: dict):
        """保存消息到数据库。"""
        await self._engine._data_manager.save_chat_message(
            user_id=msg.get("user_id", ""),
            name=msg.get("name", ""),
            realm=msg.get("realm", ""),
            content=msg.get("content", ""),
            created_at=msg.get("time", time.time()),
            sect_name=msg.get("sect_name", ""),
            sect_role=msg.get("sect_role", ""),
            sect_role_name=msg.get("sect_role_name", ""),
        )

    async def broadcast_chat(self, msg: dict):
        """广播世界频道消息给所有在线玩家。"""
        await self.broadcast({"type": "world_chat_msg", "data": msg})

    def start_chat_cleanup_task(self):
        """启动定期清理过期世界频道消息的后台任务。"""
        if self._chat_cleanup_task and not self._chat_cleanup_task.done():
            return
        self._chat_cleanup_task = asyncio.create_task(self._chat_cleanup_loop())

    async def stop_chat_cleanup_task(self):
        """停止定期清理过期世界频道消息的后台任务。"""
        task = self._chat_cleanup_task
        if not task:
            return
        if task.done():
            self._chat_cleanup_task = None
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        finally:
            self._chat_cleanup_task = None

    async def _chat_cleanup_loop(self):
        """每隔一段时间清理超过1个月的世界频道消息。"""
        logger = logging.getLogger("qikan.world_chat")
        while True:
            try:
                await asyncio.sleep(WORLD_CHAT_CLEANUP_INTERVAL)
                deleted = await self._engine._data_manager.cleanup_old_chat_messages(WORLD_CHAT_MAX_AGE)
                if deleted > 0:
                    logger.info("已清理 %d 条过期世界频道消息", deleted)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("世界频道消息清理失败")


def create_ws_router(
    engine: GameEngine,
    guard_token: str = "",
    command_prefix: str = "骑砍",
    api_rate_limit_1s_count: int = 10000,
) -> APIRouter:
    router = APIRouter()
    ws_manager = ConnectionManager(engine)
    engine._ws_manager = ws_manager
    ws_manager.start_chat_cleanup_task()
    access_guard = get_access_guard()
    required_guard_token = (guard_token or "").strip()
    try:
        limit_1s_count = int(api_rate_limit_1s_count)
    except (TypeError, ValueError):
        limit_1s_count = 10000
    limit_1s_count = max(100, limit_1s_count)
    ws_conn_window = 60.0
    ws_conn_limit = 30
    ws_block_seconds = 120.0
    ws_msg_window = 1.0
    ws_msg_limit = limit_1s_count
    ws_msg_burst_count = limit_1s_count + 1
    ws_msg_burst_window = 1.0

    def _client_ip_from_ws(websocket: WebSocket) -> str:
        headers = websocket.headers
        for key in (
            "cf-connecting-ip",
            "x-real-ip",
            "x-forwarded-for",
            "x-client-ip",
            "x-cluster-client-ip",
            "forwarded",
        ):
            raw = str(headers.get(key, "")).strip()
            if not raw:
                continue
            if key == "forwarded":
                for part in raw.split(";"):
                    part = part.strip()
                    if part.lower().startswith("for="):
                        ip = access_guard.normalize_ip(part)
                        if ip:
                            return ip
                continue
            ip = access_guard.normalize_ip(raw)
            if ip:
                return ip
        if websocket.client and websocket.client.host:
            ip = access_guard.normalize_ip(str(websocket.client.host))
            if ip:
                return ip
            return str(websocket.client.host)[:64]
        return "unknown"

    @router.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        user_id = None
        client_ip = "unknown"
        client_ua = ""
        client_page_key = ""
        page_guard: dict[str, str | int] = {"page_id": "", "issued_at": 0, "signature": ""}

        try:
            client_ip = _client_ip_from_ws(websocket)
            client_ua = str(websocket.headers.get("user-agent", "")).strip().lower()
            client_page_key = str(websocket.cookies.get("qikan_page_client", "")).strip()
            ok, reason = access_guard.check_ws_connect(
                ip=client_ip,
                limit=ws_conn_limit,
                window=ws_conn_window,
                block_seconds=ws_block_seconds,
            )
            if not ok:
                await websocket.send_json({"type": "error", "message": reason or "连接过于频繁，请稍后再试"})
                await websocket.close()
                return

            # 等待登录消息（token 认证）
            raw = await websocket.receive_json()
            if raw.get("type") != "login":
                await websocket.send_json({"type": "error", "message": "请先登录"})
                await websocket.close()
                return

            token = raw.get("data", {}).get("token", "")
            page_guard = {
                "page_id": str(raw.get("data", {}).get("page_id", "")).strip(),
                "issued_at": raw.get("data", {}).get("issued_at", 0),
                "signature": str(raw.get("data", {}).get("signature", "")).strip(),
            }
            ok, reason = access_guard.validate_page_session(
                secret=required_guard_token,
                page_id=page_guard.get("page_id", ""),
                issued_at=page_guard.get("issued_at", 0),
                signature=page_guard.get("signature", ""),
                ip=client_ip,
                ua=client_ua,
                client_key=client_page_key,
            )
            if not ok:
                await websocket.send_json({"type": "error", "message": reason or "页面凭证无效，请刷新页面"})
                await websocket.close(code=1008)
                return
            if not token or not engine.auth:
                await websocket.send_json({"type": "error", "message": "认证信息缺失"})
                await websocket.close()
                return

            user_id = engine.auth.verify_web_token(token)
            if not user_id:
                await websocket.send_json({"type": "error", "message": "登录已过期，请重新登录"})
                await websocket.close()
                return

            player = await engine.get_player(user_id)
            if not player:
                await websocket.send_json({"type": "error", "message": "角色不存在"})
                await websocket.close()
                return

            await ws_manager.connect(user_id, websocket)

            # 发送初始状态
            panel = await engine.get_panel(user_id)
            await websocket.send_json({
                "type": "state_update",
                "data": panel or player.to_dict(),
            })
            await websocket.send_json({
                "type": "rankings_data",
                "data": _build_rankings_payload(engine, user_id),
            })
            ws_manager.queue_rankings_refresh(engine)
            await websocket.send_json({
                "type": "world_chat_history",
                "data": await ws_manager.get_world_chat_history(),
            })

            # 推送公告
            announcements = await engine.get_active_announcements()
            if announcements:
                await websocket.send_json({"type": "announcements", "data": announcements})

            # 主消息循环
            while True:
                msg = await websocket.receive_json()
                ok, reason = access_guard.validate_page_session(
                    secret=required_guard_token,
                    page_id=page_guard.get("page_id", ""),
                    issued_at=page_guard.get("issued_at", 0),
                    signature=page_guard.get("signature", ""),
                    ip=client_ip,
                    ua=client_ua,
                    client_key=client_page_key,
                )
                if not ok:
                    await websocket.send_json({"type": "error", "message": reason or "页面凭证已失效，请刷新页面"})
                    await websocket.close(code=1008)
                    break
                ok, reason = access_guard.check_ws_message(
                    ip=client_ip,
                    limit=ws_msg_limit,
                    window=ws_msg_window,
                    burst_count=ws_msg_burst_count,
                    burst_window=ws_msg_burst_window,
                    block_seconds=ws_block_seconds,
                )
                if not ok:
                    await websocket.send_json({"type": "error", "message": reason or "请求过于频繁，请稍后再试"})
                    await websocket.close()
                    break
                try:
                    result = await _handle_message(
                        engine,
                        user_id,
                        msg,
                        command_prefix=command_prefix,
                        ws_manager=ws_manager,
                    )
                except Exception:
                    detail = "unknown"
                    try:
                        import traceback
                        detail = traceback.format_exc(limit=5).strip().splitlines()[-1]
                    except Exception:
                        pass
                    ws_logger.exception(
                        "骑砍世界：WS消息处理失败 user_id=%s msg_type=%s",
                        user_id,
                        msg.get("type", ""),
                    )
                    try:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"服务器处理请求时发生异常：{detail}",
                        })
                    except Exception:
                        pass
                    continue
                if result and result.get("type") != "noop":
                    request_id = msg.get("requestId")
                    if request_id:
                        result["requestId"] = request_id
                    await websocket.send_json(result)

        except WebSocketDisconnect:
            pass
        except Exception:
            ws_logger.exception("骑砍世界：WebSocket会话异常 user_id=%s", user_id)
        finally:
            if user_id:
                ws_manager.disconnect(user_id)
                ws_manager.queue_rankings_refresh(engine)

    return router


def _build_rankings_snapshot(engine: GameEngine) -> tuple[dict, dict[str, dict]]:
    """构造排行榜公共快照，并缓存每个在线用户的个人排名映射。"""
    all_rankings = engine.get_rankings(limit=999)
    death_rankings = engine.get_death_rankings(limit=10)
    online_rankings = engine.get_online_rankings(limit=50)
    online = 0
    if engine._ws_manager:
        online = len(engine._ws_manager._connections)

    my_rank_map: dict[str, dict] = {}
    for row in all_rankings:
        owner_id = engine._name_index.get(str(row.get("name", "")))
        if owner_id and owner_id not in my_rank_map:
            my_rank_map[owner_id] = row

    payload = {
        "success": True,
        "total_players": len(engine._players),
        "online_players": online,
        "rankings": all_rankings[:10],
        "death_rankings": death_rankings,
        "online_rankings": online_rankings,
    }
    return payload, my_rank_map


def _build_rankings_payload(engine: GameEngine, user_id: str) -> dict:
    """构造排行榜响应数据（WebSocket）。"""
    payload, my_rank_map = _build_rankings_snapshot(engine)
    data = dict(payload)
    data["my_rank"] = my_rank_map.get(user_id)
    return data


async def _review_chat_content(engine: GameEngine, content: str) -> dict:
    """调用 AI 审核世界频道消息内容。"""
    reviewer = getattr(engine, "_chat_reviewer", None)
    if not callable(reviewer):
        return {"allow": True, "reason": ""}
    try:
        result = await reviewer(content)
        if isinstance(result, dict):
            return {
                "allow": bool(result.get("allow", True)),
                "reason": str(result.get("reason", "")).strip(),
            }
        return {"allow": True, "reason": ""}
    except Exception:
        return {"allow": True, "reason": ""}


async def _push_player_snapshot(
    engine: GameEngine,
    ws_manager: ConnectionManager,
    user_id: str,
):
    """主动同步玩家面板与背包。"""
    panel = await engine.get_panel(user_id)
    if panel:
        await ws_manager.send_to_player(user_id, {
            "type": "state_update",
            "data": panel,
        })
    inventory = await engine.get_inventory(user_id)
    await ws_manager.send_to_player(user_id, {
        "type": "inventory",
        "data": inventory,
    })


async def _broadcast_pvp_result(
    engine: GameEngine,
    ws_manager: ConnectionManager,
    result: dict,
):
    """向双方推送 PvP 状态，并在结束时回写副本流。"""
    session_id = str(result.get("session_id", "")).strip()
    session_obj = engine.pvp._sessions.get(session_id)
    if not session_obj:
        return

    a_id = session_obj.player_a_id
    b_id = session_obj.player_b_id
    if result.get("ended"):
        await ws_manager.send_to_player(a_id, {
            "type": "pvp_result",
            "data": result["pvp_state_a"],
        })
        await ws_manager.send_to_player(b_id, {
            "type": "pvp_result",
            "data": result["pvp_state_b"],
        })
        dungeon_result = await engine.dungeon.resolve_pvp_result(session_obj)
        await _push_player_snapshot(engine, ws_manager, a_id)
        await _push_player_snapshot(engine, ws_manager, b_id)
        if dungeon_result and session_obj.dungeon_owner_id:
            await ws_manager.send_to_player(session_obj.dungeon_owner_id, {
                "type": "action_result",
                "action": "dungeon_pvp_result",
                "data": dungeon_result,
            })
        engine.pvp.cleanup_session(session_id)
        return

    await ws_manager.send_to_player(a_id, {
        "type": "pvp_update",
        "data": {"pvp_state": result["pvp_state_a"]},
    })
    await ws_manager.send_to_player(b_id, {
        "type": "pvp_update",
        "data": {"pvp_state": result["pvp_state_b"]},
    })


async def _broadcast_sect_changed(
    ws_manager: ConnectionManager | None,
    exclude_user_id: str | None = None,
):
    """广播家族数据变更，让在线前端自行刷新家族相关面板。"""
    if not ws_manager:
        return
    try:
        await ws_manager.broadcast({"type": "sect_changed"}, exclude_user_id=exclude_user_id)
    except Exception:
        ws_logger.exception("骑砍世界：家族变更广播失败")


def _schedule_pvp_challenge_timeout(
    engine: GameEngine,
    ws_manager: ConnectionManager,
    session_id: str,
):
    """在应战倒计时结束后自动判定为放弃。"""

    async def _runner():
        session = engine.pvp._sessions.get(session_id)
        if not session:
            return
        delay = max(0.0, float(session.countdown_deadline or 0.0) - time.time())
        if delay > 0:
            await asyncio.sleep(delay)
        payload = engine.pvp.expire_challenge(session_id)
        if not payload:
            return
        await _broadcast_pvp_result(engine, ws_manager, payload)

    asyncio.create_task(_runner())


async def _handle_message(
    engine: GameEngine,
    user_id: str,
    msg: dict,
    command_prefix: str = "骑砍",
    ws_manager: ConnectionManager | None = None,
) -> dict | None:
    """处理客户端 WebSocket 消息。"""
    msg_type = msg.get("type", "")

    if engine.has_pending_death(user_id) and msg_type not in _PENDING_DEATH_ALLOWED_TYPES:
        return {
            "type": "error",
            "message": "道陨未决，请先完成携宝重生选择，当前无法执行其他操作",
        }

    if msg_type == "cultivate":
        result = await engine.cultivate(user_id)
        return {"type": "action_result", "action": "cultivate", "data": result}

    elif msg_type == "checkin":
        result = await engine.daily_checkin(user_id)
        return {"type": "action_result", "action": "checkin", "data": result}

    elif msg_type == "start_afk":
        minutes = msg.get("data", {}).get("minutes", 0)
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            return {"type": "error", "message": "请输入有效的分钟数"}
        result = await engine.start_afk_cultivate(user_id, minutes)
        return {"type": "action_result", "action": "start_afk", "data": result}

    elif msg_type == "collect_afk":
        result = await engine.collect_afk_cultivate(user_id)
        return {"type": "action_result", "action": "collect_afk", "data": result}

    elif msg_type == "cancel_afk":
        result = await engine.cancel_afk_cultivate(user_id)
        return {"type": "action_result", "action": "cancel_afk", "data": result}

    elif msg_type == "adventure":
        result = await engine.adventure(user_id)
        return {"type": "action_result", "action": "dungeon_start", "data": result}

    elif msg_type == "get_scenes":
        scenes = await engine.get_adventure_scenes()
        return {"type": "scenes", "data": scenes}

    elif msg_type == "get_announcements":
        announcements = await engine.get_active_announcements()
        return {"type": "announcements", "data": announcements}

    elif msg_type == "get_about_page":
        data = await engine.get_about_page()
        return {"type": "about_page", "data": data}

    elif msg_type == "get_spawn_origins":
        origins = get_all_spawn_origins()
        return {"type": "spawn_origins", "data": origins}

    elif msg_type == "get_spawn_locations":
        locations = get_all_spawn_locations()
        return {"type": "spawn_locations", "data": locations}

    elif msg_type == "get_spawn_locations_by_faction":
        faction = msg.get("data", {}).get("faction")
        if faction is None:
            return {"type": "error", "message": "请指定阵营"}
        locations = get_spawn_locations_by_faction(faction)
        return {"type": "spawn_locations", "data": locations}

    elif msg_type == "breakthrough":
        result = await engine.breakthrough(user_id)
        return {"type": "action_result", "action": "breakthrough", "data": result}

    elif msg_type == "set_spawn_origin":
        spawn_origin = msg.get("data", {}).get("origin", "")
        spawn_location = msg.get("data", {}).get("location", "")
        result = await engine.set_spawn_origin(user_id, spawn_origin, spawn_location)
        return {"type": "action_result", "action": "set_spawn_origin", "data": result}

    elif msg_type == "use_item":
        item_id = msg.get("data", {}).get("item_id", "")
        raw_count = msg.get("data", {}).get("count", 1)
        try:
            count = int(raw_count)
        except (TypeError, ValueError):
            return {"type": "error", "message": "使用数量必须是整数"}
        if count < 1:
            return {"type": "error", "message": "使用数量至少为1"}
        result = await engine.use_item_action(user_id, item_id, count)
        return {"type": "action_result", "action": "use_item", "data": result}

    elif msg_type == "confirm_replace_heart_method":
        data = msg.get("data", {})
        new_method_id = data.get("new_method_id", "")
        source_item_id = data.get("source_item_id", "")
        raw_convert = data.get("convert_to_value", False)
        if isinstance(raw_convert, str):
            convert_to_value = raw_convert.strip().lower() in {"1", "true", "yes", "on"}
        else:
            convert_to_value = bool(raw_convert)
        result = await engine.confirm_replace_heart_method(
            user_id,
            new_method_id,
            convert_to_value,
            source_item_id,
        )
        return {"type": "action_result", "action": "confirm_replace_heart_method", "data": result}

    elif msg_type == "get_panel":
        panel = await engine.get_panel(user_id)
        if panel:
            return {"type": "state_update", "data": panel}
        return {"type": "error", "message": "角色不存在"}

    # ==================== 地图相关 ====================
    elif msg_type == "get_map_locations":
        from ..game.map_system import TOWNS, CASTLES, VILLAGES, BANDIT_CAMPS, LocationType
        all_locations = {**TOWNS, **CASTLES, **VILLAGES, **BANDIT_CAMPS}
        locations = []
        for loc_id, loc in all_locations.items():
            try:
                type_val = int(loc.location_type)
                type_name = LocationType(type_val).name if 0 <= type_val <= 3 else str(type_val)
            except (ValueError, AttributeError):
                type_name = str(loc.location_type)
            locations.append({
                "location_id": loc.location_id,
                "name": loc.name,
                "type": type_name,
                "x": loc.x,
                "y": loc.y,
                "description": loc.description,
                "faction": str(loc.faction) if loc.faction else "",
            })
        return {"type": "map_locations", "data": locations}

    elif msg_type == "get_map_player":
        player = await engine.get_player(user_id)
        if not player:
            return {"type": "error", "message": "角色不存在"}
        map_state = player.map_state if hasattr(player, 'map_state') else None
        if not map_state:
            return {"type": "error", "message": "地图状态异常"}
        return {"type": "map_player", "data": {
            "location_id": map_state.current_location,
            "x": map_state.x,
            "y": map_state.y,
            "travel_destination": map_state.travel_destination,
            "travel_progress": map_state.travel_progress,
        }}

    elif msg_type == "get_map_players":
        # 使用位置管理器获取附近玩家 (默认150单位范围)
        nearby_radius = msg.get("data", {}).get("radius", 150)
        
        if ws_manager:
            # 先尝试从缓存获取附近玩家
            player_pos = ws_manager._position_manager.get_player(user_id)
            if player_pos:
                nearby = ws_manager._position_manager.get_nearby_players(user_id, nearby_radius)
            else:
                # 玩家不在缓存中，返回所有在线玩家
                nearby = ws_manager._position_manager.get_all_positions()
                nearby = [p for p in nearby if p["user_id"] != user_id]
        else:
            nearby = []
        
        return {"type": "map_players", "data": nearby}

    elif msg_type == "update_map_position":
        # 更新玩家位置 (节流处理)
        import time
        current_time = time.time()
        
        if not ws_manager:
            return None
        
        last_update = ws_manager._position_update_cooldowns.get(user_id, 0)
        
        if current_time - last_update < ws_manager._position_throttle:
            return None  # 忽略频繁更新
        
        ws_manager._position_update_cooldowns[user_id] = current_time
        
        # 获取玩家位置信息
        player = await engine.get_player(user_id)
        if not player:
            return {"type": "error", "message": "角色不存在"}
        
        map_state = player.map_state if hasattr(player, 'map_state') else None
        if not map_state:
            return {"type": "error", "message": "地图状态异常"}
        
        x = map_state.x
        y = map_state.y
        
        # 获取玩家图标
        icon = "👤"
        try:
            from ..game.renderer import get_player_display_icon
            icon = get_player_display_icon(player)
        except Exception:
            pass
        
        # 获取境界名称
        realm_name = "平民"
        try:
            from ..game.constants import get_realm_name
            realm_name = get_realm_name(player.realm)
        except Exception:
            pass
        
        # 更新位置缓存
        ws_manager._position_manager.update_position(
            user_id, player.name, x, y,
            player.realm, realm_name, icon
        )
        
        # 广播给附近玩家
        nearby_users = ws_manager._position_manager.broadcast_to_nearby(user_id, 150)
        
        broadcast_data = {
            "type": "player_position_update",
            "data": {
                "user_id": user_id,
                "name": player.name,
                "x": x,
                "y": y,
                "realm": player.realm,
                "realm_name": realm_name,
                "icon": icon,
            }
        }
        
        for uid in nearby_users:
            if uid != user_id:
                await ws_manager.send_to_player(uid, broadcast_data)
        
        return {"type": "position_updated", "data": {"x": x, "y": y}}

    elif msg_type == "map_travel":
        destination = msg.get("data", {}).get("destination", "")
        from ..game.map_system import TOWNS, CASTLES, VILLAGES, BANDIT_CAMPS, calculate_map_travel_time
        all_locations = {**TOWNS, **CASTLES, **VILLAGES, **BANDIT_CAMPS}
        dest_loc = all_locations.get(destination)
        if not dest_loc:
            return {"type": "error", "message": "目的地不存在"}
        
        player = await engine.get_player(user_id)
        if not player:
            return {"type": "error", "message": "角色不存在"}
        
        map_state = player.map_state if hasattr(player, 'map_state') else None
        if not map_state:
            return {"type": "error", "message": "地图状态异常"}
        
        map_state.travel_destination = destination
        map_state.travel_progress = 0
        map_state.travel_time = calculate_map_travel_time(
            map_state.x, map_state.y, dest_loc.x, dest_loc.y
        )
        
        return {"type": "action_result", "action": "map_travel", "data": {
            "success": True,
            "message": f"开始前往{dest_loc.name}，预计{map_state.travel_time}秒到达"
        }}

    elif msg_type == "map_arrive":
        player = await engine.get_player(user_id)
        if not player:
            return {"type": "error", "message": "角色不存在"}
        
        map_state = player.map_state if hasattr(player, 'map_state') else None
        if not map_state or not map_state.travel_destination:
            return {"type": "error", "message": "没有在旅行中"}
        
        from ..game.map_system import arrive_at_location
        result = arrive_at_location(map_state, map_state.travel_destination)
        
        if result.get("success"):
            await engine._save_player(player)
        
        return {"type": "action_result", "action": "map_arrive", "data": result}

    elif msg_type == "enter_location":
        location_id = msg.get("data", {}).get("location_id", "")
        if not location_id:
            return {"type": "error", "message": "需要location_id"}
        result = await engine.enter_location(user_id, location_id)
        return {"type": "action_result", "action": "enter_location", "data": result}

    elif msg_type == "leave_location":
        result = await engine.leave_location(user_id)
        return {"type": "action_result", "action": "leave_location", "data": result}

    elif msg_type == "get_town_menu":
        location_id = msg.get("data", {}).get("location_id", "")
        if not location_id:
            return {"type": "error", "message": "需要location_id"}
        result = await engine.get_town_menu(user_id, location_id)
        return {"type": "town_menu", "data": result}

    elif msg_type == "town_menu_action":
        data = msg.get("data", {})
        action_id = data.get("action_id", "")
        location_id = data.get("location_id", "")
        npc_id = data.get("npc_id", "")
        if not action_id or not location_id:
            return {"type": "error", "message": "需要action_id和location_id"}
        result = await engine.town_menu_action(user_id, action_id, location_id, npc_id)
        return {"type": "action_result", "action": "town_menu_action", "data": result}

    elif msg_type == "get_village_industries":
        village_id = msg.get("data", {}).get("village_id", "")
        if not village_id:
            return {"type": "error", "message": "需要village_id"}
        result = await engine.get_village_industries(user_id, village_id)
        return {"type": "action_result", "action": "get_village_industries", "data": result}

    elif msg_type == "build_industry":
        data = msg.get("data", {})
        village_id = data.get("village_id", "")
        industry_id = data.get("industry_id", "")
        if not village_id or not industry_id:
            return {"type": "error", "message": "需要village_id和industry_id"}
        result = await engine.build_village_industry(user_id, village_id, industry_id)
        return {"type": "action_result", "action": "build_industry", "data": result}

    elif msg_type == "upgrade_industry":
        data = msg.get("data", {})
        village_id = data.get("village_id", "")
        industry_id = data.get("industry_id", "")
        if not village_id or not industry_id:
            return {"type": "error", "message": "需要village_id和industry_id"}
        result = await engine.upgrade_village_industry(user_id, village_id, industry_id)
        return {"type": "action_result", "action": "upgrade_industry", "data": result}

    elif msg_type == "collect_industry_income":
        village_id = msg.get("data", {}).get("village_id", "")
        if not village_id:
            return {"type": "error", "message": "需要village_id"}
        result = await engine.collect_industry_income(user_id, village_id)
        return {"type": "action_result", "action": "collect_industry_income", "data": result}

    elif msg_type == "repair_industry":
        data = msg.get("data", {})
        village_id = data.get("village_id", "")
        industry_id = data.get("industry_id", "")
        if not village_id or not industry_id:
            return {"type": "error", "message": "需要village_id和industry_id"}
        result = await engine.repair_industry_action(user_id, village_id, industry_id)
        return {"type": "action_result", "action": "repair_industry", "data": result}

    elif msg_type == "rest_at_settlement":
        result = await engine.rest_at_settlement(user_id)
        return {"type": "action_result", "action": "rest_at_settlement", "data": result}

    elif msg_type == "heal_troops":
        result = await engine.heal_troops(user_id)
        return {"type": "action_result", "action": "heal_troops", "data": result}

    elif msg_type == "tournament_combat":
        data = msg.get("data", {})
        result = await engine.tournament_combat_action(user_id, data.get("action", "attack"), data)
        return {"type": "action_result", "action": "tournament_combat", "data": result}

    elif msg_type == "start_npc_dialog":
        npc_id = msg.get("data", {}).get("npc_id", "")
        if not npc_id:
            return {"type": "error", "message": "需要npc_id"}
        result = await engine.start_npc_dialog(user_id, npc_id)
        return {"type": "action_result", "action": "start_npc_dialog", "data": result}

    elif msg_type == "give_gift_to_npc":
        npc_id = msg.get("data", {}).get("npc_id", "")
        gift_id = msg.get("data", {}).get("gift_id", "")
        if not npc_id or not gift_id:
            return {"type": "error", "message": "需要npc_id和gift_id"}
        result = await engine.give_gift(user_id, npc_id, gift_id)
        return {"type": "action_result", "action": "give_gift_to_npc", "data": result}

    elif msg_type == "get_gift_list":
        result = await engine.get_gift_list(user_id)
        return {"type": "gift_list", "data": result}

    elif msg_type == "get_rankings":
        return {"type": "rankings_data", "data": _build_rankings_payload(engine, user_id)}

    elif msg_type == "get_inventory":
        inv = await engine.get_inventory(user_id)
        return {"type": "inventory", "data": inv}

    elif msg_type == "equip":
        equip_id = msg.get("data", {}).get("equip_id", "")
        result = await engine.equip_action(user_id, equip_id)
        return {"type": "action_result", "action": "equip", "data": result}

    elif msg_type == "unequip":
        slot = msg.get("data", {}).get("slot", "")
        result = await engine.unequip_action(user_id, slot)
        return {"type": "action_result", "action": "unequip", "data": result}

    elif msg_type == "equip_mount":
        mount_id = msg.get("data", {}).get("mount_id", "")
        result = await engine.equip_mount_action(user_id, mount_id)
        return {"type": "action_result", "action": "equip_mount", "data": result}

    elif msg_type == "unequip_mount":
        result = await engine.unequip_mount_action(user_id)
        return {"type": "action_result", "action": "unequip_mount", "data": result}

    elif msg_type == "equip_mount_item":
        equip_id = msg.get("data", {}).get("equip_id", "")
        result = await engine.equip_mount_item_action(user_id, equip_id)
        return {"type": "action_result", "action": "equip_mount_item", "data": result}

    elif msg_type == "unequip_mount_item":
        slot = msg.get("data", {}).get("slot", "")
        result = await engine.unequip_mount_item_action(user_id, slot)
        return {"type": "action_result", "action": "unequip_mount_item", "data": result}

    elif msg_type == "learn_heart_method":
        return {
            "type": "action_result",
            "action": "learn_heart_method",
            "data": {
                "success": False,
                "message": "已取消直接选择被动技能，请通过历练掉落秘籍并在背包中使用。",
            },
        }

    elif msg_type == "get_heart_methods":
        return {
            "type": "heart_methods",
            "data": {
                "success": False,
                "methods": [],
                "message": "已取消直接选择被动技能，请通过历练掉落秘籍并在背包中使用。",
            },
        }

    elif msg_type == "get_bind_key":
        if engine.auth:
            key = await engine.auth.create_bind_key(user_id)
            return {
                "type": "bind_key",
                "data": {
                    "key": key,
                    "message": f"请在QQ中发送：/{command_prefix} 登录 {key}",
                },
            }
        return {"type": "error", "message": "认证系统未启用"}

    elif msg_type == "recycle":
        item_id = msg.get("data", {}).get("item_id", "")
        raw_count = msg.get("data", {}).get("count", 1)
        try:
            count = int(raw_count)
        except (TypeError, ValueError):
            return {"type": "error", "message": "回收数量必须是整数"}
        if count < 1:
            return {"type": "error", "message": "回收数量至少为1"}
        result = await engine.recycle_action(user_id, item_id, count)
        return {"type": "action_result", "action": "recycle", "data": result}

    # ── 音效系统 ─────────────────────────────────────────────
    elif msg_type == "get_audio_config":
        data = await engine.get_audio_config()
        return {"type": "audio_config", "data": data}

    elif msg_type == "update_audio_settings":
        data = msg.get("data", {})
        result = await engine.update_audio_settings(
            enabled=data.get("enabled"),
            music_enabled=data.get("music_enabled"),
            sound_volume=data.get("sound_volume"),
            music_volume=data.get("music_volume"),
        )
        return {"type": "action_result", "action": "update_audio_settings", "data": result}

    # ── 天机阁（商店） ──────────────────────────────────────
    elif msg_type == "get_shop":
        data = await engine.shop_get_items(user_id)
        return {"type": "shop_data", "data": data}

    elif msg_type == "shop_buy":
        item_id = msg.get("data", {}).get("item_id", "")
        raw_qty = msg.get("data", {}).get("quantity", 1)
        try:
            quantity = int(raw_qty)
        except (TypeError, ValueError):
            return {"type": "error", "message": "购买数量必须是整数"}
        if quantity < 1:
            return {"type": "error", "message": "购买数量至少为1"}
        result = await engine.shop_buy(user_id, item_id, quantity)
        return {"type": "action_result", "action": "shop_buy", "data": result}

    # ── 铁匠铺 ──────────────────────────────────────────────
    elif msg_type == "blacksmith_info":
        data = msg.get("data", {})
        item_id = data.get("item_id", "")
        if not item_id:
            return {"type": "error", "message": "请指定装备"}
        result = await engine.get_item_prefix_info(user_id, item_id)
        return {"type": "blacksmith_info", "data": result}

    elif msg_type == "blacksmith_repair":
        item_id = msg.get("data", {}).get("item_id", "")
        if not item_id:
            return {"type": "error", "message": "请指定装备"}
        result = await engine.blacksmith_repair_prefix(user_id, item_id)
        return {"type": "action_result", "action": "blacksmith_repair", "data": result}

    elif msg_type == "blacksmith_enhance":
        data = msg.get("data", {})
        item_id = data.get("item_id", "")
        target_quality = data.get("target_quality", "good")
        if not item_id:
            return {"type": "error", "message": "请指定装备"}
        result = await engine.blacksmith_enhance_prefix(user_id, item_id, target_quality)
        return {"type": "action_result", "action": "blacksmith_enhance", "data": result}

    # ── 坊市 ──────────────────────────────────────────────
    elif msg_type == "market_list":
        data = msg.get("data", {})
        item_id = data.get("item_id", "")
        try:
            quantity = int(data.get("quantity", 0))
            unit_price = int(data.get("unit_price", 0))
        except (TypeError, ValueError):
            return {"type": "error", "message": "数量和价格必须是整数"}
        result = await engine.market_list(user_id, item_id, quantity, unit_price)
        return {"type": "action_result", "action": "market_list", "data": result}

    elif msg_type == "market_buy":
        listing_id = msg.get("data", {}).get("listing_id", "")
        result = await engine.market_buy(user_id, listing_id)
        return {"type": "action_result", "action": "market_buy", "data": result}

    elif msg_type == "market_cancel":
        listing_id = msg.get("data", {}).get("listing_id", "")
        result = await engine.market_cancel(user_id, listing_id)
        return {"type": "action_result", "action": "market_cancel", "data": result}

    elif msg_type == "get_market":
        page = msg.get("data", {}).get("page", 1)
        try:
            page = int(page)
        except (TypeError, ValueError):
            page = 1
        if ws_manager:
            ws_manager.set_market_watch(user_id, enabled=True, tab="browse", page=page)
        data = await engine.market_get_listings(page, page_size=9)
        return {"type": "market_data", "data": data}

    elif msg_type == "get_my_listings":
        if ws_manager:
            ws_manager.set_market_watch(user_id, enabled=True, tab="my")
        listings = await engine.market_get_my_listings(user_id)
        return {"type": "my_listings", "data": {"listings": listings}}

    elif msg_type == "market_watch":
        data = msg.get("data", {})
        raw_enabled = data.get("enabled", False)
        if isinstance(raw_enabled, str):
            enabled = raw_enabled.strip().lower() in {"1", "true", "yes", "on"}
        else:
            enabled = bool(raw_enabled)
        tab = str(data.get("tab", "")).strip().lower()
        page = data.get("page", 1)
        if ws_manager:
            ws_manager.set_market_watch(user_id, enabled=enabled, tab=tab, page=page)
        return {"type": "noop"}

    elif msg_type == "market_clear_history":
        include_expired = bool(msg.get("data", {}).get("include_expired", False))
        result = await engine.market_clear_my_history(user_id, include_expired=include_expired)
        return {"type": "action_result", "action": "market_clear_history", "data": result}

    elif msg_type == "market_fee_preview":
        data = msg.get("data", {})
        item_id = data.get("item_id", "")
        try:
            quantity = int(data.get("quantity", 0))
            unit_price = int(data.get("unit_price", 0))
        except (TypeError, ValueError):
            return {"type": "error", "message": "数量和价格必须是整数"}
        preview = await engine.market_fee_preview(item_id, quantity, unit_price)
        return {"type": "fee_preview", "data": preview}

    # ── 世界频道 ──────────────────────────────────────────
    elif msg_type == "world_chat_send":
        content = str(msg.get("data", {}).get("content", "")).strip()
        if not content:
            return {"type": "world_chat_blocked", "data": {"reason": "消息不能为空"}}
        if len(content) > WORLD_CHAT_MAX_LEN:
            return {"type": "world_chat_blocked", "data": {"reason": f"消息不能超过{WORLD_CHAT_MAX_LEN}字"}}
        if not _RE_CHINESE_ONLY.match(content):
            return {"type": "world_chat_blocked", "data": {"reason": "世界频道暂时只支持中文和数字"}}
        if not ws_manager:
            return {"type": "world_chat_blocked", "data": {"reason": "服务不可用"}}
        # 冷却检查
        ok, remaining = ws_manager.check_chat_cooldown(user_id)
        if not ok:
            return {"type": "world_chat_blocked", "data": {"reason": f"发言冷却中，请等待{remaining:.0f}秒"}}
        # AI 内容审核
        review = await _review_chat_content(engine, content)
        if not review["allow"]:
            return {"type": "world_chat_blocked", "data": {"reason": review["reason"]}}
        # 获取玩家名
        player = await engine.get_player(user_id)
        player_name = player.name if player else "未知"
        player_realm = get_realm_name(player.realm, player.sub_realm) if player else ""
        # 获取家族名
        sect_name = ""
        sect_role = ""
        sect_role_name = ""
        membership = await engine._data_manager.load_player_sect(user_id)
        if membership:
            sect_role = membership.get("role", "")
            sect_role_name = ROLE_NAMES.get(sect_role, sect_role)
            sect = await engine._data_manager.load_sect(membership["sect_id"])
            if sect:
                sect_name = sect["name"]
        chat_msg = {
            "user_id": user_id,
            "name": player_name,
            "realm": player_realm,
            "sect_name": sect_name,
            "sect_role": sect_role,
            "sect_role_name": sect_role_name,
            "content": content,
            "time": time.time(),
        }
        ws_manager.record_chat_send(user_id)
        await ws_manager.add_chat_message(chat_msg)
        await ws_manager.broadcast_chat(chat_msg)
        return {"type": "noop"}

    elif msg_type == "get_world_chat_history":
        if not ws_manager:
            return {"type": "world_chat_history", "data": []}
        return {"type": "world_chat_history", "data": await ws_manager.get_world_chat_history()}

    # ── 死亡保留确认 ─────────────────────────────────────
    elif msg_type == "death_confirm_keep":
        kept_ids = msg.get("data", {}).get("kept_ids", [])
        if not isinstance(kept_ids, list):
            return {"type": "error", "message": "kept_ids 必须是列表"}
        result = await engine.confirm_death(user_id, kept_ids)
        return {"type": "action_result", "action": "death_confirm_keep", "data": result}

    # ── 战技遗忘 ─────────────────────────────────────────
    elif msg_type == "forget_gongfa":
        slot = msg.get("data", {}).get("slot", "")
        result = await engine.forget_gongfa(user_id, slot)
        return {"type": "action_result", "action": "forget_gongfa", "data": result}

    # ── 副本系统 ─────────────────────────────────────────
    elif msg_type == "dungeon_start":
        result = await engine.adventure(user_id)
        return {"type": "action_result", "action": "dungeon_start", "data": result}

    elif msg_type == "dungeon_advance":
        player = await engine.get_player(user_id)
        if not player:
            return {"type": "error", "message": "角色不存在"}
        result = await engine.dungeon.advance(player)
        if result.get("success"):
            completed_tasks = await engine._auto_update_task_progress(user_id, "adventure")
            if completed_tasks:
                result["task_completed"] = completed_tasks
        if result.get("pvp_notice") and ws_manager and result.get("pvp_opponent_id"):
            await ws_manager.send_to_player(result["pvp_opponent_id"], {
                "type": "pvp_challenge_notice",
                    "data": {
                        "session_id": result.get("pvp_session_id"),
                        "countdown_deadline": result["pvp_notice"].get("countdown_deadline", 0),
                        "challenger_name": result["pvp_notice"].get("challenger_name", "未知修士"),
                        "layer_name": result["pvp_notice"].get("layer_name", "秘境"),
                        "source": "dungeon",
                        "message": "请在 10 秒内决定是否应战；若拒绝或超时，对方将直接夺得本层机缘。",
                    },
                })
            _schedule_pvp_challenge_timeout(engine, ws_manager, result["pvp_session_id"])
        return {"type": "action_result", "action": "dungeon_advance", "data": result}

    elif msg_type == "dungeon_combat":
        player = await engine.get_player(user_id)
        if not player:
            return {"type": "error", "message": "角色不存在"}
        action = msg.get("data", {}).get("action", "attack")
        data = msg.get("data", {})
        result = await engine.dungeon.combat_action(player, action, data)
        return {"type": "action_result", "action": "dungeon_combat", "data": result}

    elif msg_type == "dungeon_exit":
        player = await engine.get_player(user_id)
        if not player:
            return {"type": "error", "message": "角色不存在"}
        result = await engine.dungeon.exit_dungeon(player)
        return {"type": "action_result", "action": "dungeon_exit", "data": result}

    elif msg_type == "dungeon_state":
        session = engine.dungeon.get_session(user_id)
        if session:
            return {"type": "dungeon_state", "data": session.to_dict()}
        return {"type": "dungeon_state", "data": None}

    # ── PvP 系统 ──────────────────────────────────────────
    elif msg_type == "pvp_match":
        return {
            "type": "error",
            "message": "已取消主动切磋，请在副本中遭遇在线玩家",
        }

    elif msg_type == "pvp_action":
        session_id = msg.get("data", {}).get("session_id", "")
        action = msg.get("data", {}).get("action", {})
        player = await engine.get_player(user_id)
        result = await engine.pvp.submit_action(session_id, user_id, action, player)
        if result.get("pvp_state"):
            return {"type": "pvp_update", "data": result}
        if result.get("resolved") and ws_manager:
            await _broadcast_pvp_result(engine, ws_manager, result)
            if result.get("winner_id") == user_id:
                completed_tasks = await engine._auto_update_task_progress(user_id, "pvp")
                if completed_tasks:
                    result["task_completed"] = completed_tasks
            return {"type": "noop"}
        return {"type": "action_result", "action": "pvp_action", "data": result}

    elif msg_type == "pvp_challenge_response":
        session_id = msg.get("data", {}).get("session_id", "")
        accept = bool(msg.get("data", {}).get("accept", False))
        player = await engine.get_player(user_id)
        result = engine.pvp.respond_challenge(session_id, user_id, accept, player)
        if result.get("started") and ws_manager:
            session = engine.pvp.get_session_for_player(user_id)
            if session:
                await ws_manager.send_to_player(session.player_a_id, {
                    "type": "pvp_start",
                    "data": result["pvp_state_a"],
                })
                await ws_manager.send_to_player(session.player_b_id, {
                    "type": "pvp_start",
                    "data": result["pvp_state_b"],
                })
                await _push_player_snapshot(engine, ws_manager, session.player_a_id)
                await _push_player_snapshot(engine, ws_manager, session.player_b_id)
            return {"type": "noop"}
        if result.get("ended") and ws_manager:
            await _broadcast_pvp_result(engine, ws_manager, result)
            return {"type": "noop"}
        return {"type": "action_result", "action": "pvp_challenge_response", "data": result}

    elif msg_type == "pvp_flee_offer":
        session_id = msg.get("data", {}).get("session_id", "")
        items = msg.get("data", {}).get("items", [])
        player = await engine.get_player(user_id)
        result = await engine.pvp.submit_flee_request(session_id, user_id, items, player)
        if result.get("pvp_state_a") and result.get("pvp_state_b") and ws_manager:
            await _broadcast_pvp_result(engine, ws_manager, result)
            return {"type": "noop"}
        return {"type": "action_result", "action": "pvp_flee_offer", "data": result}

    elif msg_type == "pvp_flee_response":
        session_id = msg.get("data", {}).get("session_id", "")
        accept = bool(msg.get("data", {}).get("accept", False))
        player = await engine.get_player(user_id)
        result = await engine.pvp.respond_flee_request(session_id, user_id, accept, player)
        if result.get("pvp_state_a") and result.get("pvp_state_b") and ws_manager:
            await _broadcast_pvp_result(engine, ws_manager, result)
            return {"type": "noop"}
        return {"type": "action_result", "action": "pvp_flee_response", "data": result}

    elif msg_type == "pvp_state":
        session = engine.pvp.get_session_for_player(user_id)
        if session:
            return {"type": "pvp_state", "data": session.to_dict(user_id)}
        return {"type": "pvp_state", "data": None}

    # ── 家族系统 ─────────────────────────────────────────

    elif msg_type == "sect_create":
        data = msg.get("data", {})
        name = str(data.get("name", "")).strip()
        description = str(data.get("description", "")).strip()
        if not name:
            return {"type": "error", "message": "请输入家族名称"}
        result = await engine.sect_create(user_id, name, description)
        if result.get("success"):
            await _broadcast_sect_changed(ws_manager, exclude_user_id=user_id)
        return {"type": "action_result", "action": "sect_create", "data": result}

    elif msg_type == "sect_list":
        page = msg.get("data", {}).get("page", 1)
        try:
            page = int(page)
        except (TypeError, ValueError):
            page = 1
        data = await engine.sect_list(page, page_size=10)
        return {"type": "sect_list_data", "data": data}

    elif msg_type == "sect_my":
        data = await engine.sect_my(user_id)
        return {"type": "sect_my_data", "data": data}

    elif msg_type == "sect_detail":
        sect_id = msg.get("data", {}).get("sect_id", "")
        if not sect_id:
            return {"type": "error", "message": "缺少家族ID"}
        data = await engine.sect_detail(sect_id)
        return {"type": "sect_detail_data", "data": data}

    elif msg_type == "sect_join":
        sect_id = msg.get("data", {}).get("sect_id", "")
        if not sect_id:
            return {"type": "error", "message": "缺少家族ID"}
        result = await engine.sect_join(user_id, sect_id)
        if result.get("success"):
            await _broadcast_sect_changed(ws_manager, exclude_user_id=user_id)
        return {"type": "action_result", "action": "sect_join", "data": result}

    elif msg_type == "sect_leave":
        result = await engine.sect_leave(user_id)
        if result.get("success"):
            await _broadcast_sect_changed(ws_manager, exclude_user_id=user_id)
        return {"type": "action_result", "action": "sect_leave", "data": result}

    elif msg_type == "sect_kick":
        target_id = msg.get("data", {}).get("target_id", "")
        if not target_id:
            return {"type": "error", "message": "缺少目标玩家ID"}
        result = await engine.sect_kick(user_id, target_id)
        if result.get("success"):
            await _broadcast_sect_changed(ws_manager, exclude_user_id=user_id)
        return {"type": "action_result", "action": "sect_kick", "data": result}

    elif msg_type == "sect_set_role":
        data = msg.get("data", {})
        target_id = data.get("target_id", "")
        role = data.get("role", "")
        if not target_id or not role:
            return {"type": "error", "message": "缺少目标玩家或身份"}
        result = await engine.sect_set_role(user_id, target_id, role)
        if result.get("success"):
            await _broadcast_sect_changed(ws_manager, exclude_user_id=user_id)
        return {"type": "action_result", "action": "sect_set_role", "data": result}

    elif msg_type == "sect_update_info":
        data = msg.get("data", {})
        result = await engine.sect_update_info(user_id, data)
        if result.get("success"):
            await _broadcast_sect_changed(ws_manager, exclude_user_id=user_id)
        return {"type": "action_result", "action": "sect_update_info", "data": result}

    elif msg_type == "sect_transfer":
        target_id = msg.get("data", {}).get("target_id", "")
        if not target_id:
            return {"type": "error", "message": "缺少目标玩家ID"}
        result = await engine.sect_transfer(user_id, target_id)
        if result.get("success"):
            await _broadcast_sect_changed(ws_manager, exclude_user_id=user_id)
        return {"type": "action_result", "action": "sect_transfer", "data": result}

    elif msg_type == "sect_disband":
        result = await engine.sect_disband(user_id)
        if result.get("success"):
            await _broadcast_sect_changed(ws_manager, exclude_user_id=user_id)
        return {"type": "action_result", "action": "sect_disband", "data": result}

    # ── 家族仓库 ──────────────────────────────────────────

    elif msg_type == "sect_warehouse_list":
        data = await engine.sect_warehouse_list(user_id)
        return {"type": "sect_warehouse_data", "data": data}

    elif msg_type == "sect_warehouse_deposit":
        d = msg.get("data", {})
        item_id = str(d.get("item_id", "")).strip()
        if not item_id:
            return {"type": "error", "message": "缺少物品ID"}
        try:
            count = max(1, int(d.get("count", 1)))
        except (TypeError, ValueError):
            count = 1
        result = await engine.sect_warehouse_deposit(user_id, item_id, count)
        if result.get("success"):
            await _broadcast_sect_changed(ws_manager, exclude_user_id=user_id)
        return {"type": "action_result", "action": "sect_warehouse_deposit", "data": result}

    elif msg_type == "sect_warehouse_exchange":
        d = msg.get("data", {})
        item_id = str(d.get("item_id", "")).strip()
        if not item_id:
            return {"type": "error", "message": "缺少物品ID"}
        try:
            count = max(1, int(d.get("count", 1)))
        except (TypeError, ValueError):
            count = 1
        result = await engine.sect_warehouse_exchange(user_id, item_id, count)
        if result.get("success"):
            await _broadcast_sect_changed(ws_manager, exclude_user_id=user_id)
        return {"type": "action_result", "action": "sect_warehouse_exchange", "data": result}

    elif msg_type == "sect_contribution_rules":
        data = await engine.sect_get_contribution_rules(user_id)
        return {"type": "sect_contribution_rules_data", "data": data}

    elif msg_type == "sect_set_submit_rule":
        d = msg.get("data", {})
        quality_key = str(d.get("quality_key", "")).strip()
        if not quality_key:
            return {"type": "error", "message": "缺少品质分类"}
        try:
            points = max(0, int(d.get("points", 0)))
        except (TypeError, ValueError):
            return {"type": "error", "message": "贡献点数必须为整数"}
        result = await engine.sect_set_submit_rule(user_id, quality_key, points)
        return {"type": "action_result", "action": "sect_set_submit_rule", "data": result}

    elif msg_type == "sect_set_exchange_rule":
        d = msg.get("data", {})
        target_key = str(d.get("target_key", "")).strip()
        if not target_key:
            return {"type": "error", "message": "缺少目标键"}
        try:
            points = max(0, int(d.get("points", 0)))
        except (TypeError, ValueError):
            return {"type": "error", "message": "贡献点数必须为整数"}
        raw_is_item = d.get("is_item", False)
        is_item = raw_is_item is True or (isinstance(raw_is_item, str) and raw_is_item.lower() in ("true", "1"))
        result = await engine.sect_set_exchange_rule(user_id, target_key, points, is_item=is_item)
        return {"type": "action_result", "action": "sect_set_exchange_rule", "data": result}

    # ── 家族任务 API ──────────────────────────────────────
    elif msg_type == "sect_create_task":
        d = msg.get("data", {})
        title = str(d.get("title", "")).strip()
        if not title:
            return {"type": "error", "message": "请输入任务标题"}
        description = str(d.get("description", "")).strip()
        task_type = str(d.get("task_type", "")).strip()
        if not task_type:
            return {"type": "error", "message": "请选择任务类型"}
        try:
            target_count = max(1, int(d.get("target_count", 1)))
            reward_points = max(0, int(d.get("reward_points", 0)))
            reward_item_count = max(0, int(d.get("reward_item_count", 0)))
            expires_hours = max(0, int(d.get("expires_hours", 24)))
        except (TypeError, ValueError):
            return {"type": "error", "message": "参数必须是整数"}
        result = await engine.sect_create_task(
            user_id=user_id,
            title=title,
            description=description,
            task_type=task_type,
            target_count=target_count,
            reward_points=reward_points,
            reward_item_id=d.get("reward_item_id", ""),
            reward_item_count=reward_item_count,
            expires_hours=expires_hours,
        )
        return {"type": "action_result", "action": "sect_create_task", "data": result}

    elif msg_type == "sect_get_tasks":
        d = msg.get("data", {})
        status = str(d.get("status", "")).strip()
        result = await engine.sect_get_tasks(user_id, status)
        return {"type": "sect_tasks_data", "data": result}

    elif msg_type == "sect_accept_task":
        d = msg.get("data", {})
        try:
            task_id = int(d.get("task_id", 0))
        except (TypeError, ValueError):
            return {"type": "error", "message": "任务ID无效"}
        if task_id <= 0:
            return {"type": "error", "message": "请指定任务"}
        result = await engine.sect_accept_task(user_id, task_id)
        return {"type": "action_result", "action": "sect_accept_task", "data": result}

    elif msg_type == "sect_update_task_progress":
        d = msg.get("data", {})
        try:
            task_id = int(d.get("task_id", 0))
            progress = max(1, int(d.get("progress", 1)))
        except (TypeError, ValueError):
            return {"type": "error", "message": "参数必须是整数"}
        if task_id <= 0:
            return {"type": "error", "message": "请指定任务"}
        result = await engine.sect_update_task_progress(user_id, task_id, progress)
        return {"type": "action_result", "action": "sect_update_task_progress", "data": result}

    elif msg_type == "sect_cancel_task":
        d = msg.get("data", {})
        try:
            task_id = int(d.get("task_id", 0))
        except (TypeError, ValueError):
            return {"type": "error", "message": "任务ID无效"}
        if task_id <= 0:
            return {"type": "error", "message": "请指定任务"}
        result = await engine.sect_cancel_task(user_id, task_id)
        return {"type": "action_result", "action": "sect_cancel_task", "data": result}

    # ── 骑砍技能树 API ──────────────────────────────────

    elif msg_type == "get_skill_trees":
        """获取所有技能树信息"""
        player = await engine.get_player(user_id)
        if not player:
            return {"type": "error", "message": "角色不存在"}
        
        skill_trees = mb_skills.get_all_skill_trees()
        trees_data = []
        
        for tree_id, tree_info in skill_trees.items():
            skill_ids = tree_info["skills"]
            skills_detail = []
            for skill_id in skill_ids:
                from ..game.constants import HEART_METHOD_REGISTRY, get_heart_method_bonus
                hm = HEART_METHOD_REGISTRY.get(skill_id)
                if hm:
                    # 检查是否满足学习条件
                    can_learn = player.realm >= hm.realm
                    is_equipped = player.heart_method == skill_id
                    
                    # 计算当前熟练度加成
                    mastery = player.heart_method_mastery if is_equipped else 0
                    bonus = get_heart_method_bonus(skill_id, mastery)
                    
                    skills_detail.append({
                        "method_id": hm.method_id,
                        "name": hm.name,
                        "description": hm.description,
                        "quality": hm.quality,
                        "quality_name": {0: "普通", 1: "稀有", 2: "传说"}.get(hm.quality, "普通"),
                        "realm_required": hm.realm,
                        "realm_name": {0: "平民", 1: "新兵", 2: "老兵", 3: "骑士", 4: "骑士长", 5: "领主", 6: "男爵", 7: "子爵", 8: "伯爵"}.get(hm.realm, "未知"),
                        "exp_multiplier": hm.exp_multiplier,
                        "attack_bonus": bonus["attack_bonus"],
                        "defense_bonus": bonus["defense_bonus"],
                        "dao_yun_rate": hm.dao_yun_rate,
                        "mastery_exp": hm.mastery_exp,
                        "can_learn": can_learn,
                        "is_equipped": is_equipped,
                        "current_mastery": player.heart_method_mastery if is_equipped else 0,
                        "current_exp": player.heart_method_exp if is_equipped else 0,
                    })
            
            trees_data.append({
                "tree_id": tree_id,
                "name": tree_info["name"],
                "name_en": tree_info.get("name_en", ""),
                "desc": tree_info["desc"],
                "stat": tree_info["stat"],
                "skills": skills_detail,
            })
        
        return {"type": "skill_trees_data", "data": trees_data}

    elif msg_type == "get_combat_skills":
        """获取所有战斗技能信息"""
        player = await engine.get_player(user_id)
        if not player:
            return {"type": "error", "message": "角色不存在"}
        
        from ..game.constants import GONGFA_REGISTRY, get_gongfa_bonus
        
        # 按前缀分组
        skill_groups = {
            "charge": {"name": "冲锋", "name_en": "Charge", "skills": []},
            "shield_bash": {"name": "盾击", "name_en": "Shield Bash", "skills": []},
            "battle_cry": {"name": "战吼", "name_en": "Battle Cry", "skills": []},
            "berserk": {"name": "狂暴", "name_en": "Berserk", "skills": []},
            "feint": {"name": "虚晃", "name_en": "Feint", "skills": []},
            "other": {"name": "其他技能", "name_en": "Other Skills", "skills": []},
        }
        
        for gf_id, gf in GONGFA_REGISTRY.items():
            if gf_id.startswith("mb_gf_"):
                # 判断所属技能树
                if "charge" in gf_id:
                    group_key = "charge"
                elif "sb_" in gf_id:
                    group_key = "shield_bash"
                elif "bc_" in gf_id:
                    group_key = "battle_cry"
                elif "bk_" in gf_id:
                    group_key = "berserk"
                elif "ft_" in gf_id:
                    group_key = "feint"
                else:
                    group_key = "other"
                
                # 检查装备状态
                equipped_slot = None
                current_mastery = 0
                current_exp = 0
                for slot in ["gongfa_1", "gongfa_2", "gongfa_3"]:
                    if getattr(player, slot, None) == gf_id:
                        equipped_slot = slot
                        current_mastery = getattr(player, f"{slot}_mastery", 0)
                        current_exp = getattr(player, f"{slot}_exp", 0)
                        break
                
                bonus = get_gongfa_bonus(gf_id, current_mastery, player.realm)
                
                skill_data = {
                    "gongfa_id": gf.gongfa_id,
                    "name": gf.name,
                    "description": gf.description,
                    "tier": gf.tier,
                    "tier_name": {0: "初级", 1: "中级", 2: "高级", 3: "大师级"}.get(gf.tier, "未知"),
                    "attack_bonus": gf.attack_bonus,
                    "defense_bonus": gf.defense_bonus,
                    "hp_regen": gf.hp_regen,
                    "lingqi_regen": gf.lingqi_regen,
                    "lingqi_cost": gf.lingqi_cost,
                    "mastery_exp": gf.mastery_exp,
                    "equipped_slot": equipped_slot,
                    "current_mastery": current_mastery,
                    "current_exp": current_exp,
                }
                skill_groups[group_key]["skills"].append(skill_data)
        
        return {"type": "combat_skills_data", "data": skill_groups}

    elif msg_type == "get_available_skills":
        """获取当前爵位可学习的技能"""
        player = await engine.get_player(user_id)
        if not player:
            return {"type": "error", "message": "角色不存在"}
        
        from ..game.constants import HEART_METHOD_REGISTRY, get_heart_method_bonus
        
        available = []
        for hm_id, hm in HEART_METHOD_REGISTRY.items():
            if player.realm >= hm.realm:
                is_equipped = player.heart_method == hm_id
                mastery = player.heart_method_mastery if is_equipped else 0
                bonus = get_heart_method_bonus(hm_id, mastery)
                
                available.append({
                    "method_id": hm.method_id,
                    "name": hm.name,
                    "description": hm.description,
                    "quality": hm.quality,
                    "quality_name": {0: "普通", 1: "稀有", 2: "传说"}.get(hm.quality, "普通"),
                    "realm_required": hm.realm,
                    "realm_name": {0: "平民", 1: "新兵", 2: "老兵", 3: "骑士", 4: "骑士长", 5: "领主", 6: "男爵", 7: "子爵", 8: "伯爵"}.get(hm.realm, "未知"),
                    "exp_multiplier": hm.exp_multiplier,
                    "attack_bonus": bonus["attack_bonus"],
                    "defense_bonus": bonus["defense_bonus"],
                    "dao_yun_rate": hm.dao_yun_rate,
                    "mastery_exp": hm.mastery_exp,
                    "is_equipped": is_equipped,
                    "current_mastery": mastery,
                })
        
        return {"type": "available_skills_data", "data": available}

    elif msg_type == "get_skill_detail":
        """获取技能详情"""
        method_id = msg.get("data", {}).get("method_id", "")
        if not method_id:
            return {"type": "error", "message": "缺少技能ID"}
        
        from ..game.constants import HEART_METHOD_REGISTRY
        
        hm = HEART_METHOD_REGISTRY.get(method_id)
        if not hm:
            return {"type": "error", "message": "技能不存在"}
        
        return {
            "type": "skill_detail_data",
            "data": {
                "method_id": hm.method_id,
                "name": hm.name,
                "description": hm.description,
                "quality": hm.quality,
                "quality_name": {0: "普通", 1: "稀有", 2: "传说"}.get(hm.quality, "普通"),
                "realm_required": hm.realm,
                "realm_name": {0: "平民", 1: "新兵", 2: "老兵", 3: "骑士", 4: "骑士长", 5: "领主", 6: "男爵", 7: "子爵", 8: "伯爵"}.get(hm.realm, "未知"),
                "exp_multiplier": hm.exp_multiplier,
                "attack_bonus": hm.attack_bonus,
                "defense_bonus": hm.defense_bonus,
                "dao_yun_rate": hm.dao_yun_rate,
                "mastery_exp": hm.mastery_exp,
                "effects": [
                    {"name": "经验倍率", "value": f"+{int(hm.exp_multiplier * 100)}%"},
                    {"name": "攻击加成", "value": f"+{hm.attack_bonus}"},
                    {"name": "防御加成", "value": f"+{hm.defense_bonus}"},
                    {"name": "声望效率", "value": f"+{int(hm.dao_yun_rate * 100)}%"},
                ]
            }
        }

    # ==================== 劫匪系统 ====================

    elif msg_type == "get_bandits":
        """获取所有劫匪"""
        from ..game.map_system import get_bandit_manager
        manager = get_bandit_manager()
        return {"type": "bandits_data", "data": manager.to_dict()}

    elif msg_type == "get_nearby_bandits":
        """获取附近的劫匪"""
        from ..game.map_system import get_bandit_manager
        player = await engine.get_player(user_id)
        if not player:
            return {"type": "error", "message": "玩家不存在"}
        
        manager = get_bandit_manager()
        nearby = manager.get_nearby_bandits(
            player.map_state.x, 
            player.map_state.y, 
            radius=msg.get("data", {}).get("radius", 200)
        )
        return {
            "type": "nearby_bandits",
            "data": {
                "bandits": [
                    {
                        "bandit_id": b.bandit_id,
                        "name": b.name,
                        "type": b.bandit_type,
                        "level": b.level,
                        "member_count": b.member_count,
                        "hp": b.hp,
                        "max_hp": b.max_hp,
                        "x": b.x,
                        "y": b.y,
                        "is_defeated": b.is_defeated,
                    }
                    for b in nearby
                ]
            }
        }

    elif msg_type == "attack_bandit":
        """攻击劫匪"""
        from ..game.bandit_combat import engage_bandit
        bandit_id = msg.get("data", {}).get("bandit_id", "")
        if not bandit_id:
            return {"type": "error", "message": "缺少劫匪ID"}
        
        player = await engine.get_player(user_id)
        if not player:
            return {"type": "error", "message": "玩家不存在"}
        
        result = await engage_bandit(player, bandit_id)
        return {"type": "bandit_attack_result", "data": result}

    elif msg_type == "get_bandit_info":
        """获取劫匪详情"""
        from ..game.map_system import get_bandit_manager, BANDIT_TYPE_NAMES, BANDIT_TYPE_ICONS
        bandit_id = msg.get("data", {}).get("bandit_id", "")
        if not bandit_id:
            return {"type": "error", "message": "缺少劫匪ID"}
        
        manager = get_bandit_manager()
        bandit = manager.bandit_groups.get(bandit_id)
        if not bandit:
            return {"type": "error", "message": "劫匪不存在"}
        
        return {
            "type": "bandit_info",
            "data": {
                "bandit_id": bandit.bandit_id,
                "name": bandit.name,
                "type": BANDIT_TYPE_NAMES.get(bandit.bandit_type, "未知"),
                "icon": BANDIT_TYPE_ICONS.get(bandit.bandit_type, "⚔️"),
                "level": bandit.level,
                "member_count": bandit.member_count,
                "hp": bandit.hp,
                "max_hp": bandit.max_hp,
                "attack": bandit.attack,
                "defense": bandit.defense,
                "x": bandit.x,
                "y": bandit.y,
                "exp_reward": bandit.exp_reward,
                "gold_reward": bandit.gold_reward,
                "is_defeated": bandit.is_defeated,
            }
        }

    # ── 医疗系统 ──────────────────────────────────────────
    elif msg_type == "gather_herbs":
        """采集草药"""
        result = await engine.gather_herbs(user_id)
        return {"type": "action_result", "action": "gather_herbs", "data": result}

    elif msg_type == "use_heal_skill":
        """使用医疗技能"""
        skill_id = msg.get("data", {}).get("skill_id", "")
        if not skill_id:
            return {"type": "error", "message": "请指定医疗技能"}
        result = await engine.use_heal_skill(user_id, skill_id)
        return {"type": "action_result", "action": "use_heal_skill", "data": result}

    elif msg_type == "get_medical_info":
        """获取医疗系统信息"""
        result = engine.get_medical_info(user_id)
        return {"type": "medical_info", "data": result}

    elif msg_type == "craft_item":
        """制作物品"""
        recipe_id = msg.get("data", {}).get("recipe_id", "")
        if not recipe_id:
            return {"type": "error", "message": "请指定配方"}
        result = await engine.craft_item(user_id, recipe_id)
        return {"type": "action_result", "action": "craft_item", "data": result}

    # ── 贸易系统 ──────────────────────────────────────────
    elif msg_type == "get_trade_goods":
        """获取贸易商品"""
        location_id = msg.get("data", {}).get("location_id")
        result = engine.get_trade_list(user_id, location_id)
        return {"type": "trade_goods", "data": result}

    elif msg_type == "trade_buy":
        """购买商品"""
        good_id = msg.get("data", {}).get("good_id", "")
        count = msg.get("data", {}).get("count", 1)
        location_id = msg.get("data", {}).get("location_id")
        try:
            count = int(count)
        except (TypeError, ValueError):
            return {"type": "error", "message": "数量必须是整数"}
        if count < 1:
            return {"type": "error", "message": "数量至少为1"}
        result = await engine.trade_buy(user_id, good_id, count, location_id)
        return {"type": "action_result", "action": "trade_buy", "data": result}

    elif msg_type == "trade_sell":
        """出售商品"""
        good_id = msg.get("data", {}).get("good_id", "")
        count = msg.get("data", {}).get("count", 1)
        location_id = msg.get("data", {}).get("location_id")
        try:
            count = int(count)
        except (TypeError, ValueError):
            return {"type": "error", "message": "数量必须是整数"}
        if count < 1:
            return {"type": "error", "message": "数量至少为1"}
        result = await engine.trade_sell(user_id, good_id, count, location_id)
        return {"type": "action_result", "action": "trade_sell", "data": result}

    # ── 锻造系统 ──────────────────────────────────────────
    elif msg_type == "get_forging_materials":
        """获取锻造材料"""
        result = engine.get_forging_materials(user_id)
        return {"type": "forging_materials", "data": result}

    elif msg_type == "get_forging_recipes":
        """获取锻造配方"""
        result = engine.get_forging_recipes(user_id)
        return {"type": "forging_recipes", "data": result}

    elif msg_type == "forge_item":
        """锻造装备"""
        recipe_id = msg.get("data", {}).get("recipe_id", "")
        if not recipe_id:
            return {"type": "error", "message": "请指定配方"}
        result = await engine.forge_item(user_id, recipe_id)
        return {"type": "action_result", "action": "forge_item", "data": result}

    elif msg_type == "buy_forging_material":
        """购买锻造材料"""
        material_id = msg.get("data", {}).get("material_id", "")
        count = msg.get("data", {}).get("count", 1)
        try:
            count = int(count)
        except (TypeError, ValueError):
            return {"type": "error", "message": "数量必须是整数"}
        if count < 1:
            return {"type": "error", "message": "数量至少为1"}
        result = await engine.buy_forging_material(user_id, material_id, count)
        return {"type": "action_result", "action": "buy_forging_material", "data": result}

    # ── 狩猎系统 ──────────────────────────────────────────
    elif msg_type == "hunt_wildlife":
        """狩猎野生动物"""
        wildlife_id = msg.get("data", {}).get("wildlife_id")
        result = await engine.hunt_wildlife(user_id, wildlife_id)
        return {"type": "action_result", "action": "hunt_wildlife", "data": result}

    elif msg_type == "get_hunting_info":
        """获取狩猎信息"""
        result = engine.get_hunting_info(user_id)
        return {"type": "hunting_info", "data": result}

    elif msg_type == "craft_accessory":
        """制作饰品"""
        accessory_id = msg.get("data", {}).get("accessory_id", "")
        if not accessory_id:
            return {"type": "error", "message": "请指定饰品"}
        result = await engine.craft_accessory(user_id, accessory_id)
        return {"type": "action_result", "action": "craft_accessory", "data": result}

    elif msg_type == "allocate_attribute_points":
        """批量分配属性点"""
        from ..game.player_level import LevelSystem
        
        data = msg.get("data", {})
        strength = data.get("strength", 0)
        intelligence = data.get("intelligence", 0)
        agility = data.get("agility", 0)
        
        result = {"success": False, "message": ""}
        total_points = strength + intelligence + agility
        
        if total_points == 0:
            result = {"success": True, "message": "没有分配任何属性点"}
        else:
            player = await engine.get_player(user_id)
            if not player:
                result = {"success": False, "message": "玩家不存在"}
            elif player.attribute_points < total_points:
                result = {"success": False, "message": f"属性点不足，需要{total_points}点，当前有{player.attribute_points}点"}
            else:
                try:
                    if strength > 0:
                        for _ in range(strength):
                            r = LevelSystem.allocate_attribute(player, "strength")
                            if not r["success"]:
                                result = r
                                break
                    if result.get("success", True) and intelligence > 0:
                        for _ in range(intelligence):
                            r = LevelSystem.allocate_attribute(player, "intelligence")
                            if not r["success"]:
                                result = r
                                break
                    if result.get("success", True) and agility > 0:
                        for _ in range(agility):
                            r = LevelSystem.allocate_attribute(player, "agility")
                            if not r["success"]:
                                result = r
                                break
                    
                    if result.get("success", True):
                        result = {
                            "success": True, 
                            "message": f"力量+{strength} 智力+{intelligence} 敏捷+{agility}",
                            "data": {
                                "strength": player.strength,
                                "intelligence": player.intelligence,
                                "agility": player.agility,
                                "remaining_points": player.attribute_points
                            }
                        }
                        await engine._save_player(player)
                except Exception as e:
                    ws_logger.error(f"[allocate_attribute_points] Error: {e}")
                    result = {"success": False, "message": f"分配失败: {str(e)}"}
        
        return {"type": "action_result", "action": "allocate_attribute_points", "data": result}

    elif msg_type == "allocate_skill_points":
        """分配技能点"""
        from ..game.player_level import LevelSystem
        
        data = msg.get("data", {})
        
        result = {"success": False, "message": ""}
        
        if not data:
            result = {"success": True, "message": "没有分配任何技能点"}
        else:
            player = await engine.get_player(user_id)
            if not player:
                result = {"success": False, "message": "玩家不存在"}
            else:
                total_needed = sum(data.values())
                
                base_skill_points = (player.strength // 3) + (player.intelligence // 3) + (player.agility // 3)
                used_skill_points = sum(player.skills.values()) if player.skills else 0
                available = base_skill_points - used_skill_points
                
                if available < total_needed:
                    result = {"success": False, "message": f"技能点不足，需要{total_needed}点，当前有{available}点"}
                else:
                    try:
                        for skill_id, points in data.items():
                            if points > 0:
                                player.skills = player.skills or {}
                                player.skills[skill_id] = player.skills.get(skill_id, 0) + points
                        
                        result = {
                            "success": True, 
                            "message": f"技能点分配成功! (力量:{player.strength} 敏捷:{player.agility} 智力:{player.intelligence})",
                            "data": {
                                "skills": player.skills,
                            }
                        }
                        await engine._save_player(player)
                    except Exception as e:
                        ws_logger.error(f"[allocate_skill_points] Error: {e}")
                        result = {"success": False, "message": f"分配失败: {str(e)}"}
        
        return {"type": "action_result", "action": "allocate_skill_points", "data": result}

    elif msg_type == "get_player_skills":
        """获取玩家技能"""
        player = await engine.get_player(user_id)
        if not player:
            return {"type": "error", "message": "玩家不存在"}
        
        skills = []
        if player.skills:
            from ..game.mb_attributes import SKILL_DEFINITIONS
            for skill_id, level in player.skills.items():
                if skill_id in SKILL_DEFINITIONS:
                    skill_def = SKILL_DEFINITIONS[skill_id]
                    skills.append({
                        "skill_id": skill_id,
                        "name": skill_def.name,
                        "description": skill_def.description,
                        "effect": skill_def.effect,
                        "icon": getattr(skill_def, 'icon', '⚔️'),
                        "level": level,
                        "max_level": getattr(skill_def, 'max_level', 10),
                    })
        
        return {"type": "player_skills_data", "data": {"skills": skills}}

    else:
        return {"type": "error", "message": f"未知操作: {msg_type}"}
