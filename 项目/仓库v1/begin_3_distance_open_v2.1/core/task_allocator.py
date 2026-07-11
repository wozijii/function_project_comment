from utils.coordinate_fixer import snap_to_nearest_free
"""
任务分配模块
根据策略分配任务给拣货人员
"""
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from models.worker import Worker
from models.task import Task
from core.task_optimizer import TaskOptimizer
from utils.time_utils import parse_datetime, add_seconds_to_time
try:
    from core.path_finder import PathFinder
except ImportError:
    # 如果导入失败，可能需要相对导入
    from .path_finder import PathFinder
# 导入坐标修正

from utils.coordinate_fixer import snap_to_nearest_free

class TaskAllocator:
    def __init__(self, warehouse_map, map_converter, config):
        """
        初始化任务分配器
        Args:
            warehouse_map: 仓库地图
            map_converter: 坐标转换器
            config: 配置对象
        """
        self.warehouse_map = warehouse_map
        self.map_converter = map_converter
        self.config = config
        # 初始化任务优化器(传入实际尺寸参数)
        self.task_optimizer = TaskOptimizer(warehouse_map, map_converter, config.REAL_X_MAX, config.REAL_Y_MAX)

        # 初始化路径查找器(传入实际尺寸参数)
        self.path_finder = PathFinder(warehouse_map, config.REAL_X_MAX, config.REAL_Y_MAX)

        # TSP缓存：{(task_id, start_grid_row, start_grid_col): (sku_order, distance)}
        self.tsp_cache = {}
    def allocate_task(self, workers: List[Worker], new_task: Task) -> Optional[Tuple[Worker, int]]:
        """
        分配任务给最合适的拣货人员 - 支持多种策略

        核心逻辑：
        1. 遍历所有员工
        2. 根据策略计算每个员工分配该任务的成本
        3. 选择成本最低的员工

        支持的策略：
        - 'distance_first': 只看增量距离（距离优先）
        - 'load_balance': 只看完成时间（负载均衡）
        - 'hybrid': 混合策略 COST = 移动时间增量 + α × 负载时间

        Args:
            workers: 拣货人员列表
            new_task: 新任务-> 查看新任务是紧急任务还是普通任务
        Returns:
            Optional[Tuple[Worker, int]]: (分配的人员, 插入位置)，如果无法分配则返回None
        """
        best_worker = None
        best_insert_position = -1
        best_metric = float('inf')
        for worker in workers:
            # 计算该工人分配任务后的完成时间
            if new_task.is_urgent():  # 判断是否紧急
                # 紧急任务：只能插入到当前任务之后，最前面
                insert_position, completion_time, incremental_distance = self.calculate_urgent_insertion(
                    worker, new_task)
            else:
                # 非紧急任务：可以插入到任何位置
                insert_position, completion_time, incremental_distance = self.calculate_best_insertion(
                    worker, new_task)

            # 考虑紧急任务的惩罚
            if new_task.is_urgent():
                # 检查是否会在截止时间后完成
                task_deadline = parse_datetime(new_task.timeline)
                estimated_completion = add_seconds_to_time(
                    parse_datetime(worker.pad_location_time), completion_time)

                if estimated_completion > task_deadline:
                    # 超过截止时间，增加惩罚
                    delay_seconds = (estimated_completion - task_deadline).total_seconds()
                    penalty = delay_seconds * self.config.URGENT_TASK_PENALTY
                    completion_time += penalty

            # 【新增】根据配置选择使用不同的策略
            if self.config.ALLOCATION_STRATEGY == 'distance_first':
                # 距离优先：选择增量距离最短的员工
                current_metric = incremental_distance
            elif self.config.ALLOCATION_STRATEGY == 'hybrid':
                # 混合策略：COST = 移动时间增量 + α × 负载时间
                current_metric = self._calculate_hybrid_cost(
                    incremental_distance,
                    worker
                )
            else:
                # 负载均衡（默认）：选择完成时间最短的员工
                current_metric = completion_time

            if current_metric < best_metric:
                best_metric = current_metric
                best_worker = worker
                best_insert_position = insert_position
        if best_worker:
            return best_worker, best_insert_position
        return None
    
    def calculate_best_insertion(self, worker: Worker, new_task: Task) -> Tuple[int, float, float]:
        """
        计算最佳插入位置(非紧急任务) - 使用增量距离计算

        修改说明：
        - 原来：计算总距离 = sum(所有任务距离)
        - 现在：计算增量距离 = total_with_new_task - total_without_new_task
        - 优点：更公平，避免已有大量任务的员工因为总距离大而被忽略

        Args:
            worker: 拣货人员
            new_task: 新任务

        Returns:
            Tuple[int, float, float]: (插入位置, 完成时间, 增量距离)
        """
        best_position = 0
        best_time = float('inf')
        best_incremental_distance = float('inf')

        # 获取工人当前位置
        start_col, start_row = worker.get_current_grid_location(self.map_converter)
        start_grid = (start_row, start_col)

        # 计算员工当前已有任务的总距离（作为基准）
        if worker.allocated_tasks:
            _, baseline_distance = self.calculate_total_completion(
                worker.allocated_tasks, start_grid)
        else:
            baseline_distance = 0.0

        # 如果没有任务或任务很少，直接尝试所有位置
        num_tasks = len(worker.allocated_tasks)
        if num_tasks <= 5:
            candidate_positions = range(num_tasks + 1)
        else:
            # 对于较多任务，只尝试最可能的插入位置
            # 1. 计算新任务的起始网格坐标（基于第一个SKU）
            new_task_start = None
            if new_task.sku_list:
                first_sku = new_task.sku_list[0]
                col, row = self.map_converter.real_to_grid(
                    first_sku.location_x, first_sku.location_y)
                col, row = snap_to_nearest_free(col, row)
                new_task_start = (row, col)
            else:
                new_task_start = start_grid

            # 2. 计算每个任务的起始和结束位置
            task_positions = []
            current_grid = start_grid
            for i, task in enumerate(worker.allocated_tasks):
                # 任务起始位置
                task_start = current_grid

                # 计算任务结束位置
                if task.sku_list:
                    last_sku = task.sku_list[-1]
                    col, row = self.map_converter.real_to_grid(
                        last_sku.location_x, last_sku.location_y)
                    col, row = snap_to_nearest_free(col, row)
                    task_end = (row, col)
                else:
                    task_end = current_grid

                task_positions.append((task_start, task_end))
                current_grid = task_end

            # 3. 找出与新任务最接近的任务位置
            min_distance = float('inf')
            closest_task_idx = 0

            # 比较新任务与每个任务的起始位置
            for i, (task_start, task_end) in enumerate(task_positions):
                if new_task_start:
                    distance_to_start = self.path_finder.find_path_length(new_task_start, task_start)
                    distance_to_end = self.path_finder.find_path_length(new_task_start, task_end)
                    min_dist = min(distance_to_start, distance_to_end)

                    if min_dist < min_distance:
                        min_distance = min_dist
                        closest_task_idx = i

            # 4. 只尝试最接近任务的前后位置和两端位置
            candidate_positions = set()
            # 两端位置
            candidate_positions.add(0)  # 最前面
            candidate_positions.add(num_tasks)  # 最后面
            # 最接近任务的前后位置
            candidate_positions.add(max(0, closest_task_idx - 1))
            candidate_positions.add(closest_task_idx)
            candidate_positions.add(closest_task_idx + 1)
            candidate_positions.add(min(num_tasks, closest_task_idx + 2))

            # 确保位置在有效范围内
            candidate_positions = [pos for pos in candidate_positions if 0 <= pos <= num_tasks]

        # 尝试候选插入位置
        for insert_pos in candidate_positions:
            # 创建临时任务列表
            temp_tasks = worker.allocated_tasks.copy()
            temp_tasks.insert(insert_pos, new_task)

            # 计算完成所有任务的时间和距离
            total_time, total_distance = self.calculate_total_completion(
                temp_tasks, start_grid)

            # 【关键修改】计算增量距离而不是总距离
            incremental_distance = total_distance - baseline_distance

            # 根据配置选择使用时间或距离作为插入位置选择标准
            if self.config.ALLOCATION_STRATEGY == 'distance_first':
                # 距离优先：选择增量距离最短的位置
                if incremental_distance < best_incremental_distance:
                    best_incremental_distance = incremental_distance
                    best_time = total_time
                    best_position = insert_pos
            else:
                # 负载均衡：选择总时间最短的位置
                if total_time < best_time:
                    best_time = total_time
                    best_incremental_distance = incremental_distance
                    best_position = insert_pos

        # 返回增量距离而不是总距离
        return best_position, best_time, best_incremental_distance
    
    def calculate_urgent_insertion(self, worker: Worker, urgent_task: Task) -> Tuple[int, float, float]:
        """
        计算紧急任务插入位置 - 使用增量距离计算

        修改说明：
        - 紧急任务也使用增量距离计算，保持一致性

        Args:
            worker: 拣货人员
            urgent_task: 紧急任务

        Returns:
            Tuple[int, float, float]: (插入位置, 完成时间, 增量距离)
        """

        executing_task_index = -1# 正在执行的任务索引
        for i, task in enumerate(worker.allocated_tasks):
            if task.task_status == "拣货中":
                executing_task_index = i  # 找到最后一个"拣货中"任务
        if executing_task_index >= 0:
        # 有正在执行的任务，紧急任务插入到最后一个"拣货中"任务后面
            insert_position = executing_task_index + 1
        else:
            # 没有正在执行的任务，插入到最前面
            insert_position = 0


        # 获取工人当前位置
        start_col, start_row = worker.get_current_grid_location(self.map_converter)
        start_grid = (start_row, start_col)

        # 计算员工当前已有任务的总距离（作为基准）
        if worker.allocated_tasks:
            _, baseline_distance = self.calculate_total_completion(
                worker.allocated_tasks, start_grid)
        else:
            baseline_distance = 0.0

        # 创建临时任务列表
        temp_tasks = worker.allocated_tasks.copy()
        temp_tasks.insert(insert_position, urgent_task)

        # 计算完成所有任务的时间和距离
        total_time, total_distance = self.calculate_total_completion(
            temp_tasks, start_grid)

        # 【关键修改】计算增量距离而不是总距离
        incremental_distance = total_distance - baseline_distance

        return insert_position, total_time, incremental_distance
    
    def calculate_total_completion(self, tasks: List[Task], start_grid: Tuple[int, int]) -> Tuple[float, float]:
        """
        计算完成所有任务的总时间和距离（使用TSP缓存优化）
        Args:
            tasks: 任务列表
            start_grid: 起始网格坐标

        Returns:
            Tuple[float, float]: (总时间, 总距离)
        """
        if not tasks:# 没有任务
            return 0.0, 0.0

        total_time = 0.0
        total_distance = 0.0
        current_grid = start_grid

        for task in tasks:
            # 拣货中的任务不进行TSP优化，使用原有数据
            if task.task_status == '拣货中' or task.task_status == '执行中':
                # 使用任务原有的距离和时间
                task_distance = task.distance if hasattr(task, 'distance') and task.distance > 0 else None

                # 如果没有有效的距离信息，根据预测位置计算
                if task_distance is None or task_distance == 0:
                    # 优先使用预测的起始和结束位置计算距离
                    if (hasattr(task, 'predict_start_location_x') and task.predict_start_location_x is not None and
                        hasattr(task, 'predict_start_location_y') and task.predict_start_location_y is not None and
                        hasattr(task, 'predict_complete_location_x') and task.predict_complete_location_x is not None and
                        hasattr(task, 'predict_complete_location_y') and task.predict_complete_location_y is not None):

                        # 计算从预测起始位置到预测结束位置的路径距离
                        start_col, start_row = self.map_converter.real_to_grid(
                            task.predict_start_location_x, task.predict_start_location_y)
                        end_col, end_row = self.map_converter.real_to_grid(
                            task.predict_complete_location_x, task.predict_complete_location_y)
                        start_col, start_row = snap_to_nearest_free(start_col, start_row)
                        end_col, end_row = snap_to_nearest_free(end_col, end_row)
                        start_grid = (start_row, start_col)
                        end_grid = (end_row, end_col)
                        task_distance = self.path_finder.find_path_length(start_grid, end_grid)

                        # 更新任务的distance属性，以便输出时使用
                        task.distance = task_distance
                        print(f"    拣货中任务 {task.task_id} 根据预测位置计算距离: {task_distance:.2f} 米")
                    elif task.sku_list and task.optimized_sku_order:
                        # 如果没有预测位置，根据SKU顺序计算距离
                        task_distance = 0.0
                        prev_grid = current_grid
                        for idx in task.optimized_sku_order:
                            if idx < len(task.sku_list):
                                sku = task.sku_list[idx]
                                col, row = self.map_converter.real_to_grid(sku.location_x, sku.location_y)
                                col, row = snap_to_nearest_free(col, row)
                                sku_grid = (row, col)
                                task_distance += self.path_finder.find_path_length(prev_grid, sku_grid)
                                prev_grid = sku_grid
                        # 更新任务的distance属性
                        task.distance = task_distance
                        print(f"    拣货中任务 {task.task_id} 根据SKU顺序计算距离: {task_distance:.2f} 米")
                    else:
                        task_distance = 0.0

                # 计算移动时间和拣货时间
                move_time = task_distance / 1.2 if task_distance > 0 else 0
                pick_time = task.get_total_picking_time()
                task_time = move_time + pick_time

                # 使用任务原有的预测结束位置
                if hasattr(task, 'predict_complete_location_x') and hasattr(task, 'predict_complete_location_y'):
                    end_col, end_row = self.map_converter.real_to_grid(
                        task.predict_complete_location_x, task.predict_complete_location_y)
                    end_col, end_row = snap_to_nearest_free(end_col, end_row)
                    end_grid = (end_row, end_col)
                elif task.sku_list and task.optimized_sku_order:
                    # 如果没有预测位置，使用原有的SKU顺序计算结束位置
                    last_sku_idx = task.optimized_sku_order[-1]
                    last_sku = task.sku_list[last_sku_idx]
                    end_col, end_row = self.map_converter.real_to_grid(
                        last_sku.location_x, last_sku.location_y)
                    end_col, end_row = snap_to_nearest_free(end_col, end_row)
                    end_grid = (end_row, end_col)
                else:
                    end_grid = current_grid
            else:
                # 创建缓存键：(task_id, 起始行, 起始列)
                cache_key = (task.task_id, current_grid[0], current_grid[1])

                # 检查缓存
                if cache_key in self.tsp_cache:
                    # 使用缓存的TSP结果
                    sku_order, task_distance = self.tsp_cache[cache_key]
                    # 计算结束位置
                    if task.sku_list and sku_order:
                        last_sku_idx = sku_order[-1]
                        last_sku = task.sku_list[last_sku_idx]
                        end_col, end_row = self.map_converter.real_to_grid(
                            last_sku.location_x, last_sku.location_y)
                        end_col, end_row = snap_to_nearest_free(end_col, end_row)
                        end_grid = (end_row, end_col)
                    else:
                        end_grid = current_grid

                    # 计算时间
                    move_time = task_distance / 1.2 if task_distance > 0 else 0
                    pick_time = task.get_total_picking_time()
                    task_time = move_time + pick_time

                    # 设置任务信息
                    task.optimized_sku_order = sku_order
                    task.distance = task_distance
                else:
                    # 未命中缓存，执行完整计算
                    task_time, task_distance, end_grid = self.task_optimizer.calculate_task_completion_time(
                        task, current_grid, total_time)

                    # 存入缓存
                    self.tsp_cache[cache_key] = (task.optimized_sku_order, task_distance)

            total_time += task_time
            total_distance += task_distance
            current_grid = end_grid

        return total_time, total_distance
    
    def update_worker_schedule(self, worker: Worker, new_task: Task, insert_position: int) -> None:
        """
        更新工人的任务计划
        
        Args:
            worker: 拣货人员
            new_task: 新任务
            insert_position: 插入位置
        """
        # 设置任务信息
        current_time = parse_datetime(worker.pad_location_time)
        
        # 计算新任务的开始时间
        if insert_position == 0:
            # 插入到最前面，立即开始
            new_task.predict_start_time = current_time
            start_x, start_y = worker.get_current_location()
            new_task.predict_start_location_x = start_x
            new_task.predict_start_location_y = start_y
        else:
            # 需要计算前面所有任务的完成时间
            # 这里简化处理，实际需要精确计算
            new_task.predict_start_time = current_time
        
        # 设置任务分配给该工人
        new_task.user_id = worker.user_id
        new_task.task_status = "已分配"
        
        # 添加到工人任务列表
        worker.add_task(new_task, insert_position)
    # 在TaskAllocator类末尾添加这个方法：

    def optimize_worker_tasks(self, worker: Worker) -> List[Task]:
        """
        优化员工的任务顺序（使用TSP缓存优化）

        Args:
            worker: 员工对象

        Returns:
            List[Task]: 优化后的任务列表
        """
        if len(worker.allocated_tasks) <= 1:
            # 只有一个任务，只需要优化SKU顺序
            for task in worker.allocated_tasks:
                start_grid = worker.get_current_grid_location(self.map_converter)
                cache_key = (task.task_id, start_grid[0], start_grid[1])

                # 检查缓存
                if cache_key in self.tsp_cache:
                    sku_order, distance = self.tsp_cache[cache_key]
                    task.optimized_sku_order = sku_order
                    task.distance = distance
                    print(f"    任务 {task.task_id} 使用缓存: 距离 {distance:.2f} 米, SKU顺序: {sku_order}")
                else:
                    sku_order, distance = self.task_optimizer.optimize_sku_order_in_task(task, start_grid)
                    task.optimized_sku_order = sku_order
                    task.distance = distance
                    self.tsp_cache[cache_key] = (sku_order, distance)
                    print(f"    任务 {task.task_id} 优化后距离: {distance:.2f} 米, SKU顺序: {sku_order}")
            return worker.allocated_tasks

        # 分离任务: 拣货中 > 紧急 > 普通
        picking_tasks = []      # 拣货中 (第一优先级)
        urgent_tasks = []       # 紧急任务 (第二优先级)
        non_urgent_tasks = []   # 普通任务 (第三优先级)

        for task in worker.allocated_tasks:
            if task.task_status == '拣货中' or task.task_status == '执行中':
                picking_tasks.append(task)
            elif task.is_urgent():
                urgent_tasks.append(task)
            else:
                non_urgent_tasks.append(task)

        # 多个任务，优化任务顺序
        start_grid = worker.get_current_grid_location(self.map_converter)

        # 创建优化后的任务列表
        optimized_tasks = []
        current_grid = start_grid

        # 第一优先级: 先处理所有"拣货中"的任务，保持原有顺序
        for task in picking_tasks:
            # 拣货中任务不进行TSP优化，保持原有预测数据
            print(f"    拣货中任务 {task.task_id} 跳过TSP优化，保持原有数据")

            # 使用任务原有的预测结束位置更新当前位置
            if hasattr(task, 'predict_complete_location_x') and hasattr(task, 'predict_complete_location_y'):
                # 使用预测的完成位置
                end_col, end_row = self.map_converter.real_to_grid(
                    task.predict_complete_location_x, task.predict_complete_location_y)
                end_col, end_row = snap_to_nearest_free(end_col, end_row)
                current_grid = (end_row, end_col)
            elif task.sku_list and task.optimized_sku_order:
                # 如果没有预测位置，使用原有的SKU顺序计算结束位置
                last_sku_idx = task.optimized_sku_order[-1]
                last_sku = task.sku_list[last_sku_idx]
                end_col, end_row = self.map_converter.real_to_grid(
                    last_sku.location_x, last_sku.location_y)
                end_col, end_row = snap_to_nearest_free(end_col, end_row)
                current_grid = (end_row, end_col)

            optimized_tasks.append(task)

        # 第二优先级: 处理所有紧急任务，按距离排序
        if urgent_tasks:
            task_distances = []
            for task in urgent_tasks:
                # 计算到任务第一个SKU的距离
                if task.sku_list:
                    first_sku = task.sku_list[0]
                    sku_col, sku_row = self.map_converter.real_to_grid(
                        first_sku.location_x, first_sku.location_y)
                    sku_col, sku_row = snap_to_nearest_free(sku_col, sku_row)

                    # 转换为(row, col)格式
                    sku_grid = (sku_row, sku_col)
                    distance = self.path_finder.find_path_length(current_grid, sku_grid)
                else:
                    distance = 0
                task_distances.append((task, distance))

            # 按距离排序紧急任务
            task_distances.sort(key=lambda x: x[1])

            # 处理排序后的紧急任务
            for task, _ in task_distances:
                # 检查缓存
                cache_key = (task.task_id, current_grid[0], current_grid[1])
                if cache_key in self.tsp_cache:
                    sku_order, distance = self.tsp_cache[cache_key]
                    task.optimized_sku_order = sku_order
                    task.distance = distance
                    print(f"    紧急任务 {task.task_id} 使用缓存: 距离 {distance:.2f} 米")
                else:
                    # 优化任务内SKU顺序
                    sku_order, distance = self.task_optimizer.optimize_sku_order_in_task(task, current_grid)
                    task.optimized_sku_order = sku_order
                    task.distance = distance
                    self.tsp_cache[cache_key] = (sku_order, distance)
                    print(f"    紧急任务 {task.task_id} 优化后距离: {distance:.2f} 米")

                # 更新当前位置（任务结束位置）
                if task.sku_list and sku_order:
                    last_sku_idx = sku_order[-1]
                    last_sku = task.sku_list[last_sku_idx]
                    end_col, end_row = self.map_converter.real_to_grid(
                        last_sku.location_x, last_sku.location_y)
                    end_col, end_row = snap_to_nearest_free(end_col, end_row)
                    # 转换为(row, col)格式
                    current_grid = (end_row, end_col)

                optimized_tasks.append(task)

        # 第三优先级: 处理所有普通任务，按距离排序
        if non_urgent_tasks:
            task_distances = []
            for task in non_urgent_tasks:
                # 计算到任务第一个SKU的距离
                if task.sku_list:
                    first_sku = task.sku_list[0]
                    sku_col, sku_row = self.map_converter.real_to_grid(
                        first_sku.location_x, first_sku.location_y)
                    sku_col, sku_row = snap_to_nearest_free(sku_col, sku_row)

                    # 转换为(row, col)格式
                    sku_grid = (sku_row, sku_col)
                    distance = self.path_finder.find_path_length(current_grid, sku_grid)
                else:
                    distance = 0
                task_distances.append((task, distance))

            # 按距离排序非紧急任务
            task_distances.sort(key=lambda x: x[1])

            # 处理排序后的非紧急任务
            for task, _ in task_distances:
                # 检查缓存
                cache_key = (task.task_id, current_grid[0], current_grid[1])
                if cache_key in self.tsp_cache:
                    sku_order, distance = self.tsp_cache[cache_key]
                    task.optimized_sku_order = sku_order
                    task.distance = distance
                    print(f"    任务 {task.task_id} 使用缓存: 距离 {distance:.2f} 米")
                else:
                    # 优化任务内SKU顺序
                    sku_order, distance = self.task_optimizer.optimize_sku_order_in_task(task, current_grid)
                    task.optimized_sku_order = sku_order
                    task.distance = distance
                    self.tsp_cache[cache_key] = (sku_order, distance)
                    print(f"    任务 {task.task_id} 优化后距离: {distance:.2f} 米")

                # 更新当前位置（任务结束位置）
                if task.sku_list and sku_order:
                    last_sku_idx = sku_order[-1]
                    last_sku = task.sku_list[last_sku_idx]
                    end_col, end_row = self.map_converter.real_to_grid(
                        last_sku.location_x, last_sku.location_y)
                    end_col, end_row = snap_to_nearest_free(end_col, end_row)
                    # 转换为(row, col)格式
                    current_grid = (end_row, end_col)

                optimized_tasks.append(task)

        return optimized_tasks

    def clear_tsp_cache(self):
        """清除TSP缓存"""
        self.tsp_cache.clear()
        print(f"TSP缓存已清除")

    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        return {
            "cache_size": len(self.tsp_cache),
            "cached_tasks": len(set(key[0] for key in self.tsp_cache.keys()))
        }

    # ==================== 混合策略辅助方法 ====================

    def _estimate_worker_load_time(self, worker: Worker) -> float:
        """
        估算员工当前任务队列的负载时间（秒）

        Args:
            worker: 员工对象

        Returns:
            float: 当前任务队列预计完成时间（秒）
        """
        if not worker.allocated_tasks:
            return 0.0

        start_col, start_row = worker.get_current_grid_location(self.map_converter)
        start_grid = (start_row, start_col)

        total_time, _ = self.calculate_total_completion(
            worker.allocated_tasks, start_grid)

        return total_time

    def _calculate_hybrid_cost(
        self,
        incremental_distance: float,
        worker: Worker
    ) -> float:
        """
        计算混合策略的成本

        公式：COST = 移动时间增量 + w_load × 当前负载时间

        其中：
        - 移动时间增量 = incremental_distance / MOVEMENT_SPEED
        - 当前负载时间 = 该员工当前任务队列的预计完成时间
        - w_load = alpha × 0.01 (负载权重系数)

        Args:
            incremental_distance: 增量距离（米）
            worker: 员工对象

        Returns:
            float: 混合成本（越小越好）
        """
        MOVEMENT_SPEED = 0.83  # 移动速度（米/秒）

        # 1. 计算移动时间增量（秒）
        incremental_time = incremental_distance / MOVEMENT_SPEED

        # 2. 计算该员工当前的负载时间（秒）
        current_load_time = self._estimate_worker_load_time(worker)

        # 3. 计算混合成本
        alpha = self.config.HYBRID_ALPHA
        load_weight = alpha * 0.01  # 负载权重系数（0.01用于平衡数量级）
        hybrid_cost = incremental_time + load_weight * current_load_time

        # 调试输出
        print(f"      员工 {worker.name}: 增量距离={incremental_distance:.2f}m, "
              f"增量时间={incremental_time:.2f}s, "
              f"负载时间={current_load_time:.2f}s, "
              f"混合成本={hybrid_cost:.2f}")

        return hybrid_cost