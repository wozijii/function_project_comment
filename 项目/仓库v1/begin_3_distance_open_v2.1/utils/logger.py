"""
日志工具模块
提供统一的日志配置和输出到文件/控制台的功能
按日期分层组织日志结构:
logs/
├── all.log                      # 全局所有日志汇总(最外层)
└── 20251230/                    # 按日期分文件夹
    ├── process/                 # 任务分配相关日志
    │   └── process_20251230_143022_123456.log
    ├── STATUS/                  # 状态查询日志
    │   └── get__status_process_20251230_143022_123456.log
    ├── simulate/                # 仿真相关日志
    │   └── simulate_20251230_143022_123456.log
    ├── main/                    # 主流程日志
    │   └── main_20251230.log
    └── error/                   # 错误日志
        └── error_20251230_143022_123456.log
"""
import logging
import sys
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional


class LoggerManager:
    """日志管理器"""

    _loggers = {}
    _initialized = False
    _project_root = None
    _log_base_dir = None
    _current_date = None
    _daily_dirs = {}

    @classmethod
    def setup_logging(cls, log_dir: Optional[Path] = None, project_root: Optional[Path] = None):
        """
        设置全局日志配置

        Args:
            log_dir: 日志目录路径，默认为 project_root/logs
            project_root: 项目根目录
        """
        if cls._initialized:
            return

        # 确定项目根目录
        if project_root is None:
            # 假设这个文件在 utils/ 目录下
            cls._project_root = Path(__file__).parent.parent
        else:
            cls._project_root = project_root

        # 确定日志目录
        if log_dir is None:
            cls._log_base_dir = cls._project_root / 'logs'
        else:
            cls._log_base_dir = log_dir

        # 创建基础日志目录
        cls._log_base_dir.mkdir(parents=True, exist_ok=True)

        # 初始化当前日期
        cls._current_date = datetime.now().strftime("%Y%m%d")

        # 创建今天的日期目录和子目录
        cls._setup_daily_directories(cls._current_date)

        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        # 清除现有的处理器
        root_logger.handlers.clear()

        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 1. 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # 2. 文件处理器 - 所有日志汇总(放在最外层)
        all_log_file = cls._log_base_dir / 'all.log'
        file_handler_all = logging.FileHandler(all_log_file, encoding='utf-8')
        file_handler_all.setLevel(logging.INFO)
        file_handler_all.setFormatter(formatter)
        root_logger.addHandler(file_handler_all)

        # 3. 文件处理器 - 主流程日志(按日期)
        main_log_file = cls._daily_dirs[cls._current_date]['main'] / f'main_{cls._current_date}.log'
        file_handler_main = logging.FileHandler(main_log_file, encoding='utf-8')
        file_handler_main.setLevel(logging.INFO)
        file_handler_main.setFormatter(formatter)
        root_logger.addHandler(file_handler_main)

        cls._initialized = True

        # 记录初始化信息
        logger = logging.getLogger(__name__)
        logger.info("=" * 60)
        logger.info("日志系统初始化完成")
        logger.info(f"日志基础目录: {cls._log_base_dir}")
        logger.info(f"所有日志汇总: {all_log_file}")
        logger.info(f"今日主流程日志: {main_log_file}")
        logger.info(f"今日日期目录: {cls._daily_dirs[cls._current_date]['date_dir']}")
        logger.info("=" * 60)

    @classmethod
    def _setup_daily_directories(cls, date_str: str) -> dict:
        """
        设置指定日期的目录结构

        Args:
            date_str: 日期字符串，格式 YYYYMMDD

        Returns:
            dict: 包含各类型日志目录的字典
        """
        date_dir = cls._log_base_dir / date_str

        # 创建各类型日志的子目录
        process_dir = date_dir / 'process'
        status_dir = date_dir / 'STATUS'
        simulate_dir = date_dir / 'simulate'
        main_dir = date_dir / 'main'
        error_dir = date_dir / 'error'

        # 创建所有目录
        for directory in [process_dir, status_dir, simulate_dir, main_dir, error_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        dirs_dict = {
            'date_dir': date_dir,
            'process': process_dir,
            'STATUS': status_dir,
            'simulate': simulate_dir,
            'main': main_dir,
            'error': error_dir
        }

        cls._daily_dirs[date_str] = dirs_dict
        return dirs_dict

    @classmethod
    def get_daily_directories(cls) -> dict:
        """
        获取当前日期的目录结构

        Returns:
            dict: 包含各类型日志目录的字典
        """
        if not cls._initialized:
            cls.setup_logging()

        # 检查日期是否变更
        current_date = datetime.now().strftime("%Y%m%d")
        if current_date != cls._current_date:
            cls._current_date = current_date
            cls._setup_daily_directories(current_date)

            # 更新主流程日志处理器
            root_logger = logging.getLogger()
            # 移除旧的 main 日志处理器
            handlers_to_remove = []
            for handler in root_logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    if 'main_' in str(handler.baseFilename):
                        handlers_to_remove.append(handler)

            for handler in handlers_to_remove:
                handler.close()
                root_logger.removeHandler(handler)

            # 添加新的 main 日志处理器
            main_log_file = cls._daily_dirs[current_date]['main'] / f'main_{current_date}.log'
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler_main = logging.FileHandler(main_log_file, encoding='utf-8')
            file_handler_main.setLevel(logging.INFO)
            file_handler_main.setFormatter(formatter)
            root_logger.addHandler(file_handler_main)

            logger = logging.getLogger(__name__)
            logger.info(f"日期变更，新日志目录: {cls._daily_dirs[current_date]['date_dir']}")

        return cls._daily_dirs[cls._current_date]

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        获取指定名称的日志记录器

        Args:
            name: 日志记录器名称，通常使用 __name__

        Returns:
            logging.Logger: 配置好的日志记录器
        """
        if not cls._initialized:
            cls.setup_logging()

        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(name)

        return cls._loggers[name]

    @classmethod
    def log_error(cls, error_message: str, exception: Optional[Exception] = None,
                  context: Optional[dict] = None):
        """
        记录错误到专门的错误日志文件

        Args:
            error_message: 错误消息
            exception: 异常对象(可选)
            context: 错误上下文信息,如输入数据等(可选)
        """
        try:
            daily_dirs = cls.get_daily_directories()
            error_dir = daily_dirs['error']

            # 生成错误日志文件名(带时间戳)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            error_log_file = error_dir / f'error_{timestamp}.log'

            # 写入错误日志
            with open(error_log_file, 'w', encoding='utf-8') as f:
                f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"错误信息: {error_message}\n")
                f.write("=" * 60 + "\n\n")

                # 记录上下文信息
                if context is not None:
                    f.write("错误上下文:\n")
                    f.write("-" * 60 + "\n")
                    import json
                    try:
                        context_str = json.dumps(context, ensure_ascii=False, indent=2)
                        f.write(context_str)
                    except Exception:
                        f.write(str(context))
                    f.write("\n" + "-" * 60 + "\n\n")

                if exception is not None:
                    f.write(f"异常类型: {type(exception).__name__}\n")
                    f.write(f"异常详情: {str(exception)}\n")
                    f.write("\n堆栈跟踪:\n")
                    f.write(traceback.format_exc())

                # 同时记录到全局日志
                logger = cls.get_logger(__name__)
                logger.error(f"错误已记录到: {error_log_file}")
                if exception:
                    logger.error(f"错误详情: {error_message} - {str(exception)}")
                else:
                    logger.error(f"错误详情: {error_message}")

        except Exception as e:
            # 如果记录错误失败，至少打印到控制台
            print(f"记录错误日志失败: {e}")


def setup_logger(log_dir: Optional[Path] = None, project_root: Optional[Path] = None):
    """
    设置日志系统的快捷函数

    Args:
        log_dir: 日志目录路径
        project_root: 项目根目录
    """
    LoggerManager.setup_logging(log_dir, project_root)


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器的快捷函数

    使用示例:
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("这是一条日志")

    Args:
        name: 日志记录器名称，通常使用 __name__

    Returns:
        logging.Logger: 配置好的日志记录器
    """
    return LoggerManager.get_logger(name)


def get_log_directories() -> dict:
    """
    获取当前日期的日志目录结构

    Returns:
        dict: 包含各类型日志目录的字典
        {
            'date_dir': Path,      # 日期根目录
            'process': Path,       # process 日志目录
            'STATUS': Path,        # STATUS 日志目录
            'simulate': Path,      # simulate 日志目录
            'main': Path,          # main 日志目录
            'error': Path          # error 日志目录
        }

    使用示例:
        from utils.logger import get_log_directories
        dirs = get_log_directories()
        process_log = dirs['process'] / 'my_process.log'
    """
    return LoggerManager.get_daily_directories()


def log_error(error_message: str, exception: Optional[Exception] = None,
              context: Optional[dict] = None):
    """
    记录错误到专门的错误日志文件

    使用示例:
        from utils.logger import log_error
        try:
            # some code
        except Exception as e:
            log_error("处理数据失败", e, {"input_data": payload})

    Args:
        error_message: 错误消息
        exception: 异常对象(可选)
        context: 错误上下文信息,如输入数据等(可选)
    """
    LoggerManager.log_error(error_message, exception, context)


# 自动初始化 (当模块被导入时)
# 如果需要自定义路径，请在使用前调用 setup_logger()
try:
    project_root = Path(__file__).parent.parent
    setup_logger(project_root=project_root)
except Exception as e:
    # 如果自动初始化失败，使用基本配置
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
