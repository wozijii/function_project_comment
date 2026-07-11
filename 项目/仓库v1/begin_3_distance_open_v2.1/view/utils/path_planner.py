# path_planner.py
import heapq
from typing import List, Tuple
import numpy as np


class AStarPlanner:
    def __init__(self, grid: np.ndarray):
        self.grid = grid
        self.rows, self.cols = grid.shape
    
    def heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """曼哈顿距离作为启发函数"""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    
    def get_neighbors(self, point: Tuple[int, int]) -> List[Tuple[int, int]]:
        """获取可通行的邻居节点（8方向）"""
        col, row = point
        neighbors = []
        directions = [
            (0, 1), (1, 0), (0, -1), (-1, 0),
        ]
        
        for dc, dr in directions:
            nc, nr = col + dc, row + dr
            if 0 <= nc < self.cols and 0 <= nr < self.rows:
                if self.grid[nr][nc] == 0:  # 可通行
                    neighbors.append((nc, nr))
        return neighbors
    
    def plan_path(self, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        """使用A*算法规划路径"""
        # 边界检查
        if not (0 <= start[0] < self.cols and 0 <= start[1] < self.rows):
            return [start]
        if not (0 <= goal[0] < self.cols and 0 <= goal[1] < self.rows):
            return [start]
        
        # 可通行性检查
        if self.grid[start[1]][start[0]] != 0:
            return [start]
        if self.grid[goal[1]][goal[0]] != 0:
            return [start]
        
        if start == goal:
            return [start]
        
        # A*算法
        open_set = []
        heapq.heappush(open_set, (0, start))
        
        came_from = {}
        g_score = {start: 0}
        f_score = {start: self.heuristic(start, goal)}
        
        while open_set:
            current_f, current = heapq.heappop(open_set)
            
            if current == goal:
                # 重建路径
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]
            
            for neighbor in self.get_neighbors(current):
                tentative_g = g_score[current] + 1
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self.heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
        
        # 如果没有找到路径，返回起点
        return [start]