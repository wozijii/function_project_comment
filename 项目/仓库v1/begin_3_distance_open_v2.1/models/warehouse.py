"""
仓库地图模型
负责加载和处理仓库地图数据
"""
import numpy as np
from typing import Tuple, List
class WarehouseMap:
    def __init__(self, map_file_path: str):
        """
        初始化仓库地图
        Args:
            map_file_path: 地图文件路径
        """
        self.map_file_path = map_file_path
        self.grid = None
        self.height = 0
        self.width = 0
        self.load_map()
    
    def load_map(self) -> None:
        """加载地图文件"""
        try:
            self.grid = np.loadtxt(self.map_file_path, dtype=int)
            self.height, self.width = self.grid.shape
            print(f"地图加载成功，尺寸: {self.height}x{self.width}")
        except Exception as e:
            print(f"地图加载失败: {e}")
            # 创建默认地图
            self.grid = np.zeros((100, 100), dtype=int)
            self.height, self.width = 100, 100
    
    def is_valid_position(self, row: int, col: int) -> bool:
        """
        检查位置是否有效且可通行
        Args:
            row: 行坐标
            col: 列坐标
        Returns:
            bool: 是否有效
        """
        if 0 <= row < self.height and 0 <= col < self.width:
            return self.grid[row][col] == 0
        return False
    
    def get_neighbors(self, row: int, col: int) -> List[Tuple[int, int]]:
        """
        获取相邻的可通行位置(四方向)
        Args:
            row: 当前行
            col: 当前列
        Returns:
            List[Tuple[int, int]]: 相邻位置列表
        """
        neighbors = []
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # 右,下,左,上
        for dr, dc in directions:
            new_row, new_col = row + dr, col + dc
            if self.is_valid_position(new_row, new_col):
                neighbors.append((new_row, new_col))
        return neighbors
    
    def print_map_region(self, center_row: int, center_col: int, radius: int = 5) -> None:# 暂时没有什么用
        """
        打印地图指定区域
        Args:
            center_row: 中心行
            center_col: 中心列
            radius: 显示半径
        """
        start_row = max(0, center_row - radius)
        end_row = min(self.height, center_row + radius + 1)
        start_col = max(0, center_col - radius)
        end_col = min(self.width, center_col + radius + 1)
        print(f"地图区域 ({start_row}:{end_row}, {start_col}:{end_col}):")
        for r in range(start_row, end_row):
            row_str = ""
            for c in range(start_col, end_col):
                if r == center_row and c == center_col:
                    row_str += "X "  # 当前位置
                else:
                    row_str += f"{self.grid[r][c]} "
            print(row_str)