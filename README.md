# 🌈 Sky Tools Plugin - 光遇工具插件

![版本](https://img.shields.io/badge/版本-1.0.4-blue)
![MaiBot](https://img.shields.io/badge/MaiBot-0.7%2B-orange)
![许可证](https://img.shields.io/badge/许可证-MIT-green)

**为光遇玩家打造的一站式查询工具 —— 身高、任务、蜡烛、复刻、红石、日历…… 所有信息，触手可及**

---

## 📖 项目简介

**Sky Tools Plugin** 是专为 [MaiBot](https://github.com/MaiM-with-u/MaiBot) 开发的光遇辅助插件。它聚合了多个主流数据源，为光遇玩家提供**即时、准确、全面的游戏信息查询服务**。

无论你是每日必做任务的肝帝，还是偶尔上线看复刻的佛系玩家，本插件都能让你**在聊天框内一键获取所有需要的信息**。

---

## ✨ 功能特性

| 功能 | 描述 | 数据源 |
|------|------|--------|
| 📋 **每日任务** | 获取当日任务位置及攻略图片 | 独角兽/应天API |
| 🕯️ **季节蜡烛** | 季蜡刷新位置地图 | 独角兽/应天API |
| 💎 **大蜡烛** | 大蜡烛位置标记图 | 独角兽/应天API |
| 🔴 **红石/黑石** | 堕落之地位置及时间 | 独角兽API |
| 🧭 **复刻先祖** | 本周复刻信息 + 兑换图 | 独角兽API |
| 🔮 **每日魔法** | 魔法商店可兑换物品 | 独角兽/应天API |
| 📅 **活动日历** | 当月活动时间表 | 独角兽API |
| 🔍 **服务器状态** | 光遇国服炸服检测 | 独角兽API |
| 📏 **身高查询** | **三大平台**：芒果、独角兽、应天 | 全平台支持 |

### 🚀 **特色亮点**

✅ **多平台聚合** - 信息查询支持芒果、独角兽、应天  
✅ **智能合并转发** - 图片+文字混合消息，整洁美观  
✅ **热重载配置** - 修改配置无需重启，自动生效(修改命令前缀请重启MaiBot主程序)  
✅ **备用发送机制** - Napcat 不可用时自动降级，消息不丢失      

---

## 📦 安装指南

### 前置要求

- [MaiBot](https://github.com/MaiM-with-u/MaiBot) `v0.10.0` 或更高版本
- Python `3.10+`
- [Napcat](https://napcat.napneko.icu/) 创建HTTP Server 5222端口 关闭CORS与Websocket

### 安装步骤

1. **克隆插件到 MaiBot 插件目录**
```bash
cd MaiBot/plugins
git clone https://github.com/xc94188/sky_tools_plugin.git
```

2. **安装依赖**
```bash
# 使用uv子命令 uv pip 并使用国内源安装依赖
uv pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple --upgrade
```

3. **启动 MaiBot，自动生成配置文件**
```bash
uv run python3 bot.py
```

4. **编辑配置文件**  
打开 `plugins/sky_tools_plugin/config.toml`，填入你的 API 密钥（详见[配置说明](#-配置说明)）

---

## ⚙️ 配置说明

### 🔑 必须配置项

#### 身高查询 API（若启用则至少配置一个平台）

```toml
[height_api]
# 芒果工具
mango_key = "你的芒果工具API密钥"  # 获取：https://mangotool.cn/openAPI

# 独角兽平台
ovoav_key = "你的独角兽平台API密钥"  # 获取：https://ovoav.com

# 应天平台
yingtian_key = "你的应天平台API密钥"  # 获取：https://api.t1qq.com
```

#### 日常查询 API（以独角兽平台为例）

```toml
[task_api]
key = "你的独角兽平台API密钥"  # 每日任务

[candle_api]  
key = "你的独角兽平台API密钥"  # 大蜡烛

[ancestor_api]
key = "你的独角兽平台API密钥"  # 复刻先祖

# ... 其他 API 配置类似
```

### 🧩 可选配置

```toml
[napcat]
# 合并转发配置（默认即可）
api_url = "http://127.0.0.1:5222"
enabled = true

[settings]
# 命令显示顺序（影响帮助列表功能显示顺序）
command_display_order = ["all", "height", "task", "candle", ...]

# 独立开关（可单独禁用某项功能）
enable_height_query = true
enable_task_query = true
# ...
```

---

## 📋 命令列表

所有命令默认前缀为 `#`，可在配置中修改。

### 🎯 一键汇总

| 命令 | 别名 | 功能 |
|------|------|------|
| `#all` | `#每日`、`#日常`、`#rc`、`#mr` | **一键获取所有已启用的日常信息** |

### 📏 身高查询

| 命令 | 说明 |
|------|------|
| `#height <游戏ID> [好友码]` | 使用默认平台查询 |
| `#height <平台> <游戏ID> [好友码]` | 指定平台查询 |

**平台别名**：
- 芒果平台：`mango`、`mg`、`芒果`
- 独角兽平台：`ovoav`、`djs`、`独角兽`
- 应天平台：`yingtian`、`yt`、`应天`

> ⚠️ **首次查询必须提供好友码**，格式：`XXXX-XXXX-XXXX`
> 可在配置中自行增减别名

### 🖼️ 日常查询

| 命令 | 别名 | 功能 |
|------|------|------|
| `#task` | `#rw`、`#任务`、`#每日任务` | 每日任务位置图 |
| `#candle` | `#dl`、`#大蜡`、`#大蜡烛` | 大蜡烛位置图 |
| `#season_candle` | `#jl`、`#季蜡` | 季节蜡烛位置图 |
| `#redstone` | `#hs`、`#红石` | 红石/黑石位置图 |
| `#magic` | `#mf`、`#魔法` | 每日魔法兑换 |
| `#calendar` | `#rl`、`#日历` | 当月活动日历 |
| `#ancestor` | `#fk`、`#复刻` | 本周复刻先祖 |
| `#skytest` | - | 服务器状态检测(是否炸服) |

### ℹ️ 帮助

| 命令 | 功能 |
|------|------|
| `#skytools` | 显示命令概览 |

---

## 🧠 高级特性

### 🔄 配置热重载

插件内置**智能配置监控器**：
- 支持 `watchdog`（实时）和轮询（降级）两种模式
- 修改 `config.toml` 后**自动重载插件**，无需重启 MaiBot

### 📎 合并转发与备用发送

- **优先模式**：Napcat HTTP API → 混合消息
- **备用模式**：Napcat 不可用时 → 分条发送 + 用户提示（效果较差）

**请尽量使用napcat进行发送，保证速度和体验**

### 🧩 扩展性设计

- **命令元数据注册表**：集中管理命令名称、别名、描述、参数、示例
- **平台处理器注册表**：新增身高数据源仅需实现 `BasePlatformHandler`

---

### 拓展开发指引

### 一、添加新命令

**1. 创建文件 `commands/demo.py`**
```python
from .base import SkyBaseCommand

class DemoCommand(SkyBaseCommand):
    command_name = "demo"
    command_description = "演示命令"
    command_pattern = r"^{escaped_prefix}demo$"

    async def execute(self):
        await self.send_text("✅ 演示命令执行成功！")
        return True, "成功", True
```

**2. 注册元数据 `metadata/command_metadata.py`**
```python
DEMO_METADATA = {
    "name": "demo",
    "description": "演示命令",
    "aliases": ["测试"],
    "category": "其他",
}
ALL_COMMAND_METADATA = [
    ...
    DEMO_METADATA,
]
```

**3. 注册命令 `plugin.py`**
```python
from .commands.demo import DemoCommand

def get_plugin_components(self):
    command_classes = [..., DemoCommand]  # 加在这里
```

**✅ 完成！**

---

### 二、添加新身高平台

**1. 创建文件 `platforms/demo.py`**
```python
from .base import BasePlatformHandler
from .registry import register_platform

@register_platform(name="demo", aliases=["测试"])
class DemoPlatform(BasePlatformHandler):
    async def query(self, url, key, game_id, friend_code, timeout):
        return {
            "success": True,
            "message": "📏 demo平台"
        }
```

**2. 添加配置 `plugin.py`**
```python
"height_api": {
    ...
    "enable_demo": ConfigField(type=bool, default=True, description="启用demo平台"),
    "demo_url": ConfigField(type=str, default="demo_url", description="身高查询API地址"),
    "demo_key": ConfigField(type=str, default="你的密钥", description="API密钥"),
    ...
}
```

**✅ 完成！**

---

### 🔍 验证

```
# 测试命令
#demo

# 测试身高平台
#height demo xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```
---

## 📄 许可证

本项目采用 **MIT 许可证**。  
您可以自由使用、修改、分发，但需保留版权声明。

---

## 🙏 鸣谢

- [MaiBot](https://github.com/MaiM-with-u/MaiBot) - 麦麦机器人框架
- DeepSeek -帮忙篡写Readme.md
---
