"""
错误处理模块
统一处理系统中的错误,记录错误日志并回传给前端
"""
import sys
import traceback
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path


class ErrorHandler:
    """
    错误处理器

    职责:
    1. 捕获并记录所有异常
    2. 记录错误上下文信息
    3. 生成错误报告
    4. 支持错误回传给前端
    """

    def __init__(self):
        self._error_counts = {}  # 错误统计

    def handle_exception(
        self,
        error_message: str,
        exception: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
        notify_frontend: bool = True,
        module: str = "unknown"
    ) -> Dict[str, Any]:
        """
        统一处理异常

        Args:
            error_message: 错误消息
            exception: 异常对象(可选)
            context: 错误上下文信息(可选)
            notify_frontend: 是否通知前端(默认True)
            module: 发生错误的模块名称

        Returns:
            Dict: 错误信息字典,可用于回传给前端
        """
        try:
            # 1. 记录到日志文件
            from utils.logger import log_error
            log_error(error_message, exception, context)

            # 2. 生成错误信息字典
            error_info = self._generate_error_info(
                error_message, exception, context, module
            )

            # 3. 更新状态追踪器
            if module == "process":
                from utils.status_tracker import status_tracker
                status_tracker.process_error(error_message)
            elif module == "simulate":
                from utils.status_tracker import status_tracker
                status_tracker.simulate_error(error_message)

            # 4. 如果需要,通知前端
            if notify_frontend:
                self._notify_frontend(error_info)

            # 5. 错误统计
            self._update_error_stats(error_message)

            return error_info

        except Exception as e:
            # 如果错误处理本身出错,至少打印到控制台
            print(f"❌ 错误处理失败: {e}")
            return {
                "success": False,
                "error": error_message,
                "details": str(exception) if exception else "",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    def _generate_error_info(
        self,
        error_message: str,
        exception: Optional[Exception],
        context: Optional[Dict[str, Any]],
        module: str
    ) -> Dict[str, Any]:
        """
        生成标准化的错误信息字典

        Returns:
            Dict: {
                "success": False,
                "error": "错误消息",
                "error_type": "异常类型",
                "details": "详细错误信息",
                "traceback": "堆栈跟踪",
                "module": "模块名称",
                "timestamp": "时间戳",
                "context": {}  # 错误上下文
            }
        """
        error_info = {
            "success": False,
            "error": error_message,
            "module": module,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 如果有异常对象
        if exception:
            error_info["error_type"] = type(exception).__name__
            error_info["details"] = str(exception)
            error_info["traceback"] = traceback.format_exc()
        else:
            error_info["error_type"] = "UnknownError"
            error_info["details"] = ""
            error_info["traceback"] = ""

        # 添加上下文信息(如果有的话)
        if context:
            error_info["context"] = context

        return error_info

    def _notify_frontend(self, error_info: Dict[str, Any]):
        """
        通知前端错误信息

        通过回调接口发送错误信息到前端
        """
        try:
            import requests
            from utils.logger import get_logger

            # 读取当前轮次信息
            simulate_id = self._get_current_simulate_id()

            # 构建回调数据
            callback_data = {
                "type": "error",
                "simulate_id": simulate_id,
                "error_info": error_info,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # 发送回调请求
            url = "http://10.10.82.46:3000/api/v1/virtual-simulation/callback"
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            response = requests.post(url, json=callback_data, headers=headers, timeout=5)

            if response.status_code == 200:
                logger = get_logger(__name__)
                logger.info(f"✅ 错误信息已通知前端: {error_info['error']}")
            else:
                logger = get_logger(__name__)
                logger.warning(f"⚠️ 通知前端失败,状态码: {response.status_code}")

        except Exception as e:
            # 回调失败不影响主流程
            print(f"⚠️ 通知前端错误失败: {e}")

    def _get_current_simulate_id(self) -> Optional[int]:
        """获取当前轮次ID"""
        try:
            import json
            latest_input_path = Path("./data/latest_input.json")
            if latest_input_path.exists():
                with open(latest_input_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get('simulate_id', 0)
        except Exception:
            pass
        return None

    def _update_error_stats(self, error_message: str):
        """更新错误统计"""
        error_type = error_message.split(':')[0] if ':' in error_message else error_message
        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1

    def get_error_stats(self) -> Dict[str, int]:
        """获取错误统计"""
        return self._error_counts.copy()


# 全局单例
_error_handler = None


def get_error_handler() -> ErrorHandler:
    """获取错误处理器实例"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def handle_error(
    error_message: str,
    exception: Optional[Exception] = None,
    context: Optional[Dict[str, Any]] = None,
    notify_frontend: bool = True,
    module: str = "unknown"
) -> Dict[str, Any]:
    """
    处理错误的快捷函数

    使用示例:
        from utils.error_handler import handle_error

        try:
            # some code
        except Exception as e:
            handle_error(
                "处理数据失败",
                e,
                context={"input_data": payload},
                module="process"
            )
    """
    handler = get_error_handler()
    return handler.handle_exception(
        error_message, exception, context, notify_frontend, module
    )
