"""
光遇工具帮助命令 - 动态生成概览与详细帮助（支持自定义顺序+元数据前缀）
"""
from typing import Tuple, Optional

from .base import SkyBaseCommand
from ..message_forward_helper import MessageForwardHelper
from ..metadata.registry import registry


class HelpCommand(SkyBaseCommand):
    """光遇工具帮助命令"""

    command_name = "skytools"
    command_description = "查看光遇工具插件所有功能"
    command_pattern = r"^{escaped_prefix}(?:skytools|help)(?:\s+(?P<command_name>\S+))?$"

    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        """执行帮助命令"""
        cmd_name = self.matched_groups.get("command_name")
        if cmd_name:
            help_text = await self._generate_detail(cmd_name)
        else:
            help_text = await self._generate_overview()

        await MessageForwardHelper.send_forward_message(self, [help_text])
        return True, "显示帮助信息", True

    async def _generate_overview(self) -> str:
        """生成命令概览（支持自定义顺序，未指定命令自动追加）"""
        prefix = self.get_config("plugin.command_prefix", "#")

        # 获取所有启用的命令元数据
        enabled_metadata = registry.get_all_enabled(self.get_config)

        lines = ["✨ 光遇工具插件使用说明 ✨", "", "📋 可用命令:"]

        # 从配置获取自定义显示顺序
        display_order = self.get_config("settings.command_display_order", [])
        
        # 用于记录已处理的命令
        processed_commands = set()
        
        # 1. 先按指定顺序显示命令
        for cmd_name in display_order:
            if cmd_name in enabled_metadata and cmd_name not in processed_commands:
                meta = enabled_metadata[cmd_name]
                self._append_command_line(lines, meta, prefix)
                processed_commands.add(cmd_name)
        
        # 2. 再按元数据注册顺序显示剩余的命令
        from ..metadata.command_metadata import ALL_COMMAND_METADATA
        for meta in ALL_COMMAND_METADATA:
            cmd_name = meta["name"]
            if cmd_name in enabled_metadata and cmd_name not in processed_commands and cmd_name != self.command_name:
                self._append_command_line(lines, enabled_metadata[cmd_name], prefix)
                processed_commands.add(cmd_name)

        lines.append("💡 提示: 部分功能可能已被管理员禁用")
        return "\n".join(lines)

    def _append_command_line(self, lines: list, meta: dict, prefix: str):
        """添加单条命令显示行（还原硬编码风格）"""
        # 获取元数据中的 emoji 前缀，默认使用 •
        cmd_prefix = meta.get("prefix", "•")
        
        # 主命令（使用全局配置的前缀）
        main_cmd = f"{prefix}{meta['name']}"
        
        # 别名（也使用全局配置的前缀）
        aliases = [f"{prefix}{a}" for a in meta.get("aliases", [])]
        
        if aliases:
            cmd_str = f"{cmd_prefix} {main_cmd} 或 {' 或 '.join(aliases)}"
        else:
            cmd_str = f"{cmd_prefix} {main_cmd}"
            
        lines.append(cmd_str)
        lines.append(f"   → {meta['description']}")
        lines.append("")  # 命令之间空行

    async def _generate_detail(self, command_name: str) -> str:
        """生成命令详细帮助（从元数据获取）"""
        prefix = self.get_config("plugin.command_prefix", "#")

        # 1. 通过命令名查找
        cmd_meta = registry.get_by_name(command_name)
        if not cmd_meta:
            # 2. 通过别名查找
            cmd_meta = registry.get_by_alias(command_name)

        if not cmd_meta:
            return f"❌ 未找到命令 `{command_name}`"

        # 检查该命令是否被禁用
        config_key = cmd_meta.get("config_key")
        if config_key and not self.get_config(config_key, True):
            return f"❌ 命令 `{cmd_meta['name']}` 当前已被管理员禁用"

        lines = [
            f"📘 **{prefix}{cmd_meta['name']}** 命令详解",
            "━━━━━━━━━━━━━━━━━━━━",
            "",
            cmd_meta.get("detailed") or cmd_meta["description"],
            "",
        ]

        # 使用示例
        if cmd_meta.get("examples"):
            lines.append("**📌 使用示例**")
            for ex in cmd_meta["examples"]:
                lines.append(f"  `{ex}`")
            lines.append("")

        # 参数说明
        if cmd_meta.get("parameters"):
            lines.append("**🔧 参数说明**")
            for param, desc in cmd_meta["parameters"].items():
                lines.append(f"  • `{param}`: {desc}")
            lines.append("")

        # 别名
        if cmd_meta.get("aliases"):
            aliases = ", ".join([f"`{prefix}{a}`" for a in cmd_meta["aliases"]])
            lines.append(f"**🔖 别名**：{aliases}")
            lines.append("")

        # 注意事项
        if cmd_meta.get("notes"):
            lines.append("**⚠️ 注意事项**")
            for note in cmd_meta["notes"]:
                lines.append(f"  • {note}")
            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)