"""
任务优化模块
优化任务内SKU顺序和任务间顺序
"""

from typing import List, Tuple, Dict, Optional
import itertools
import logging
from models.task import Task
from models.sku import SKU
from core.path_finder import PathFinder
from core.tsp_solver import TSPSolver
from utils.map_converter import MapConverter
from utils.coordinate_fixer import snap_to_nearest_free
from utils.stop_signal import stop_signal
from datetime import datetime

logger = logging.getLogger(__name__)

class TaskOptimizer:
    def __init__(self, warehouse_map, map_converter: MapConverter, real_x_max: float = 66.417, real_y_max: float = 37.7715):
        """
        初始化任务优化器

        Args:
            warehouse_map: 仓库地图
            map_converter: 坐标转换器
            real_x_max: 实际X轴最大坐标(米)
            real_y_max: 实际Y轴最大坐标(米)
        """
        self.warehouse_map = warehouse_map
        self.map_converter = map_converter
        self.path_finder = PathFinder(warehouse_map, real_x_max, real_y_max)
    
    
    def optimize_sku_order_in_task(self, task: Task, start_grid: Tuple[int, int]) -> Tuple[List[int], float]:
        """
        优化任务内SKU的顺序(旅行商问题)

        Args:
            task: 任务对象
            start_grid: 起始网格坐标 (row, col) 格式

        Returns:
            Tuple[List[int], float]: (优化后的SKU顺序索引, 最短距离)
        """
        # 检查停止信号
        if stop_signal.should_stop():
            logger.info(f"任务 {task.task_id} 的TSP优化被用户停止")
            return list(range(len(task.sku_list))), 0.0

        if len(task.sku_list) <= 1:
            # 只有一个或零个SKU，不需要TSP优化
            print(f"    DEBUG: 任务 {task.task_id} 只有 {len(task.sku_list)} 个SKU，跳过TSP优化")
            if task.sku_list:
                sku = task.sku_list[0]
                sku_col, sku_row = self.map_converter.real_to_grid(sku.location_x, sku.location_y)
                sku_col, sku_row = snap_to_nearest_free(sku_col, sku_row)

                # 注意：start_grid是(row, col)，SKU位置是(col, row)
                # 需要转换格式
                distance = self.path_finder.find_path_length(
                    start_grid,  # (row, col)
                    (sku_row, sku_col)  # 转换为(row, col)
                )
                print(f"    DEBUG: 单SKU距离 = {distance:.2f} 米")
                return [0], distance if distance < float('inf') else 0.0
            print(f"    DEBUG: 任务无SKU，距离 = 0.0 米")
            return [0], 0.0
        
        # 获取所有SKU的实际坐标
        real_coords = [(sku.location_x, sku.location_y) for sku in task.sku_list]
        
        # 批量转换为网格坐标
        grid_coords = self.map_converter.batch_real_to_grid(real_coords)
        
        # 修正坐标并转换为(row, col)格式
        sku_grids = []
        for col, row in grid_coords:
            col, row = snap_to_nearest_free(col, row)
            sku_grids.append((row, col))
        
        # 构建距离矩阵(包括起点)
        all_points = [start_grid] + sku_grids
        n = len(all_points)

        # ortools需要整数距离,将米转换为厘米避免精度损失
        distance_matrix = [[0] * n for _ in range(n)]

        # 计算所有点对之间的距离
        for i in range(n):
            for j in range(n):
                if i != j:
                    # all_points[i]和all_points[j]都是(row, col)格式
                    distance = self.path_finder.find_path_length(all_points[i], all_points[j])

                    # 检查是否为无穷大
                    if distance == float('inf') or distance >= 1e9:
                        # 设置一个大值而不是inf (转换为厘米)
                        distance_matrix[i][j] = 1000000  # 10000米
                    else:
                        # 转换为厘米,确保是整数
                        distance_matrix[i][j] = int(distance * 100)

        # 使用TSP求解器优化顺序(开环模式,起点固定为0)
        try:
            tsp_solver = TSPSolver(distance_matrix, open_loop=True)
            route, total_distance_cm = tsp_solver.solve()

            # 调试信息
            print(f"    DEBUG: TSP route = {route}")
            print(f"    DEBUG: TSP total_distance_cm = {total_distance_cm}厘米 = {total_distance_cm/100:.2f}米")

            # 手动验证路径距离
            if len(route) >= 2:
                manual_dist = 0
                for i in range(len(route)-1):
                    from_node = route[i]
                    to_node = route[i+1]
                    d = distance_matrix[from_node][to_node]
                    manual_dist += d
                    print(f"    DEBUG: 路径段 {from_node} -> {to_node}: {d}厘米 = {d/100:.2f}米")
                print(f"    DEBUG: 手动计算路径距离(开环): {manual_dist}厘米 = {manual_dist/100:.2f}米")

            total_distance = total_distance_cm / 100.0  # 转回米

        except Exception as e:
            print(f"    TSP求解失败: {e}, 使用原始顺序")
            return list(range(len(task.sku_list))), 0.0

        # 如果总距离异常大，使用简单顺序
        if total_distance >= 10000.0 * (n-1) * 0.5:
            print(f"    TSP距离异常大: {total_distance:.2f}, 使用原始顺序")
            return list(range(len(task.sku_list))), 0.0

        # 从路径中提取SKU的顺序(跳过起点)
        sku_order = []
        for node in route:
            if node > 0:  # 0是起点，1开始是SKU
                sku_order.append(node - 1)

        return sku_order, total_distance
    
    def optimize_task_sequence(self, tasks: List[Task], start_grid: Tuple[int, int]) -> Tuple[List[int], float]:
        """
        优化任务序列顺序
        
        Args:
            tasks: 任务列表
            start_grid: 起始网格坐标
            
        Returns:
            Tuple[List[int], float]: (优化后的任务顺序索引, 最短距离)
        """
        if len(tasks) <= 1:
            # 只有一个任务，不需要优化
            return [0], 0.0
        
        # 获取每个任务的起始和结束网格坐标
        task_points = []
        for task in tasks:
            # 任务起点(上一个任务的结束位置或初始位置)
            start_col, start_row = start_grid[1], start_grid[0]
            
            # 任务内优化(这里简化处理，实际需要优化SKU顺序)
            # 计算任务结束位置(最后一个SKU的位置)
            if task.sku_list:
                last_sku = task.sku_list[-1]
                end_col, end_row = self.map_converter.real_to_grid(
                    last_sku.location_x, last_sku.location_y)
                end_col, end_row = snap_to_nearest_free(end_col, end_row)
            else:
                end_col, end_row = start_col, start_row
            
            task_points.append(((start_row, start_col), (end_row, end_col)))
        
        # 构建任务间的距离矩阵(使用整数,厘米为单位)
        n = len(tasks)
        distance_matrix = [[0] * n for _ in range(n)]

        # 计算任务间的移动距离(从任务i的结束点到任务j的起点)
        for i in range(n):
            for j in range(n):
                if i != j:
                    # 从任务i的结束点到任务j的起点
                    end_i = task_points[i][1]
                    start_j = task_points[j][0]
                    distance = self.path_finder.find_path_length(end_i, start_j)
                    if distance >= float('inf') - 1:
                        distance_matrix[i][j] = 1000000  # 10000米
                    else:
                        distance_matrix[i][j] = int(distance * 100)  # 转为厘米

        # 使用TSP求解器优化任务顺序
        tsp_solver = TSPSolver(distance_matrix)
        task_order, total_distance_cm = tsp_solver.solve()
        total_distance = total_distance_cm / 100.0  # 转回米

        return task_order, total_distance
    def  calculate_task_completion_time(self, task: Task, start_grid: Tuple[int, int], # 包数*时间
                                 start_time: float) -> Tuple[float, float, Tuple[int, int]]:
        """
        计算任务的完成时间和距离
        
        Args:
            task: 任务对象
            start_grid: 起始网格坐标
            start_time: 开始时间
            
        Returns:
            Tuple[float, float, Tuple[int, int]]: (完成时间, 移动距离, 结束网格坐标)
        """
        # 优化SKU顺序
        sku_order, distance = self.optimize_sku_order_in_task(task, start_grid)
        
        # 设置优化后的SKU顺序
        task.optimized_sku_order = sku_order
        
        # 计算总时间 = 移动时间 + 拣货时间
        move_time = distance / 0.83  # 假设移动速度为0.83米/秒
        
        # 拣货时间：每个SKU的拣货时间 = skuPickSpeed × inspectedQuantity
        pick_time = task.get_total_picking_time()  # 这里已经是乘法计算
        
        total_time = move_time + pick_time
        # 计算结束位置(最后一个SKU的位置)
        if task.sku_list:
            last_sku_idx = sku_order[-1]
            last_sku = task.sku_list[last_sku_idx]
            end_col, end_row = self.map_converter.real_to_grid(
                last_sku.location_x, last_sku.location_y)
            end_col, end_row = snap_to_nearest_free(end_col, end_row)
        else:
            end_row, end_col = start_grid
        
        # 设置任务距离
        task.distance = distance
        
        return total_time, distance, (end_row, end_col)