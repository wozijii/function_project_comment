"""
项目运行状态追踪模块
用于实时追踪任务分配和仿真的执行状态,供前端查询
"""
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum


class ProcessStatus(Enum):
    """Process 任务分配状态枚举"""
    IDLE = "空闲"
    LOADING_DATA = "加载数据中"
    ALLOCATING = "任务分配中"
    OPTIMIZING = "优化员工顺序中"
    SAVING = "保存结果中"
    COMPLETE = "完成"
    ERROR = "错误"
    STOPPED = "已停止"


class SimulateStatus(Enum):
    """Simulate 仿真状态枚举"""
    IDLE = "空闲"
    PREPARING = "准备数据中"
    RENDERING = "渲染视频中"
    COMPLETE = "完成"
    ERROR = "错误"
    STOPPED = "已停止"


@dataclass
class ProcessState:
    """Process 任务分配状态"""
    status: ProcessStatus = ProcessStatus.IDLE# 状态    
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    current_task_id: Optional[str] = None  # 当前正在分配的任务ID
    current_worker_name: Optional[str] = None  # 当前正在分配的员工
    task_progress: int = 0  # 已分配任务数
    total_tasks: int = 0  # 总任务数
    worker_optimization_progress: int = 0  # 已优化的员工数
    total_workers: int = 0  # 总员工数
    error_message: Optional[str] = None
    simulate_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "status": self.status.value,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S") if self.start_time else None,
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S") if self.end_time else None,
            "current_task_id": self.current_task_id,
            "current_worker_name": self.current_worker_name,
            "task_progress": self.task_progress,
            "total_tasks": self.total_tasks,
            "worker_optimization_progress": self.worker_optimization_progress,
            "total_workers": self.total_workers,
            "error_message": self.error_message,
            "simulate_id": self.simulate_id,
            "event": self._get_event_description()
        }
        return result

    def _get_event_description(self) -> str:
        """获取当前事件的详细描述"""
        if self.status == ProcessStatus.IDLE:
            return "等待任务"
        elif self.status == ProcessStatus.LOADING_DATA:
            return "加载员工和任务数据中"
        elif self.status == ProcessStatus.ALLOCATING:
            if self.current_task_id and self.current_worker_name:
                return f"任务分配中: 任务 {self.current_task_id} → {self.current_worker_name} ({self.task_progress}/{self.total_tasks})"
            return f"任务分配中 ({self.task_progress}/{self.total_tasks})"
        elif self.status == ProcessStatus.OPTIMIZING:
            return f"优化员工顺序中 ({self.worker_optimization_progress}/{self.total_workers})"
        elif self.status == ProcessStatus.SAVING:
            return "保存分配结果中"
        elif self.status == ProcessStatus.COMPLETE:
            return "任务分配完成"
        elif self.status == ProcessStatus.ERROR:
            return f"错误: {self.error_message}"
        elif self.status == ProcessStatus.STOPPED:
            return "任务分配已停止"
        return "未知状态"


@dataclass
class SimulateState:
    """Simulate 仿真状态"""
    status: SimulateStatus = SimulateStatus.IDLE
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    current_frame: Optional[int] = None  # 当前渲染帧
    total_frames: Optional[int] = None  # 总帧数
    progress_percent: float = 0.0  # 进度百分比
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "status": self.status.value,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S") if self.start_time else None,
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S") if self.end_time else None,
            "current_frame": self.current_frame,
            "total_frames": self.total_frames,
            "progress_percent": round(self.progress_percent, 2),
            "error_message": self.error_message,
            "event": self._get_event_description()
        }
        return result

    def _get_event_description(self) -> str:
        """获取当前事件的详细描述"""
        if self.status == SimulateStatus.IDLE:
            return "等待仿真"
        elif self.status == SimulateStatus.PREPARING:
            return "准备仿真数据中"
        elif self.status == SimulateStatus.RENDERING:
            if self.total_frames and self.current_frame:
                return f"渲染视频中: {self.current_frame}/{self.total_frames} 帧 ({self.progress_percent:.1f}%)"
            return "渲染视频中"
        elif self.status == SimulateStatus.COMPLETE:
            return "仿真完成"
        elif self.status == SimulateStatus.ERROR:
            return f"错误: {self.error_message}"
        elif self.status == SimulateStatus.STOPPED:
            return "仿真已停止"
        return "未知状态"


