"""
全局停止信号管理器

用于在任务分配和仿真过程中提供停止功能。
当用户点击停止按钮时，设置停止标志，正在运行的任务会检测到该标志并退出。
"""
import threading
import logging

logger = logging.getLogger(__name__)


class StopSignal:
    """线程安全的停止信号管理器"""

    def __init__(self):
        self._lock = threading.Lock()
        self._stop_requested = False

    def request_stop(self):
        """请求停止任务"""
        with self._lock:
            self._stop_requested = True
        logger.info("停止信号已设置")

    def should_stop(self) -> bool:
        """检查是否应该停止"""
        with self._lock:
            return self._stop_requested

    def reset(self):
        """重置停止标志（开始新任务前调用）"""
        with self._lock:
            was_stopped = self._stop_requested
            self._stop_requested = False
        if was_stopped:
            logger.info("停止信号已重置")


# 全局单例
stop_signal = StopSignal()
