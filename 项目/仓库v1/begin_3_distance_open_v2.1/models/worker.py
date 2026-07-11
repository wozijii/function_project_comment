"""
拣货人员模型
表示一个拣货人员的信息和状态
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from datetime import datetime
from .task import Task

@dataclass
class Worker:
    """拣货人员数据类"""
    sn: str  # 设备序列号
    user_id: str  # 用户ID
    name: str  # 姓名
    user_move_speed: float  # 移动速度 
    pda_location_x: float  # PDA当前位置X 
    pda_location_y: float  # PDA当前位置Y 
    pad_location_time: datetime  # PDA位置记录时间
    area: List[str] = field(default_factory=list)  # 负责区域# 暂时不用
    allocated_tasks: List[Task] = field(default_factory=list)  # 已分配任务
    current_task_index: int = 0  # 当前执行的任务索引
    
    def __post_init__(self):# 
        """初始化后处理"""
        if self.user_move_speed <= 0:
            self.user_move_speed = 0.83# 移动速度
    
    
    def get_current_location(self) -> Tuple[float, float]:# 持续更新
        """
        获取当前位置
        
        Returns:
            Tuple[float, float]: (x, y)坐标
        """
        
        if self.allocated_tasks:
            # 查找最后一个已完成的任务
            for task in reversed(self.allocated_tasks):
                if task.task_status == "已完成" and task.predict_complete_location_x and task.predict_complete_location_y:
                    return (task.predict_complete_location_x, task.predict_complete_location_y)
        
        # 否则返回PDA位置
        return (self.pda_location_x, self.pda_location_y)
    
    def get_current_grid_location(self, map_converter) -> Tuple[int, int]:
        """
        获取当前网格坐标位置
        
        Args:
            map_converter: 坐标转换器
            
        Returns:
            Tuple[int, int]: (row, col)网格坐标格式
        """

        x, y = self.get_current_location()
        col, row = map_converter.real_to_grid(x, y)

        # 打印时间戳
        from datetime import datetime
        now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\ntime: {now_time}")

        # 打印调试信息
        print(f"员工 {self.name} 当前位置:")
        print(f"  实际坐标: ({x:.2f}, {y:.2f})")
        print(f"  转换后网格坐标: col={col}, row={row}")
        
        # 修正到可通行位置
        try:
            from utils.coordinate_fixer import snap_to_nearest_free
            col, row = snap_to_nearest_free(col, row)
            print(f"  修正后可通行坐标: col={col}, row={row}")
        except Exception as e:
            print(f"坐标修正失败: {e}")
            # 确保坐标在有效范围内
            if hasattr(map_converter, 'W') and hasattr(map_converter, 'H'):
                col = max(0, min(col, map_converter.W - 1))
                row = max(0, min(row, map_converter.H - 1))
                print(f"  边界修正后坐标: col={col}, row={row}")
        
        # 返回(row, col)格式
        return row, col
    
    def calculate_completion_time(self, new_task: Task, insert_position: int = -1) -> Tuple[float, List[int]]:
        """
        计算插入新任务后的完成时间
        Args:
            new_task: 新任务
            insert_position: 插入位置(-1表示最后)
        Returns:
            Tuple[float, List[int]]: (完成时间, 任务顺序)
        """
        # 这里只是一个占位实现，具体计算在optimizer中
        return 0.0, []
    
    def add_task(self, task: Task, insert_position: int = -1) -> None:
        """
        添加任务到任务列表
        Args:
            task: 要添加的任务
            insert_position: 插入位置(-1表示最后)
        """
        if insert_position == -1:
            self.allocated_tasks.append(task)
        else:
            self.allocated_tasks.insert(insert_position, task)
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "sn": self.sn,
            "userId": self.user_id,
            "name": self.name,
            "usermoveSpeed": self.user_move_speed,
            "area": self.area,
            "allocatedTask": [task.to_dict() for task in self.allocated_tasks],
            "pdaLocationX": self.pda_location_x,
            "pdaLocationY": self.pda_location_y,
            "padLocationTime": self.pad_location_time.strftime("%Y-%m-%d %H:%M:%S")
        }