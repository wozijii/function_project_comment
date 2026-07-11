"""
任务模型
表示一个拣货任务
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from datetime import datetime
from .sku import SKU

@dataclass
class Task:
    """任务数据类"""
    task_id: str  # 任务ID
    mainId: int # 订单ID
    ingredient_list: str  # 配料单标识
    priority: int  # 任务优先级("1"或"2")# 默认值得在非默认值之后
    sku_list: List[SKU]  # SKU列表
    timeline: datetime  # 截止时间
    user_id: Optional[str] = None  # 分配的用户ID
    predict_start_time: Optional[datetime] = None  # 预计开始时间
    predict_start_location_x: Optional[float] = None  # 预计开始位置X
    predict_start_location_y: Optional[float] = None  # 预计开始位置Y
    predict_complete_time: Optional[datetime] = None  # 预计完成时间
    predict_complete_location_x: Optional[float] = None  # 预计完成位置X
    predict_complete_location_y: Optional[float] = None  # 预计完成位置Y
    task_status: str = "未分配"  # 任务状态# 初始状态默认
    optimized_sku_order: List[int] = field(default_factory=list)  # 优化后的SKU顺序索引
    distance: float = 0.0  # 任务执行距离
    
    def is_urgent(self) -> bool:
        """判断是否为紧急任务 (priority=1为紧急, priority=2为普通)"""
        return self.priority == 1
    
    
    def get_total_picking_time(self) -> float:
        """计算总拣货时间 - 每个SKU时间 = skuPickSpeed × inspectedQuantity"""
        total_time = 0.0
        for sku in self.sku_list:
            total_time += sku.get_picking_time()  # sku_pick_speed × inspected_quantity
        return total_time
    
    def to_dict(self) -> dict:
        """转换为输出字典格式"""
        return {
            "taskId": self.task_id,
            "mainId": self.mainId,
            "userId": self.user_id,
            "sku_order": [sku.to_dict() for sku in self.sku_list],
            "predictStartTime": self.predict_start_time.strftime("%Y-%m-%d %H:%M:%S") if self.predict_start_time else None,
            "predictStartLocationX": self.predict_start_location_x,
            "predictStartLocationY": self.predict_start_location_y,
            "predictCompleteTime": self.predict_complete_time.strftime("%Y-%m-%d %H:%M:%S") if self.predict_complete_time else None,
            "predictCompleteLocationX": self.predict_complete_location_x,
            "predictCompleteLocationY": self.predict_complete_location_y,
            "distance": round(self.distance, 2)
        }