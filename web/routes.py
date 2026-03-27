"""HTTP 路由：首页、认证 API、状态接口。"""

from __future__ import annotations

import json
import re
from pathlib import Path
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

from ..game.engine import GameEngine
from .access_guard import get_access_guard

ADMIN_TOKEN_EXPIRY = 7 * 24 * 3600
PAGE_GUARD_TTL_SECONDS = 6 * 3600


def create_router(
    engine: GameEngine,
    access_password: str = "",
    guard_token: str = "",
    admin_account: str = "",
    admin_password: str = "",
    command_prefix: str = "骑砍",
    api_rate_limit_1s_count: int = 10000,
) -> APIRouter:
    router = APIRouter()
    static_dir = Path(__file__).parent.parent / "static"
    required_web_password = (access_password or "").strip()
    required_guard_token = (guard_token or "").strip()
    required_admin_account = (admin_account or "").strip()
    required_admin_password = (admin_password or "").strip()
    cmd_login = f"/{command_prefix} 登录"
    admin_tokens: dict[str, float] = {}
    access_guard = get_access_guard()

    # 反爬/限流配置：1 秒内超过阈值才封禁（默认 10000 次，封禁 60 秒）
    try:
        limit_1s_count = int(api_rate_limit_1s_count)
    except (TypeError, ValueError):
        limit_1s_count = 10000
    limit_1s_count = max(100, limit_1s_count)
    default_limit = (limit_1s_count, 1.0)
    auth_limit = (limit_1s_count, 1.0)
    admin_limit = (limit_1s_count, 1.0)
    public_limit = (limit_1s_count, 1.0)
    burst_guard_count = limit_1s_count + 1
    burst_guard_window = 1.0
    block_seconds = 60.0

    def _client_ip(request: Request) -> str:
        """获取客户端 IP（优先反向代理头）。"""
        headers = request.headers
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
                # RFC 7239: Forwarded: for=1.2.3.4;proto=https
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
        if request.client and request.client.host:
            ip = access_guard.normalize_ip(str(request.client.host))
            if ip:
                return ip
            return str(request.client.host)[:64]
        return "unknown"

    def _pick_limit(path: str, ua: str) -> tuple[int, float]:
        """按路径和 UA 选择限流阈值。"""
        if path in {"/api/register", "/api/login", "/api/admin/login"}:
            limit, window = auth_limit
        elif path in {"/api/rankings", "/api/status", "/api/adventure-scenes", "/api/realm-names"}:
            limit, window = public_limit
        elif path.startswith("/api/admin/"):
            limit, window = admin_limit
        else:
            limit, window = default_limit

        return limit, window

    def _check_page_guard(request: Request):
        """校验 HTTP 请求携带的页面级凭证。"""
        if not required_guard_token:
            return

        ip = _client_ip(request)
        ua = str(request.headers.get("user-agent", "")).strip().lower()
        ok, reason = access_guard.validate_page_session(
            secret=required_guard_token,
            page_id=request.headers.get("x-qikan-page-id", ""),
            issued_at=request.headers.get("x-qikan-page-ts", ""),
            signature=request.headers.get("x-qikan-page-sign", ""),
            ip=ip,
            ua=ua,
            client_key=request.cookies.get("qikan_page_client", ""),
        )
        if not ok:
            raise HTTPException(status_code=403, detail=reason or "页面凭证无效，请刷新页面")

    async def _page_guard_required(request: Request):
        path = request.url.path
        if not path.startswith("/api/"):
            return
        _check_page_guard(request)

    async def _anti_crawl_guard(request: Request):
        """统一接口反爬守卫。"""
        path = request.url.path
        if not path.startswith("/api/"):
            return

        ip = _client_ip(request)
        ua = str(request.headers.get("user-agent", "")).strip().lower()
        limit, window = _pick_limit(path, ua)
        ok, reason = access_guard.check_http(
            ip=ip,
            path=path,
            ua=ua,
            limit=limit,
            window=window,
            burst_count=burst_guard_count,
            burst_window=burst_guard_window,
            block_seconds=block_seconds,
        )
        if not ok:
            raise HTTPException(status_code=429, detail=reason or "请求过于频繁，请稍后再试")

    router.dependencies.append(Depends(_page_guard_required))
    router.dependencies.append(Depends(_anti_crawl_guard))

    def _check_web_password(body: dict):
        """校验 Web 访问密码（配置为空时不校验）。"""
        if not required_web_password:
            return None
        provided = str(
            body.get("access_password", body.get("admin_password", body.get("admin_key", "")))
        ).strip()
        if not secrets.compare_digest(provided, required_web_password):
            return JSONResponse(
                {"success": False, "message": "访问密码错误"},
                status_code=403,
            )
        return None

    def _get_token_from_request(request: Request) -> str | None:
        """从请求中提取token，支持Authorization header和body。"""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        if hasattr(request, "json") and request.method == "POST":
            try:
                body = request._json
                if body:
                    return body.get("token", "")
            except:
                pass
        return None

    def _verify_token(request: Request) -> str | None:
        """验证token并返回user_id。"""
        token = _get_token_from_request(request)
        if not token:
            return None
        return engine.auth.verify_web_token(token)

    def _create_admin_token() -> str:
        token = secrets.token_urlsafe(32)
        admin_tokens[token] = time.time() + ADMIN_TOKEN_EXPIRY
        return token

    def _verify_admin_token(token: str) -> bool:
        if not token:
            return False
        expires_at = admin_tokens.get(token)
        if not expires_at:
            return False
        if time.time() > expires_at:
            admin_tokens.pop(token, None)
            return False
        return True

    @router.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """提供游戏主页。"""
        html = (static_dir / "index.html").read_text(encoding="utf-8")
        page_guard = {"enabled": False, "page_id": "", "issued_at": 0, "signature": ""}
        page_client_id = str(request.cookies.get("qikan_page_client", "")).strip()
        if not page_client_id:
            page_client_id = secrets.token_hex(16)
        if required_guard_token:
            ip = _client_ip(request)
            ua = str(request.headers.get("user-agent", "")).strip().lower()
            page_guard = access_guard.issue_page_session(
                secret=required_guard_token,
                ip=ip,
                ua=ua,
                client_key=page_client_id,
                ttl_seconds=PAGE_GUARD_TTL_SECONDS,
            )
        bootstrap = (
            "<script>"
            f"window.__XIUXIAN_PAGE_GUARD__ = {json.dumps(page_guard, ensure_ascii=False)};"
            "</script>"
        )
        html = re.sub(r'(<script\b)', f'{bootstrap}\n    \\1', html, count=1)
        response = HTMLResponse(html)
        response.set_cookie(
            key="qikan_page_client",
            value=page_client_id,
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite="lax",
        )
        return response

    @router.get("/skills", response_class=HTMLResponse)
    async def skill_tree(request: Request):
        """提供技能树页面。"""
        html = (static_dir / "skills" / "index.html").read_text(encoding="utf-8")
        page_guard = {"enabled": False, "page_id": "", "issued_at": 0, "signature": ""}
        page_client_id = str(request.cookies.get("qikan_page_client", "")).strip()
        if not page_client_id:
            page_client_id = secrets.token_hex(16)
        if required_guard_token:
            ip = _client_ip(request)
            ua = str(request.headers.get("user-agent", "")).strip().lower()
            page_guard = access_guard.issue_page_session(
                secret=required_guard_token,
                ip=ip,
                ua=ua,
                client_key=page_client_id,
                ttl_seconds=PAGE_GUARD_TTL_SECONDS,
            )
        
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("x-forwarded-host", request.headers.get("host", ""))
        ws_base = f"{scheme}://{host}"
        
        bootstrap = (
            "<script>"
            f"window.__XIUXIAN_PAGE_GUARD__ = {json.dumps(page_guard, ensure_ascii=False)};"
            f"window.__XIUXIAN_WS_BASE__ = {json.dumps(ws_base, ensure_ascii=False)};"
            "</script>"
        )
        html = re.sub(r'(<script\b)', f'{bootstrap}\n    \\1', html, count=1)
        response = HTMLResponse(html)
        response.set_cookie(
            key="qikan_page_client",
            value=page_client_id,
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite="lax",
        )
        return response

    @router.get("/map", response_class=HTMLResponse)
    async def map_page(request: Request):
        """提供卡拉迪亚大陆地图页面。"""
        html = (static_dir / "map" / "index.html").read_text(encoding="utf-8")
        page_guard = {"enabled": False, "page_id": "", "issued_at": 0, "signature": ""}
        page_client_id = str(request.cookies.get("qikan_page_client", "")).strip()
        if not page_client_id:
            page_client_id = secrets.token_hex(16)
        if required_guard_token:
            ip = _client_ip(request)
            ua = str(request.headers.get("user-agent", "")).strip().lower()
            page_guard = access_guard.issue_page_session(
                secret=required_guard_token,
                ip=ip,
                ua=ua,
                client_key=page_client_id,
                ttl_seconds=PAGE_GUARD_TTL_SECONDS,
            )
        
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("x-forwarded-host", request.headers.get("host", ""))
        ws_base = f"{scheme}://{host}"
        
        bootstrap = (
            "<script>"
            f"window.__XIUXIAN_PAGE_GUARD__ = {json.dumps(page_guard, ensure_ascii=False)};"
            f"window.__XIUXIAN_WS_BASE__ = {json.dumps(ws_base, ensure_ascii=False)};"
            "</script>"
        )
        html = re.sub(r'(<script\b)', f'{bootstrap}\n    \\1', html, count=1)
        response = HTMLResponse(html)
        response.set_cookie(
            key="qikan_page_client",
            value=page_client_id,
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite="lax",
        )
        return response

    @router.get("/api/status")
    async def status():
        """健康检查和基础统计。"""
        online = 0
        if engine._ws_manager:
            online = len(engine._ws_manager._connections)
        return {
            "status": "ok",
            "players_total": len(engine._players),
            "players_online": online,
        }

    # ==================== 认证 API ====================

    @router.post("/api/register")
    async def register(request: Request):
        """注册新角色：角色名 + 密码。"""
        body = await request.json()
        auth_error = _check_web_password(body)
        if auth_error:
            return auth_error
        name = body.get("name", "").strip()
        password = body.get("password", "")

        result = await engine.register_with_password(name, password)
        if not result["success"]:
            return JSONResponse(result, status_code=400)

        # 自动登录，生成 token
        user_id = result["user_id"]
        token = await engine.auth.create_web_token(user_id)
        return {
            "success": True,
            "message": result["message"],
            "token": token,
            "user_id": user_id,
            "is_admin": False,
        }

    @router.post("/api/login")
    async def login(request: Request):
        """登录：角色名 + 密码。"""
        body = await request.json()
        auth_error = _check_web_password(body)
        if auth_error:
            return auth_error
        name = body.get("name", "").strip()
        password = body.get("password", "")

        player = engine.verify_login(name, password)
        if not player:
            return JSONResponse(
                {"success": False, "message": "角色名或密码错误"},
                status_code=401,
            )

        token = await engine.auth.create_web_token(player.user_id)
        return {
            "success": True,
            "message": f"欢迎回来，{player.name}",
            "token": token,
            "user_id": player.user_id,
            "is_admin": False,
        }

    @router.post("/api/set-password")
    async def set_password(request: Request):
        """为已有角色设置密码（首次从聊天创建的角色）。"""
        body = await request.json()
        password = body.get("password", "")

        user_id = _verify_token(request)
        if not user_id:
            return JSONResponse(
                {"success": False, "message": "登录已过期，请重新登录"},
                status_code=401,
            )

        result = await engine.set_password(user_id, password)
        if not result["success"]:
            return JSONResponse(result, status_code=400)
        return result

    @router.post("/api/bind-key")
    async def get_bind_key(request: Request):
        """获取6位数聊天绑定密钥。"""
        user_id = _verify_token(request)
        if not user_id:
            return JSONResponse(
                {"success": False, "message": "登录已过期，请重新登录"},
                status_code=401,
            )

        key = await engine.auth.create_bind_key(user_id)
        return {
            "success": True,
            "bind_key": key,
            "message": f"请在QQ中发送：{cmd_login} {key}",
            "expires_in": "7天",
        }

    @router.post("/api/verify-token")
    async def verify_token(request: Request):
        """验证 Web Token 是否有效。"""
        user_id = _verify_token(request)
        if not user_id:
            return JSONResponse(
                {"success": False, "message": "Token 无效或已过期"},
                status_code=401,
            )

        player = await engine.get_player(user_id)
        if not player:
            return JSONResponse(
                {"success": False, "message": "角色不存在"},
                status_code=404,
            )

        return {
            "success": True,
            "user_id": user_id,
            "name": player.name,
            "is_admin": False,
        }

    # ==================== 签到 API ====================

    @router.post("/api/checkin")
    async def daily_checkin(request: Request):
        """每日签到。"""
        user_id = _verify_token(request)
        if not user_id:
            return JSONResponse(
                {"success": False, "message": "Token 无效或已过期"},
                status_code=401,
            )

        result = await engine.daily_checkin(user_id)
        return result

    # ==================== 挂机修炼 API ====================

    @router.post("/api/start-afk")
    async def start_afk(request: Request):
        """开始挂机修炼。"""
        user_id = _verify_token(request)
        if not user_id:
            return JSONResponse(
                {"success": False, "message": "Token 无效或已过期"},
                status_code=401,
            )

        body = await request.json()
        minutes = body.get("minutes", 0)
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            return JSONResponse(
                {"success": False, "message": "请输入有效的分钟数"},
                status_code=400,
            )

        result = await engine.start_afk_cultivate(user_id, minutes)
        return result

    @router.post("/api/collect-afk")
    async def collect_afk(request: Request):
        """结算挂机修炼。"""
        user_id = _verify_token(request)
        if not user_id:
            return JSONResponse(
                {"success": False, "message": "Token 无效或已过期"},
                status_code=401,
            )

        result = await engine.collect_afk_cultivate(user_id)
        return result

    @router.post("/api/cancel-afk")
    async def cancel_afk(request: Request):
        """取消挂机修炼。"""
        user_id = _verify_token(request)
        if not user_id:
            return JSONResponse(
                {"success": False, "message": "Token 无效或已过期"},
                status_code=401,
            )

        result = await engine.cancel_afk_cultivate(user_id)
        return result

    # ==================== 历练 API ====================

    @router.post("/api/adventure")
    async def do_adventure(request: Request):
        """执行历练。"""
        user_id = _verify_token(request)
        if not user_id:
            return JSONResponse(
                {"success": False, "message": "Token 无效或已过期"},
                status_code=401,
            )

        result = await engine.adventure(user_id)
        return result

    @router.get("/api/adventure-scenes")
    async def get_scenes():
        """获取历练场景列表。"""
        scenes = await engine.get_adventure_scenes()
        return {"success": True, "scenes": scenes}

    # ==================== 管理员 API ====================

    @router.post("/api/admin/login")
    async def admin_login(request: Request):
        """管理员登录，返回管理员 Token。"""
        body = await request.json()
        auth_error = _check_web_password(body)
        if auth_error:
            return auth_error

        account = str(body.get("account", "")).strip()
        password = str(body.get("password", ""))
        if not required_admin_account or not required_admin_password:
            return JSONResponse(
                {"success": False, "message": "未配置管理员账号或密码"},
                status_code=403,
            )
        if (
            not secrets.compare_digest(account, required_admin_account)
            or not secrets.compare_digest(password, required_admin_password)
        ):
            return JSONResponse(
                {"success": False, "message": "管理员账号或密码错误"},
                status_code=403,
            )

        token = _create_admin_token()
        return {
            "success": True,
            "message": "管理员登录成功",
            "admin_token": token,
            "expires_in": "7天",
            "is_admin": True,
        }

    @router.post("/api/admin/verify-token")
    async def admin_verify_token(request: Request):
        """校验管理员 Token。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse(
                {"success": False, "message": "管理员登录已过期"},
                status_code=401,
            )
        return {"success": True, "is_admin": True}

    @router.post("/api/admin/adventure-scenes/list")
    async def admin_list_adventure_scenes(request: Request):
        """管理员接口：历练场景列表。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        scenes = await engine.admin_list_adventure_scenes()
        return {"success": True, "scenes": scenes}

    @router.post("/api/admin/adventure-scenes/create")
    async def admin_create_adventure_scene(request: Request):
        """管理员接口：新增历练场景。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        result = await engine.admin_create_adventure_scene(
            body.get("category", ""),
            body.get("name", ""),
            body.get("description", ""),
        )
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        return result

    @router.post("/api/admin/adventure-scenes/update")
    async def admin_update_adventure_scene(request: Request):
        """管理员接口：修改历练场景。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        result = await engine.admin_update_adventure_scene(
            body.get("id"),
            body.get("category", ""),
            body.get("name", ""),
            body.get("description", ""),
        )
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        return result

    @router.post("/api/admin/adventure-scenes/delete")
    async def admin_delete_adventure_scene(request: Request):
        """管理员接口：删除历练场景。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        result = await engine.admin_delete_adventure_scene(body.get("id"))
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        return result

    # ── 公告管理 ────────────────────────────────────────────
    @router.post("/api/admin/announcements/list")
    async def admin_list_announcements(request: Request):
        """管理员接口：公告列表。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        announcements = await engine.admin_list_announcements()
        return {"success": True, "announcements": announcements}

    @router.post("/api/admin/announcements/create")
    async def admin_create_announcement(request: Request):
        """管理员接口：新增公告。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        result = await engine.admin_create_announcement(
            body.get("title", ""),
            body.get("content", ""),
        )
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        return result

    @router.post("/api/admin/announcements/update")
    async def admin_update_announcement(request: Request):
        """管理员接口：修改公告。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        result = await engine.admin_update_announcement(
            body.get("id"),
            body.get("title", ""),
            body.get("content", ""),
            body.get("enabled", 1),
        )
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        return result

    @router.post("/api/admin/announcements/delete")
    async def admin_delete_announcement(request: Request):
        """管理员接口：删除公告。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        result = await engine.admin_delete_announcement(body.get("id"))
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        return result

    @router.post("/api/admin/heart-methods/list")
    async def admin_list_heart_methods(request: Request):
        """管理员接口：被动技能列表。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        heart_methods = await engine.admin_list_heart_methods()
        return {"success": True, "heart_methods": heart_methods}

    @router.post("/api/admin/heart-methods/create")
    async def admin_create_heart_method(request: Request):
        """管理员接口：新增被动技能。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        payload = body.get("heart_method", {})
        if not isinstance(payload, dict):
            return JSONResponse({"success": False, "message": "参数 heart_method 无效"}, status_code=400)
        result = await engine.admin_create_heart_method(payload)
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        return result

    @router.post("/api/admin/heart-methods/update")
    async def admin_update_heart_method(request: Request):
        """管理员接口：更新被动技能。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        method_id = str(body.get("method_id", "")).strip()
        payload = body.get("heart_method", {})
        if not method_id:
            return JSONResponse({"success": False, "message": "缺少 method_id"}, status_code=400)
        if not isinstance(payload, dict):
            return JSONResponse({"success": False, "message": "参数 heart_method 无效"}, status_code=400)
        result = await engine.admin_update_heart_method(method_id, payload)
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        return result

    @router.post("/api/admin/heart-methods/delete")
    async def admin_delete_heart_method(request: Request):
        """管理员接口：删除被动技能。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        method_id = str(body.get("method_id", "")).strip()
        result = await engine.admin_delete_heart_method(method_id)
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        return result

    # ── 战技管理 ────────────────────────────────────────────
    @router.post("/api/admin/gongfas/list")
    async def admin_list_gongfas(request: Request):
        """管理员接口：战技列表。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        gongfas = await engine.admin_list_gongfas()
        return {"success": True, "gongfas": gongfas}

    @router.post("/api/admin/gongfas/create")
    async def admin_create_gongfa(request: Request):
        """管理员接口：新增战技。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        payload = body.get("gongfa", {})
        if not isinstance(payload, dict):
            return JSONResponse({"success": False, "message": "参数 gongfa 无效"}, status_code=400)
        result = await engine.admin_create_gongfa(payload)
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        return result

    @router.post("/api/admin/gongfas/update")
    async def admin_update_gongfa(request: Request):
        """管理员接口：更新战技。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        gongfa_id = str(body.get("gongfa_id", "")).strip()
        payload = body.get("gongfa", {})
        if not gongfa_id:
            return JSONResponse({"success": False, "message": "缺少 gongfa_id"}, status_code=400)
        if not isinstance(payload, dict):
            return JSONResponse({"success": False, "message": "参数 gongfa 无效"}, status_code=400)
        result = await engine.admin_update_gongfa(gongfa_id, payload)
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        return result

    @router.post("/api/admin/gongfas/delete")
    async def admin_delete_gongfa(request: Request):
        """管理员接口：删除战技。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        gongfa_id = str(body.get("gongfa_id", "")).strip()
        result = await engine.admin_delete_gongfa(gongfa_id)
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        return result

    # ---- 爵位管理 CRUD ----

    @router.get("/api/realm-names")
    async def get_realm_names():
        """公开接口：获取爵位等级→名称映射。"""
        names = await engine.get_realm_names()
        return {"success": True, "realm_names": names}

    @router.post("/api/admin/realms/list")
    async def admin_list_realms(request: Request):
        """管理员接口：爵位配置列表。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        realms = await engine.admin_list_realms()
        return {"success": True, "realms": realms}

    @router.post("/api/admin/realms/create")
    async def admin_create_realm(request: Request):
        """管理员接口：新增爵位。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        payload = body.get("realm", {})
        if not isinstance(payload, dict):
            return JSONResponse({"success": False, "message": "参数 realm 无效"}, status_code=400)
        result = await engine.admin_create_realm(payload)
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        return result

    @router.post("/api/admin/realms/update")
    async def admin_update_realm(request: Request):
        """管理员接口：更新爵位配置。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        try:
            level = int(body.get("level", -1))
        except (TypeError, ValueError):
            return JSONResponse({"success": False, "message": "缺少 level"}, status_code=400)
        payload = body.get("realm", {})
        if not isinstance(payload, dict):
            return JSONResponse({"success": False, "message": "参数 realm 无效"}, status_code=400)
        result = await engine.admin_update_realm(level, payload)
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        return result

    @router.post("/api/admin/realms/delete")
    async def admin_delete_realm(request: Request):
        """管理员接口：删除爵位。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        try:
            level = int(body.get("level", -1))
        except (TypeError, ValueError):
            return JSONResponse({"success": False, "message": "缺少 level"}, status_code=400)
        result = await engine.admin_delete_realm(level)
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        return result

    @router.post("/api/admin/weapons/list")
    async def admin_list_weapons(request: Request):
        """管理员接口：武器/护甲列表。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        weapons = await engine.admin_list_weapons()
        return {"success": True, "weapons": weapons}

    @router.post("/api/admin/weapons/create")
    async def admin_create_weapon(request: Request):
        """管理员接口：新增武器/护甲。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        payload = body.get("weapon", {})
        if not isinstance(payload, dict):
            return JSONResponse({"success": False, "message": "参数 weapon 无效"}, status_code=400)
        result = await engine.admin_create_weapon(payload)
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        return result

    @router.post("/api/admin/weapons/update")
    async def admin_update_weapon(request: Request):
        """管理员接口：更新武器/护甲。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        equip_id = str(body.get("equip_id", "")).strip()
        payload = body.get("weapon", {})
        if not equip_id:
            return JSONResponse({"success": False, "message": "缺少 equip_id"}, status_code=400)
        if not isinstance(payload, dict):
            return JSONResponse({"success": False, "message": "参数 weapon 无效"}, status_code=400)
        result = await engine.admin_update_weapon(equip_id, payload)
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        return result

    @router.post("/api/admin/weapons/delete")
    async def admin_delete_weapon(request: Request):
        """管理员接口：删除武器/护甲。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        equip_id = str(body.get("equip_id", "")).strip()
        result = await engine.admin_delete_weapon(equip_id)
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        return result

    @router.post("/api/admin/market/list")
    async def admin_list_market(request: Request):
        """管理员接口：坊市记录列表。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)

        try:
            page = int(body.get("page", 1))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(body.get("page_size", 20))
        except (TypeError, ValueError):
            page_size = 20
        status = str(body.get("status", "")).strip()
        keyword = str(body.get("keyword", "")).strip()

        data = await engine.admin_list_market_listings(
            page=page, page_size=page_size, status=status, keyword=keyword,
        )
        return {"success": True, "market": data}

    @router.post("/api/admin/market/create")
    async def admin_create_market(request: Request):
        """管理员接口：新增坊市记录。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        payload = body.get("market", {})
        if not isinstance(payload, dict):
            return JSONResponse({"success": False, "message": "参数 market 无效"}, status_code=400)
        result = await engine.admin_create_market_listing(payload)
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        return result

    @router.post("/api/admin/market/update")
    async def admin_update_market(request: Request):
        """管理员接口：更新坊市记录。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        listing_id = str(body.get("listing_id", "")).strip()
        payload = body.get("market", {})
        if not listing_id:
            return JSONResponse({"success": False, "message": "缺少 listing_id"}, status_code=400)
        if not isinstance(payload, dict):
            return JSONResponse({"success": False, "message": "参数 market 无效"}, status_code=400)
        result = await engine.admin_update_market_listing(listing_id, payload)
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        return result

    @router.post("/api/admin/market/delete")
    async def admin_delete_market(request: Request):
        """管理员接口：删除坊市记录。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        listing_id = str(body.get("listing_id", "")).strip()
        result = await engine.admin_delete_market_listing(listing_id)
        if not result.get("success"):
            return JSONResponse(result, status_code=400)
        return result

    @router.post("/api/admin/ip/list")
    async def admin_list_ips(request: Request):
        """管理员接口：访问IP统计列表。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)

        try:
            page = int(body.get("page", 1))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(body.get("page_size", 20))
        except (TypeError, ValueError):
            page_size = 20
        keyword = str(body.get("keyword", "")).strip()
        raw_blocked_only = body.get("blocked_only", False)
        if isinstance(raw_blocked_only, str):
            blocked_only = raw_blocked_only.strip().lower() in {"1", "true", "yes", "y", "on"}
        else:
            blocked_only = bool(raw_blocked_only)
        data = access_guard.list_ips(
            page=page,
            page_size=page_size,
            keyword=keyword,
            blocked_only=blocked_only,
        )
        return {"success": True, "ips": data}

    @router.post("/api/admin/ip/block")
    async def admin_block_ip(request: Request):
        """管理员接口：手动封禁IP。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        ip = str(body.get("ip", "")).strip()
        if not ip:
            return JSONResponse({"success": False, "message": "缺少IP"}, status_code=400)
        try:
            seconds = int(body.get("seconds", 0))
        except (TypeError, ValueError):
            return JSONResponse({"success": False, "message": "封禁时长必须是整数秒"}, status_code=400)
        if seconds < 0:
            return JSONResponse({"success": False, "message": "封禁时长不能为负数"}, status_code=400)
        reason = str(body.get("reason", "管理员手动封禁")).strip() or "管理员手动封禁"
        ok = access_guard.manual_block(ip, seconds=seconds, reason=reason)
        if not ok:
            return JSONResponse({"success": False, "message": "IP格式无效"}, status_code=400)
        return {"success": True, "message": f"已封禁IP：{ip}"}

    @router.post("/api/admin/ip/unblock")
    async def admin_unblock_ip(request: Request):
        """管理员接口：解除IP封禁。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        ip = str(body.get("ip", "")).strip()
        if not ip:
            return JSONResponse({"success": False, "message": "缺少IP"}, status_code=400)
        ok = access_guard.manual_unblock(ip)
        if not ok:
            return JSONResponse({"success": False, "message": "IP格式无效"}, status_code=400)
        return {"success": True, "message": f"已解除封禁：{ip}"}

    # ==================== 图标管理 API ====================

    @router.get("/api/icons/config")
    async def get_icon_config():
        """获取图标配置。"""
        icons_dir = static_dir / "icons"
        config_file = icons_dir / "config.json"
        if not config_file.exists():
            return JSONResponse({"success": False, "message": "图标配置文件不存在"}, status_code=404)
        try:
            config = json.loads(config_file.read_text(encoding="utf-8"))
            return {"success": True, "config": config}
        except Exception as e:
            return JSONResponse({"success": False, "message": f"读取配置失败: {str(e)}"}, status_code=500)

    @router.post("/api/admin/icons/update")
    async def update_icon_config(request: Request):
        """更新图标配置。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)

        icon_key = body.get("icon_key", "")
        emoji = body.get("emoji", "")
        image = body.get("image", "")

        icons_dir = static_dir / "icons"
        config_file = icons_dir / "config.json"
        if not config_file.exists():
            return JSONResponse({"success": False, "message": "图标配置文件不存在"}, status_code=404)

        try:
            config = json.loads(config_file.read_text(encoding="utf-8"))
            if icon_key not in config.get("icons", {}):
                return JSONResponse({"success": False, "message": f"无效的图标key: {icon_key}"}, status_code=400)

            config["icons"][icon_key]["emoji"] = emoji
            config["icons"][icon_key]["image"] = image
            config["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

            config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"success": True, "message": f"已更新图标: {config['icons'][icon_key]['name']}"}
        except Exception as e:
            return JSONResponse({"success": False, "message": f"更新配置失败: {str(e)}"}, status_code=500)

    @router.post("/api/admin/icons/upload")
    async def upload_icon(request: Request):
        """上传图标图片。"""
        admin_token = request.headers.get("X-Admin-Token", "")
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)

        try:
            form = await request.form()
            icon_key = form.get("icon_key", "")
            file = form.get("file")

            if not file:
                return JSONResponse({"success": False, "message": "未选择文件"}, status_code=400)

            icons_dir = static_dir / "icons"
            icons_dir.mkdir(exist_ok=True)

            allowed_extensions = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in allowed_extensions:
                return JSONResponse({"success": False, "message": "不支持的图片格式"}, status_code=400)

            filename = f"{icon_key}{file_ext}"
            file_path = icons_dir / filename

            content = await file.read()
            file_path.write_bytes(content)

            image_url = f"/static/icons/{filename}"

            config_file = icons_dir / "config.json"
            if config_file.exists():
                config = json.loads(config_file.read_text(encoding="utf-8"))
                if icon_key in config.get("icons", {}):
                    config["icons"][icon_key]["image"] = image_url
                    config["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

            return {"success": True, "message": "上传成功", "url": image_url}
        except Exception as e:
            return JSONResponse({"success": False, "message": f"上传失败: {str(e)}"}, status_code=500)

    @router.get("/api/icons/{icon_key}")
    async def get_icon(icon_key: str):
        """获取指定图标。"""
        icons_dir = static_dir / "icons"
        for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"]:
            file_path = icons_dir / f"{icon_key}{ext}"
            if file_path.exists():
                content = file_path.read_bytes()
                mime_types = {
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".gif": "image/gif",
                    ".svg": "image/svg+xml",
                    ".webp": "image/webp",
                }
                return Response(content, media_type=mime_types.get(ext, "image/png"))
        return JSONResponse({"success": False, "message": "图标不存在"}, status_code=404)

    @router.post("/api/admin/overview")
    async def admin_overview(request: Request):
        """管理员首页概览。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse(
                {"success": False, "message": "管理员登录已过期"},
                status_code=401,
            )

        online = 0
        if engine._ws_manager:
            online = len(engine._ws_manager._connections)
        weapon_count = len(await engine.admin_list_weapons())
        heart_method_count = len(await engine.admin_list_heart_methods())
        gongfa_count = len(await engine.admin_list_gongfas())
        scene_count = len(await engine.admin_list_adventure_scenes())
        announcement_count = len(await engine.admin_list_announcements())
        return {
            "success": True,
            "overview": {
                "players_total": len(engine._players),
                "players_online": online,
                "admin_account": required_admin_account,
                "weapons_total": weapon_count,
                "heart_methods_total": heart_method_count,
                "gongfas_total": gongfa_count,
                "scenes_total": scene_count,
                "announcements_total": announcement_count,
            },
        }

    @router.post("/api/admin/players")
    async def admin_players(request: Request):
        """管理员接口：获取所有玩家列表和数据。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse(
                {"success": False, "message": "管理员登录已过期"},
                status_code=401,
            )

        from ..game.constants import get_realm_name

        players_list = []
        for uid, p in engine._players.items():
            players_list.append(
                {
                    "user_id": uid,
                    "name": p.name,
                    "realm": p.realm,
                    "realm_name": get_realm_name(p.realm, p.sub_realm),
                    "exp": p.exp,
                    "hp": p.hp,
                    "max_hp": p.max_hp,
                    "attack": p.attack,
                    "defense": p.defense,
                    "spirit_stones": p.spirit_stones,
                    "has_password": p.password_hash is not None,
                    "created_at": p.created_at,
                    "inventory_count": sum(p.inventory.values()),
                }
            )

        players_list.sort(key=lambda x: x["created_at"])

        # 在线状态标记
        online_ids = engine.get_online_user_ids()
        for p in players_list:
            p["is_online"] = p["user_id"] in online_ids

        return {
            "success": True,
            "total": len(players_list),
            "players": players_list,
        }

    @router.post("/api/admin/player-detail")
    async def admin_player_detail(request: Request):
        """管理员接口：获取单个玩家详细数据（含背包）。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        user_id = body.get("user_id", "")
        detail = engine.get_player_detail(user_id)
        if not detail:
            return JSONResponse({"success": False, "message": "玩家不存在"}, status_code=404)
        online_ids = engine.get_online_user_ids()
        detail["is_online"] = user_id in online_ids
        return {"success": True, "player": detail}

    @router.post("/api/admin/delete-player")
    async def admin_delete_player(request: Request):
        """管理员接口：删除单个玩家。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        user_id = body.get("user_id", "")
        result = await engine.delete_player(user_id)
        if not result["success"]:
            return JSONResponse(result, status_code=404)
        return result

    @router.post("/api/admin/batch-delete")
    async def admin_batch_delete(request: Request):
        """管理员接口：批量删除玩家。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        user_ids = body.get("user_ids", [])
        if not isinstance(user_ids, list) or not user_ids:
            return JSONResponse({"success": False, "message": "请提供要删除的玩家列表"}, status_code=400)
        result = await engine.batch_delete_players(user_ids)
        return result

    @router.post("/api/admin/update-player")
    async def admin_update_player(request: Request):
        """管理员接口：修改玩家数据。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        user_id = body.get("user_id", "")
        updates = body.get("updates", {})
        if not isinstance(updates, dict) or not updates:
            return JSONResponse({"success": False, "message": "无更新数据"}, status_code=400)
        result = await engine.update_player_data(user_id, updates)
        if not result["success"]:
            return JSONResponse(result, status_code=400)
        return result

    @router.post("/api/admin/wipe-data")
    async def admin_wipe_data(request: Request):
        """管理员接口：清空全部游戏数据。"""
        body = await request.json()
        admin_token = str(body.get("admin_token", ""))
        if not _verify_admin_token(admin_token):
            return JSONResponse({"success": False, "message": "管理员登录已过期"}, status_code=401)
        confirm = body.get("confirm", "")
        if confirm != "确认清档":
            return JSONResponse({"success": False, "message": "请传入 confirm='确认清档'"}, status_code=400)
        await engine.clear_all_data(remove_dir=False)
        return {"success": True, "message": "已清空全部游戏数据"}

    # ==================== 公开 API ====================

    @router.get("/api/rankings")
    async def rankings(user_id: str = ""):
        """公开排行榜接口。可传 user_id 获取自己的排名。"""
        all_rankings = engine.get_rankings(limit=999)
        death_rankings = engine.get_death_rankings(limit=10)
        online_rankings = engine.get_online_rankings(limit=50)
        online = 0
        if engine._ws_manager:
            online = len(engine._ws_manager._connections)
        my_rank = None
        if user_id:
            for r in all_rankings:
                player = engine.get_player_by_name(r["name"])
                if player and player.user_id == user_id:
                    my_rank = r
                    break
        return {
            "success": True,
            "total_players": len(engine._players),
            "online_players": online,
            "rankings": all_rankings[:10],
            "death_rankings": death_rankings,
            "online_rankings": online_rankings,
            "my_rank": my_rank,
        }

    # ==================== 劫匪系统 API ====================

    @router.get("/api/bandits")
    async def get_bandits():
        """获取所有劫匪数据。"""
        from ..game.map_system import get_bandit_manager
        manager = get_bandit_manager()
        return {"success": True, "bandits": manager.to_dict()["bandits"]}

    @router.get("/api/bandits/nearby")
    async def get_nearby_bandits(x: float = 500, y: float = 500, radius: float = 200):
        """获取指定位置附近的劫匪。"""
        from ..game.map_system import get_bandit_manager
        manager = get_bandit_manager()
        nearby = manager.get_nearby_bandits(x, y, radius)
        return {
            "success": True,
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

    # ==================== 地图系统 API ====================

    @router.get("/api/map/locations")
    async def get_map_locations():
        """获取所有地图地点（城镇/城堡/村庄/匪窝）。"""
        from ..game.map_system import TOWNS, CASTLES, VILLAGES, BANDIT_CAMPS, LocationType, FACTION_NAMES, FACTION_SHORT_NAMES
        
        locations = []
        
        for loc_id, loc in TOWNS.items():
            locations.append({
                "id": loc.location_id,
                "name": loc.name,
                "type": "town",
                "type_name": "城镇",
                "faction": loc.faction,
                "faction_name": FACTION_NAMES.get(loc.faction, "无"),
                "faction_short": FACTION_SHORT_NAMES.get(loc.faction, ""),
                "x": loc.x,
                "y": loc.y,
                "level_range": loc.level_range,
                "description": loc.description,
                "prosperity": loc.prosperity if hasattr(loc, 'prosperity') else 50,
            })
        
        for loc_id, loc in CASTLES.items():
            locations.append({
                "id": loc.location_id,
                "name": loc.name,
                "type": "castle",
                "type_name": "城堡",
                "faction": loc.faction,
                "faction_name": FACTION_NAMES.get(loc.faction, "无"),
                "faction_short": FACTION_SHORT_NAMES.get(loc.faction, ""),
                "x": loc.x,
                "y": loc.y,
                "level_range": loc.level_range,
                "description": loc.description,
                "garrison_size": loc.garrison_size,
                "strategic_value": loc.strategic_value,
            })
        
        for loc_id, loc in VILLAGES.items():
            locations.append({
                "id": loc.location_id,
                "name": loc.name,
                "type": "village",
                "type_name": "村庄",
                "faction": loc.faction,
                "faction_name": FACTION_NAMES.get(loc.faction, "无"),
                "faction_short": FACTION_SHORT_NAMES.get(loc.faction, ""),
                "x": loc.x,
                "y": loc.y,
                "level_range": loc.level_range,
                "description": loc.description,
                "village_type": loc.village_type,
                "production": loc.production,
                "prosperity": loc.prosperity,
            })
        
        for loc_id, loc in BANDIT_CAMPS.items():
            locations.append({
                "id": loc.location_id,
                "name": loc.name,
                "type": "bandit_camp",
                "type_name": "匪窝",
                "faction": -1,
                "faction_name": "无",
                "faction_short": "",
                "x": loc.x,
                "y": loc.y,
                "level_range": loc.level_range,
                "description": loc.description,
                "bandit_type": loc.bandit_type,
                "difficulty": loc.difficulty,
                "rewards": loc.rewards,
            })
        
        return {"success": True, "locations": locations}

    @router.get("/api/map/player")
    async def get_player_map_state(user_id: str = ""):
        """获取玩家地图状态。"""
        from ..game.map_system import TOWNS, CASTLES, VILLAGES, BANDIT_CAMPS
        
        if not user_id:
            return {"success": False, "message": "需要user_id"}
        
        player = engine.get_player(user_id)
        if not player:
            return {"success": False, "message": "玩家不存在"}
        
        map_state = player.map_state if hasattr(player, 'map_state') else None
        
        current_location = None
        if map_state and map_state.current_location:
            for loc_id, loc in {**TOWNS, **CASTLES, **VILLAGES, **BANDIT_CAMPS}.items():
                if loc.location_id == map_state.current_location:
                    current_location = {
                        "id": loc.location_id,
                        "name": loc.name,
                        "type": loc.location_type,
                    }
                    break
        
        return {
            "success": True,
            "player": {
                "user_id": player.user_id,
                "name": player.name,
                "x": map_state.x if map_state else 500,
                "y": map_state.y if map_state else 500,
                "level": getattr(player, 'level', 1),
                "current_location": current_location,
                "travel_destination": map_state.travel_destination if map_state else "",
                "travel_progress": map_state.travel_progress if map_state else 0,
                "travel_time": map_state.travel_time if map_state else 0,
                "active_quests": list(map_state.active_quests) if map_state else [],
            }
        }

    @router.get("/api/map/location/{location_id}")
    async def get_location_detail(location_id: str):
        """获取地点详细信息。"""
        from ..game.map_system import TOWNS, CASTLES, VILLAGES, BANDIT_CAMPS, LocationType, FACTION_NAMES
        
        all_locations = {**TOWNS, **CASTLES, **VILLAGES, **BANDIT_CAMPS}
        loc = all_locations.get(location_id)
        
        if not loc:
            return {"success": False, "message": "地点不存在"}
        
        type_map = {
            LocationType.TOWN: ("town", "城镇"),
            LocationType.CASTLE: ("castle", "城堡"),
            LocationType.VILLAGE: ("village", "村庄"),
            LocationType.BANDIT_CAMP: ("bandit_camp", "匪窝"),
        }
        
        result = {
            "success": True,
            "location": {
                "id": loc.location_id,
                "name": loc.name,
                "type": type_map.get(loc.location_type, ("unknown", "未知"))[0],
                "type_name": type_map.get(loc.location_type, ("unknown", "未知"))[1],
                "faction": loc.faction,
                "faction_name": FACTION_NAMES.get(loc.faction, "无"),
                "x": loc.x,
                "y": loc.y,
                "level_range": loc.level_range,
                "description": loc.description,
            }
        }
        
        if loc.location_type == LocationType.TOWN:
            result["location"]["shop_items"] = loc.shop_items
            result["location"]["tax_rate"] = loc.tax_rate
        elif loc.location_type == LocationType.VILLAGE:
            result["location"]["village_type"] = loc.village_type
            result["location"]["production"] = loc.production
            result["location"]["prosperity"] = loc.prosperity
        elif loc.location_type == LocationType.CASTLE:
            result["location"]["garrison_size"] = loc.garrison_size
            result["location"]["strategic_value"] = loc.strategic_value
        elif loc.location_type == LocationType.BANDIT_CAMP:
            result["location"]["bandit_type"] = loc.bandit_type
            result["location"]["difficulty"] = loc.difficulty
            result["location"]["rewards"] = loc.rewards
        
        return result

    @router.get("/api/map/quests")
    async def get_available_quests(user_id: str = "", location_id: str = ""):
        """获取指定地点的任务列表。"""
        from ..game.map_system import generate_quests_for_location
        
        if not user_id:
            return {"success": False, "message": "需要user_id"}
        
        player = engine.get_player(user_id)
        if not player:
            return {"success": False, "message": "玩家不存在"}
        
        quests = generate_quests_for_location(location_id, player.level if hasattr(player, 'level') else 1)
        
        return {"success": True, "quests": quests}

    @router.post("/api/map/travel")
    async def start_travel(data: dict):
        """开始旅行到指定地点。"""
        user_id = data.get("user_id", "")
        destination = data.get("destination", "")
        
        if not user_id:
            return {"success": False, "message": "需要user_id"}
        
        player = engine.get_player(user_id)
        if not player:
            return {"success": False, "message": "玩家不存在"}
        
        from ..game.map_system import TOWNS, CASTLES, VILLAGES, BANDIT_CAMPS, calculate_map_travel_time
        all_locations = {**TOWNS, **CASTLES, **VILLAGES, **BANDIT_CAMPS}
        
        dest_loc = all_locations.get(destination)
        if not dest_loc:
            return {"success": False, "message": "目的地不存在"}
        
        map_state = player.map_state if hasattr(player, 'map_state') else None
        if not map_state:
            return {"success": False, "message": "玩家地图状态异常"}
        
        map_state.travel_destination = destination
        map_state.travel_progress = 0
        map_state.travel_time = calculate_map_travel_time(
            map_state.x, map_state.y,
            dest_loc.x, dest_loc.y
        )
        
        return {
            "success": True,
            "message": f"开始前往{dest_loc.name}",
            "destination": dest_loc.name,
            "duration": map_state.travel_time,
        }

    @router.post("/api/map/arrive")
    async def arrive_at_location(data: dict):
        """玩家到达指定地点。"""
        user_id = data.get("user_id", "")
        location = data.get("location", "")
        
        if not user_id:
            return {"success": False, "message": "需要user_id"}
        
        player = engine.get_player(user_id)
        if not player:
            return {"success": False, "message": "玩家不存在"}
        
        from ..game.map_system import TOWNS, CASTLES, VILLAGES, BANDIT_CAMPS
        all_locations = {**TOWNS, **CASTLES, **VILLAGES, **BANDIT_CAMPS}
        
        loc = all_locations.get(location)
        if not loc:
            return {"success": False, "message": "地点不存在"}
        
        map_state = player.map_state if hasattr(player, 'map_state') else None
        if map_state:
            map_state.current_location = location
            map_state.x = loc.x
            map_state.y = loc.y
            map_state.travel_destination = ""
            map_state.travel_progress = 0
        
        return {
            "success": True,
            "message": f"已到达{loc.name}",
            "location": {
                "id": loc.location_id,
                "name": loc.name,
                "type": loc.location_type,
            }
        }

    @router.get("/api/map/factions")
    async def get_factions():
        """获取所有势力信息。"""
        from ..game.map_system import FACTION_NAMES, FACTION_SHORT_NAMES
        
        factions = []
        for i in range(6):
            factions.append({
                "id": i,
                "name": FACTION_NAMES.get(i, "未知势力"),
                "short_name": FACTION_SHORT_NAMES.get(i, ""),
            })
        
        return {"success": True, "factions": factions}

    # ==================== 村庄好感系统 API ====================

    @router.get("/api/village/{village_id}/info")
    async def get_village_info(village_id: str, user_id: str = ""):
        """获取村庄详细信息和玩家好感状态。"""
        from ..game.map_system import VILLAGES
        from ..game.village_system import (
            get_village_state, get_favor_status, get_favor_benefits,
            apply_favor_decay, FAME_LEVELS
        )
        
        village = VILLAGES.get(village_id)
        if not village:
            return {"success": False, "message": "村庄不存在"}
        
        current_date = "2026-03-27"  # TODO: 实际获取当前日期
        
        result = {
            "success": True,
            "village": {
                "id": village.location_id,
                "name": village.name,
                "type": village.village_type,
                "faction": village.faction,
                "production": village.production,
                "prosperity": village.prosperity,
                "description": village.description,
            }
        }
        
        if user_id:
            player = engine.get_player(user_id)
            if player:
                player_fame = getattr(player, 'fame', 0) if hasattr(player, 'fame') else 0
                state = get_village_state({}, user_id, village_id)
                
                apply_favor_decay(state, current_date)
                
                favor_status, attitude = get_favor_status(state.favor)
                benefits = get_favor_benefits(state.favor)
                
                result["player"] = {
                    "favor": state.favor,
                    "favor_status": favor_status,
                    "attitude": attitude,
                    "benefits": benefits,
                    "total_quests": state.total_quests_completed,
                }
                
                result["fame"] = {
                    "value": player_fame,
                    "levels": [
                        {"name": l.name, "min_fame": l.min_fame}
                        for l in FAME_LEVELS
                    ]
                }
        
        return result

    @router.post("/api/village/{village_id}/visit")
    async def visit_village(village_id: str, data: dict):
        """拜访村庄头人，消耗礼物获取任务。"""
        from ..game.map_system import VILLAGES
        from ..game.village_system import (
            get_village_state, can_visit, get_quests_for_player,
            get_available_quests_for_gifts, get_fame_level, FAME_LEVELS
        )
        
        user_id = data.get("user_id", "")
        gift_ids = data.get("gifts", [])  # 礼物物品ID列表
        
        if not user_id:
            return {"success": False, "message": "需要user_id"}
        
        village = VILLAGES.get(village_id)
        if not village:
            return {"success": False, "message": "村庄不存在"}
        
        player = engine.get_player(user_id)
        if not player:
            return {"success": False, "message": "玩家不存在"}
        
        player_fame = getattr(player, 'fame', 0) if hasattr(player, 'fame') else 0
        
        can_visit_ok, msg = can_visit(player_fame)
        if not can_visit_ok:
            return {"success": False, "message": msg}
        
        state = get_village_state({}, user_id, village_id)
        
        if gift_ids:
            available_quests = get_available_quests_for_gifts(gift_ids, player_fame)
            available_quests = [q for q in available_quests if q.min_favor <= state.favor]
        else:
            available_quests = get_quests_for_player(player_fame, state.favor)
        
        fame_level = get_fame_level(player_fame)
        
        return {
            "success": True,
            "message": f"拜访{village.name}头人成功",
            "favor": state.favor,
            "max_favor": fame_level.max_favor,
            "can_quest": fame_level.can_quest,
            "available_quests": [
                {
                    "quest_id": q.quest_id,
                    "name": q.name,
                    "description": q.description,
                    "difficulty": q.difficulty,
                    "gold_reward": q.gold_reward,
                    "favor_reward": q.favor_reward,
                    "requires_combat": q.requires_combat,
                    "requires_time": q.requires_time > 0,
                }
                for q in available_quests[:5]
            ],
            "gifts_value": sum(
                10 for _ in gift_ids
            ),
        }

    @router.get("/api/village/{village_id}/quests")
    async def get_village_quests(village_id: str, user_id: str = ""):
        """获取村庄当前可接任务。"""
        from ..game.map_system import VILLAGES
        from ..game.village_system import get_village_state, get_quests_for_player
        
        village = VILLAGES.get(village_id)
        if not village:
            return {"success": False, "message": "村庄不存在"}
        
        if not user_id:
            return {"success": False, "message": "需要user_id"}
        
        player = engine.get_player(user_id)
        if not player:
            return {"success": False, "message": "玩家不存在"}
        
        player_fame = getattr(player, 'fame', 0) if hasattr(player, 'fame') else 0
        state = get_village_state({}, user_id, village_id)
        
        quests = get_quests_for_player(player_fame, state.favor)
        
        return {
            "success": True,
            "village_id": village_id,
            "player_favor": state.favor,
            "quests": [
                {
                    "quest_id": q.quest_id,
                    "name": q.name,
                    "description": q.description,
                    "difficulty": q.difficulty,
                    "gold_reward": q.gold_reward,
                    "favor_reward": q.favor_reward,
                }
                for q in quests
            ]
        }

    @router.post("/api/village/{village_id}/quest/accept")
    async def accept_village_quest(village_id: str, data: dict):
        """接受村庄任务。"""
        from ..game.map_system import VILLAGES
        from ..game.village_system import get_village_state, can_accept_quest, VILLAGE_QUESTS
        
        user_id = data.get("user_id", "")
        quest_id = data.get("quest_id", "")
        
        if not user_id or not quest_id:
            return {"success": False, "message": "参数不完整"}
        
        village = VILLAGES.get(village_id)
        if not village:
            return {"success": False, "message": "村庄不存在"}
        
        player = engine.get_player(user_id)
        if not player:
            return {"success": False, "message": "玩家不存在"}
        
        player_fame = getattr(player, 'fame', 0) if hasattr(player, 'fame') else 0
        state = get_village_state({}, user_id, village_id)
        
        quest = next((q for q in VILLAGE_QUESTS if q.quest_id == quest_id), None)
        if not quest:
            return {"success": False, "message": "任务不存在"}
        
        can_accept, msg = can_accept_quest(state, quest, player_fame)
        if not can_accept:
            return {"success": False, "message": msg}
        
        return {
            "success": True,
            "message": f"已接受任务：{quest.name}",
            "quest": {
                "quest_id": quest.quest_id,
                "name": quest.name,
                "description": quest.description,
                "requires_combat": quest.requires_combat,
                "requires_time": quest.requires_time,
            }
        }

    @router.get("/api/fame/info")
    async def get_fame_info(user_id: str = ""):
        """获取玩家名望信息。"""
        from ..game.village_system import get_fame_display, FAME_LEVELS
        
        if not user_id:
            return {"success": False, "message": "需要user_id"}
        
        player = engine.get_player(user_id)
        if not player:
            return {"success": False, "message": "玩家不存在"}
        
        player_fame = getattr(player, 'fame', 0) if hasattr(player, 'fame') else 0
        fame_info = get_fame_display(player_fame)
        
        return {
            "success": True,
            "fame": fame_info,
            "levels": [
                {
                    "name": l.name,
                    "min_fame": l.min_fame,
                    "max_favor": l.max_favor,
                    "can_visit": l.can_visit,
                    "can_quest": l.can_quest,
                }
                for l in FAME_LEVELS
            ]
        }

    @router.get("/api/gifts/list")
    async def get_gift_list():
        """获取所有礼物列表。"""
        from ..game.village_system import GIFT_ITEMS
        
        gifts = [
            {
                "id": item_id,
                "name": gift.name,
                "value": gift.value,
                "can_unlock_legendary": gift.can_unlock_legendary,
            }
            for item_id, gift in GIFT_ITEMS.items()
        ]
        
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

    @router.get("/api/village/{village_id}/daily")
    async def get_daily_quests(village_id: str, user_id: str = ""):
        """获取每日任务。"""
        from ..game.map_system import VILLAGES
        from ..game.village_system import get_village_state, refresh_daily_quests, DAILY_QUESTS
        
        village = VILLAGES.get(village_id)
        if not village:
            return {"success": False, "message": "村庄不存在"}
        
        if not user_id:
            return {"success": False, "message": "需要user_id"}
        
        player = engine.get_player(user_id)
        if not player:
            return {"success": False, "message": "玩家不存在"}
        
        state = get_village_state({}, user_id, village_id)
        current_date = "2026-03-27"
        player_fame = getattr(player, 'fame', 0) if hasattr(player, 'fame') else 0
        
        daily = refresh_daily_quests(state, current_date, player_fame)
        
        return {
            "success": True,
            "daily_quests": [
                {
                    "quest_id": q.quest_id,
                    "name": q.name,
                    "description": q.description,
                    "gold_reward": q.gold_reward,
                    "favor_reward": q.favor_reward,
                    "completed": q.quest_id in state.daily_completed,
                }
                for q in daily
            ],
            "completed_count": len(state.daily_completed),
            "total_count": len(state.daily_quests),
        }

    return router
