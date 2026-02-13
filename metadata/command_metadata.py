"""
所有命令的元数据定义集中在此文件
每个命令的元数据是一个字典，包含以下字段：

必填字段：
- name: str               - 命令名称（command_name）
- description: str        - 简短描述（用于概览）
- category: str          - 分类

选填字段：
- aliases: List[str]     - 命令别名（不含前缀）
- detailed: str          - 详细描述（用于详情页）
- examples: List[str]    - 使用示例
- parameters: dict       - 参数说明 {参数名: 说明}
- notes: List[str]       - 注意事项
- config_key: str        - 配置开关键，默认自动生成
"""
from typing import List, Dict


def _default_config_key(name: str) -> str:
    """生成默认的配置开关键"""
    return f"settings.enable_{name}_query"


# ========== 帮助命令 ==========
HELP_METADATA = {
    "name": "skytools",
    "description": "显示本帮助信息",
    "detailed": "显示插件所有命令的概览帮助，或通过指定命令名查看该命令的详细说明。",
    "aliases": ["help"],
    "examples": ["#skytools", "#help", "#help height"],
    "category": "帮助",
    "config_key": "settings.enable_skytools_query",
}


# ========== 身高查询 ==========
HEIGHT_METADATA = {
    "name": "height",
    "description": "查询光遇国服玩家身高数据",
    "detailed": (
        "通过游戏长ID或好友码查询玩家的详细身高数据，包括体型值(s值)、身高值(h值)、"
        "当前身高、最矮/最高身高、身高类型、距离最矮/最高差距等。支持多个查询平台。"
    ),
    "aliases": ["身高"],
    "examples": [
        "#height xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "#height mango xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "#height djs XXXX-XXXX-XXXX",
        "#height yt xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx XXXX-XXXX-XXXX",
    ],
    "parameters": {
        "[平台]": "可选，指定查询平台（mango/独角兽/应天等），不填则使用默认平台",
        "<游戏长ID>": "UUID格式的游戏ID，可通过游戏内设置→精灵询问获取",
        "[好友码]": "可选，格式为 XXXX-XXXX-XXXX，首次查询建议提供",
    },
    "notes": [
        "芒果平台必须提供游戏长ID，好友码可选",
        "独角兽平台提供游戏长ID或好友码任选其一",
        "应天平台必须提供游戏长ID，好友码可选",
        "首次查询请提供好友码",
        "请勿拉黑测身高好友，否则后续无法查询",
    ],
    "category": "数据查询",
    "config_key": _default_config_key("height"),
    "prefix": "📏",  # 添加 emoji 前缀
}


# ========== 每日任务 ==========
TASK_METADATA = {
    "name": "task",
    "description": "获取光遇每日任务图片",
    "detailed": "获取当天光遇每日任务的攻略图片，包含任务位置和完成方法。",
    "aliases": ["rw", "任务", "每日任务"],
    "examples": ["#task", "#rw", "#每日任务"],
    "category": "日常查询",
    "config_key": _default_config_key("task"),
    "prefix": "🖼️",  # 添加 emoji 前缀
}


# ========== 大蜡烛 ==========
CANDLE_METADATA = {
    "name": "candle",
    "description": "获取光遇大蜡烛位置图片",
    "detailed": "获取当天光遇大蜡烛的刷新位置图片，包含多个地图的详细标记。",
    "aliases": ["dl", "大蜡", "大蜡烛"],
    "examples": ["#candle", "#dl", "#大蜡烛"],
    "category": "日常查询",
    "config_key": _default_config_key("candle"),
    "prefix": "💎",  # 添加 emoji 前缀
}


# ========== 复刻先祖 ==========
ANCESTOR_METADATA = {
    "name": "ancestor",
    "description": "获取光遇复刻先祖位置图片",
    "detailed": "获取本周光遇复刻先祖的位置图片、可兑换物品及所需蜡烛信息。",
    "aliases": ["fk", "复刻", "先祖", "复刻先祖"],
    "examples": ["#ancestor", "#fk", "#复刻"],
    "category": "活动查询",
    "config_key": _default_config_key("ancestor"),
    "prefix": "🧭",  # 添加 emoji 前缀
}


