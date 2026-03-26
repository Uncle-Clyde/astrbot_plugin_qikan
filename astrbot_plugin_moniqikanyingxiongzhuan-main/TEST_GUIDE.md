# 骑砍英雄传 - 本地测试指南

## 方法一：通过AstrBot插件管理器（推荐）

### 1. 安装插件
将整个 `astrbot_plugin_moniqikanyingxiongzhuan-main` 文件夹复制到 AstrBot 的插件目录：

```
AstrBot安装目录/
├── astrbot/
├── data/
├── plugins/           <-- 放到这里
│   └── astrbot_plugin_moniqikanyingxiongzhuan-main/
└── ...
```

### 2. 配置插件
在 AstrBot 的插件配置页面，找到「骑砍英雄传」插件，配置以下选项：

```json
{
  "web_access_password": "123456",        // 网页访问密码（留空则不验证）
  "web_admin_account": "admin",            // 管理员账号
  "web_admin_password": "admin123",        // 管理员密码
  "web_port": 8099,                        // Web服务端口
  "web_host": "0.0.0.0",                 // 监听地址
  "enable_web": true                       // 必须开启！
}
```

### 3. 重启AstrBot
配置完成后重启 AstrBot 服务，日志中看到以下信息表示启动成功：
```
骑砍英雄传：Web 服务已启动，端口 8099
骑砍英雄传：骑砍英雄传插件已加载
```

### 4. 访问网页
在浏览器中打开：`http://你的服务器IP:8099`

---

## 方法二：独立运行（开发调试用）

如果只想测试Web界面，可以单独启动Web服务：

### 1. 创建测试脚本 `test_web.py`
```python
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.engine import GameEngine
from game.data_manager import DataManager
from game.auth import AuthManager
from web.server import create_web_server


async def main():
    # 初始化数据管理器
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    
    data_manager = DataManager(data_dir)
    auth_manager = AuthManager()
    engine = GameEngine(data_manager)
    
    # 初始化引擎
    await engine.initialize()
    engine.auth = auth_manager
    
    # 创建Web服务器
    server = create_web_server(
        engine=engine,
        host="0.0.0.0",
        port=8099,
        access_password="",
        guard_token="",
        admin_account="admin",
        admin_password="admin123",
        command_prefix="骑砍",
    )
    
    # 启动服务器
    config = uvicorn.Config(server, host="0.0.0.0", port=8099, log_level="info")
    server_runner = uvicorn.Server(config)
    await server_runner.serve()


if __name__ == "__main__":
    asyncio.run(main())
```

### 2. 安装依赖
```bash
pip install fastapi uvicorn jinja2 pillow aiofiles
```

### 3. 运行测试
```bash
python test_web.py
```

---

## 测试账号

插件会自动创建玩家数据，无需预注册。

### 通过网页注册
1. 打开 `http://服务器IP:8099`
2. 点击「注册账号」
3. 输入角色名和密码
4. 注册成功后自动登录

### 通过聊天注册（如果接入了QQ）
发送：`骑砍 注册 张三`

---

## 功能测试清单

- [ ] 网页注册/登录
- [ ] 查看角色面板
- [ ] 训练获得经验
- [ ] 查看等级和属性点
- [ ] 分配属性点
- [ ] 查看/攻击劫匪
- [ ] 挑战/历练
- [ ] 使用医疗技能
- [ ] 使用药剂
- [ ] 装备系统
- [ ] 排行榜

---

## 常见问题

### Q: 启动报错 `ModuleNotFoundError: No module named 'astrbot'`
**A:** 这是正常的，插件需要AstrBot环境才能完整运行。如果只想测试Web界面，使用「方法二」。

### Q: 网页显示空白
**A:** 检查浏览器控制台是否有错误，确保 `enable_web` 配置为 `true`。

### Q: 端口被占用
**A:** 修改 `_conf_schema.json` 中的 `web_port` 为其他端口，如 8100。

---

## 联系方式
如有问题，请查看 AstrBot 插件市场或联系开发者。
