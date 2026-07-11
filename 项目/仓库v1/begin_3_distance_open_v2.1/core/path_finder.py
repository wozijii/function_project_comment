"""
路径规划模块
使用A*算法寻找最短路径
"""

import heapq
from typing import List, Tuple, Optional, Dict
from models.warehouse import WarehouseMap

class PathFinder:
    def __init__(self, warehouse_map: WarehouseMap, real_x_max: float = 66.417, real_y_max: float = 37.7715):
        """
        初始化路径规划器
        Args:
            warehouse_map: 仓库地图
            real_x_max: 实际X轴最大坐标(米)
            real_y_max: 实际Y轴最大坐标(米)
        """
        self.warehouse_map = warehouse_map
        # 距离缓存，避免重复计算相同点对之间的距离
        self.distance_cache: Dict[Tuple[Tuple[int, int], Tuple[int, int]], float] = {}

        # 计算网格分辨率(每个网格的实际米数)
        self.grid_resolution_x = real_x_max / warehouse_map.width if warehouse_map.width > 0 else 0.2535
        self.grid_resolution_y = real_y_max / warehouse_map.height if warehouse_map.height > 0 else 0.2535

        # 使用平均分辨率作为每步的距离(简化计算)
        self.meters_per_grid_step = (self.grid_resolution_x + self.grid_resolution_y) / 2
    def a_star_search(self, start: Tuple[int, int], goal: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        """
        A*算法寻找最短路径
        
        Args:
            start: 起点(行, 列)
            goal: 终点(行, 列)
            
        Returns:
            Optional[List[Tuple[int, int]]]: 路径点列表，如果找不到则返回None
        """
        # 导入修正函数
        from utils.coordinate_fixer import snap_to_nearest_free
        
        # 首先修正起点和终点
        start_col, start_row = snap_to_nearest_free(start[1], start[0])  # 输入(row,col)，输出(col,row)
        goal_col, goal_row = snap_to_nearest_free(goal[1], goal[0])
        
        # 转换回(row, col)格式
        start = (start_row, start_col)
        goal = (goal_row, goal_col)
        
        # 检查坐标有效性
        if start[0] < 0 or start[0] >= self.warehouse_map.height:
            return None
        
        if start[1] < 0 or start[1] >= self.warehouse_map.width:
            return None
        
        if goal[0] < 0 or goal[0] >= self.warehouse_map.height:
            return None
        
        if goal[1] < 0 or goal[1] >= self.warehouse_map.width:
            return None
        
        # 验证修正后的点是否确实可通行
        if not self.warehouse_map.is_valid_position(start[0], start[1]):
            # 直接返回None，避免无限循环
            return None
        
        if not self.warehouse_map.is_valid_position(goal[0], goal[1]):
            return None
        
        # 如果起点和终点相同
        if start == goal:
            return [start]
    
    
        # 初始化优先队列
        open_set = []
        heapq.heappush(open_set, (0, start))
        # 记录父节点
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        # g(n): 从起点到当前节点的实际代价
        g_score: Dict[Tuple[int, int], float] = {start: 0}
        # f(n) = g(n) + h(n)
        f_score: Dict[Tuple[int, int], float] = {start: self.heuristic(start, goal)}
        while open_set:
            current = heapq.heappop(open_set)[1]
            # 如果到达目标
            if current == goal:
                return self.reconstruct_path(came_from, current)
            # 遍历邻居节点
            for neighbor in self.warehouse_map.get_neighbors(current[0], current[1]):
                # 计算从起点到邻居的代价
                tentative_g_score = g_score[current] + 1  # 每个移动代价为1
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    # 找到更好的路径
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self.heuristic(neighbor, goal)
                    # 如果邻居不在开放列表中，加入
                    if neighbor not in [item[1] for item in open_set]:
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))
        # 没有找到路径
        return None
    def heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """
        启发函数(曼哈顿距离)
        Args:
            a: 点A
            b: 点B
        Returns:
            float: 启发值
        """
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    def reconstruct_path(self, came_from: Dict[Tuple[int, int], Tuple[int, int]], 
                        current: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        重建路径
        Args:
            came_from: 父节点字典
            current: 当前节点
            
        Returns:
            List[Tuple[int, int]]: 重建的路径
        """
        total_path = [current]
        while current in came_from:
            current = came_from[current]
            total_path.append(current)
        total_path.reverse()
        return total_path
    
    def find_path_length(self, start: Tuple[int, int], goal: Tuple[int, int]) -> float:
        """
        计算最短路径长度(实际米数)

        Args:
            start: 起点
            goal: 终点

        Returns:
            float: 路径长度(米)
        """
        # 检查缓存中是否已有结果
        cache_key = (start, goal)
        if cache_key in self.distance_cache:
            return self.distance_cache[cache_key]

        # 计算路径并缓存结果
        path = self.a_star_search(start, goal)
        if path:
            grid_steps = len(path) - 1  # 减去起点,得到网格步数
            # 将网格步数转换为实际米数
            distance = grid_steps * self.meters_per_grid_step
        else:
            distance = float('inf')  # 无法到达

        # 缓存结果
        self.distance_cache[cache_key] = distance
        return distance

    def clear_distance_cache(self):
        """清除距离缓存"""
        self.distance_cache.clear()

    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        return {
            "cache_size": len(self.distance_cache),
            "cached_pairs": len(self.distance_cache)
        }