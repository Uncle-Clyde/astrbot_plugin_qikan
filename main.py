"""骑砍英雄传 — AstrBot 骑砍文字RPG游戏插件。"""

from __future__ import annotations

import sys
import os
import zipfile
from pathlib import Path

_py_version = f"cp{sys.version_info.major}{sys.version_info.minor}"

_libs_dir = Path(__file__).parent / "libs"
if _libs_dir.exists():
    _libs_str = str(_libs_dir)
    if _libs_str not in sys.path:
        sys.path.insert(0, _libs_str)
    
    _extracted_dir = _libs_dir / "extracted" / _py_version
    if not _extracted_dir.exists():
        _extracted_dir.mkdir(parents=True, exist_ok=True)
        for _wheel_file in _libs_dir.glob("*.whl"):
            if _wheel_file.suffix == ".whl":
                _wheel_name = _wheel_file.stem
                if _py_version in _wheel_name or "py3-none-any" in _wheel_name or "py2.py3" in _wheel_name:
                    try:
                        with zipfile.ZipFile(_wheel_file, 'r') as _zf:
                            _zf.extractall(_extracted_dir)
                    except Exception:
                        pass
    
    if _extracted_dir.exists():
        _extracted_str = str(_extracted_dir)
        if _extracted_str not in sys.path:
            sys.path.insert(0, _extracted_str)

import json
import re
import time
import asyncio
from typing import Optional

from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register

from .game.data_manager import DataManager
from .game.engine import GameEngine
from .game.auth import AuthManager
from .game import renderer

_MISSING = object()
CMD_PREFIX = "骑砍"


