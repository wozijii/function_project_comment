"""
距离计算工具
计算实际距离和网格距离
"""
import math
from typing import List, Tuple
class DistanceCalculator:
    @staticmethod
    def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
        """
        计算欧几里得距离
        
        Args:
            x1, y1: 点1坐标
            x2, y2: 点2坐标
        Returns:
            float: 距离
        """
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    @staticmethod
    def manhattan_distance(x1: float, y1: float, x2: float, y2: float) -> float:
        """
        计算曼哈顿距离
        
        Args:
            x1, y1: 点1坐标
            x2, y2: 点2坐标
            
        Returns:
            float: 距离
        """
        return abs(x2 - x1) + abs(y2 - y1)
    @staticmethod
    def calculate_path_distance(path: List[Tuple[int, int]], map_converter) -> float:
        """
        计算路径的实际距离
        
        Args:
            path: 路径点列表(网格坐标)
            map_converter: 坐标转换器
        Returns:
            float: 实际距离
        """
        if len(path) < 2:
            return 0.0
        total_distance = 0.0
        for i in range(len(path) - 1):
            # 将网格坐标转换为实际坐标
            x1, y1 = map_converter.grid_to_real(path[i][0], path[i][1])
            x2, y2 = map_converter.grid_to_real(path[i+1][0], path[i+1][1])
            
            # 计算实际距离
            total_distance += DistanceCalculator.manhattan_distance(x1, y1, x2, y2)
        
        return total_distance