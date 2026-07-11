"""
坐标转换类
将实际坐标转换到网格坐标
"""
from typing import Tuple, List
import numpy as np
class MapConverter:
    def __init__(self, real_x_max: float = 66.417, real_y_max: float = 37.7715):
        """
        初始化坐标转换器

        Args:
            real_x_max: 实际X轴最大坐标(米)
            real_y_max: 实际Y轴最大坐标(米)
        """
        try:
            self.grid = np.loadtxt('./map.txt', dtype=int)
        except:
            self.grid = np.zeros((100, 100), dtype=int)

        self.H, self.W = self.grid.shape

        # 确保实际坐标范围正确
        self.REAL_X_MAX = real_x_max if real_x_max > 0 else 66.417
        self.REAL_Y_MAX = real_y_max if real_y_max > 0 else 37.7715

        # 计算分辨率
        self.res_x = self.REAL_X_MAX / self.W if self.W > 0 else 0.1
        self.res_y = self.REAL_Y_MAX / self.H if self.H > 0 else 0.1
    
    def real_to_grid(self, x_real: float, y_real: float) -> Tuple[int, int]:
        """
        将实际坐标转换为网格坐标

        Args:
            x_real: 实际X坐标
            y_real: 实际Y坐标

        Returns:
            Tuple[int, int]: (col, row)网格坐标
        """
        # 确保坐标是数值类型
        try:
            x_real = float(x_real) if x_real is not None else 0.0
            y_real = float(y_real) if y_real is not None else 0.0
        except (ValueError, TypeError):
            raise ValueError(f"坐标值无效: x_real={x_real} (类型: {type(x_real).__name__}), y_real={y_real} (类型: {type(y_real).__name__})")

        # 检查 REAL_X_MAX 和 REAL_Y_MAX 是否有效
        if self.REAL_X_MAX is None or self.REAL_Y_MAX is None:
            raise ValueError(f"地图边界未初始化: REAL_X_MAX={self.REAL_X_MAX}, REAL_Y_MAX={self.REAL_Y_MAX}")

        # 检查坐标范围
        x_real = max(0, min(x_real, self.REAL_X_MAX))
        y_real = max(0, min(y_real, self.REAL_Y_MAX))

        # 计算网格坐标
        col = int(round(x_real / self.res_x))
        row = int(round(y_real / self.res_y))

        # 确保坐标在网格范围内
        col = np.clip(col, 0, self.W - 1)
        row = np.clip(row, 0, self.H - 1)

        return int(col), int(row)
    

    
    def batch_real_to_grid(self, coordinates: List[Tuple[float, float]]) -> List[Tuple[int, int]]:
        """
        批量将实际坐标转换为网格坐标
        
        Args:
            coordinates: 实际坐标列表，每个元素为(x_real, y_real)
            
        Returns:
            List[Tuple[int, int]]: 网格坐标列表，每个元素为(col, row)
        """
        if not coordinates:
            return []
        
        # 将坐标转换为numpy数组进行批量处理
        coords_np = np.array(coordinates)
        
        # 检查并裁剪坐标范围
        coords_np[:, 0] = np.clip(coords_np[:, 0], 0, self.REAL_X_MAX)
        coords_np[:, 1] = np.clip(coords_np[:, 1], 0, self.REAL_Y_MAX)
        
        # 批量计算网格坐标
        cols = np.round(coords_np[:, 0] / self.res_x).astype(int)
        rows = np.round(coords_np[:, 1] / self.res_y).astype(int)
        
        # 确保坐标在网格范围内
        cols = np.clip(cols, 0, self.W - 1)
        rows = np.clip(rows, 0, self.H - 1)
        
        # 转换为列表返回
        return list(zip(cols, rows))

