"""
智能配置监控器
支持 Watchdog 和轮询两种模式，单例模式避免重复启动
"""
import asyncio
import os
import time
from typing import Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from src.plugin_system.apis import plugin_manage_api, get_logger

logger = get_logger("sky_tools_plugin.ConfigMonitor")


class AsyncWatchdogHandler(FileSystemEventHandler):
    """异步安全的 Watchdog 处理器"""

    def __init__(self, callback, loop):
        self.callback = callback
        self.loop = loop
        self._last_trigger_time = 0
        self._debounce_task = None

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith("config.toml"):
            self._handle_config_change()

    def on_closed(self, event):
        if not event.is_directory and event.src_path.endswith("config.toml"):
            self._handle_config_change()

    def _handle_config_change(self):
        current_time = time.time()
        if current_time - self._last_trigger_time < 3:
            return
        self._last_trigger_time = current_time

        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()
        self._debounce_task = asyncio.run_coroutine_threadsafe(
            self._debounced_reload(), self.loop
        )

    async def _debounced_reload(self):
        await asyncio.sleep(2.0)
        await self.callback()


class ConfigMonitor:
    """智能配置监控器 - 单例模式"""

    _instances = {}
    _lock = asyncio.Lock()

    def __new__(cls, plugin):
        plugin_name = plugin.plugin_name
        if plugin_name not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[plugin_name] = instance
            instance._initialized = False
        return cls._instances[plugin_name]

    def __init__(self, plugin):
        if getattr(self, "_initialized", False):
            return
        self.plugin = plugin
        self.plugin_name = plugin.plugin_name
        self.is_running = False
        self.observer = None
        self._reload_in_progress = False
        self.config_path = self._get_config_path()
        self.loop = asyncio.get_event_loop()
        self._initialized = True
        logger.info(f"ConfigMonitor 初始化: {self.plugin_name}")

    async def start(self):
        async with self._lock:
            if self.is_running:
                logger.warning(f"{self.plugin_name} 监控已运行")
                return
            self.is_running = True
            try:
                import watchdog
                await self._start_watchdog_monitor()
            except ImportError:
                logger.warning("watchdog 未安装，使用轮询模式")
                await self._start_polling_monitor()
            except Exception as e:
                logger.error(f"Watchdog 启动失败: {e}，回退轮询")
                await self._start_polling_monitor()

    async def _start_watchdog_monitor(self):
        self.observer = Observer()
        handler = AsyncWatchdogHandler(self._safe_reload_plugin, self.loop)
        monitor_path = os.path.dirname(self.config_path)
        self.observer.schedule(handler, path=monitor_path, recursive=False)
        self.observer.start()
        logger.info(f"Watchdog 监控已启动: {monitor_path}")

    async def _start_polling_monitor(self):
        self.task = asyncio.create_task(self._polling_loop())
        logger.info("轮询监控已启动")

    async def _polling_loop(self):
        while self.is_running:
            try:
                await asyncio.sleep(30)
                await self._safe_check_config()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"轮询监控错误: {e}")
                await asyncio.sleep(60)

    async def _safe_check_config(self):
        if self._reload_in_progress or not os.path.exists(self.config_path):
            return
        try:
            current_mtime = os.path.getmtime(self.config_path)
            if not hasattr(self, "_last_mtime"):
                self._last_mtime = current_mtime
                return
            if current_mtime > self._last_mtime:
                logger.info("检测到配置文件变化")
                self._last_mtime = current_mtime
                await self._safe_reload_plugin()
        except Exception as e:
            logger.error(f"配置检查失败: {e}")

    async def _safe_reload_plugin(self):
        if self._reload_in_progress:
            return
        self._reload_in_progress = True
        try:
            await asyncio.sleep(1)
            if not os.path.exists(self.config_path):
                return
            success = await asyncio.wait_for(
                plugin_manage_api.reload_plugin(self.plugin_name), timeout=30.0
            )
            if success:
                logger.info("插件热重载成功")
            else:
                logger.error("插件热重载失败")
        except asyncio.TimeoutError:
            logger.error("插件重载超时")
        except Exception as e:
            logger.error(f"重载插件出错: {e}")
        finally:
            self._reload_in_progress = False

    async def stop(self):
        async with self._lock:
            if not self.is_running:
                return
            self.is_running = False
            if self.observer:
                self.observer.stop()
                self.observer.join(timeout=5)
                self.observer = None
            if hasattr(self, "task") and self.task and not self.task.done():
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
            logger.info("配置监控已停止")

    def _get_config_path(self):
        """获取配置文件路径 - 监控插件根目录"""
        # 获取插件根目录（向上两级：utils/ -> sky_tools_plugin/）
        current_dir = os.path.dirname(os.path.abspath(__file__))  # .../utils
        plugin_root = os.path.dirname(current_dir)  # .../sky_tools_plugin
        return os.path.join(plugin_root, "config.toml")

    @classmethod
    async def cleanup(cls, plugin_name):
        if plugin_name in cls._instances:
            instance = cls._instances[plugin_name]
            if instance.is_running:
                await instance.stop()
            del cls._instances[plugin_name]
            logger.info(f"已清理 {plugin_name} 的配置监控实例")