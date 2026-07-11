# simulation_engine.py
from typing import List, Dict, Tuple
import numpy as np
try:
    from ..utils.data_structures import WorkerInfo
    from ..utils.map_utils import MapConverter, PositionCorrector
    from ..utils.path_planner import AStarPlanner
except ImportError:
    from utils.data_structures import WorkerInfo
    from utils.map_utils import MapConverter, PositionCorrector
    from utils.path_planner import AStarPlanner


class SimulationEngine:
    def __init__(self, map_file_path: str = './map.txt'):
        """初始化仿真引擎"""
        self.map_converter = MapConverter(map_file_path=map_file_path)
        self.position_corrector = PositionCorrector(map_file_path=map_file_path)
        self.astar = AStarPlanner(self.map_converter.grid)
        self.workers = []
        
        # 颜色配置
        self.colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
            '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9'
        ]
        
        # 仿真参数
        self.speed = 3
        self.frame_interval = 100
    
    def initialize_workers(self, workers_data: List[Dict]) -> None:
        """初始化工作人员数据"""
        for i, worker_dict in enumerate(workers_data):
            worker_id = worker_dict['userId']
            worker_name = worker_dict['name']

            # 转换起点坐标
            start_col, start_row = self.map_converter.real_to_grid(
                worker_dict['location_X'], worker_dict['location_Y']
            )
            start_col, start_row = self.position_corrector.snap_to_nearest_free(start_col, start_row)

            # 转换路径点坐标，同时记录原始位置和修正后位置
            path_points = []
            original_positions = []

            for task in worker_dict['path']:
                # 转换到网格坐标（原始位置）
                original_col, original_row = self.map_converter.real_to_grid(
                    task['locationX'], task['locationY']
                )

                # 修正到最近的可通行位置
                corrected_col, corrected_row = self.position_corrector.snap_to_nearest_free(
                    original_col, original_row
                )

                # 记录原始位置和修正后位置
                original_positions.append((original_col, original_row))
                path_points.append((corrected_col, corrected_row))

            # 创建工作人员信息对象
            color_idx = i % len(self.colors) if self.colors else 0
            worker = WorkerInfo(
                worker_id=worker_id,
                name=worker_name,
                start=(start_col, start_row),
                path=path_points,
                color_idx=color_idx,
                original_positions=original_positions
            )

            self.workers.append(worker)
    
    def generate_movement_frames(self) -> List[List[Dict]]:
        """生成所有移动帧"""
        print("开始生成移动帧...")
        frames = []
        frame_count = 0
        max_frames = 50000000
        
        while frame_count < max_frames:
            frame_count += 1
            current_frame = []
            all_completed = True
            
            for worker in self.workers:
                if worker.completed:
                    # 已完成所有任务
                    current_frame.append({
                        'id': worker.id,
                        'name': worker.name,
                        'pos': worker.current_pos,
                        'type': 'worker',
                        'color_idx': worker.color_idx,
                        'traveled_path': worker.traveled_path.copy() if hasattr(worker, 'traveled_path') else [worker.current_pos]
                    })
                    continue
                
                all_completed = False
                
                # 规划新路径
                if not worker.current_path and worker.current_target_idx < len(worker.path):
                    target = worker.path[worker.current_target_idx]
                    path = self.astar.plan_path(worker.current_pos, target)
                    if len(path) > 1:
                        worker.current_path = path[1:]
                
                # 沿路径移动
                if worker.current_path:
                    steps_to_move = min(self.speed, len(worker.current_path))
                    for _ in range(steps_to_move):
                        if worker.current_path:
                            new_pos = worker.current_path.pop(0)
                            # 使用更新位置的方法
                            if hasattr(worker, 'update_position'):
                                worker.update_position(new_pos)
                            else:
                                # 兼容性处理
                                if not hasattr(worker, 'traveled_path'):
                                    worker.traveled_path = [worker.current_pos]
                                worker.traveled_path.append(new_pos)
                                worker.current_pos = new_pos
                
                # 检查是否到达目标
                if (worker.current_target_idx < len(worker.path) and 
                    worker.current_pos == worker.path[worker.current_target_idx]):
                    worker.current_target_idx += 1
                    worker.current_path = []
                
                # 检查是否完成所有任务
                if worker.current_target_idx >= len(worker.path):
                    worker.completed = True
                
                # 添加当前帧数据
                traveled_path = worker.traveled_path if hasattr(worker, 'traveled_path') else [worker.current_pos]
                current_frame.append({
                    'id': worker.id,
                    'name': worker.name,
                    'pos': worker.current_pos,
                    'type': 'worker',
                    'color_idx': worker.color_idx,
                    'traveled_path': traveled_path.copy()
                })
            
            frames.append(current_frame)
            
            if frame_count % 50 == 0:
                completed_count = sum(1 for w in self.workers if w.completed)
                print(f"已生成 {frame_count} 帧，完成人数: {completed_count}/{len(self.workers)}")
            
            if all_completed:
                break
        
        print(f"移动帧生成完成，共 {len(frames)} 帧")
        return frames
    
    def get_simulation_info(self) -> Dict:
        """获取仿真信息"""
        return {
            'worker_count': len(self.workers),
            'map_size': (self.map_converter.H, self.map_converter.W),
            'colors': self.colors,
            'speed': self.speed,
            'frame_interval': self.frame_interval
        }