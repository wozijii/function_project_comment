"""
SKU商品模型
表示单个商品的信息
"""

from dataclasses import dataclass
from typing import Optional
# 单个sku：包数量乘以时间
# models/sku.py - 修改SKU类

@dataclass
class SKU:
    """SKU商品数据类"""
    sku_code: str  # 商品编码
    location_x: float  # 实际X坐标
    location_y: float  # 实际Y坐标
    sku_pick_speed: float = 1.0  # 拣一包用时（秒/包）
    inspected_quantity: int = 1  # 需要拣选的数量（包数）
    task_detail_id: Optional[int] = None  # 任务明细ID

    def __post_init__(self):
        """初始化后处理"""
        if self.sku_pick_speed <= 0:
            self.sku_pick_speed = 1.0
        if self.inspected_quantity <= 0:
            self.inspected_quantity = 1

    def get_picking_time(self) -> float:
        """
        获取拣货时间
        总拣货时间 = skuPickSpeed × inspectedQuantity
        """
        return self.sku_pick_speed * self.inspected_quantity

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "skuCode": self.sku_code,
            "locationX": self.location_x,
            "locationY": self.location_y,
            "skuPickSpeed": self.sku_pick_speed,
            "inspectedQuantity": self.inspected_quantity,
            "taskDetailId": self.task_detail_id  # 添加 taskDetailId 到输出
        }
