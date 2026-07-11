# map_utils.py
import numpy as np
from typing import List, Tuple
from collections import deque


class MapConverter:
    def __init__(self, real_x_max: float = 66.417, real_y_max: float = 37.7715,
                 map_file_path: str = './map.txt'):
        """
        初始化坐标转换器
        """
        try:
            self.grid = np.loadtxt(map_file_path, dtype=int)
        except Exception as e:
            print(f"警告: 无法加载地图文件 {map_file_path}: {e}")
            print("使用默认地图")
            self.grid = np.zeros((100, 100), dtype=int)

        self.H, self.W = self.grid.shape
        print(f"地图加载成功，尺寸: {self.H}x{self.W}")

        self.REAL_X_MAX = real_x_max if real_x_max > 0 else 66.417
        self.REAL_Y_MAX = real_y_max if real_y_max > 0 else 37.7715

        self.res_x = self.REAL_X_MAX / self.W if self.W > 0 else 0.1
        self.res_y = self.REAL_Y_MAX / self.H if self.H > 0 else 0.1
    
    def real_to_grid(self, x_real: float, y_real: float) -> Tuple[int, int]:
        """将实际坐标转换为网格坐标"""
        x_real = max(0, min(x_real, self.REAL_X_MAX))
        y_real = max(0, min(y_real, self.REAL_Y_MAX))
        
        col = int(round(x_real / self.res_x))
        row = int(round(y_real / self.res_y))
        
        col = np.clip(col, 0, self.W - 1)
        row = np.clip(row, 0, self.H - 1)
        
        return col, row


class PositionCorrector:
    def __init__(self, map_file_path: str = './map.txt'):
        """初始化位置修正器"""
        try:
            self.grid = np.loadtxt(map_file_path, dtype=int)
        except Exception as e:
            print(f"错误: 无法加载地图文件 {map_file_path}: {e}")
            self.grid = np.zeros((100, 100), dtype=int)
        
        self.rows, self.cols = self.grid.shape
    
    def snap_to_nearest_free(self, col: int, row: int) -> Tuple[int, int]:
        """修正位置到最近的可通行位置"""
        start_r, start_c = row, col
        
        # 检查并修正边界
        start_r = max(0, min(start_r, self.rows - 1))
        start_c = max(0, min(start_c, self.cols - 1))
        
        # 如果起始位置可通行，直接返回
        if self.grid[start_r][start_c] == 0:
            return start_c, start_r
        
        # BFS搜索最近的可通行位置
        queue = deque()
        visited = [[False] * self.cols for _ in range(self.rows)]
        queue.append((start_r, start_c))
        visited[start_r][start_c] = True
        
        # 搜索方向
        directions = [
            (0, 1), (1, 0), (0, -1), (-1, 0),
           
        ]
        
        while queue:
            r, c = queue.popleft()
            
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                
                if 0 <= nr < self.rows and 0 <= nc < self.cols and not visited[nr][nc]:
                    visited[nr][nc] = True
                    
                    if self.grid[nr][nc] == 0:
                        return nc, nr
                    
                    queue.append((nr, nc))
        
        # 如果没有找到，返回原始位置
        return start_c, start_r