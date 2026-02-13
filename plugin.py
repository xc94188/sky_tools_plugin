"""
光遇工具插件主入口
负责插件注册、配置加载、组件收集和配置监控
"""
import asyncio
import re
from typing import List, Tuple, Type

from src.plugin_system import (
    BasePlugin,
    register_plugin,
    ComponentInfo,
    ConfigField,
    ConfigSection,
)
from src.plugin_system.apis import get_logger

# ========== 相对导入所有需要的组件 ==========
from .commands import (
    SkyBaseCommand,
    HelpCommand,
    HeightQueryCommand,
    TaskQueryCommand,
    CandleQueryCommand,
    AncestorQueryCommand,
    MagicQueryCommand,
    SeasonCandleQueryCommand,
    CalendarQueryCommand,
    RedStoneQueryCommand,
    SkyTestCommand,
    AllQueryCommand,
)
from .utils.config_monitor import ConfigMonitor
from .metadata.command_metadata import ALL_COMMAND_METADATA
from .metadata.registry import registry

logger = get_logger("sky_tools_plugin")


@register_plugin
class SkyToolsPlugin(BasePlugin):
    """光遇工具插件"""

    plugin_name = "sky_tools_plugin"
    enable_plugin = True
    dependencies = []
    python_dependencies = ["aiohttp", "watchdog"]
    config_file_name = "config.toml"

    # ========== 配置节描述（用于 WebUI）==========
    config_section_descriptions = {
        "plugin": ConfigSection(title="插件基本信息", icon="settings", order=1),
        "napcat": ConfigSection(title="Napcat 合并转发", icon="message-square", order=2),
        "height_api": ConfigSection(title="身高查询 API", icon="ruler", order=3),
        "task_api": ConfigSection(title="每日任务图片", icon="image", order=4),
        "candle_api": ConfigSection(title="大蜡烛位置", icon="candle", order=5),
        "ancestor_api": ConfigSection(title="复刻先祖", icon="users", order=6),
        "magic_api": ConfigSection(title="每日魔法", icon="wand", order=7),
        "season_candle_api": ConfigSection(title="季节蜡烛", icon="flame", order=8),
        "calendar_api": ConfigSection(title="活动日历", icon="calendar", order=9),
        "redstone_api": ConfigSection(title="红石位置", icon="alert-circle", order=10),
        "skytest_api": ConfigSection(title="服务器状态", icon="server", order=11),
        "settings": ConfigSection(title="功能开关", icon="toggle-left", order=12),
    }

    # ========== 配置 Schema（完整，同原文件）==========
    config_schema = {
        "plugin": {
            "enabled": ConfigField(type=bool, default=True, description="是否启用插件"),
            "config_version": ConfigField(type=str, default="2.0.2", description="配置文件版本"),
            "command_prefix": ConfigField(
                type=str,
                default="#",
                description="命令前缀（注：修改命令前缀需要重启主程序才能更新，热重载无效）"
            ),
        },
        "napcat": {
            "api_url": ConfigField(
                type=str,
                default="http://127.0.0.1:5222",
                description="Napcat API地址，默认: http://127.0.0.1:5222"
            ),
            "token": ConfigField(
                type=str,
                default="",
                description="Napcat API令牌（可选）"
            ),
            "timeout": ConfigField(
                type=int,
                default=30,
                description="API请求超时时间（秒）"
            ),
            "enabled": ConfigField(
                type=bool,
                default=True,
                description="是否启用合并转发消息功能"
            )
        },
        "height_api": {
            "default_platform": ConfigField(
                type=str,
                default="mango",
                description="默认身高查询平台",
                choices=["mango", "ovoav", "yingtian"]
            ),
            "platform_aliases": ConfigField(
                type=list,
                default=["mango:芒果,mg", "ovoav:独角兽,djs", "yingtian:应天,yt"],
                description="平台别名配置，格式：主平台名:别名1,别名2,..."
            ),
            "enable_mango": ConfigField(
                type=bool,
                default=True,
                description="是否启用芒果平台身高查询"
            ),
            "enable_ovoav": ConfigField(
                type=bool,
                default=True,
                description="是否启用独角兽平台身高查询"
            ),
            "enable_yingtian": ConfigField(
                type=bool,
                default=True,
                description="是否启用应天平台身高查询"
            ),
            "mango_url": ConfigField(
                type=str,
                default="https://api.mangotool.cn/sky/out/cn",
                description="芒果工具身高查询API地址"
            ),
            "mango_key": ConfigField(
                type=str,
                default="你的芒果工具API密钥",
                description="芒果工具身高查询API密钥，获取方式：芒果工具：https://mangotool.cn/openAPI",
                required=True
            ),
            "ovoav_url": ConfigField(
                type=str,
                default="https://ovoav.com/api/sky/sgwz/sgv1",
                description="独角兽平台身高查询API地址"
            ),
            "ovoav_key": ConfigField(
                type=str,
                default="你的独角兽平台API密钥",
                description="独角兽平台身高查询API密钥，获取方式：独角兽API：https://ovoav.com",
                required=True
            ),
            "yingtian_url": ConfigField(
                type=str,
                default="https://api.t1qq.com/api/sky/sc/sg",
                description="应天平台身高查询API地址"
            ),
            "yingtian_key": ConfigField(
                type=str,
                default="你的应天平台API密钥",
                description="应天平台身高查询API密钥，获取方式：应天API：https://api.t1qq.com",
                required=True
            ),
            "timeout": ConfigField(
                type=int,
                default=15,
                description="身高API请求超时时间（秒）"
            )
        },
        "task_api": {
            "url": ConfigField(
                type=str,
                default="https://ovoav.com/api/sky/rwtp/rwt",
                description="任务图片API地址，应天API：https://api.t1qq.com/api/sky/sc/scrw，独角兽API：https://ovoav.com/api/sky/rwtp/rwt"
            ),
            "key": ConfigField(
                type=str,
                default="你的任务API密钥",
                description="任务图片API密钥，获取方式：应天API：https://api.t1qq.com，独角兽API：https://ovoav.com",
                required=True
            ),
            "timeout": ConfigField(
                type=int,
                default=15,
                description="任务API请求超时时间（秒）"
            )
        },
        "candle_api": {
            "url": ConfigField(
                type=str,
                default="https://ovoav.com/api/sky/dlzwz/dl",
                description="大蜡烛位置API地址，应天API：https://api.t1qq.com/api/sky/sc/scdl，独角兽API：https://ovoav.com/api/sky/dlzwz/dl"
            ),
            "key": ConfigField(
                type=str,
                default="你的大蜡烛API密钥",
                description="大蜡烛位置API密钥，获取方式：应天API：https://api.t1qq.com，独角兽API：https://ovoav.com",
                required=True
            ),
            "timeout": ConfigField(
                type=int,
                default=15,
                description="大蜡烛API请求超时时间（秒）"
            )
        },
        "ancestor_api": {
            "url": ConfigField(
                type=str,
                default="https://ovoav.com/api/sky/fkxz/xz",
                description="复刻先祖位置API地址，应天API：暂无，独角兽API：https://ovoav.com/api/sky/fkxz/xz"
            ),
            "key": ConfigField(
                type=str,
                default="你的复刻先祖API密钥",
                description="复刻先祖位置API密钥，获取方式：应天API：https://api.t1qq.com，独角兽API：https://ovoav.com",
                required=True
            ),
            "timeout": ConfigField(
                type=int,
                default=15,
                description="复刻先祖API请求超时时间（秒）"
            )
        },
        "magic_api": {
            "url": ConfigField(
                type=str,
                default="https://ovoav.com/api/sky/mftp/mf",
                description="每日魔法API地址，应天API：https://api.t1qq.com/api/sky/mf/magic，独角兽API：https://ovoav.com/api/sky/mftp/mf"
            ),
            "key": ConfigField(
                type=str,
                default="你的每日魔法API密钥",
                description="每日魔法API密钥，获取方式：应天API：https://api.t1qq.com，独角兽API：https://ovoav.com",
                required=True
            ),
            "timeout": ConfigField(
                type=int,
                default=15,
                description="每日魔法API请求超时时间（秒）"
            )
        },
        "season_candle_api": {
            "url": ConfigField(
                type=str,
                default="https://ovoav.com/api/sky/jlwz/jl",
                description="每日季蜡位置API地址，应天API：https://api.t1qq.com/api/sky/sc/scjl，独角兽API：https://ovoav.com/api/sky/jlwz/jl"
            ),
            "key": ConfigField(
                type=str,
                default="你的季蜡API密钥",
                description="每日季蜡位置API密钥，获取方式：应天API：https://api.t1qq.com，独角兽API：https://ovoav.com",
                required=True
            ),
            "timeout": ConfigField(
                type=int,
                default=15,
                description="季蜡API请求超时时间（秒）"
            )
        },
        "calendar_api": {
            "url": ConfigField(
                type=str,
                default="https://ovoav.com/api/sky/rltp/rl",
                description="光遇日历API地址，应天API：暂无，独角兽API：https://ovoav.com/api/sky/rltp/rl"
            ),
            "key": ConfigField(
                type=str,
                default="你的日历API密钥",
                description="光遇日历API密钥，获取方式：应天API：https://api.t1qq.com，独角兽API：https://ovoav.com",
                required=True
            ),
            "timeout": ConfigField(
                type=int,
                default=15,
                description="日历API请求超时时间（秒）"
            )
        },
        "redstone_api": {
            "url": ConfigField(
                type=str,
                default="https://ovoav.com/api/sky/hstp/hs",
                description="红石位置API地址，应天API：暂无，独角兽API：https://ovoav.com/api/sky/hstp/hs"
            ),
            "key": ConfigField(
                type=str,
                default="你的红石API密钥",
                description="红石位置API密钥，获取方式：应天API：https://api.t1qq.com，独角兽API：https://ovoav.com",
                required=True
            ),
            "timeout": ConfigField(
                type=int,
                default=15,
                description="红石API请求超时时间（秒）"
            )
        },
        "skytest_api": {
            "url": ConfigField(
                type=str,
                default="https://ovoav.com/api/sky/gyzt/zt",
                description="服务器状态测试API地址"
            ),
            "key": ConfigField(
                type=str,
                default="你的服务器状态API密钥",
                description="服务器状态测试API密钥，获取方式：独角兽API：https://ovoav.com",
                required=True
            ),
            "timeout": ConfigField(
                type=int,
                default=15,
                description="服务器状态API请求超时时间（秒）"
            )
        },
        "settings": {
            "command_display_order": ConfigField(
                type=list,
                default=["all", "height", "task", "candle", "season_candle", "ancestor", "magic", "calendar", "redstone", "skytest"],
                description="命令显示顺序（按此列表顺序显示，未在列表中的命令会自动追加到末尾）",
                hint="可调整帮助文本显示顺序",
                item_type="string"
            ),
            "enable_height_query": ConfigField(
                type=bool,
                default=True,
                description="是否启用身高查询功能"
            ),
            "enable_task_query": ConfigField(
                type=bool,
                default=True,
                description="是否启用任务查询功能"
            ),
            "enable_candle_query": ConfigField(
                type=bool,
                default=True,
                description="是否启用大蜡烛查询功能"
            ),
            "enable_ancestor_query": ConfigField(
                type=bool,
                default=True,
                description="是否启用复刻先祖查询功能"
            ),
            "enable_magic_query": ConfigField(
                type=bool,
                default=True,
                description="是否启用每日魔法查询功能"
            ),
            "enable_season_candle_query": ConfigField(
                type=bool,
                default=True,
                description="是否启用季蜡查询功能"
            ),
            "enable_calendar_query": ConfigField(
                type=bool,
                default=True,
                description="是否启用日历查询功能"
            ),
            "enable_redstone_query": ConfigField(
                type=bool,
                default=True,
                description="是否启用红石查询功能"
            ),
            "enable_skytest_query": ConfigField(
                type=bool,
                default=True,
                description="是否启用服务器状态查询功能"
            ),
            "enable_all_query": ConfigField(
                type=bool,
                default=True,
                description="是否启用一键汇总查询功能"
            ),
        }
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._monitor_start_task = None
        self.config_monitor = None  # 显式初始化

        # ========== 强制初始化命令元数据注册表 ==========
        logger.info(f"📦 正在注册 {len(ALL_COMMAND_METADATA)} 个命令元数据")
        
        # 清空注册表（热重载时必须）
        registry.clear()
        
        # 逐个注册
        for meta in ALL_COMMAND_METADATA:
            registry.register(meta)
            logger.debug(f"✅ 已注册命令: {meta['name']}")
        
        logger.info(f"✅ 元数据注册完成，共 {len(registry.get_all())} 个命令")
        logger.debug(f"📋 命令列表: {list(registry.get_all().keys())}")

        # ========== 启动配置监控（关键修复）==========
        # 检查插件是否启用，如果启用则启动配置监控
        plugin_enabled = self.get_config("plugin.enabled", True)
        if plugin_enabled:
            logger.info("🔄 插件已启用，正在初始化配置监控...")
            try:
                # 创建配置监控器实例
                from .utils.config_monitor import ConfigMonitor
                self.config_monitor = ConfigMonitor(self)
                
                # 延迟启动监控，避免启动时立即重载
                if not self._monitor_start_task or self._monitor_start_task.done():
                    self._monitor_start_task = asyncio.create_task(
                        self._start_config_monitor_after_delay()
                    )
                    logger.info("✅ 配置监控任务已创建，将在10秒后启动")
            except Exception as e:
                logger.error(f"❌ 配置监控初始化失败: {e}", exc_info=True)
                self.config_monitor = None
        else:
            logger.info("⏸️ 插件未启用，跳过配置监控")

    async def _start_config_monitor_after_delay(self):
        """延迟10秒启动配置监控"""
        logger.info(f"{self.plugin_name} - 等待10秒后启动配置监控...")
        await asyncio.sleep(10)
        if self.config_monitor:
            if not self.config_monitor.is_running:
                logger.info(f"🚀 {self.plugin_name} - 开始启动配置监控...")
                await self.config_monitor.start()
            else:
                logger.info(f"ℹ️ {self.plugin_name} - 配置监控已在运行")
        else:
            logger.error(f"❌ {self.plugin_name} - 配置监控器未初始化")

    async def on_unload(self):
        """插件卸载时清理监控任务"""
        logger.info("🔄 插件正在卸载，清理配置监控...")
        
        # 取消延迟启动任务
        if self._monitor_start_task and not self._monitor_start_task.done():
            self._monitor_start_task.cancel()
            try:
                await self._monitor_start_task
            except asyncio.CancelledError:
                pass
            self._monitor_start_task = None
        
        # 停止并清理配置监控器
        if self.config_monitor:
            try:
                from .utils.config_monitor import ConfigMonitor  # 添加这行
                await ConfigMonitor.cleanup(self.plugin_name)
                logger.info("✅ 配置监控已清理")
            except Exception as e:
                logger.error(f"❌ 配置监控清理失败: {e}")
            finally:
                self.config_monitor = None
        
        await super().on_unload()

    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        """返回插件包含的所有命令组件"""
        # 1. 收集所有命令类
        command_classes = [
            HelpCommand,
            HeightQueryCommand,
            TaskQueryCommand,
            CandleQueryCommand,
            AncestorQueryCommand,
            MagicQueryCommand,
            SeasonCandleQueryCommand,
            CalendarQueryCommand,
            RedStoneQueryCommand,
            SkyTestCommand,
            AllQueryCommand,
        ]

        # 2. 动态替换命令前缀
        prefix = self.get_config("plugin.command_prefix", "#")
        escaped_prefix = re.escape(prefix)
        for cmd_cls in command_classes:
            cmd_cls.command_pattern = cmd_cls.command_pattern.format(escaped_prefix=escaped_prefix)

        # 3. 返回组件列表
        return [(cls.get_command_info(), cls) for cls in command_classes]