@register("astrbot_plugin_qikan", "qikan", "骑砍文字RPG游戏，支持聊天指令和网页界面", "0.1.21")
class XiuxianPlugin(Star):
    def __init__(self, context: Context, config=None):
        super().__init__(context)
        self._plugin_config = config
        self._engine: GameEngine | None = None
        self._web_server = None
        self._web_error_message = ""
        self._image_cache_dir = ""
        # 持久化 DataManager / AuthManager 实例，避免 AstrBot 重载时重复创建连接
        self._data_manager: Optional[DataManager] = None
        self._auth_manager: Optional[AuthManager] = None

    def _get_cfg(self, key: str, default):
        """读取插件配置，优先使用插件级配置，兼容不同 AstrBot 版本。"""
        sources = [
            getattr(self, "config", None),
            self._plugin_config,
            getattr(self.context, "config", None),
            getattr(self.context, "_config", None),
        ]
        for source in sources:
            if source is None:
                continue
            try:
                if hasattr(source, "__contains__") and key in source:
                    if hasattr(source, "get"):
                        return source.get(key)
                    return source[key]
            except (KeyError, TypeError, IndexError, AttributeError):
                pass
            try:
                if hasattr(source, "get"):
                    value = source.get(key, _MISSING)
                    if value is not _MISSING:
                        return value
            except (KeyError, TypeError, AttributeError):
                continue
        return default

    def _get_cfg_int(self, key: str, default: int) -> int:
        value = self._get_cfg(key, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            logger.warning(f"骑砍英雄传：配置项 {key}={value} 非法，回退默认值 {default}")
            return default

    def _get_cfg_bool(self, key: str, default: bool) -> bool:
        value = self._get_cfg(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    def _get_checkin_config(self) -> dict:
        """读取签到、挂机、历练相关配置项。"""
        return {
            "checkin_stones_min": self._get_cfg_int("checkin_stones_min", 20),
            "checkin_stones_max": self._get_cfg_int("checkin_stones_max", 300),
            "checkin_exp_min": self._get_cfg_int("checkin_exp_min", 500),
            "checkin_exp_max": self._get_cfg_int("checkin_exp_max", 5000),
            "checkin_stones_with_pill_min": self._get_cfg_int("checkin_stones_with_pill_min", 10),
            "checkin_stones_with_pill_max": self._get_cfg_int("checkin_stones_with_pill_max", 100),
            "checkin_prob_stones": self._get_cfg_int("checkin_prob_stones", 60),
            "checkin_prob_exp": self._get_cfg_int("checkin_prob_exp", 25),
            "afk_cultivate_max_minutes": self._get_cfg_int("afk_cultivate_max_minutes", 60),
            "adventure_cooldown": self._get_cfg_int("adventure_cooldown", 1800),
        }

    def _cmd(self, sub_cmd: str = "") -> str:
        base = f"/{CMD_PREFIX}"
        if sub_cmd:
            return f"{base} {sub_cmd}"
        return base

    def _render_image_path(self, img_bytes: bytes, tag: str = "img") -> str | None:
        """将渲染后的图片 bytes 落盘，返回本地路径供 image_result 发送。"""
        if not isinstance(img_bytes, (bytes, bytearray)):
            logger.error(f"骑砍世界：渲染结果不是 bytes，tag={tag}")
            return None

        cache_dir = self._image_cache_dir or os.path.join(
            "data", "plugin_data", "astrbot_plugin_qikan", "render_cache"
        )
        try:
            os.makedirs(cache_dir, exist_ok=True)
            file_name = f"{int(time.time() * 1000)}_{tag}.png"
            file_path = os.path.join(cache_dir, file_name)
            with open(file_path, "wb") as f:
                f.write(img_bytes)

            # 简单清理：避免目录无限增长
            try:
                files = sorted(
                    (
                        os.path.join(cache_dir, x)
                        for x in os.listdir(cache_dir)
                        if x.lower().endswith(".png")
                    ),
                    key=lambda p: os.path.getmtime(p),
                )
                if len(files) > 120:
                    for p in files[: len(files) - 80]:
                        try:
                            os.remove(p)
                        except OSError:
                            pass
            except OSError:
                logger.debug("骑砍英雄传：缓存清理失败")

            return file_path
        except Exception:
            logger.exception(f"骑砍英雄传：图片落盘失败，tag={tag}")
            return None

    async def initialize(self):
        """插件初始化：加载数据、启动游戏引擎和 Web 服务。"""
        data_dir = os.path.join("data", "plugin_data", "astrbot_plugin_qikan")
        self._image_cache_dir = os.path.join(data_dir, "render_cache")
        os.makedirs(self._image_cache_dir, exist_ok=True)

        # 强制清理：重装插件时，旧的 DataManager 实例和数据库连接可能已被锁定
        if self._data_manager is not None:
            logger.info("骑砍英雄传：强制清理旧 DataManager...")
            try:
                if self._data_manager.db is not None:
                    await self._data_manager.db.close()
            except Exception:
                pass
            self._data_manager = None

        # 强制清理残留的 WAL 相关文件
        for suffix in (".wal", "-shm", "-journal"):
            wal_file = os.path.join(data_dir, f"qikan{suffix}")
            try:
                if os.path.exists(wal_file):
                    os.remove(wal_file)
                    logger.info(f"骑砍英雄传：已删除残留文件 {wal_file}")
            except Exception:
                pass

        await asyncio.sleep(0.3)

        self._data_manager = DataManager(data_dir)
        await self._data_manager.initialize()

        self._auth_manager = AuthManager(self._data_manager.db, data_dir)
        await self._auth_manager.initialize()

        # 游戏引擎
        cooldown = self._get_cfg_int("cultivate_cooldown", 60)
        if self._engine is None:
            self._engine = GameEngine(self._data_manager, cultivate_cooldown=cooldown)
            self._engine.auth = self._auth_manager
            self._engine.set_name_reviewer(self._review_name_with_ai)
            self._engine.set_chat_reviewer(self._review_chat_with_ai)
            self._engine.set_sect_name_reviewer(self._review_sect_name_with_ai)
        else:
            # 已有 engine，只更新配置
            pass

        if not getattr(self._engine, "_initialized", False):
            await self._engine.initialize()
            self._engine._initialized = True

        self._engine._checkin_config = self._get_checkin_config()
        logger.info("骑砍英雄传：游戏引擎已初始化")

        # Web 服务（可配置开关）
        enable_web = self._get_cfg_bool("enable_web", False)
        if enable_web:
            try:
                from .web.server import WebServer
                host = str(self._get_cfg("web_host", "0.0.0.0"))
                port = self._get_cfg_int("web_port", 8099)
                access_pw = str(self._get_cfg("web_access_password", ""))
                guard_token = str(self._get_cfg("web_guard_token", "")).strip()
                if not access_pw:
                    access_pw = str(self._get_cfg("web_admin_password", ""))
                admin_account = str(
                    self._get_cfg("web_admin_account", self._get_cfg("master_account", "admin"))
                )
                admin_pw = str(self._get_cfg("web_admin_password", ""))
                api_rate_limit_1s_count = self._get_cfg_int("api_rate_limit_1s_count", 10000)
                logger.info(
                    f"骑砍英雄传：Web 配置已加载 enable_web={enable_web}, host={host}, port={port}"
                )
                self._web_server = WebServer(
                    self._engine, host=host, port=port,
                    access_password=access_pw,
                    guard_token=guard_token,
                    admin_account=admin_account,
                    admin_password=admin_pw,
                    command_prefix=CMD_PREFIX,
                    api_rate_limit_1s_count=api_rate_limit_1s_count,
                )
                await self._web_server.start()
                self._web_error_message = ""
                logger.info(f"骑砍英雄传：Web 服务已启动 http://{host}:{port}")
            except ModuleNotFoundError as e:
                self._web_server = None
                self._web_error_message = (
                    f"Web 依赖缺失：{e.name}。请在 AstrBot 环境安装 requirements.txt 中依赖后重载插件。"
                )
                logger.error(f"骑砍英雄传：{self._web_error_message}")
            except Exception:
                self._web_server = None
                self._web_error_message = "Web 服务启动失败，请检查端口占用和依赖安装。"
                logger.exception("骑砍英雄传：Web 服务启动失败")

    async def _review_name_with_ai(self, name: str) -> dict:
        """调用 AstrBot 当前模型对骑士名做安全审核。"""
        get_provider = getattr(self.context, "get_using_provider", None)
        if not callable(get_provider):
            return {"allow": True, "reason": "AI审核器未配置，按本地规则放行"}

        try:
            provider = get_provider()
        except Exception:
            return {"allow": True, "reason": "AI审核器初始化失败，按本地规则放行"}
        if hasattr(provider, "__await__"):
            try:
                provider = await provider
            except Exception:
                return {"allow": True, "reason": "AI审核器初始化失败，按本地规则放行"}

        if not provider or not hasattr(provider, "text_chat"):
            return {"allow": True, "reason": "AI审核器未就绪，按本地规则放行"}

        prompt = (
            "你是骑砍游戏骑士名审核器。\n"
            "请判断该骑士名是否明显包含以下内容："
            "色情、侮辱谩骂、人身攻击、低俗挑逗。\n"
            "只有在\"高度确定违规\"时才拒绝；不确定时必须放行。\n"
            "只输出JSON，不要任何额外文本，格式："
            "{\"allow\": true/false, \"reason\": \"一句话原因\"}。\n"
            f"待审核骑士名：{name}"
        )

        try:
            llm_response = await provider.text_chat(prompt=prompt, contexts=[])
        except Exception:
            logger.exception("骑砍英雄传：骑士名AI审核调用失败")
            return {"allow": True, "reason": "AI审核服务异常，按本地规则放行"}

        raw = str(
            getattr(llm_response, "completion_text", "")
            or getattr(llm_response, "text", "")
            or llm_response
            or ""
        ).strip()
        if not raw:
            return {"allow": True, "reason": "AI审核结果为空，按本地规则放行"}

        # 优先解析 JSON
        try:
            m = re.search(r"\{[\s\S]*\}", raw)
            if m:
                obj = json.loads(m.group(0))
                allow = bool(obj.get("allow", obj.get("ok", False)))
                reason = str(obj.get("reason", "")).strip()
                return {"allow": allow, "reason": reason}
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass

        # JSON 解析失败时做文本兜底（宽松策略：仅明确违规才拒绝）
        text = raw.lower()
        blocked_signals = (
            "\"allow\":false", "\"allow\": false",
            "判定违规", "明显违规", "拒绝通过", "不予通过",
        )
        passed_signals = (
            "\"allow\":true", "\"allow\": true",
            "allow:true", "allow = true",
            "通过", "合规", "正常", "可用",
        )
        if any(s in text for s in blocked_signals):
            return {"allow": False, "reason": "AI判定骑士名违规"}
        if any(s in text for s in passed_signals):
            return {"allow": True, "reason": ""}
        return {"allow": True, "reason": "AI审核结果不明确，按本地规则放行"}

    async def _review_sect_name_with_ai(self, name: str) -> dict:
        """调用 AstrBot 当前模型对家族名称做安全审核。"""
        def local_review() -> dict:
            allow, reason = self._engine._local_name_risk_check(name)
            return {"allow": bool(allow), "reason": str(reason or "").strip()}

        get_provider = getattr(self.context, "get_using_provider", None)
        if not callable(get_provider):
            return local_review()

        try:
            provider = get_provider()
        except Exception:
            return local_review()
        if hasattr(provider, "__await__"):
            try:
                provider = await asyncio.wait_for(provider, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("骑砍英雄传：家族名AI审核器初始化超时，降级到本地规则")
                return local_review()
            except Exception:
                return local_review()

        if not provider or not hasattr(provider, "text_chat"):
            return local_review()

        prompt = (
            "你是骑砍游戏家族名称审核器。\n"
            "请判断该家族名称是否明显包含以下内容："
            "色情、侮辱谩骂、歧视攻击、低俗挑逗。\n"
            "注意：中世纪风格名称（如红狮子家族、灰狼骑士团）属于正常风格，应予放行。\n"
            "只有在「高度确定违规」时才拒绝；不确定时必须放行。\n"
            "只输出JSON，不要任何额外文本，格式："
            "{\"allow\": true/false, \"reason\": \"一句话原因\"}。\n"
            f"待审核家族名称：{name}"
        )

        try:
            llm_response = await asyncio.wait_for(
                provider.text_chat(prompt=prompt, contexts=[]),
                timeout=5.0,
            )
        except asyncio.TimeoutError:
            logger.warning("骑砍英雄传：家族名AI审核超时，降级到本地规则")
            return local_review()
        except Exception:
            logger.exception("骑砍英雄传：家族名AI审核调用失败")
            return local_review()

        raw = str(
            getattr(llm_response, "completion_text", "")
            or getattr(llm_response, "text", "")
            or llm_response
            or ""
        ).strip()
        if not raw:
            return {"allow": True, "reason": "AI审核结果为空，按本地规则放行"}

        try:
            m = re.search(r"\{[\s\S]*\}", raw)
            if m:
                obj = json.loads(m.group(0))
                allow = bool(obj.get("allow", obj.get("ok", False)))
                reason = str(obj.get("reason", "")).strip()
                return {"allow": allow, "reason": reason}
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass

        text = raw.lower()
        blocked_signals = (
            "\"allow\":false", "\"allow\": false",
            "判定违规", "明显违规", "拒绝通过", "不予通过",
        )
        passed_signals = (
            "\"allow\":true", "\"allow\": true",
            "allow:true", "allow = true",
            "通过", "合规", "正常", "可用",
        )
        if any(s in text for s in blocked_signals):
            return {"allow": False, "reason": "AI判定家族名违规"}
        if any(s in text for s in passed_signals):
            return {"allow": True, "reason": ""}
        return {"allow": True, "reason": "AI审核结果不明确，按本地规则放行"}

    async def _review_chat_with_ai(self, content: str) -> dict:
        """调用 AstrBot 当前模型对世界频道消息做安全审核。"""
        get_provider = getattr(self.context, "get_using_provider", None)
        if not callable(get_provider):
            return {"allow": True, "reason": ""}

        try:
            provider = get_provider()
        except Exception:
            return {"allow": True, "reason": ""}
        if hasattr(provider, "__await__"):
            try:
                provider = await provider
            except Exception:
                return {"allow": True, "reason": ""}

        if not provider or not hasattr(provider, "text_chat"):
            return {"allow": True, "reason": ""}

        prompt = (
            "你是骑砍游戏世界频道聊天内容审核器。\n"
            "请判断以下聊天内容是否包含："
            "脏话、骂人、色情、低俗挑逗、人身攻击。\n"
            "只有在\"高度确定违规\"时才拒绝；普通聊天和游戏讨论必须放行。\n"
            "只输出JSON，不要任何额外文本，格式："
            '{"allow": true/false, "reason": "一句话原因"}。\n'
            f"待审核内容：{content}"
        )

        try:
            llm_response = await provider.text_chat(prompt=prompt, contexts=[])
        except Exception:
            logger.exception("骑砍英雄传：聊天AI审核调用失败")
            return {"allow": True, "reason": ""}

        raw = str(
            getattr(llm_response, "completion_text", "")
            or getattr(llm_response, "text", "")
            or llm_response
            or ""
        ).strip()
        if not raw:
            return {"allow": True, "reason": ""}

        try:
            m = re.search(r"\{[\s\S]*\}", raw)
            if m:
                obj = json.loads(m.group(0))
                allow = bool(obj.get("allow", obj.get("ok", False)))
                reason = str(obj.get("reason", "")).strip()
                return {"allow": allow, "reason": reason}
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass

        text = raw.lower()
        if any(s in text for s in ('"allow":false', '"allow": false', "违规", "拒绝")):
            return {"allow": False, "reason": "消息包含不当内容"}
        return {"allow": True, "reason": ""}

    # ==================== 指令组 ====================

    def _resolve_player_id(self, event: AstrMessageEvent) -> str | None:
        """从聊天事件解析绑定的玩家ID。"""
        chat_user_id = event.get_sender_id()
        if self._engine.auth:
            return self._engine.auth.get_player_id_for_chat(chat_user_id)
        return None

    @filter.command_group(CMD_PREFIX)
    def qikan_group(self):
        """骑砍英雄传 — 文字骑砍游戏"""
        pass

    @filter.command_group("骑砍管理员")
    def admin_group(self):
        """骑砍管理员命令"""
        pass

    # 指令定义表，用于动态帮助输出
    _CMD_HELP = [
        ("帮助", "显示所有可用指令"),
        ("签到", "每日签到领取奖励"),
        ("面板", "查看角色属性面板"),
        ("训练", "训练获取经验"),
        ("挂机 <分钟>", "挂机训练(1~60分钟)"),
        ("结算", "领取挂机训练收益"),
        ("取消挂机", "随时取消挂机并放弃本次收益"),
        ("征战", "进入副本征战"),
        ("晋升", "尝试晋升当前爵位"),
        ("背包", "查看背包物品"),
        ("使用 <物品名>", "使用消耗品"),
        ("装备 <装备名>", "装备武器或护甲"),
        ("卸下 <武器|护甲>", "卸下已装备的物品"),
        ("查看 <装备|物品|技能> <物品名>", "按类型精确查看详情"),
        ("回收 <装备|物品|技能> <物品名> [数量]", "回收物品获取第纳尔（推荐按类型精确命中）"),
        ("集市 [页码]", "查看集市商品列表"),
        ("上架 <装备|物品|技能> <物品名> <数量> <单价>", "上架物品到集市（推荐按类型精确命中）"),
        ("购买 <编号>", "从集市购买商品"),
        ("下架 <编号>", "取消上架商品"),
        ("排行", "查看骑士爵位排行榜"),
        ("死亡排行", "查看死亡次数排行榜"),
        ("在线", "查看当前在线骑士"),
        ("登录 <密钥>", "用Web端6位密钥绑定角色"),
        ("登出", "解除QQ角色绑定"),
        ("web", "获取网页版链接"),
    ]

    @qikan_group.command("帮助")
    async def show_help(self, event: AstrMessageEvent):
        """显示所有可用指令。"""
        img_bytes = renderer.render_help(self._CMD_HELP, CMD_PREFIX)
        img_path = self._render_image_path(img_bytes, "help")
        if not img_path:
            yield event.plain_result("帮助图片渲染失败，请稍后重试")
            return
        yield event.image_result(img_path)

    @qikan_group.command("面板")
    async def show_panel(self, event: AstrMessageEvent):
        """查看角色面板。"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        panel = await self._engine.get_panel(player_id)
        if not panel:
            yield event.plain_result("角色数据异常，请联系管理员")
            return
        img_bytes = renderer.render_panel(panel)
        img_path = self._render_image_path(img_bytes, "panel")
        if not img_path:
            yield event.plain_result("面板图片渲染失败，请稍后重试")
            return
        yield event.image_result(img_path)

    @qikan_group.command("训练")
    async def cultivate(self, event: AstrMessageEvent):
        """训练获取经验。"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        result = await self._engine.cultivate(player_id)
        yield event.plain_result(result["message"])

    @qikan_group.command("签到")
    async def daily_checkin(self, event: AstrMessageEvent):
        """每日签到领取奖励。"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        result = await self._engine.daily_checkin(player_id)
        if result["success"]:
            img_bytes = renderer.render_checkin(result)
            img_path = self._render_image_path(img_bytes, "checkin")
            if img_path:
                yield event.image_result(img_path)
                return
        yield event.plain_result(result["message"])

    @qikan_group.command("挂机")
    async def afk_cultivate(self, event: AstrMessageEvent, minutes: str = ""):
        """开始挂机修炼。"""
        if not minutes.strip():
            yield event.plain_result(f"请指定挂机时长(分钟)，如：{self._cmd('挂机 10')}")
            return
        try:
            mins = int(minutes.strip())
        except ValueError:
            yield event.plain_result("请输入有效的分钟数")
            return
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        result = await self._engine.start_afk_cultivate(player_id, mins)
        yield event.plain_result(result["message"])

    @qikan_group.command("结算")
    async def collect_afk(self, event: AstrMessageEvent):
        """领取挂机修炼收益。"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        result = await self._engine.collect_afk_cultivate(player_id)
        if result["success"]:
            img_bytes = renderer.render_afk_result(result)
            img_path = self._render_image_path(img_bytes, "afk")
            if img_path:
                yield event.image_result(img_path)
                return
        yield event.plain_result(result["message"])

    @qikan_group.command("取消挂机")
    async def cancel_afk(self, event: AstrMessageEvent):
        """取消挂机修炼。"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        result = await self._engine.cancel_afk_cultivate(player_id)
        yield event.plain_result(result["message"])

    @qikan_group.command("征战")
    async def do_adventure(self, event: AstrMessageEvent):
        """进入副本征战。"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        result = await self._engine.adventure(player_id)
        yield event.plain_result(result["message"])

    @qikan_group.command("征战场景")
    async def show_scenes(self, event: AstrMessageEvent):
        """提示旧版征战场景已停用。"""
        yield event.plain_result("旧版征战场景已停用，征战现已改为 Web 端的副本探索。")

    @qikan_group.command("晋升")
    async def breakthrough(self, event: AstrMessageEvent):
        """尝试晋升爵位。"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        result = await self._engine.breakthrough(player_id)
        yield event.plain_result(result["message"])

    @qikan_group.command("背包")
    async def show_inventory(self, event: AstrMessageEvent):
        """查看背包物品。"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        inv = await self._engine.get_inventory(player_id)
        img_bytes = renderer.render_inventory(inv)
        img_path = self._render_image_path(img_bytes, "inventory")
        if not img_path:
            yield event.plain_result("背包图片渲染失败，请稍后重试")
            return
        yield event.image_result(img_path)

    @qikan_group.command("使用")
    async def use_item_cmd(self, event: AstrMessageEvent, item_name: str = ""):
        """使用物品。"""
        if not item_name.strip():
            yield event.plain_result(f"请指定物品名，如：{self._cmd('使用 回血丹')}")
            return
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        result = await self._engine.use_item_by_name(player_id, item_name.strip())
        yield event.plain_result(result["message"])

    @qikan_group.command("装备")
    async def equip_cmd(self, event: AstrMessageEvent, item_name: str = ""):
        """装备武器或护甲。"""
        if not item_name.strip():
            yield event.plain_result(f"请指定装备名，如：{self._cmd('装备 铁剑')}")
            return
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        result = await self._engine.equip_by_name(player_id, item_name.strip())
        yield event.plain_result(result["message"])

    @qikan_group.command("卸下")
    async def unequip_cmd(self, event: AstrMessageEvent, slot_name: str = ""):
        """卸下装备。"""
        slot_map = {
            "武器": "weapon",
            "护甲": "body",
            "头部": "head",
            "手部": "hands",
            "腿部": "legs",
            "肩甲": "shoulders",
            "饰品1": "accessory1",
            "饰品2": "accessory2",
        }
        slot = slot_map.get(slot_name.strip(), "")
        if not slot:
            slots = " / ".join([self._cmd(f"卸下 {k}") for k in slot_map.keys()])
            yield event.plain_result(f"请指定槽位：{slots}")
            return
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        result = await self._engine.unequip_action(player_id, slot)
        yield event.plain_result(result["message"])

    @qikan_group.command("查看")
    async def view_item(self, event: AstrMessageEvent, query_type: str = "", item_name: str = ""):
        """按类型查看物品/装备/被动技能详情。"""
        query_type = query_type.strip()
        item_name = item_name.strip()
        if not query_type or not item_name:
            yield event.plain_result(f"用法：{self._cmd('查看 装备 铁剑')} / {self._cmd('查看 被动技能 灭世雷诀秘籍')} / {self._cmd('查看 战技 基础剑法卷轴')}")
            return

        type_map = {
            "装备": "equipment",
            "物品": "item",
            "技能": "heart_method",
            "战技": "gongfa",
        }
        target_type = type_map.get(query_type)
        if not target_type:
            yield event.plain_result("类型仅支持：装备 / 物品 / 技能 / 战技")
            return

        detail = self._engine.get_item_detail(item_name, query_type=target_type)
        if not detail:
            yield event.plain_result(f"未找到{query_type}「{item_name}」，请检查名称和类型是否正确")
            return
        img_bytes = renderer.render_item_detail(detail)
        img_path = self._render_image_path(img_bytes, "item_detail")
        if not img_path:
            yield event.plain_result("物品详情渲染失败，请稍后重试")
            return
        yield event.image_result(img_path)

    @qikan_group.command("回收")
    async def recycle_cmd(self, event: AstrMessageEvent, args: str = ""):
        """回收物品获取第纳尔。"""
        args = args.strip()
        if not args:
            yield event.plain_result(
                f"用法：{self._cmd('回收 装备 铁剑')} / {self._cmd('回收 装备 铁剑 3')}（兼容旧格式：{self._cmd('回收 铁剑 3')}）"
            )
            return

        user_id = await self._resolve_player_id(event)
        if not user_id:
            yield event.plain_result("你还没有角色，请先创建")
            return

        type_map = {
            "装备": "equipment",
            "物品": "item",
            "技能": "heart_method",
            "战技": "gongfa",
        }
        tokens = args.split()
        if not tokens:
            yield event.plain_result("请输入要回收的物品")
            return

        query_type = None
        count = 1
        item_name = ""
        if tokens[0] in type_map:
            query_type = type_map[tokens[0]]
            if len(tokens) == 1:
                yield event.plain_result("请在类型后输入物品名")
                return
            if len(tokens) >= 3 and tokens[-1].isdigit():
                count = int(tokens[-1])
                item_name = " ".join(tokens[1:-1]).strip()
            else:
                item_name = " ".join(tokens[1:]).strip()
        else:
            if len(tokens) >= 2 and tokens[-1].isdigit():
                count = int(tokens[-1])
                item_name = " ".join(tokens[:-1]).strip()
            else:
                item_name = args

        if not item_name:
            yield event.plain_result("物品名不能为空")
            return

        result = await self._engine.recycle_by_name(user_id, item_name, count, query_type=query_type)
        yield event.plain_result(result["message"])

    @qikan_group.command("集市")
    async def show_market(self, event: AstrMessageEvent, args: str = ""):
        """查看集市商品列表。"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        page = 1
        if args.strip().isdigit():
            page = max(1, int(args.strip()))
        data = await self._engine.market_get_listings(page, page_size=8)
        img_bytes = renderer.render_market(
            data["listings"], data["page"], data["total_pages"],
        )
        img_path = self._render_image_path(img_bytes, "market")
        if not img_path:
            yield event.plain_result("集市图片渲染失败，请稍后重试")
            return
        yield event.image_result(img_path)

    @qikan_group.command("上架")
    async def market_list_cmd(self, event: AstrMessageEvent, args: str = ""):
        """上架物品到集市。"""
        args = args.strip()
        if not args:
            yield event.plain_result(
                f"用法：{self._cmd('上架 装备 铁剑 1 100')}（兼容旧格式：{self._cmd('上架 铁剑 1 100')}）"
            )
            return

        user_id = self._resolve_player_id(event)
        if not user_id:
            yield event.plain_result("你还没有角色，请先创建")
            return

        tokens = args.split()
        if len(tokens) < 3:
            yield event.plain_result(
                f"用法：{self._cmd('上架 装备 铁剑 1 100')}（兼容旧格式：{self._cmd('上架 铁剑 1 100')}）"
            )
            return

        type_map = {
            "装备": "equipment",
            "物品": "item",
            "技能": "heart_method",
            "战技": "gongfa",
        }
        query_type = None

        # 最后两个 token 是数量和单价（支持可选类型前缀）
        try:
            unit_price = int(tokens[-1])
            quantity = int(tokens[-2])
        except ValueError:
            yield event.plain_result("数量和单价必须是整数")
            return

        if tokens[0] in type_map:
            query_type = type_map[tokens[0]]
            item_name = " ".join(tokens[1:-2]).strip()
        else:
            item_name = " ".join(tokens[:-2]).strip()

        if not item_name:
            yield event.plain_result("请输入物品名")
            return

        result = await self._engine.market_list_by_name(
            user_id, item_name, quantity, unit_price, query_type=query_type,
        )
        yield event.plain_result(result["message"])

    @qikan_group.command("购买")
    async def market_buy_cmd(self, event: AstrMessageEvent, args: str = ""):
        """从坊市购买商品。"""
        code = args.strip()
        if not code:
            yield event.plain_result(f"用法：{self._cmd('购买 <编号>')}（坊市商品编号）")
            return

        user_id = self._resolve_player_id(event)
        if not user_id:
            yield event.plain_result("你还没有角色，请先创建")
            return

        result = await self._engine.market_buy_by_prefix(user_id, code)
        yield event.plain_result(result["message"])

    @qikan_group.command("技能")
    async def list_heart_methods(self, event: AstrMessageEvent):
        """提示技能修炼入口已调整为技能书掉落。"""
        yield event.plain_result("已取消直接选择技能。\n请通过征战掉落【普通技能书】，再在背包中使用技能书进行训练。")

    @qikan_group.command("学习技能")
    async def learn_heart_method_cmd(self, event: AstrMessageEvent, method_name: str = ""):
        """提示技能修炼入口已调整为技能书掉落。"""
        yield event.plain_result("已取消直接选择技能。\n请在背包中使用征战掉落的【普通技能书】进行训练。")

    @qikan_group.command("web")
    async def web_link(self, event: AstrMessageEvent):
        """获取网页游戏链接。"""
        enable_web = self._get_cfg_bool("enable_web", False)
        if not enable_web:
            yield event.plain_result("Web 游戏界面未启用")
            return
        if not self._web_server:
            msg = self._web_error_message or "Web 服务未启动，请检查插件日志。"
            yield event.plain_result(msg)
            return
        port = self._get_cfg_int("web_port", 8099)
        default_msg = f"骑砍英雄传网页版：http://<服务器IP>:{port}\n在浏览器中打开即可游玩"
        template = str(self._get_cfg("web_link_message", default_msg))
        yield event.plain_result(template.replace("{port}", str(port)))

    @qikan_group.command("登录")
    async def chat_login(self, event: AstrMessageEvent, key: str = ""):
        """用Web端密钥登录。"""
        if not key.strip():
            yield event.plain_result(
                "请输入从Web端获取的6位密钥\n"
                f"用法：{self._cmd('登录 123456')}\n"
                "密钥获取方式：在Web端登录后点击「获取QQ绑定密钥」"
            )
            return

        if not self._engine.auth:
            yield event.plain_result("认证系统未初始化")
            return

        chat_user_id = event.get_sender_id()
        player_id = await self._engine.auth.verify_bind_key(key.strip(), chat_user_id)
        if not player_id:
            err = self._engine.auth.last_bind_error or "密钥无效或已过期，请重新从Web端获取"
            yield event.plain_result(err)
            return

        player = await self._engine.get_player(player_id)
        if not player:
            yield event.plain_result("关联角色不存在，请联系管理员")
            return

        player.unified_msg_origin = event.unified_msg_origin
        await self._engine._save_player(player)

        yield event.plain_result(
            f"登录成功！已绑定角色「{player.name}」\n"
            f"绑定有效期：7天\n"
            f"现在可以使用 {self._cmd('面板')}、{self._cmd('修炼')} 等指令了"
        )

    @qikan_group.command("登出")
    async def chat_logout(self, event: AstrMessageEvent):
        """解除QQ绑定。"""
        if not self._engine.auth:
            yield event.plain_result("认证系统未初始化")
            return

        chat_user_id = event.get_sender_id()
        player_id = self._engine.auth.get_player_id_for_chat(chat_user_id)
        if not player_id:
            yield event.plain_result("你当前没有绑定角色")
            return

        await self._engine.auth.unbind_chat(chat_user_id)
        yield event.plain_result("已解除角色绑定")

    @qikan_group.command("排行")
    async def show_rankings(self, event: AstrMessageEvent):
        """查看骑士爵位排行榜。"""
        player_id = self._resolve_player_id(event)
        my_rank = None
        if player_id:
            all_rankings = self._engine.get_rankings(limit=999)
            for r in all_rankings:
                if r["user_id"] == player_id:
                    my_rank = r
                    break
            rankings = all_rankings[:10]
        else:
            rankings = self._engine.get_rankings(limit=10)
        total = len(self._engine._players)
        online_ids = self._engine.get_online_user_ids()
        img_bytes = renderer.render_ranking(rankings, total, len(online_ids), my_rank)
        img_path = self._render_image_path(img_bytes, "ranking")
        if not img_path:
            yield event.plain_result("排行榜图片渲染失败，请稍后重试")
            return
        yield event.image_result(img_path)

    @qikan_group.command("死亡排行")
    async def show_death_rankings(self, event: AstrMessageEvent):
        """查看死亡次数排行榜。"""
        rankings = self._engine.get_death_rankings(limit=10)
        img_bytes = renderer.render_death_ranking(rankings)
        img_path = self._render_image_path(img_bytes, "death_ranking")
        if not img_path:
            yield event.plain_result("死亡排行榜图片渲染失败，请稍后重试")
            return
        yield event.image_result(img_path)

    @qikan_group.command("在线")
    async def show_online(self, event: AstrMessageEvent):
        """查看当前在线骑士。"""
        online_ids = self._engine.get_online_user_ids()
        players_data = []
        for uid in online_ids:
            player = await self._engine.get_player(uid)
            if player:
                from .game.constants import get_realm_name
                players_data.append({
                    "name": player.name,
                    "realm_name": get_realm_name(player.realm, player.sub_realm),
                })
        img_bytes = renderer.render_online(players_data, len(online_ids))
        img_path = self._render_image_path(img_bytes, "online")
        if not img_path:
            yield event.plain_result("在线列表图片渲染失败，请稍后重试")
            return
        yield event.image_result(img_path)

    @qikan_group.command("劫匪")
    async def show_nearby_bandits(self, event: AstrMessageEvent):
        """查看附近的劫匪。"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        player = await self._engine.get_player(player_id)
        if not player:
            yield event.plain_result("角色不存在")
            return
        
        from .game.map_system import get_bandit_manager, BANDIT_TYPE_NAMES, BANDIT_TYPE_ICONS
        
        manager = get_bandit_manager()
        nearby = manager.get_nearby_bandits(player.map_state.x, player.map_state.y, radius=200)
        
        if not nearby:
            yield event.plain_result("你周围没有发现劫匪踪迹。\n可以在大地图上移动寻找劫匪，或者前往已知的匪窝。")
            return
        
        lines = ["🏴 附近发现劫匪：", ""]
        for i, bandit in enumerate(nearby[:5], 1):
            icon = BANDIT_TYPE_ICONS.get(bandit.bandit_type, "⚔️")
            btype = BANDIT_TYPE_NAMES.get(bandit.bandit_type, "未知")
            dist = int(((bandit.x - player.map_state.x) ** 2 + (bandit.y - player.map_state.y) ** 2) ** 0.5)
            lines.append(f"{i}. {icon} {bandit.name}(Lv.{bandit.level} {btype})")
            lines.append(f"   人数: {bandit.member_count} | 血量: {bandit.hp}/{bandit.max_hp}")
            lines.append(f"   距离: {dist} | 经验: {bandit.exp_reward} | 赏金: {bandit.gold_reward}")
            lines.append(f"   ID: {bandit.bandit_id}")
            lines.append("")
        
        lines.append(f"共发现 {len(nearby)} 组劫匪")
        lines.append(f"使用 {self._cmd('攻击 <ID>')} 攻击劫匪")
        
        yield event.plain_result("\n".join(lines))

    @qikan_group.command("攻击")
    async def attack_bandit(self, event: AstrMessageEvent, bandit_id: str = ""):
        """攻击劫匪。"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        if not bandit_id.strip():
            yield event.plain_result(f"请指定劫匪ID，如：{self._cmd('攻击 bandit_1')}\n使用 {self._cmd('劫匪')} 查看附近劫匪ID")
            return
        
        from .game.bandit_combat import engage_bandit
        from .game.heal_skills import can_fight, check_injury_expired
        
        player = self._engine.get_player(player_id)
        if not player:
            yield event.plain_result("玩家数据异常")
            return
        
        check_injury_expired(player)
        
        can, reason = can_fight(player)
        if not can:
            yield event.plain_result(reason)
            return
        
        result = await engage_bandit(player, bandit_id.strip())
        
        if not result["success"]:
            yield event.plain_result(result["message"])
            return
        
        lines = [result["message"]]
        
        if result.get("defeated"):
            lines.append("")
            lines.append(f"🎉 战利品：")
            lines.append(f"  经验 +{result['exp_reward']}")
            lines.append(f"  第纳尔 +{result['gold_reward']}")
            
            if result.get("loot"):
                loot = result["loot"]
                lines.append(f"  装备 {loot['tier_name']}【{loot['item_name']}】")
            
            if result.get("rank"):
                lines.append("")
                lines.append(f"🏆 称号：{result['rank']} (Lv.{result['rank_level']})")
        else:
            lines.append("")
            lines.append(f"你的血量: {result['player_hp']}/{result['player_max_hp']}")
            
            if result.get("injured"):
                lines.append("")
                lines.append("⚠️ 你受到重创，陷入重伤状态！")
                lines.append("需要治疗才能恢复战斗能力。使用治疗技能或道具进行治疗。")
            else:
                lines.append(f"继续攻击以击败劫匪！")
        
        yield event.plain_result("\n".join(lines))

    @qikan_group.command("劫匪列表")
    async def list_all_bandits(self, event: AstrMessageEvent):
        """查看所有劫匪。"""
        from .game.map_system import get_bandit_manager, BANDIT_TYPE_NAMES, BANDIT_TYPE_ICONS
        
        manager = get_bandit_manager()
        all_bandits = manager.get_all_active_bandits()
        
        if not all_bandits:
            yield event.plain_result("目前地图上没有活跃的劫匪。")
            return
        
        lines = ["🏴 卡拉迪亚大陆劫匪分布：", ""]
        
        by_type = {}
        for bandit in all_bandits:
            btype = bandit.bandit_type
            if btype not in by_type:
                by_type[btype] = []
            by_type[btype].append(bandit)
        
        for btype, bandits in sorted(by_type.items()):
            icon = BANDIT_TYPE_ICONS.get(btype, "⚔️")
            bname = BANDIT_TYPE_NAMES.get(btype, "未知")
            lines.append(f"{icon} {bname}：{len(bandits)}组")
            for bandit in bandits[:3]:
                lines.append(f"   - {bandit.name}(Lv.{bandit.level}) 人数:{bandit.member_count} 经验:{bandit.exp_reward}")
            if len(bandits) > 3:
                lines.append(f"   ... 还有{len(bandits) - 3}组")
            lines.append("")
        
        lines.append(f"总计 {len(all_bandits)} 组劫匪活跃中")
        
        yield event.plain_result("\n".join(lines))

    @qikan_group.command("劫匪信息")
    async def bandit_info(self, event: AstrMessageEvent, bandit_id: str = ""):
        """查看劫匪详细信息。"""
        if not bandit_id.strip():
            yield event.plain_result(f"请指定劫匪ID，如：{self._cmd('劫匪信息 bandit_1')}")
            return
        
        from .game.map_system import get_bandit_manager, BANDIT_TYPE_NAMES, BANDIT_TYPE_ICONS
        
        manager = get_bandit_manager()
        bandit = manager.bandit_groups.get(bandit_id.strip())
        
        if not bandit:
            yield event.plain_result("未找到该劫匪")
            return
        
        icon = BANDIT_TYPE_ICONS.get(bandit.bandit_type, "⚔️")
        btype = BANDIT_TYPE_NAMES.get(bandit.bandit_type, "未知")
        
        status = "已被击败" if bandit.is_defeated else "活跃"
        if bandit.is_defeated:
            import time as time_module
            remaining = int(bandit.last_defeated_time + bandit.respawn_time - time_module.time())
            status = f"已击败，{remaining}秒后复活"
        
        lines = [
            f"{icon} {bandit.name}",
            f"类型: {btype} | 等级: {bandit.level}",
            f"状态: {status}",
            f"人数: {bandit.member_count}/{bandit.max_member_count}",
            f"血量: {bandit.hp}/{bandit.max_hp}",
            f"攻击: {bandit.attack} | 防御: {bandit.defense}",
            f"位置: ({int(bandit.x)}, {int(bandit.y)})",
            f"经验奖励: {bandit.exp_reward}",
            f"金币奖励: {bandit.gold_reward}",
        ]
        
        yield event.plain_result("\n".join(lines))

    @qikan_group.command("治疗")
    async def heal_command(self, event: AstrMessageEvent, skill_name: str = ""):
        """治疗自己或治疗重伤状态。"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        player = await self._engine.get_player(player_id)
        if not player:
            yield event.plain_result("角色不存在")
            return
        
        from .game.heal_skills import (
            can_fight, check_injury_expired, cure_injury,
            HEAL_SKILLS, get_heal_skill
        )
        
        check_injury_expired(player)
        
        if player.is_injured:
            can, reason = can_fight(player)
            if not can:
                yield event.plain_result(f"你处于重伤状态：{reason}")
                
                if skill_name:
                    skill = get_heal_skill(skill_name.strip())
                    if not skill:
                        yield event.plain_result(f"未找到医疗技能：{skill_name}")
                        return
                    
                    result = cure_injury(player, skill)
                    yield event.plain_result(result["message"])
                    if result["cured"]:
                        yield event.plain_result(f"生命已恢复至 {player.hp}/{player.max_hp}")
                    return
                
                lines = ["你可以使用以下技能进行治疗：", ""]
                for skill_id, skill in HEAL_SKILLS.items():
                    if skill.skill_level_req <= getattr(player, 'heal_skill_level', 0):
                        lines.append(f"• {skill.name} (消耗 {skill.stamina_cost * 3} 体力)")
                lines.append("")
                lines.append(f"使用方法：{self._cmd('治疗 <技能名>')}")
                lines.append(f"例如：{self._cmd('治疗 战地医疗')}")
                yield event.plain_result("\n".join(lines))
                return
        
        if player.hp >= player.max_hp:
            yield event.plain_result("你已经很健康，不需要治疗")
            return
        
        if skill_name:
            skill = get_heal_skill(skill_name.strip())
            if not skill:
                yield event.plain_result(f"未找到医疗技能：{skill_name}")
                return
            
            from .game.heal_skills import use_heal_skill
            result = use_heal_skill(player, skill.skill_id)
            yield event.plain_result(result["message"])
            if result.get("current_hp"):
                yield event.plain_result(f"当前生命：{result['current_hp']}/{player.max_hp}")
        else:
            yield event.plain_result(f"当前生命：{player.hp}/{player.max_hp}")
            yield event.plain_result(f"使用方法：{self._cmd('治疗 <技能名>')}")

    @qikan_group.command("等级")
    async def show_level(self, event: AstrMessageEvent):
        """查看当前等级和经验。"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        player = await self._engine.get_player(player_id)
        if not player:
            yield event.plain_result("角色不存在")
            return
        
        from .game.player_level import LevelSystem, MAX_LEVEL, get_title_manager
        
        progress = LevelSystem.get_exp_progress(player)
        title_manager = get_title_manager()
        title = title_manager.get_player_title(player_id)
        
        lines = [
            f"⚔️ 等级：Lv.{player.level} / {MAX_LEVEL}",
            f"经验：{progress['exp']} / {progress['exp_to_next']}",
            f"进度条：[{'█' * int(progress['progress'] // 5)}{'░' * (20 - int(progress['progress'] // 5))}] {progress['progress']:.1f}%",
        ]
        
        if player.unallocated_points > 0:
            lines.append("")
            lines.append(f"📦 可分配属性点：{player.unallocated_points}")
            lines.append(f"使用 {self._cmd('加点 <属性>')} 分配")
            lines.append("属性类型：力量(str)、敏捷(agi)、活力(vit)、统御(lead)")
        
        if title:
            lines.append("")
            lines.append(f"🏆 称号：{title['name']}")
        
        yield event.plain_result("\n".join(lines))

    @qikan_group.command("属性")
    async def show_attributes(self, event: AstrMessageEvent):
        """查看属性分配情况。"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        player = await self._engine.get_player(player_id)
        if not player:
            yield event.plain_result("角色不存在")
            return
        
        lines = [
            "📊 属性面板",
            "",
            f"力量 (str): {player.attributes.strength} → 攻击 +{player.attributes.get_attack_bonus()}",
            f"敏捷 (agi): {player.attributes.agility} → 防御 +{player.attributes.get_defense_bonus()}",
            f"活力 (vit): {player.attributes.vitality} → 生命 +{player.attributes.get_hp_bonus()}",
            f"统御 (lead): {player.attributes.leadership} → 队伍 +{int(player.attributes.get_leadership_bonus() * 100)}%",
            "",
            f"已分配属性点：{player.attributes.total_points()}",
        ]
        
        if player.unallocated_points > 0:
            lines.append(f"可分配属性点：{player.unallocated_points}")
            lines.append(f"使用 {self._cmd('加点 <属性>')} 分配")
        
        yield event.plain_result("\n".join(lines))

    @qikan_group.command("加点")
    async def allocate_point(self, event: AstrMessageEvent, attr_type: str = ""):
        """分配属性点。"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        if not attr_type.strip():
            yield event.plain_result(
                f"用法：{self._cmd('加点 <属性>')}\n"
                "属性类型：\n"
                "  力量/str - 增加攻击力\n"
                "  敏捷/agi - 增加防御力\n"
                "  活力/vit - 增加生命值\n"
                "  统御/lead - 增加队伍属性加成\n"
                f"当前可分配：{player_id.unallocated_points if (player := await self._engine.get_player(player_id)) else 0} 点"
            )
            return
        
        player = await self._engine.get_player(player_id)
        if not player:
            yield event.plain_result("角色不存在")
            return
        
        from .game.player_level import LevelSystem
        
        result = LevelSystem.allocate_point(player, attr_type.strip())
        yield event.plain_result(result["message"])

    @qikan_group.command("我的称号")
    async def my_title(self, event: AstrMessageEvent):
        """查看当前称号。"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        from .game.player_level import get_title_manager
        
        title_manager = get_title_manager()
        title = title_manager.get_player_title(player_id)
        
        if not title:
            yield event.plain_result("你目前没有称号")
            return
        
        lines = [
            f"🏆 当前称号：{title['name']}",
            f"描述：{title.get('description', '无')}",
            "",
            "称号效果：",
        ]
        
        if title.get("attack_bonus"):
            lines.append(f"  攻击力 +{title['attack_bonus']}")
        if title.get("defense_bonus"):
            lines.append(f"  防御力 +{title['defense_bonus']}")
        if title.get("hp_bonus"):
            lines.append(f"  生命值 +{title['hp_bonus']}")
        if title.get("exp_bonus"):
            lines.append(f"  经验获取 +{int(title['exp_bonus'] * 100)}%")
        if title.get("gold_bonus"):
            lines.append(f"  金币获取 +{int(title['gold_bonus'] * 100)}%")
        
        yield event.plain_result("\n".join(lines))

    @qikan_group.command("技能")
    async def show_skills(self, event: AstrMessageEvent):
        """查看骑砍技能列表"""
        from .game.skills_simple import SKILL_TREES, get_skill_trees_by_category, HEART_METHOD_REGISTRY
        
        player_id = self._resolve_player_id(event)
        player = None
        if player_id:
            player = await self._engine.get_player(player_id)
        
        lines = ["⚔️ 骑砍技能系统", ""]
        
        categories = get_skill_trees_by_category()
        
        cat_names = {
            "personal": "【个人技能】",
            "weapon": "【武器技能】",
            "horse": "【骑乘技能】",
            "social": "【社交技能】",
        }
        
        for cat_id, cat_name in cat_names.items():
            trees = categories.get(cat_id, [])
            if trees:
                lines.append(cat_name)
                for tree in trees:
                    lines.append(f"  • {tree['name']}: {tree['desc']}")
                lines.append("")
        
        lines.append("使用 /skills 打开技能树界面查看详细")
        
        yield event.plain_result("\n".join(lines))

    @qikan_group.command("技能树")
    async def show_skill_trees(self, event: AstrMessageEvent):
        """查看所有技能树详情"""
        from .game.skills_simple import SKILL_TREES, HEART_METHOD_REGISTRY
        
        lines = ["⚔️ 骑砍技能树", ""]
        
        for tree_id, tree in SKILL_TREES.items():
            lines.append(f"【{tree['name']}】{tree['desc']}")
            for skill_id in tree['skills']:
                skill = HEART_METHOD_REGISTRY.get(skill_id)
                if skill:
                    lines.append(f"  {skill.name}: {skill.description}")
            lines.append("")
        
        yield event.plain_result("\n".join(lines))

    # ══════════════════════════════════════════════════════════════
    # 医疗与药剂命令
    # ══════════════════════════════════════════════════════════════

    @qikan_group.command("医疗技能")
    async def show_heal_skills(self, event: AstrMessageEvent):
        """查看医疗技能列表"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        player = await self._engine.get_player(player_id)
        if not player:
            yield event.plain_result("角色不存在")
            return
        
        from .game.heal_skills import format_heal_skills_list
        yield event.plain_result(format_heal_skills_list(player))

    @qikan_group.command("治疗")
    async def use_heal_skill_cmd(self, event: AstrMessageEvent, skill_name: str = ""):
        """使用医疗技能"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        if not skill_name.strip():
            yield event.plain_result(
                f"用法：{self._cmd('治疗 <技能名>')}\n"
                "可用技能：战场包扎、野战救护、战地医疗、野战外科、创伤治疗、外科大师"
            )
            return
        
        player = await self._engine.get_player(player_id)
        if not player:
            yield event.plain_result("角色不存在")
            return
        
        skill_map = {
            "包扎": "basic_bandage",
            "战场包扎": "basic_bandage",
            "野战": "field_dressing",
            "野战救护": "field_dressing",
            "战地医疗": "battlefield_medicine",
            "外科": "field_surgery",
            "野战外科": "field_surgery",
            "创伤": "trauma_treatment",
            "创伤治疗": "trauma_treatment",
            "大师": "master_surgeon",
            "外科大师": "master_surgeon",
        }
        
        skill_id = skill_map.get(skill_name.strip())
        if not skill_id:
            yield event.plain_result(f"未找到技能：{skill_name}\n可用：战场包扎、野战救护、战地医疗、野战外科、创伤治疗、外科大师")
            return
        
        from .game.heal_skills import use_heal_skill
        result = use_heal_skill(player, skill_id)
        yield event.plain_result(result["message"])

    @qikan_group.command("药剂列表")
    async def show_potions(self, event: AstrMessageEvent):
        """查看可用药剂"""
        from .game.simple_potions import format_potion_shop
        yield event.plain_result(format_potion_shop())

    @qikan_group.command("使用药剂")
    async def use_potion_cmd(self, event: AstrMessageEvent, potion_name: str = ""):
        """使用药剂"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        if not potion_name.strip():
            yield event.plain_result(
                f"用法：{self._cmd('使用药剂 <药剂名>')}\n"
                "绷带、草药、劣质药剂、小型治疗药水、中型治疗药水、大型治疗药水、治疗秘药"
            )
            return
        
        player = await self._engine.get_player(player_id)
        if not player:
            yield event.plain_result("角色不存在")
            return
        
        potion_map = {
            "绷带": "potion_bandage",
            "草药": "potion_herb",
            "劣质药剂": "potion_apothecary",
            "小型治疗药水": "potion_health_small",
            "中型治疗药水": "potion_health_medium",
            "大型治疗药水": "potion_health_large",
            "治疗秘药": "potion_health_elixir",
            "神圣治疗药水": "potion_grand_healing",
            "解毒剂": "potion_antidote",
        }
        
        potion_id = potion_map.get(potion_name.strip())
        if not potion_id:
            yield event.plain_result(f"未找到药剂：{potion_name}")
            return
        
        from .game.simple_potions import use_potion
        result = use_potion(player, potion_id)
        yield event.plain_result(result["message"])

    @qikan_group.command("购买药剂")
    async def buy_potion(self, event: AstrMessageEvent, potion_name: str = ""):
        """购买药剂"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        if not potion_name.strip():
            yield event.plain_result(f"用法：{self._cmd('购买药剂 <药剂名>')}")
            return
        
        player = await self._engine.get_player(player_id)
        if not player:
            yield event.plain_result("角色不存在")
            return
        
        potion_map = {
            "绷带": ("potion_bandage", 10),
            "草药": ("potion_herb", 25),
            "劣质药剂": ("potion_apothecary", 50),
            "小型治疗药水": ("potion_health_small", 100),
            "中型治疗药水": ("potion_health_medium", 250),
            "解毒剂": ("potion_antidote", 80),
            "大型治疗药水": ("potion_health_large", 500),
            "治疗秘药": ("potion_health_elixir", 1500),
            "神圣治疗药水": ("potion_grand_healing", 3000),
        }
        
        if potion_name.strip() not in potion_map:
            yield event.plain_result(f"未找到药剂：{potion_name}")
            return
        
        potion_id, price = potion_map[potion_name.strip()]
        
        if player.spirit_stones < price:
            yield event.plain_result(f"金币不足，需要 {price} 金币，你只有 {player.spirit_stones} 金币")
            return
        
        player.spirit_stones -= price
        
        if not hasattr(player, 'inventory'):
            player.inventory = {}
        
        player.inventory[potion_id] = player.inventory.get(potion_id, 0) + 1
        
        yield event.plain_result(f"购买了 {potion_name}，花费 {price} 金币")

    # ══════════════════════════════════════════════════════════════
    # 医疗系统命令
    # ══════════════════════════════════════════════════════════════

    @qikan_group.command("采集")
    async def gather_cmd(self, event: AstrMessageEvent):
        """采集草药"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        result = await self._engine.gather_herbs(player_id)
        yield event.plain_result(result["message"])

    @qikan_group.command("制作")
    async def craft_cmd(self, event: AstrMessageEvent, recipe_name: str = ""):
        """制作医疗物品"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        if not recipe_name.strip():
            from .game.crafting import format_recipes_list
            player = await self._engine.get_player(player_id)
            if player:
                yield event.plain_result(format_recipes_list(player))
            else:
                yield event.plain_result("角色不存在")
            return
        
        recipe_map = {
            "绷带": "make_bandage",
            "高级绷带": "make_bandage_advanced",
            "解毒剂": "make_antidote",
            "草药": "make_healing_herb",
        }
        
        recipe_id = recipe_map.get(recipe_name.strip())
        if not recipe_id:
            yield event.plain_result(f"未找到配方：{recipe_name}")
            return
        
        result = await self._engine.craft_item(player_id, recipe_id)
        yield event.plain_result(result["message"])

    @qikan_group.command("使用草药")
    async def use_herb_cmd(self, event: AstrMessageEvent):
        """使用背包中的草药"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        result = await self._engine.use_medical_item(player_id, "herb_use")
        yield event.plain_result(result["message"])

    @qikan_group.command("使用绷带")
    async def use_bandage_cmd(self, event: AstrMessageEvent):
        """使用绷带"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        result = await self._engine.use_medical_item(player_id, "bandage")
        yield event.plain_result(result["message"])

    @qikan_group.command("使用高级绷带")
    async def use_advanced_bandage_cmd(self, event: AstrMessageEvent):
        """使用高级绷带"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        result = await self._engine.use_medical_item(player_id, "bandage_advanced")
        yield event.plain_result(result["message"])

    @qikan_group.command("医疗信息")
    async def medical_info_cmd(self, event: AstrMessageEvent):
        """查看医疗系统信息"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        info = self._engine.get_medical_info(player_id)
        if not info.get("success"):
            yield event.plain_result(info.get("message", "获取信息失败"))
            return
        
        lines = ["🏥 医疗系统信息：", ""]
        lines.append(f"  急救技能: {info['first_aid_level']} 级")
        lines.append(f"  草药学: {info['herbalism_level']} 级")
        lines.append(f"  外科手术: {info['surgery_level']} 级")
        lines.append("")
        
        gather_info = info.get("gather_info", {})
        lines.append(f"  采集: 消耗{gather_info.get('lingqi_cost', 10)}体力, 预计获得 {gather_info.get('estimated_herbs', '?')} 株")
        
        from .game.crafting import format_inventory_medical
        player = await self._engine.get_player(player_id)
        if player:
            lines.append("")
            lines.append(format_inventory_medical(player))
        
        yield event.plain_result("\n".join(lines))

    # ══════════════════════════════════════════════════════════════
    # 跑商系统命令
    # ══════════════════════════════════════════════════════════════

    @qikan_group.command("商品")
    async def trade_list_cmd(self, event: AstrMessageEvent, buy_or_sell: str = "买"):
        """查看当前城镇的商品列表"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        player = await self._engine.get_player(player_id)
        if not player:
            yield event.plain_result("角色不存在")
            return
        
        if not hasattr(player, 'map_state') or not player.map_state:
            yield event.plain_result("无法获取位置信息")
            return
        
        loc = player.map_state.current_location
        if not loc:
            yield event.plain_result("你不在任何城镇或村庄")
            return
        
        is_buying = "买" in buy_or_sell or "卖" not in buy_or_sell
        
        from .game.trading import format_trade_list
        result = format_trade_list(loc, player, is_buying)
        yield event.plain_result(result)

    @qikan_group.command("买")
    async def trade_buy_cmd(self, event: AstrMessageEvent, goods_name: str = "", count: int = 1):
        """买入商品: 买 商品名 [数量]"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        if not goods_name.strip():
            yield event.plain_result(f"用法：{self._cmd('买 <商品> [数量]')}")
            yield event.plain_result("例如：买 谷物 10")
            return
        
        player = await self._engine.get_player(player_id)
        if not player:
            yield event.plain_result("角色不存在")
            return
        
        if not hasattr(player, 'map_state') or not player.map_state:
            yield event.plain_result("无法获取位置信息")
            return
        
        loc = player.map_state.current_location
        if not loc:
            yield event.plain_result("你不在任何城镇或村庄")
            return
        
        # 查找商品ID
        from .game.trading import GOODS
        good_id = None
        for gid, g in GOODS.items():
            if goods_name.strip() in g.name:
                good_id = gid
                break
        
        if not good_id:
            yield event.plain_result(f"未找到商品：{goods_name}")
            return
        
        result = await self._engine.trade_buy(player_id, good_id, count, loc)
        yield event.plain_result(result.get("message", "购买失败"))

    @qikan_group.command("卖")
    async def trade_sell_cmd(self, event: AstrMessageEvent, goods_name: str = "", count: int = 1):
        """卖出商品: 卖 商品名 [数量]"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        if not goods_name.strip():
            yield event.plain_result(f"用法：{self._cmd('卖 <商品> [数量]')}")
            yield event.plain_result("例如：卖 谷物 10")
            return
        
        player = await self._engine.get_player(player_id)
        if not player:
            yield event.plain_result("角色不存在")
            return
        
        if not hasattr(player, 'map_state') or not player.map_state:
            yield event.plain_result("无法获取位置信息")
            return
        
        loc = player.map_state.current_location
        if not loc:
            yield event.plain_result("你不在任何城镇或村庄")
            return
        
        # 查找商品ID
        from .game.trading import GOODS
        good_id = None
        for gid, g in GOODS.items():
            if goods_name.strip() in g.name:
                good_id = gid
                break
        
        if not good_id:
            yield event.plain_result(f"未找到商品：{goods_name}")
            return
        
        result = await self._engine.trade_sell(player_id, good_id, count, loc)
        yield event.plain_result(result.get("message", "出售失败"))

    @qikan_group.command("背包商品")
    async def trade_inventory_cmd(self, event: AstrMessageEvent):
        """查看背包商品"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        info = self._engine.get_trade_inventory(player_id)
        if not info.get("success"):
            yield event.plain_result(info.get("message", "获取失败"))
            return
        
        goods = info.get("goods", {})
        if not goods:
            yield event.plain_result("🎒 背包商品: (空)")
            return
        
        lines = ["🎒 背包商品:"]
        for good_id, item in goods.items():
            lines.append(f"  {item['name']}: {item['count']}个")
        
        yield event.plain_result("\n".join(lines))

    # ══════════════════════════════════════════════════════════════
    # 锻造系统命令
    # ══════════════════════════════════════════════════════════════

    @qikan_group.command("锻造材料")
    async def forging_materials_cmd(self, event: AstrMessageEvent):
        """查看锻造材料"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        info = self._engine.get_forging_materials(player_id)
        if not info.get("success"):
            yield event.plain_result(info.get("message", "获取失败"))
            return
        
        materials = info.get("materials", {})
        if not materials:
            yield event.plain_result("🔨 锻造材料: (空)")
            return
        
        from .game.forging import format_materials_list
        player = await self._engine.get_player(player_id)
        if player:
            yield event.plain_result(format_materials_list(player))
        else:
            lines = ["🔨 锻造材料:"]
            for mat_id, item in materials.items():
                lines.append(f"  {item['name']}: {item['count']}个")
            yield event.plain_result("\n".join(lines))

    @qikan_group.command("锻造配方")
    async def forging_recipes_cmd(self, event: AstrMessageEvent):
        """查看锻造配方"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        info = self._engine.get_forging_recipes(player_id)
        if not info.get("success"):
            yield event.plain_result(info.get("message", "获取失败"))
            return
        
        recipes = info.get("recipes", [])
        skill_level = info.get("skill_level", 0)
        
        if not recipes:
            yield event.plain_result("⚒️ 锻造配方: (无)")
            return
        
        lines = [f"⚒️ 锻造配方 (锻造等级: {skill_level}):", ""]
        
        weapons = [r for r in recipes if "sword" in r["result"]]
        armors = [r for r in recipes if "armor" in r["result"]]
        
        if weapons:
            lines.append("【武器】")
            for r in weapons:
                acc = f"+{r['accessory']}" if r['accessory'] else ""
                lines.append(f"  {r['name']}: {r['fuel']}+{r['metal']}{acc}")
        
        if armors:
            lines.append("【防具】")
            for r in armors:
                acc = f"+{r['accessory']}" if r['accessory'] else ""
                lines.append(f"  {r['name']}: {r['fuel']}+{r['metal']}{acc}")
        
        yield event.plain_result("\n".join(lines))

    @qikan_group.command("锻造")
    async def forge_cmd(self, event: AstrMessageEvent, recipe_name: str = ""):
        """锻造装备: 锻造 配方名"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        if not recipe_name.strip():
            yield event.plain_result(f"用法：{self._cmd('锻造 <配方名>')}")
            yield event.plain_result("例如：锻造 锻造铁剑")
            return
        
        # 查找配方ID
        from .game.forging import RECIPES
        recipe_id = None
        for rid, r in RECIPES.items():
            if recipe_name.strip() in r.name:
                recipe_id = rid
                break
        
        if not recipe_id:
            yield event.plain_result(f"未找到配方：{recipe_name}")
            return
        
        result = await self._engine.forge_item(player_id, recipe_id)
        yield event.plain_result(result.get("message", "锻造失败"))

    @qikan_group.command("买材料")
    async def buy_material_cmd(self, event: AstrMessageEvent, material_name: str = "", count: int = 1):
        """购买锻造材料: 买材料 材料名 [数量]"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        if not material_name.strip():
            yield event.plain_result(f"用法：{self._cmd('买材料 <材料名> [数量]')}")
            yield event.plain_result("例如：买材料 木柴 10")
            return
        
        player = await self._engine.get_player(player_id)
        if not player:
            yield event.plain_result("角色不存在")
            return
        
        if not hasattr(player, 'map_state') or not player.map_state:
            yield event.plain_result("无法获取位置信息")
            return
        
        loc = player.map_state.current_location
        if not loc:
            yield event.plain_result("你不在任何城镇")
            return
        
        # 查找材料ID
        from .game.forging import FORGING_MATERIALS, get_shop_materials
        shop_mats = get_shop_materials(loc)
        material_id = None
        for m in shop_mats:
            if material_name.strip() in m["name"]:
                material_id = m["material_id"]
                break
        
        if not material_id:
            yield event.plain_result(f"该城镇不出售此材料：{material_name}")
            return
        
        result = await self._engine.buy_forging_material(player_id, material_id, count)
        yield event.plain_result(result.get("message", "购买失败"))

    @qikan_group.command("锻造商店")
    async def forging_shop_cmd(self, event: AstrMessageEvent):
        """查看城镇锻造商店"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        player = await self._engine.get_player(player_id)
        if not player:
            yield event.plain_result("角色不存在")
            return
        
        if not hasattr(player, 'map_state') or not player.map_state:
            yield event.plain_result("无法获取位置信息")
            return
        
        loc = player.map_state.current_location
        if not loc:
            yield event.plain_result("你不在任何城镇")
            return
        
        from .game.forging import get_shop_materials
        shop_mats = get_shop_materials(loc)
        
        lines = ["🏪 锻造材料商店:", ""]
        for m in shop_mats:
            lines.append(f"  {m['name']}: {m['price']}第纳尔")
        
        yield event.plain_result("\n".join(lines))

    # ══════════════════════════════════════════════════════════════
    # 狩猎系统命令
    # ══════════════════════════════════════════════════════════════

    @qikan_group.command("狩猎")
    async def hunt_cmd(self, event: AstrMessageEvent):
        """外出狩猎"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        result = await self._engine.hunt_wildlife(player_id)
        yield event.plain_result(result.get("message", "狩猎失败"))

    @qikan_group.command("狩猎材料")
    async def hunting_materials_cmd(self, event: AstrMessageEvent):
        """查看狩猎获得的材料"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        info = self._engine.get_hunting_info(player_id)
        if info.get("success"):
            yield event.plain_result(info.get("materials", "无材料"))
        else:
            yield event.plain_result(info.get("message", "获取失败"))

    @qikan_group.command("饰品配方")
    async def accessory_recipes_cmd(self, event: AstrMessageEvent):
        """查看饰品制作配方"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        info = self._engine.get_accessory_recipes(player_id)
        if info.get("success"):
            yield event.plain_result(info.get("recipes", "无配方"))
        else:
            yield event.plain_result(info.get("message", "获取失败"))

    @qikan_group.command("制作饰品")
    async def craft_accessory_cmd(self, event: AstrMessageEvent, accessory_name: str = ""):
        """制作饰品: 制作饰品 饰品名"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        if not accessory_name.strip():
            yield event.plain_result(f"用法：{self._cmd('制作饰品 <饰品名>')}")
            yield event.plain_result("例如：制作饰品 狼牙项链")
            return
        
        # 查找饰品ID
        from .game.accessories import ACCESSORIES
        accessory_id = None
        for aid, acc in ACCESSORIES.items():
            if accessory_name.strip() in acc.name:
                accessory_id = aid
                break
        
        if not accessory_id:
            yield event.plain_result(f"未找到饰品：{accessory_name}")
            return
        
        result = await self._engine.craft_accessory(player_id, accessory_id)
        yield event.plain_result(result.get("message", "制作失败"))

    @qikan_group.command("猎人商店")
    async def hunter_shop_cmd(self, event: AstrMessageEvent):
        """查看猎人商店"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        player = await self._engine.get_player(player_id)
        if not player:
            yield event.plain_result("角色不存在")
            return
        
        if not hasattr(player, 'map_state') or not player.map_state:
            yield event.plain_result("无法获取位置信息")
            return
        
        loc = player.map_state.current_location
        if not loc:
            yield event.plain_result("你不在任何城镇")
            return
        
        from .game.hunting import get_hunter_shop_materials
        shop_mats = get_hunter_shop_materials(loc)
        
        lines = ["🏪 猎人商店:", ""]
        for m in shop_mats:
            lines.append(f"  {m['name']}: {m['price']}第纳尔")
        
        yield event.plain_result("\n".join(lines))

    @qikan_group.command("任务")
    async def city_quests_cmd(self, event: AstrMessageEvent):
        """查看城市任务列表"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        result = await self._engine.get_city_quests(player_id)
        if not result.get("success"):
            yield event.plain_result(result.get("message", "获取任务失败"))
            return
        
        location_name = result.get("location_name", "未知")
        available = result.get("available_quests", [])
        active = result.get("active_quests", [])
        
        lines = [f"📋 城镇任务 - {location_name}", ""]
        
        if active:
            lines.append("🔄 进行中的任务：")
            for q in active:
                progress = q.get("progress", 0)
                target = q.get("target_count", 1)
                name = q.get("name", "")
                lines.append(f"  • {name} ({progress}/{target})")
            lines.append("")
        
        lines.append("📋 可接任务：")
        if not available:
            lines.append("  暂无可用任务")
        else:
            for i, q in enumerate(available[:8], 1):
                name = q.get("name", "")
                qtype = q.get("quest_type", "")
                exp = q.get("exp_reward", 0)
                gold = q.get("gold_reward", 0)
                lines.append(f"  {i}. {name}")
                lines.append(f"     类型:{qtype} 奖励:{exp}经验/{gold}金币")
        
        lines.append("")
        lines.append(f"用法：{self._cmd('接受任务 <编号>')} 接受任务")
        lines.append(f"       {self._cmd('提交任务 <编号>')} 提交任务")
        
        yield event.plain_result("\n".join(lines))

    @qikan_group.command("接受任务")
    async def accept_quest_cmd(self, event: AstrMessageEvent, quest_index: str = ""):
        """接受城市任务"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        if not quest_index.strip():
            yield event.plain_result(f"用法：{self._cmd('接受任务 <编号>')}\n先使用 {self._cmd('任务')} 查看可用任务编号")
            return
        
        try:
            index = int(quest_index.strip()) - 1
        except ValueError:
            yield event.plain_result("请输入有效的任务编号")
            return
        
        quests_result = await self._engine.get_city_quests(player_id)
        if not quests_result.get("success"):
            yield event.plain_result(quests_result.get("message", "获取任务失败"))
            return
        
        available = quests_result.get("available_quests", [])
        if index < 0 or index >= len(available):
            yield event.plain_result(f"任务编号 {quest_index} 不存在")
            return
        
        quest = available[index]
        quest_id = quest.get("quest_id", "")
        
        result = await self._engine.accept_city_quest(player_id, quest_id)
        yield event.plain_result(result.get("message", "接受任务失败"))

    @qikan_group.command("提交任务")
    async def complete_quest_cmd(self, event: AstrMessageEvent, quest_index: str = ""):
        """提交城市任务"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        if not quest_index.strip():
            yield event.plain_result(f"用法：{self._cmd('提交任务 <编号>')}\n先使用 {self._cmd('任务')} 查看进行中的任务编号")
            return
        
        try:
            index = int(quest_index.strip()) - 1
        except ValueError:
            yield event.plain_result("请输入有效的任务编号")
            return
        
        quests_result = await self._engine.get_city_quests(player_id)
        if not quests_result.get("success"):
            yield event.plain_result(quests_result.get("message", "获取任务失败"))
            return
        
        active = quests_result.get("active_quests", [])
        if index < 0 or index >= len(active):
            yield event.plain_result(f"任务编号 {quest_index} 不存在")
            return
        
        quest = active[index]
        quest_id = quest.get("quest_id", "")
        
        result = await self._engine.complete_city_quest(player_id, quest_id)
        yield event.plain_result(result.get("message", "提交任务失败"))

    @qikan_group.command("传奇Boss")
    async def legendary_boss_cmd(self, event: AstrMessageEvent):
        """查看传奇BOSS列表"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        result = await self._engine.get_legendary_bosses(player_id)
        if not result.get("success"):
            yield event.plain_result("获取失败")
            return
        
        bosses = result.get("bosses", [])
        collection = result.get("collection", {})
        
        lines = ["👹 传奇BOSS列表", ""]
        
        for i, boss in enumerate(bosses, 1):
            name = boss.get("name", "")
            icon = boss.get("icon", "👹")
            is_alive = boss.get("is_alive", False)
            can_respawn = boss.get("can_respawn", False)
            level = boss.get("level", 30)
            set_name = boss.get("set_name", "")
            
            status = "✅ 已降临" if is_alive else ("⏳ 待刷新" if can_respawn else "❎ 休息中")
            lines.append(f"{i}. {icon} {name} Lv.{level}")
            lines.append(f"   状态: {status} | 套装: {set_name}")
            lines.append(f"   赏金: {boss.get('bounty_gold', 0)}金/{boss.get('bounty_exp', 0)}经验")
            lines.append("")
        
        total_pieces = collection.get("total_pieces", 0)
        complete_sets = collection.get("complete_sets", 0)
        lines.append(f"📦 收集: {total_pieces}件 | 完整套装: {complete_sets}套")
        
        lines.append("")
        lines.append(f"用法：{self._cmd('套装')} 查看收集情况")
        
        yield event.plain_result("\n".join(lines))

    @qikan_group.command("套装")
    async def legendary_sets_cmd(self, event: AstrMessageEvent):
        """查看传奇套装收集情况"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        result = await self._engine.get_player_sets(player_id)
        if not result.get("success"):
            yield event.plain_result("获取失败")
            return
        
        collection = result.get("collection", {})
        set_bonus = result.get("set_bonus", {})
        
        sets = collection.get("sets", [])
        
        lines = ["🛡️ 传奇套装收集", ""]
        
        if not sets:
            lines.append("尚���获得任何传奇装备")
            lines.append("击败传奇BOSS可获得")
        else:
            for s in sets:
                set_name = s.get("set_name", "")
                count = s.get("count", 0)
                is_complete = s.get("is_complete", False)
                check = "✅" if is_complete else "⬜"
                lines.append(f"{check} {set_name}: {count}/5件")
        
        if set_bonus.get("total_bonus"):
            lines.append("")
            lines.append("⚡ 套装加成：")
            tb = set_bonus["total_bonus"]
            if tb.get("hp"):
                lines.append(f"  生命+{tb['hp']}")
            if tb.get("attack"):
                lines.append(f"  攻击+{tb['attack']}")
            if tb.get("defense"):
                lines.append(f"  防御+{tb['defense']}")
        
        yield event.plain_result("\n".join(lines))

    @qikan_group.command("挑战Boss")
    async def challenge_legendary_cmd(self, event: AstrMessageEvent, boss_index: str = ""):
        """挑战传奇BOSS"""
        player_id = self._resolve_player_id(event)
        if not player_id:
            yield event.plain_result(f"你还未登录，请先 {self._cmd('登录 <密钥>')}")
            return
        
        if not boss_index.strip():
            yield event.plain_result(f"用法：{self._cmd('挑战Boss <编号>')}\n先使用 {self._cmd('传奇Boss')} 查看编号")
            return
        
        try:
            index = int(boss_index.strip()) - 1
        except ValueError:
            yield event.plain_result("请输入有效的编号")
            return
        
        bosses_result = await self._engine.get_legendary_bosses(player_id)
        if not bosses_result.get("success"):
            yield event.plain_result("获取失败")
            return
        
        bosses = bosses_result.get("bosses", [])
        if index < 0 or index >= len(bosses):
            yield event.plain_result(f"编号 {boss_index} 不存在")
            return
        
        boss = bosses[index]
        
        result = await self._engine.challenge_legendary_boss(player_id, boss["boss_id"])
        yield event.plain_result(result.get("message", "挑战失败"))

    # ══════════════════════════════════════════════════════════════
    # 管理员命令
    # ══════════════════════════════════════════════════════════════

    def _check_admin_level(self, event: AstrMessageEvent, required_level: int = 2) -> bool:
        """检查管理员等级"""
        sender_id = event.get_sender_id()
        admin_manager = self._engine.admin_manager
        
        if not admin_manager:
            return False
        
        admin_info = admin_manager.get_admin_info(sender_id)
        if not admin_info:
            return False
        
        return admin_info.get("level", 0) >= required_level

    @admin_group.command("发放称号")
    async def grant_title(self, event: AstrMessageEvent, player_name: str = "", title_name: str = ""):
        """发放称号给玩家"""
        if not self._check_admin_level(event, 2):
            yield event.plain_result("权限不足，需要版主及以上权限")
            return
        
        if not player_name.strip() or not title_name.strip():
            yield event.plain_result("用法：骑砍管理员 发放称号 <玩家名> <称号名>")
            return
        
        from .game.player_level import get_title_manager
        
        title_manager = get_title_manager()
        
        player = self._engine.get_player_by_name(player_name.strip())
        if not player:
            yield event.plain_result(f"未找到玩家：{player_name}")
            return
        
        titles = title_manager.get_all_titles()
        matched_title = None
        for t in titles:
            if title_name.strip() in t["name"]:
                matched_title = t
                break
        
        if not matched_title:
            yield event.plain_result(f"未找到称号：{title_name}\n可用称号：{', '.join([t['name'] for t in titles])}")
            return
        
        success = title_manager.assign_title(player.user_id, matched_title["id"])
        if success:
            yield event.plain_result(f"已为 {player.name} 发放称号：{matched_title['name']}")
        else:
            yield event.plain_result("发放称号失败")

    @admin_group.command("剥夺称号")
    async def revoke_title(self, event: AstrMessageEvent, player_name: str = ""):
        """剥夺玩家称号"""
        if not self._check_admin_level(event, 2):
            yield event.plain_result("权限不足，需要版主及以上权限")
            return
        
        if not player_name.strip():
            yield event.plain_result("用法：骑砍管理员 剥夺称号 <玩家名>")
            return
        
        from .game.player_level import get_title_manager
        
        title_manager = get_title_manager()
        
        player = self._engine.get_player_by_name(player_name.strip())
        if not player:
            yield event.plain_result(f"未找到玩家：{player_name}")
            return
        
        success = title_manager.remove_title(player.user_id)
        if success:
            yield event.plain_result(f"已剥夺 {player.name} 的称号")
        else:
            yield event.plain_result(f"{player.name} 没有称号")

    @admin_group.command("称号列表")
    async def list_titles(self, event: AstrMessageEvent):
        """查看所有称号"""
        if not self._check_admin_level(event, 1):
            yield event.plain_result("权限不足")
            return
        
        from .game.player_level import get_title_manager
        
        title_manager = get_title_manager()
        titles = title_manager.get_all_titles()
        
        if not titles:
            yield event.plain_result("目前没有称号")
            return
        
        lines = ["🏆 称号列表：", ""]
        for t in titles:
            effects = []
            if t.get("attack_bonus"):
                effects.append(f"攻击+{t['attack_bonus']}")
            if t.get("defense_bonus"):
                effects.append(f"防御+{t['defense_bonus']}")
            if t.get("hp_bonus"):
                effects.append(f"生命+{t['hp_bonus']}")
            if t.get("exp_bonus"):
                effects.append(f"经验+{int(t['exp_bonus']*100)}%")
            
            lines.append(f"• {t['name']}：{', '.join(effects) if effects else '无加成'}")
        
        yield event.plain_result("\n".join(lines))

    @admin_group.command("创建称号")
    async def create_title(self, event: AstrMessageEvent, title_name: str = "", *args):
        """创建新称号"""
        if not self._check_admin_level(event, 3):
            yield event.plain_result("权限不足，需要管理员权限")
            return
        
        if not title_name.strip():
            yield event.plain_result("用法：骑砍管理员 创建称号 <称号名> [攻击] [防御] [生命] [经验%]\n例：骑砍管理员 创建称号 勇士 10 5 100 10")
            return
        
        from .game.player_level import get_title_manager
        
        title_manager = get_title_manager()
        
        atk = int(args[0]) if len(args) > 0 else 0
        defense = int(args[1]) if len(args) > 1 else 0
        hp = int(args[2]) if len(args) > 2 else 0
        exp_bonus = float(args[3]) / 100 if len(args) > 3 else 0
        
        title = title_manager.create_title(
            name=title_name.strip(),
            description=f"管理员创建的称号",
            attack_bonus=atk,
            defense_bonus=defense,
            hp_bonus=hp,
            exp_bonus=exp_bonus,
        )
        
        yield event.plain_result(f"已创建称号：{title['name']}\n攻击+{atk} 防御+{defense} 生命+{hp} 经验+{int(exp_bonus*100)}%")

    @admin_group.command("删除称号")
    async def delete_title(self, event: AstrMessageEvent, title_name: str = ""):
        """删除称号"""
        if not self._check_admin_level(event, 3):
            yield event.plain_result("权限不足，需要管理员权限")
            return
        
        if not title_name.strip():
            yield event.plain_result("用法：骑砍管理员 删除称号 <称号名>")
            return
        
        from .game.player_level import get_title_manager
        
        title_manager = get_title_manager()
        titles = title_manager.get_all_titles()
        
        matched_title = None
        for t in titles:
            if title_name.strip() in t["name"]:
                matched_title = t
                break
        
        if not matched_title:
            yield event.plain_result(f"未找到称号：{title_name}")
            return
        
        success = title_manager.delete_title(matched_title["id"])
        if success:
            yield event.plain_result(f"已删除称号：{matched_title['name']}")
        else:
            yield event.plain_result("删除失败")

    @admin_group.command("玩家信息")
    async def admin_player_info(self, event: AstrMessageEvent, player_name: str = ""):
        """查看玩家详细信息"""
        if not self._check_admin_level(event, 1):
            yield event.plain_result("权限不足")
            return
        
        if not player_name.strip():
            yield event.plain_result("用法：骑砍管理员 玩家信息 <玩家名>")
            return
        
        player = self._engine.get_player_by_name(player_name.strip())
        if not player:
            yield event.plain_result(f"未找到玩家：{player_name}")
            return
        
        from .game.player_level import get_title_manager
        
        title_manager = get_title_manager()
        title = title_manager.get_player_title(player.user_id)
        
        lines = [
            f"玩家：{player.name}",
            f"等级：Lv.{player.level}",
            f"经验：{player.exp}",
            f"可分配点：{player.unallocated_points}",
            f"生命：{player.hp}/{player.max_hp}",
            f"攻击：{player.attack}",
            f"防御：{player.defense}",
            f"金币：{player.spirit_stones}",
            f"称号：{title['name'] if title else '无'}",
        ]
        
        yield event.plain_result("\n".join(lines))

    @admin_group.command("设置等级")
    async def set_level(self, event: AstrMessageEvent, player_name: str = "", level: str = ""):
        """设置玩家等级"""
        if not self._check_admin_level(event, 3):
            yield event.plain_result("权限不足，需要管理员权限")
            return
        
        if not player_name.strip() or not level.strip():
            yield event.plain_result("用法：骑砍管理员 设置等级 <玩家名> <等级>")
            return
        
        try:
            new_level = int(level.strip())
            if new_level < 1 or new_level > 100:
                yield event.plain_result("等级必须在1-100之间")
                return
        except ValueError:
            yield event.plain_result("请输入有效的等级数字")
            return
        
        player = await self._engine.get_player_by_name(player_name.strip())
        if not player:
            yield event.plain_result(f"未找到玩家：{player_name}")
            return
        
        from .game.player_level import LevelSystem, get_level_config
        
        old_level = player.level
        player.level = new_level
        player.exp = 0
        
        LevelSystem.recalculate_stats(player)
        
        yield event.plain_result(f"已将 {player.name} 的等级从 {old_level} 调整为 {new_level}")

    @admin_group.command("添加金币")
    async def add_gold(self, event: AstrMessageEvent, player_name: str = "", amount: str = ""):
        """给玩家添加金币"""
        if not self._check_admin_level(event, 3):
            yield event.plain_result("权限不足，需要管理员权限")
            return
        
        if not player_name.strip() or not amount.strip():
            yield event.plain_result("用法：骑砍管理员 添加金币 <玩家名> <数量>")
            return
        
        try:
            gold = int(amount.strip())
        except ValueError:
            yield event.plain_result("请输入有效的金币数量")
            return
        
        player = await self._engine.get_player_by_name(player_name.strip())
        if not player:
            yield event.plain_result(f"未找到玩家：{player_name}")
            return
        
        player.spirit_stones += gold
        yield event.plain_result(f"已为 {player.name} 增加 {gold} 金币，当前余额：{player.spirit_stones}")

    @admin_group.command("管理登录")
    async def admin_login(self, event: AstrMessageEvent, username: str = "", password: str = ""):
        """管理员登录"""
        from .game.admin_system import get_admin_manager
        
        admin_manager = get_admin_manager()
        
        if not username.strip() or not password.strip():
            yield event.plain_result("用法：骑砍管理员 管理登录 <用户名> <密码>")
            return
        
        result = admin_manager.login(username.strip(), password.strip())
        
        if result["success"]:
            sender_id = event.get_sender_id()
            admin_manager._sessions[result["token"]]["user_id"] = sender_id
            yield event.plain_result(
                f"登录成功！\n"
                f"用户名：{result['username']}\n"
                f"等级：{result['level_name']}\n"
                f"Token已绑定到此QQ"
            )
        else:
            yield event.plain_result(f"登录失败：{result['message']}")

    async def terminate(self):
        """插件销毁：停止 Web 服务、保存数据。"""
        if self._web_server:
            try:
                await self._web_server.stop()
                logger.info("骑砍英雄传：Web 服务已停止")
            except Exception:
                logger.exception("骑砍英雄传：Web 服务停止失败")
        if self._engine:
            await self._engine.shutdown()
            logger.info("骑砍英雄传：数据已保存")
