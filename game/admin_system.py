"""
分级管理员系统

管理员分为多个等级，不同等级有不同的权限。
"""

from __future__ import annotations

import time
import secrets
from dataclasses import dataclass
from typing import Optional


class AdminLevel:
    """管理员等级枚举"""
    NONE = 0          # 无权限
    VIEWER = 1        # 观察员 - 只能查看数据
    MODERATOR = 2     # 版主 - 玩家管理、发放称号
    ADMIN = 3         # 管理员 - 全功能（不含配置）
    SUPER_ADMIN = 4   # 超级管理员 - 全部功能 + UI自定义
    OWNER = 5         # 创始人 - 最高权限 + 分发管理员权限


ADMIN_LEVEL_NAMES = {
    AdminLevel.NONE: "无",
    AdminLevel.VIEWER: "观察员",
    AdminLevel.MODERATOR: "版主",
    AdminLevel.ADMIN: "管理员",
    AdminLevel.SUPER_ADMIN: "超级管理员",
    AdminLevel.OWNER: "创始人",
}


@dataclass
class AdminAccount:
    """管理员账号"""
    username: str
    password_hash: str
    level: int = AdminLevel.ADMIN
    created_at: float = 0.0
    last_login: float = 0.0
    created_by: str = ""  # 创建者用户名
    permissions: list[str] = None  # 自定义权限列表
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []
        if self.created_at == 0:
            self.created_at = time.time()


