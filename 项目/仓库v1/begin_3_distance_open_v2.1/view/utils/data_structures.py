# data_structures.py
from dataclasses import dataclass
from typing import List, Dict, Tuple, Any


@dataclass
class TaskPoint:
    locationX: float
    locationY: float


@dataclass
class WorkerData:
    userId: str
    name: str
    location_X: float
    location_Y: float
    path: List[TaskPoint]


class WorkerInfo:
    """存储工作人员仿真信息的类"""
    def __init__(self, worker_id: str, name: str, start: Tuple[int, int],
                 path: List[Tuple[int, int]], color_idx: int,
                 original_positions: List[Tuple[int, int]] = None):
        """
        Args:
            worker_id: 工作人员ID
            name: 姓名
            start: 修正后的起点坐标 (col, row)
            path: 修正后的路径点列表 [(col, row), ...]
            color_idx: 颜色索引
            original_positions: 原始位置列表 [(col, row), ...]，用于可视化显示修正关系
        """
        self.id = worker_id
        self.name = name
        self.start = start
        self.path = path
        self.current_pos = start
        self.current_target_idx = 0
        self.current_path = []
        self.completed = False
        self.color_idx = color_idx
        self.traveled_path = [start]  # 记录走过的路线
        self.original_positions = original_positions or []  # 存储原始位置

    def update_position(self, new_pos: Tuple[int, int]):
        """更新位置并记录路径"""
        self.traveled_path.append(new_pos)
        self.current_pos = new_pos