class StatusTracker:
    """
    全局状态追踪器 (线程安全单例)
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.process_state = ProcessState()
        self.simulate_state = SimulateState()
        self._data_lock = threading.Lock()

    # ========== Process 状态管理 ==========

    def process_start(self, simulate_id: Optional[int] = None):
        """开始任务分配"""
        with self._data_lock:
            self.process_state = ProcessState(
                status=ProcessStatus.LOADING_DATA,
                start_time=datetime.now(),
                simulate_id=simulate_id
            )

    def process_loading_complete(self, total_tasks: int, total_workers: int):
        """数据加载完成"""
        with self._data_lock:
            self.process_state.status = ProcessStatus.ALLOCATING
            self.process_state.total_tasks = total_tasks
            self.process_state.total_workers = total_workers

    def process_allocating_task(self, task_id: str, worker_name: str, progress: int):
        """更新任务分配进度"""
        with self._data_lock:
            self.process_state.current_task_id = task_id
            self.process_state.current_worker_name = worker_name
            self.process_state.task_progress = progress

    def process_allocation_complete(self):
        """任务分配完成,开始优化"""
        with self._data_lock:
            self.process_state.status = ProcessStatus.OPTIMIZING
            self.process_state.current_task_id = None
            self.process_state.current_worker_name = None

    def process_optimizing_worker(self, worker_name: str, progress: int):
        """更新员工优化进度"""
        with self._data_lock:
            self.process_state.current_worker_name = worker_name
            self.process_state.worker_optimization_progress = progress

    def process_saving(self):
        """开始保存结果"""
        with self._data_lock:
            self.process_state.status = ProcessStatus.SAVING

    def process_complete(self):
        """任务分配完成"""
        with self._data_lock:
            self.process_state.status = ProcessStatus.COMPLETE
            self.process_state.end_time = datetime.now()

    def process_error(self, error_message: str):
        """任务分配出错"""
        with self._data_lock:
            self.process_state.status = ProcessStatus.ERROR
            self.process_state.error_message = error_message
            self.process_state.end_time = datetime.now()

    def process_stopped(self):
        """任务分配被停止"""
        with self._data_lock:
            self.process_state.status = ProcessStatus.STOPPED
            self.process_state.end_time = datetime.now()

    def process_reset(self):
        """重置 process 状态"""
        with self._data_lock:
            self.process_state = ProcessState()

    # ========== Simulate 状态管理 ==========

    def simulate_start(self):
        """开始仿真"""
        with self._data_lock:
            self.simulate_state = SimulateState(
                status=SimulateStatus.PREPARING,
                start_time=datetime.now()
            )

    def simulate_rendering(self, total_frames: int):
        """开始渲染视频"""
        with self._data_lock:
            self.simulate_state.status = SimulateStatus.RENDERING
            self.simulate_state.total_frames = total_frames

    def simulate_rendering_progress(self, current_frame: int):
        """更新渲染进度"""
        with self._data_lock:
            self.simulate_state.current_frame = current_frame
            if self.simulate_state.total_frames:
                self.simulate_state.progress_percent = (
                    current_frame / self.simulate_state.total_frames * 100
                )

    def simulate_complete(self):
        """仿真完成"""
        with self._data_lock:
            self.simulate_state.status = SimulateStatus.COMPLETE
            self.simulate_state.end_time = datetime.now()

    def simulate_error(self, error_message: str):
        """仿真出错"""
        with self._data_lock:
            self.simulate_state.status = SimulateStatus.ERROR
            self.simulate_state.error_message = error_message
            self.simulate_state.end_time = datetime.now()

    def simulate_stopped(self):
        """仿真被停止"""
        with self._data_lock:
            self.simulate_state.status = SimulateStatus.STOPPED
            self.simulate_state.end_time = datetime.now()

    def simulate_reset(self):
        """重置 simulate 状态"""
        with self._data_lock:
            self.simulate_state = SimulateState()

    # ========== 查询接口 ==========

    def get_process_status(self) -> Dict[str, Any]:
        """获取 Process 当前状态"""
        with self._data_lock:
            return self.process_state.to_dict()

    def get_simulate_status(self) -> Dict[str, Any]:
        """获取 Simulate 当前状态"""
        with self._data_lock:
            return self.simulate_state.to_dict()

    def get_all_status(self) -> Dict[str, Any]:
        """获取所有状态"""
        with self._data_lock:
            return {
                "process": self.process_state.to_dict(),
                "simulate": self.simulate_state.to_dict(),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }


# ========== 全局单例实例 ==========
# 代码中其他地方导入这个实例来使用
status_tracker = StatusTracker()