class AdminManager:
    """管理员管理器"""
    
    def __init__(self):
        self._admins: dict[str, AdminAccount] = {}
        self._sessions: dict[str, dict] = {}  # token -> {username, level, expires_at}
        self._session_ttl = 7 * 24 * 3600  # 7天
        self._default_super_admin: dict | None = None
    
    def set_default_super_admin(self, username: str, password: str):
        """设置默认超级管理员"""
        self._default_super_admin = {
            "username": username,
            "password": password,
        }
    
    def set_owner_admin(self, username: str, password: str):
        """设置创始人管理员（仅能通过配置文件设置）"""
        admin = AdminAccount(
            username=username,
            password_hash=self.hash_password(password),
            level=AdminLevel.OWNER,
        )
        self._admins[username] = admin
    
    def can_customize_ui(self, level: int) -> bool:
        """检查是否可以自定义UI（需要lv4+）"""
        return level >= AdminLevel.SUPER_ADMIN
    
    def can_manage_admins(self, level: int) -> bool:
        """检查是否可以管理管理员（需要lv5）"""
        return level >= AdminLevel.OWNER
    
    def can_upload_icons(self, level: int) -> bool:
        """检查是否可以上传图标（需要lv4+）"""
        return level >= AdminLevel.SUPER_ADMIN
    
    def hash_password(self, password: str) -> str:
        """简单密码哈希（生产环境应使用更安全的方式）"""
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """验证密码"""
        return self.hash_password(password) == hashed
    
    def create_admin(
        self,
        username: str,
        password: str,
        level: int = AdminLevel.MODERATOR,
        created_by: str = "",
    ) -> dict:
        """创建管理员"""
        if username in self._admins:
            return {"success": False, "message": "管理员已存在"}
        
        if level <= AdminLevel.NONE or level > AdminLevel.OWNER:
            return {"success": False, "message": "无效的管理员等级"}
        
        if level >= AdminLevel.OWNER:
            return {"success": False, "message": "无法创建创始人级别管理员"}
        
        admin = AdminAccount(
            username=username,
            password_hash=self.hash_password(password),
            level=level,
            created_by=created_by,
        )
        self._admins[username] = admin
        
        return {
            "success": True,
            "message": f"管理员 {username} 创建成功",
            "username": username,
            "level": level,
            "level_name": ADMIN_LEVEL_NAMES.get(level, "未知"),
        }
    
    def delete_admin(self, username: str, operator: str) -> dict:
        """删除管理员"""
        if username not in self._admins:
            return {"success": False, "message": "管理员不存在"}
        
        admin = self._admins[username]
        if admin.level == AdminLevel.SUPER_ADMIN and operator != username:
            return {"success": False, "message": "只有超级管理员可以删除其他超级管理员"}
        
        del self._admins[username]
        return {"success": True, "message": f"管理员 {username} 已删除"}
    
    def change_password(self, username: str, old_password: str, new_password: str) -> dict:
        """修改密码"""
        admin = self._admins.get(username)
        if not admin:
            if self._default_super_admin and username == self._default_super_admin["username"]:
                if old_password != self._default_super_admin["password"]:
                    return {"success": False, "message": "原密码错误"}
                self._default_super_admin["password"] = new_password
                return {"success": True, "message": "密码修改成功"}
            return {"success": False, "message": "管理员不存在"}
        
        if not self.verify_password(old_password, admin.password_hash):
            return {"success": False, "message": "原密码错误"}
        
        admin.password_hash = self.hash_password(new_password)
        return {"success": True, "message": "密码修改成功"}
    
    def login(self, username: str, password: str) -> dict:
        """管理员登录"""
        admin = self._admins.get(username)
        
        if not admin:
            if self._default_super_admin and username == self._default_super_admin["username"]:
                if password != self._default_super_admin["password"]:
                    return {"success": False, "message": "密码错误"}
                level = AdminLevel.SUPER_ADMIN
            else:
                return {"success": False, "message": "管理员不存在"}
        else:
            if not self.verify_password(password, admin.password_hash):
                return {"success": False, "message": "密码错误"}
            level = admin.level
        
        token = secrets.token_urlsafe(32)
        expires_at = time.time() + self._session_ttl
        
        self._sessions[token] = {
            "username": username,
            "level": level,
            "expires_at": expires_at,
        }
        
        if admin:
            admin.last_login = time.time()
        
        return {
            "success": True,
            "message": "登录成功",
            "token": token,
            "username": username,
            "level": level,
            "level_name": ADMIN_LEVEL_NAMES.get(level, "未知"),
            "expires_in": self._session_ttl,
        }
    
    def logout(self, token: str) -> dict:
        """管理员登出"""
        if token in self._sessions:
            del self._sessions[token]
            return {"success": True, "message": "已登出"}
        return {"success": False, "message": "无效的token"}
    
    def verify_token(self, token: str) -> dict | None:
        """验证token"""
        if not token:
            return None
        
        session = self._sessions.get(token)
        if not session:
            return None
        
        if time.time() > session["expires_at"]:
            del self._sessions[token]
            return None
        
        return session
    
    def verify_permission(self, token: str, required_level: int) -> bool:
        """验证权限"""
        session = self.verify_token(token)
        if not session:
            return False
        return session["level"] >= required_level
    
    def list_admins(self) -> list[dict]:
        """列出所有管理员"""
        result = []
        for username, admin in self._admins.items():
            result.append({
                "username": admin.username,
                "level": admin.level,
                "level_name": ADMIN_LEVEL_NAMES.get(admin.level, "未知"),
                "created_at": admin.created_at,
                "last_login": admin.last_login,
                "created_by": admin.created_by,
            })
        return result
    
    def get_admin_info(self, username: str) -> dict | None:
        """获取管理员信息"""
        admin = self._admins.get(username)
        if not admin:
            if self._default_super_admin and username == self._default_super_admin["username"]:
                return {
                    "username": username,
                    "level": AdminLevel.SUPER_ADMIN,
                    "level_name": "超级管理员",
                    "is_default": True,
                }
            return None
        
        return {
            "username": admin.username,
            "level": admin.level,
            "level_name": ADMIN_LEVEL_NAMES.get(admin.level, "未知"),
            "created_at": admin.created_at,
            "last_login": admin.last_login,
            "created_by": admin.created_by,
        }
    
    def update_admin_level(self, username: str, new_level: int, operator: str) -> dict:
        """修改管理员等级"""
        if username not in self._admins:
            return {"success": False, "message": "管理员不存在"}
        
        if new_level <= AdminLevel.NONE or new_level > AdminLevel.OWNER:
            return {"success": False, "message": "无效的管理员等级"}
        
        if new_level == AdminLevel.OWNER:
            return {"success": False, "message": "无法设置创始人级别，只能通过配置文件创建"}
        
        operator_session = self._sessions.get(operator)
        if not operator_session:
            return {"success": False, "message": "操作者未登录"}
        
        target_admin = self._admins[username]
        
        if target_admin.level == AdminLevel.OWNER:
            return {"success": False, "message": "无法修改创始人级别管理员"}
        
        if target_admin.level == AdminLevel.SUPER_ADMIN and operator_session["level"] != AdminLevel.OWNER:
            return {"success": False, "message": "只有创始人可以修改超级管理员的等级"}
        
        if operator_session["level"] < AdminLevel.SUPER_ADMIN:
            return {"success": False, "message": "权限不足，需要超级管理员或更高"}
        
        if new_level >= operator_session["level"] and username != operator:
            return {"success": False, "message": "不能授予比自己更高或同等的管理员等级"}
        
        target_admin.level = new_level
        return {
            "success": True,
            "message": f"管理员 {username} 等级已更新为 {ADMIN_LEVEL_NAMES.get(new_level, '未知')}",
        }
    
    def to_dict(self) -> dict:
        return {
            "admins": {
                username: {
                    "username": admin.username,
                    "password_hash": admin.password_hash,
                    "level": admin.level,
                    "created_at": admin.created_at,
                    "last_login": admin.last_login,
                    "created_by": admin.created_by,
                    "permissions": admin.permissions,
                }
                for username, admin in self._admins.items()
            },
            "default_super_admin": self._default_super_admin,
        }
    
    def from_dict(self, data: dict):
        self._admins = {}
        for username, admin_data in data.get("admins", {}).items():
            self._admins[username] = AdminAccount(**admin_data)
        self._default_super_admin = data.get("default_super_admin")


_admin_manager: AdminManager | None = None


def get_admin_manager() -> AdminManager:
    global _admin_manager
    if _admin_manager is None:
        _admin_manager = AdminManager()
    return _admin_manager
