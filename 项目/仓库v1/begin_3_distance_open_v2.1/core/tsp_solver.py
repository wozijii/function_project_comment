"""
TSP求解器模块
使用or-tools解决旅行商问题
"""

from typing import List, Tuple, Dict
"""
TSP求解器模块
使用or-tools解决旅行商问题,具体是:
    1. 输入距离矩阵和求解时间限制
    2. 创建路由模型
    3. 定义距离回调函数
    4. 设置搜索参数
    5. 求解问题
    6. 提取最优路径和距离
"""
"""
    测试：time_limit

"""
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

class TSPSolver:
    def __init__(self, distance_matrix: List[List[float]], time_limit: int = None, open_loop: bool = True):
        """
        初始化TSP求解器
        Args:
            distance_matrix: 距离矩阵
            time_limit: 求解时间限制(秒)
            open_loop: 是否开环模式(不返回起点),默认True(符合仓库拣货场景)
        """
        self.distance_matrix = distance_matrix
        self.num_nodes = len(distance_matrix)
        self.open_loop = open_loop
        # 可以设置参数进行调参
        # 根据问题规模动态调整时间限制
        if time_limit is None:
            if self.num_nodes <= 6:
                self.time_limit = 0.01  # 10ms - 小问题快速求解
            elif self.num_nodes <= 10:
                self.time_limit = 0.05  # 50ms
            elif self.num_nodes <= 20:
                self.time_limit = 0.2   # 200ms
            else:
                self.time_limit = 1    # 1秒 - 大问题
        else:
                self.time_limit = time_limit
    def solve(self) -> Tuple[List[int], float]:
        """
        求解TSP问题
        Returns:
            Tuple[List[int], float]: (最优顺序, 最短距离)
        """
        if self.num_nodes <= 1:
            return [0], 0.0

        # 如果是开环模式，修改距离矩阵（返回起点的距离=0）
        # 这样TSP优化时就不会考虑返回起点的路径
        if self.open_loop:
            for i in range(1, self.num_nodes):  # 从任意点返回起点的距离为0
                self.distance_matrix[i][0] = 0

        # 创建路由模型
        manager = pywrapcp.RoutingIndexManager(
            self.num_nodes, 1, 0)  # 1辆车，起始点为0
        routing = pywrapcp.RoutingModel(manager)
        # 定义距离回调函数
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return self.distance_matrix[from_node][to_node]
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        # 设置搜索参数
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
        # time_limit需要整数，向上取整避免0
        time_limit_ms = int(max(1, self.time_limit * 1000))  # 转换为毫秒
        search_parameters.time_limit.FromMilliseconds(time_limit_ms)
        # 求解问题
        solution = routing.SolveWithParameters(search_parameters)
        if solution:
            # 提取路径
            index = routing.Start(0)
            route = []
            route_distance = 0
            while not routing.IsEnd(index):
                route.append(manager.IndexToNode(index))
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(previous_index, index, 0)
            return route, route_distance
        # 如果求解失败，返回默认顺序
        print("TSP求解失败，使用默认顺序")
        return list(range(self.num_nodes)), sum(
            self.distance_matrix[i][i+1] for i in range(self.num_nodes-1))
    