# ========== 每日魔法 ==========
MAGIC_METADATA = {
    "name": "magic",
    "description": "获取光遇每日魔法图片",
    "detailed": "获取当天光遇魔法商店可兑换的魔法列表及所需蜡烛/爱心数量。",
    "aliases": ["mf", "魔法", "每日魔法"],
    "examples": ["#magic", "#mf", "#每日魔法"],
    "category": "日常查询",
    "config_key": _default_config_key("magic"),
    "prefix": "🔮",  # 添加 emoji 前缀
}


# ========== 季节蜡烛 ==========
SEASON_CANDLE_METADATA = {
    "name": "season_candle",
    "description": "获取光遇每日季蜡位置图片",
    "detailed": "获取当天光遇季节蜡烛的刷新位置图片，包含多个地图的详细标记。",
    "aliases": ["scandel", "jl", "季蜡", "季节蜡烛", "季蜡位置"],
    "examples": ["#scandel", "#jl", "#季蜡"],
    "category": "日常查询",
    "config_key": _default_config_key("season_candle"),
    "prefix": "🕯️",  # 添加 emoji 前缀
}


# ========== 活动日历 ==========
CALENDAR_METADATA = {
    "name": "calendar",
    "description": "获取光遇日历图片",
    "detailed": "获取光遇当前月份的活动日历图片，包含复刻、活动、季节结束时间等信息。",
    "aliases": ["rl", "日历", "活动日历"],
    "examples": ["#calendar", "#rl", "#日历"],
    "category": "活动查询",
    "config_key": _default_config_key("calendar"),
    "prefix": "📅",  # 添加 emoji 前缀
}


# ========== 红石位置 ==========
REDSTONE_METADATA = {
    "name": "redstone",
    "description": "获取光遇红石位置图片",
    "detailed": "获取当天光遇红石/黑石的坠落位置图片，包含具体地图和坐标。",
    "aliases": ["hs", "红石", "红石位置"],
    "examples": ["#redstone", "#hs", "#红石"],
    "category": "日常查询",
    "config_key": _default_config_key("redstone"),
    "prefix": "🔴",  # 添加 emoji 前缀
}


# ========== 服务器状态 ==========
SKYTEST_METADATA = {
    "name": "skytest",
    "description": "查询光遇服务器状态",
    "detailed": "检测光遇国服服务器是否正常运行，返回当前服务器状态信息。",
    "aliases": [],
    "examples": ["#skytest"],
    "category": "实用工具",
    "config_key": _default_config_key("skytest"),
    "prefix": "🔍",  # 添加 emoji 前缀
}


# ========== 帮助命令 ==========
HELP_METADATA = {
    "name": "skytools",
    "description": "显示本帮助信息",
    "detailed": "显示插件所有命令的概览帮助，或通过指定命令名查看该命令的详细说明。",
    "aliases": ["help"],
    "examples": ["#skytools", "#help", "#help height"],
    "category": "帮助",
    "config_key": "settings.enable_skytools_query",
    "prefix": "ℹ️",  # 添加 emoji 前缀
}


# ========== 一键汇总查询 ==========
ALL_METADATA = {
    "name": "all",
    "description": "一键获取所有光遇日常信息",
    "detailed": "一次性获取每日任务、季节蜡烛、大蜡烛、红石、复刻先祖、每日魔法、活动日历、服务器状态等所有信息，每条信息独立发送。",
    "aliases": ["所有", "全部", "汇总"],
    "examples": ["#all", "#所有", "#汇总"],
    "category": "日常查询",
    "config_key": "settings.enable_all_query",
    "notes": [
        "此命令会依次调用所有已启用的查询功能",
        "复刻信息的图片和文字会合并为一条消息发送",
        "未启用的功能会自动跳过"
    ],
    "prefix": "📊",  # 添加 emoji 前缀
}

# ========== 所有命令元数据列表 ==========
ALL_COMMAND_METADATA = [
    HELP_METADATA,
    HEIGHT_METADATA,
    TASK_METADATA,
    CANDLE_METADATA,
    ANCESTOR_METADATA,
    MAGIC_METADATA,
    SEASON_CANDLE_METADATA,
    CALENDAR_METADATA,
    REDSTONE_METADATA,
    SKYTEST_METADATA,
    ALL_METADATA,
]