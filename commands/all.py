"""
光遇一键查询所有信息命令
使用元数据注册表动态获取启用的命令
"""
import asyncio
from typing import Tuple, Optional, List, Dict, Any

from .base import SkyBaseCommand
from ..message_forward_helper import MessageForwardHelper
from ..metadata.registry import registry


class AllQueryCommand(SkyBaseCommand):
    """光遇一键查询所有信息命令"""

    command_name = "all"
    command_description = "一键获取所有光遇日常信息"
    command_pattern = r"^{escaped_prefix}(?:all|每日|日常|rc|mr)$"

    # 命令执行顺序（按此顺序获取信息）
    EXECUTION_ORDER = [
        "task",           # 1. 📋 每日任务
        "season_candle",  # 2. 🕯️ 季节蜡烛
        "candle",         # 3. 💎 大蜡烛
        "redstone",       # 4. 🔴 红石
        "ancestor",       # 5. 🧭 复刻
        "magic",          # 6. 🔮 魔法
        "calendar",       # 7. 🗓️ 活动日历
        "skytest",        # 8. 🔍 服务器状态
    ]

    # 命令显示名称映射
    COMMAND_NAMES = {
        "task": "每日任务",
        "season_candle": "季节蜡烛",
        "candle": "大蜡烛",
        "redstone": "红石",
        "ancestor": "复刻先祖",
        "magic": "每日魔法",
        "calendar": "活动日历",
        "skytest": "服务器状态",
    }

    # 命令图标映射
    COMMAND_ICONS = {
        "task": "📋",
        "season_candle": "🕯️",
        "candle": "💎",
        "redstone": "🔴",
        "ancestor": "🧭",
        "magic": "🔮",
        "calendar": "🗓️",
        "skytest": "🔍",
    }

    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        """执行一键查询命令"""
        # 获取框架注入的 bot 和 message 实例
        bot = getattr(self, 'bot', None)
        message = getattr(self, 'message', None)

        # 获取所有启用的命令元数据
        enabled_metadata = registry.get_all_enabled(self.get_config)

        # 筛选出执行顺序中已启用的命令
        enabled_commands = []
        for cmd_name in self.EXECUTION_ORDER:
            if cmd_name in enabled_metadata:
                enabled_commands.append(cmd_name)

        if not enabled_commands:
            await self.send_text("❌ 所有查询功能均未启用，无法执行一键查询")
            return False, "所有查询功能未启用", True

        await self.send_text("🔄 正在获取所有信息，请稍候...")

        # 按顺序收集所有信息
        messages = []

        for cmd_name in enabled_commands:
            try:
                icon = self.COMMAND_ICONS.get(cmd_name, "📌")
                display_name = self.COMMAND_NAMES.get(cmd_name, cmd_name)

                result = await self._execute_command(cmd_name, bot, message)

                if result["success"]:
                    # 统一的标题行
                    title = f"{icon} {display_name}"

                    if cmd_name == "ancestor":
                        # 复刻：标题 + 图片 + 文字，合并为一条消息
                        merged = [title]
                        if result.get("image_data"):
                            merged.append(result["image_data"])
                        if result.get("text_info"):
                            merged.append(result["text_info"])
                        if len(merged) > 1:  # 至少有一条有效内容
                            messages.append(merged)
                        else:
                            messages.append(f"{title}: 无数据")

                    elif cmd_name == "skytest":
                        # 服务器状态：标题与内容拼接为纯文本消息
                        messages.append(f"{title}\n{result['message']}")

                    else:
                        # 其他图片类功能：标题 + 图片，合并为一条消息
                        if result.get("image_data"):
                            messages.append([title, result["image_data"]])
                        else:
                            messages.append(f"{title}: 无数据")

                else:
                    messages.append(f"{icon} {display_name}: ❌ {result.get('error', '获取失败')}")

            except Exception as e:
                icon = self.COMMAND_ICONS.get(cmd_name, "📌")
                display_name = self.COMMAND_NAMES.get(cmd_name, cmd_name)
                messages.append(f"{icon} {display_name}: ❌ 错误 - {str(e)[:50]}")
                continue

        if not messages:
            await self.send_text("❌ 未能获取任何信息")
            return False, "无数据返回", True

        # 发送合并转发消息
        success = await MessageForwardHelper.send_forward_message(
            self,
            messages,
            prompt="光遇日常信息汇总",
            summary=f"共 {len(messages)} 条消息"
        )

        if success:
            return True, f"已发送 {len(messages)} 条消息", True
        else:
            await self.send_text("❌ 发送失败，请稍后重试")
            return False, "发送失败", True

    async def _execute_command(self, command_name: str, bot, message) -> Dict[str, Any]:
        """动态执行指定命令的查询方法"""
        handlers = {
            "task": self._get_task,
            "season_candle": self._get_season_candle,
            "candle": self._get_candle,
            "redstone": self._get_redstone,
            "ancestor": self._get_ancestor,
            "magic": self._get_magic,
            "calendar": self._get_calendar,
            "skytest": self._get_server_status,
        }
        handler = handlers.get(command_name)
        if not handler:
            return {"success": False, "error": f"未知命令: {command_name}"}
        return await handler(bot, message)

    # ------------------- 各功能查询实现 -------------------
    async def _get_task(self, bot, message) -> Dict[str, Any]:
        from .task import TaskQueryCommand
        cmd = TaskQueryCommand(bot, message)
        return await cmd._get_task_image(
            self.get_config("task_api.url"),
            self.get_config("task_api.key"),
            self.get_config("task_api.timeout")
        )

    async def _get_season_candle(self, bot, message) -> Dict[str, Any]:
        from .season_candle import SeasonCandleQueryCommand
        cmd = SeasonCandleQueryCommand(bot, message)
        return await cmd._get_season_candle_image(
            self.get_config("season_candle_api.url"),
            self.get_config("season_candle_api.key"),
            self.get_config("season_candle_api.timeout")
        )

    async def _get_candle(self, bot, message) -> Dict[str, Any]:
        from .candle import CandleQueryCommand
        cmd = CandleQueryCommand(bot, message)
        return await cmd._get_candle_image(
            self.get_config("candle_api.url"),
            self.get_config("candle_api.key"),
            self.get_config("candle_api.timeout")
        )

    async def _get_redstone(self, bot, message) -> Dict[str, Any]:
        from .redstone import RedStoneQueryCommand
        cmd = RedStoneQueryCommand(bot, message)
        return await cmd._get_redstone_image(
            self.get_config("redstone_api.url"),
            self.get_config("redstone_api.key"),
            self.get_config("redstone_api.timeout")
        )

    async def _get_ancestor(self, bot, message) -> Dict[str, Any]:
        from .ancestor import AncestorQueryCommand
        cmd = AncestorQueryCommand(bot, message)
        return await cmd._get_ancestor_info(
            self.get_config("ancestor_api.url"),
            self.get_config("ancestor_api.key"),
            self.get_config("ancestor_api.timeout")
        )

    async def _get_magic(self, bot, message) -> Dict[str, Any]:
        from .magic import MagicQueryCommand
        cmd = MagicQueryCommand(bot, message)
        return await cmd._get_magic_image(
            self.get_config("magic_api.url"),
            self.get_config("magic_api.key"),
            self.get_config("magic_api.timeout")
        )

    async def _get_calendar(self, bot, message) -> Dict[str, Any]:
        from .calendar import CalendarQueryCommand
        cmd = CalendarQueryCommand(bot, message)
        return await cmd._get_calendar_image(
            self.get_config("calendar_api.url"),
            self.get_config("calendar_api.key"),
            self.get_config("calendar_api.timeout")
        )

    async def _get_server_status(self, bot, message) -> Dict[str, Any]:
        from .skytest import SkyTestCommand
        cmd = SkyTestCommand(bot, message)
        return await cmd._get_server_status(
            self.get_config("skytest_api.url"),
            self.get_config("skytest_api.key"),
            self.get_config("skytest_api.timeout")
        )