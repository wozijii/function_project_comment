import json
from datetime import datetime
from typing import Dict, List, Any
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config# 导入配置文件
from models.warehouse import WarehouseMap# 导入仓库地图
from models.worker import Worker# 导入员工模型
from models.task import Task# 导入任务模型
from models.sku import SKU# 导入SKU模型
from utils.map_converter import MapConverter# 导入地图转换工具
from utils.time_utils import parse_datetime, format_datetime, add_seconds_to_time# 导入时间工具
from core.task_allocator import TaskAllocator# 导入任务分配器
from utils.output_formatter import OutputFormatter# 导入输出格式化工具
from utils.stop_signal import stop_signal# 导入停止信号
from utils.status_tracker import status_tracker# 导入状态追踪器
from utils.logger import get_logger# 导入日志工具

# 使用自定义日志工具
logger = get_logger(__name__)

class WarehouseOptimizationSystem:
    def __init__(self, config: Config):
        """初始化仓库优化系统"""
        self.config = config
        self.warehouse_map = WarehouseMap(config.MAP_FILE_PATH)
        self.map_converter = MapConverter(config.REAL_X_MAX, config.REAL_Y_MAX)
        self.task_allocator = TaskAllocator(self.warehouse_map, self.map_converter, config)# 创建任务分配器
        self.workers = []
        self.tasks = []
        self.assigned_tasks = []# 存储已分配但未完成的任务  


    def load_workers_data(self, workers_data: Dict[str, Any]) -> None:# 持续更新
        """加载员工数据"""
        self.workers = []
        for user_info in workers_data.get("userInfo", []):
            worker = Worker(
                sn=user_info["sn"],
                user_id=user_info["userId"],
                name=user_info["name"],
                user_move_speed=user_info.get("usermoveSpeed", 1.2),
                pda_location_x=user_info["pdaLocationX"],
                pda_location_y=user_info["pdaLocationY"],
                pad_location_time=parse_datetime(user_info["padLocationTime"]),
                area=user_info.get("area", [])
            )
            # 加载已分配但未完成的任务
            for task_info in user_info.get("allocatedTask", []):
                task_status = task_info.get("taskStatus", "未开始")
                
                # 只加载未完成的任务
                if task_status in ["未开始", "执行中","拣货中", "待分配", "已分配"]:
                    # 创建SKU列表
                    sku_list = []
                    for sku_info in task_info.get("skuOrder", []):
                        sku = SKU(
                            sku_code=sku_info["skuCode"],
                            location_x=sku_info["locationX"],
                            location_y=sku_info["locationY"],
                            sku_pick_speed=sku_info.get("skuPickSpeed", 1.0),# 每一包的速度
                            inspected_quantity=sku_info.get("inspectedQuantity", 1),# 包数
                            task_detail_id=sku_info.get("taskDetailId")  # 添加 taskDetailId
                        )
                        sku_list.append(sku)
                    
                    # 创建任务对象
                    task = Task(
                        task_id=task_info["taskId"],
                        mainId=task_info.get("mainId"),
                        ingredient_list=task_info.get("IngredientList", ""),
                        priority=task_info.get("taskPriority", 2),  # 从数据中读取优先级,1=紧急,2=普通
                        sku_list=sku_list,
                        timeline=parse_datetime(task_info["timeLine"]),
                        user_id=worker.user_id,
                        predict_start_time=parse_datetime(task_info.get("predictStartTime", worker.pad_location_time)),
                        predict_start_location_x=task_info.get("predictStartLocationX"),
                        predict_start_location_y=task_info.get("predictStartLocationY"),
                        predict_complete_time=parse_datetime(task_info.get("predictCompleteTime", worker.pad_location_time)),
                        predict_complete_location_x=task_info.get("predictCompleteLocationX"),
                        predict_complete_location_y=task_info.get("predictCompleteLocationY"),
                        task_status=task_status,
                        distance=task_info.get("distance", 0.0)  # 读取任务距离，主要用于"拣货中"任务
                    )
                    worker.allocated_tasks.append(task)
                    
                    # 如果是拣货中的任务，记录当前任务索引
                    if task_status == "拣货中":
                        worker.current_task_index = len(worker.allocated_tasks) - 1
            self.workers.append(worker)
    
    def load_tasks_data(self, tasks_data: Dict[str, Any]) -> None:
        """加载任务数据"""
        self.tasks = []
        task_detail = tasks_data.get("taskInfo", {}).get("taskDetail", [])
        
        for task_info in task_detail:
            # 创建SKU列表
            sku_list = []
            sku_items = task_info.get("skuList", [])
            
            for sku_info in sku_items:
                sku = SKU(
                    sku_code=sku_info["skuCode"],
                    location_x=sku_info["locationX"],
                    location_y=sku_info["locationY"],
                    sku_pick_speed=sku_info.get("skuPickSpeed", 1.0),
                    inspected_quantity=sku_info.get("inspectedQuantity", 1),
                    task_detail_id=sku_info.get("taskDetailId")  # 添加 taskDetailId
                )
                sku_list.append(sku)
            
            # 创建任务
            task = Task(
                task_id=task_info["taskId"],
                mainId = task_info.get("mainId"),
                ingredient_list=task_info.get("IngredientList", ""),
                priority=task_info.get("taskPriority", 2),  # 默认为普通任务(2=普通, 1=紧急)
                sku_list=sku_list,
                timeline=parse_datetime(task_info["timeLine"])
            )
            self.tasks.append(task)
    
    def process_tasks(self) -> None:
        """处理任务分配"""
        """
            处理任务分配
            1. 遍历所有任务
            2. 调用任务分配器分配任务（这里面含有模拟时间和模拟距离作对比）
            3. 更新员工任务列表
        """
        # 清除TSP缓存（重要：地图尺寸变化后，旧缓存数据不再准确）
        self.task_allocator.clear_tsp_cache()
        cache_stats = self.task_allocator.get_cache_stats()
        print(f"TSP缓存已清除: {cache_stats}")

        # 清除PathFinder距离缓存（重要：地图尺寸变化后，旧缓存数据不再准确）
        self.task_allocator.path_finder.clear_distance_cache()
        path_finder_stats = self.task_allocator.path_finder.get_cache_stats()
        print(f"PathFinder距离缓存已清除: {path_finder_stats}")

        print(f"开始处理 {len(self.tasks)} 个任务...")

        for idx, task in enumerate(self.tasks, 1):# 遍历任务
            # 检查停止信号
            if stop_signal.should_stop():
                logger.info("任务分配被用户停止，退出处理")
                return
            now_time1 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\ntime：{now_time1}，分配任务: {task.task_id} (优先级: {task.priority})")

            # 分配任务给最合适的员工# 将所有的员工的列表传递给任务分配器
            allocation_result = self.task_allocator.allocate_task(self.workers, task)

            if allocation_result:
                worker, insert_position = allocation_result
                # 添加一个时间戳时分秒
                now_time2 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                print(f"time：{now_time2}，分配给: {worker.name} (插入的索引位置: {insert_position})")

                # 更新状态追踪器
                status_tracker.process_allocating_task(task.task_id, worker.name, idx)

                # 更新员工任务列表
                self.task_allocator.update_worker_schedule(worker, task, insert_position)
                self.assigned_tasks.append(task)
            else:
                print(f"  警告: 无法分配任务 {task.task_id}")
    def print_system_status(self):
        """打印系统状态"""
        print("\n" + "=" * 60)
        print("任务分配完成!")
        print("=" * 60)
        
        # 按员工分组显示
        for worker in self.workers:
            if worker.allocated_tasks:
                print(f"\n员工: {worker.name} (ID: {worker.user_id})")
                print(f"当前位置: ({worker.pda_location_x:.2f}, {worker.pda_location_y:.2f})")
                print(f"任务数量: {len(worker.allocated_tasks)}")
                
                total_distance = 0
                for i, task in enumerate(worker.allocated_tasks, 1):
                    distance = task.distance if hasattr(task, 'distance') else 0
                    total_distance += distance
                    
                    print(f"\n  任务{i}: {task.task_id}")
                    print(f"    优先级: {task.priority}")
                    print(f"    SKU数量: {len(task.sku_list)}")
                    print(f"    移动距离: {distance:.2f} 米")
                    
                    if hasattr(task, 'optimized_sku_order') and task.optimized_sku_order:
                        print(f"    优化顺序: {task.optimized_sku_order}")
                        print("    SKU拣货顺序:")
                        for j, idx in enumerate(task.optimized_sku_order, 1):
                            if 0 <= idx < len(task.sku_list):
                                sku = task.sku_list[idx]
                                print(f"      {j}. {sku.sku_code} ({sku.location_x:.2f}, {sku.location_y:.2f})")
                
                print(f"\n  总移动距离: {total_distance:.2f} 米")
    def optimize_all_workers_tasks(self) -> None:
        """优化所有员工的任务和SKU顺序"""
        now_time3 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n开始优化所有员工的任务顺序...time：{now_time3}")

        for idx, worker in enumerate(self.workers, 1):
            # 检查停止信号
            if stop_signal.should_stop():
                logger.info("任务优化被用户停止，退出处理")
                return

            if worker.allocated_tasks:
                # 记录优化开始时间
                opt_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n优化员工 {worker.name} 的 {len(worker.allocated_tasks)} 个任务:")
                print(f"time: {opt_start_time}")

                # 更新状态追踪器
                status_tracker.process_optimizing_worker(worker.name, idx)

                # 优化任务间顺序
                optimized_tasks = self.task_allocator.optimize_worker_tasks(worker)
                worker.allocated_tasks = optimized_tasks

                # 计算每个任务的时间和位置
                self._calculate_task_schedule(worker)

                # 记录优化结束时间
                opt_end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"time: {opt_end_time}")
    
    def _calculate_task_schedule(self, worker: Worker) -> None:
        """
        计算员工任务的时间安排（带时间校准功能）

        时间校准逻辑：
        1. 只校准时间，不改变位置、路径、距离
        2. 有"拣货中"任务：在最后一个"拣货中"任务后面的第一个任务处校准
        3. 无"拣货中"任务：在第一个任务处校准
        4. 校准使用 padLocationTime 作为开始时间
        5. 校准只执行一次，后续任务使用累积逻辑
        """
        try:
            # 初始化起点（位置保持不变，时间后面会校准）
            current_time = worker.pad_location_time
            current_x, current_y = worker.pda_location_x, worker.pda_location_y

            # 查找最后一个已完成的任务作为起点（仅用于位置，不覆盖时间）
            for task in reversed(worker.allocated_tasks):
                if task.task_status == "已完成":
                    if task.predict_complete_location_x and task.predict_complete_location_y:
                        current_x = task.predict_complete_location_x
                        current_y = task.predict_complete_location_y
                    break  # 找到最后一个已完成的任务就停止

            # ✅ 时间校准核心逻辑
            # 1. 查找所有"拣货中"任务
            executing_tasks = [task for task in worker.allocated_tasks
                             if task.task_status == "拣货中"]

            # 2. 确定是否需要时间校准
            time_calibrated = False  # 标记是否已执行时间校准

            print(f"\n    ========== 时间校准 ==========")
            print(f"    当前PDA时间: {worker.pad_location_time}")

            if executing_tasks:
                print(f"    发现 {len(executing_tasks)} 个'拣货中'任务")
                print(f"    校准位置: 最后一个'拣货中'任务后面的第一个任务")
            else:
                print(f"    没有'拣货中'任务")
                print(f"    校准位置: 第一个任务")

            print(f"    ================================\n")

            # 3. 遍历所有任务，应用时间校准
            for i, task in enumerate(worker.allocated_tasks):
                # 跳过已完成的任务
                if task.task_status == "已完成":
                    continue

                # 处理"拣货中"任务（保持原有时间）
                if task.task_status == "拣货中":
                    if task.predict_complete_time:
                        current_time = task.predict_complete_time
                    if task.predict_complete_location_x and task.predict_complete_location_y:
                        current_x = task.predict_complete_location_x
                        current_y = task.predict_complete_location_y
                    print(f"    任务 {task.task_id} (拣货中): 保持原有时间 {task.predict_start_time}")
                    continue

                # 处理非"拣货中"任务
                # ✅ 时间校准：第一个非"拣货中"任务使用 padLocationTime
                if not time_calibrated:
                    # 使用当前PDA时间作为开始时间（时间校准）
                    task.predict_start_time = worker.pad_location_time
                    current_time = worker.pad_location_time
                    time_calibrated = True  # 标记已校准，后续不再校准

                    print(f"    ✨ 任务 {task.task_id} ({task.task_status}): 时间校准")
                    print(f"       开始时间: {task.predict_start_time} (使用当前PDA时间)")
                else:
                    # 后续任务：使用累积逻辑
                    task.predict_start_time = current_time

                    print(f"    任务 {task.task_id} ({task.task_status}): 累积逻辑")
                    print(f"       开始时间: {task.predict_start_time} (基于上一个任务)")

                # 设置任务开始位置（位置不校准，保持原有逻辑）
                task.predict_start_location_x = current_x
                task.predict_start_location_y = current_y

                # 计算任务时间
                move_time = task.distance / worker.user_move_speed if task.distance > 0 else 0
                pick_time = task.get_total_picking_time()
                task_time = move_time + pick_time

                print(f"       移动距离: {task.distance if hasattr(task, 'distance') else 0:.2f} 米")
                print(f"       移动时间: {move_time:.2f} 秒")
                print(f"       拣货时间: {pick_time:.2f} 秒")
                print(f"       总时间: {task_time:.2f} 秒")

                # 更新完成时间和位置
                task.predict_complete_time = add_seconds_to_time(current_time, task_time)

                # 设置完成位置（最后一个SKU的位置）
                if task.sku_list and hasattr(task, 'optimized_sku_order') and task.optimized_sku_order:
                    last_sku_idx = task.optimized_sku_order[-1]
                    last_sku = task.sku_list[last_sku_idx]
                    task.predict_complete_location_x = last_sku.location_x
                    task.predict_complete_location_y = last_sku.location_y
                elif task.sku_list:
                    # 如果没有优化顺序，使用最后一个SKU
                    last_sku = task.sku_list[-1]
                    task.predict_complete_location_x = last_sku.location_x
                    task.predict_complete_location_y = last_sku.location_y
                else:
                    task.predict_complete_location_x = current_x
                    task.predict_complete_location_y = current_y

                # 安全地打印完成位置,处理 None 值
                print(f"       完成时间: {task.predict_complete_time}")
                loc_x = task.predict_complete_location_x if task.predict_complete_location_x is not None else 0.0
                loc_y = task.predict_complete_location_y if task.predict_complete_location_y is not None else 0.0
                print(f"       完成位置: ({loc_x:.2f}, {loc_y:.2f})")

                # 更新为下一个任务的起点（累积逻辑）
                current_time = task.predict_complete_time
                current_x = task.predict_complete_location_x
                current_y = task.predict_complete_location_y

        except Exception as e:
            # 捕获错误并记录到 error 日志
            from utils.error_handler import handle_error
            handle_error(
                f"计算任务时间安排失败 (worker: {worker.user_id if hasattr(worker, 'user_id') else 'unknown'})",
                e,
                context={
                    "worker_id": worker.user_id if hasattr(worker, 'user_id') else None,
                    "worker_name": worker.name if hasattr(worker, 'name') else None,
                    "task_count": len(worker.allocated_tasks) if hasattr(worker, 'allocated_tasks') else 0
                },
                module="process"
            )
            # 重新抛出异常,让上层处理
            raise

    def get_optimized_output(self) -> List[Dict]:
        """获取优化后的输出"""
        return OutputFormatter.format_worker_optimized_schedule(self.workers)

    """
        坐标转换有问题（已解决）
    """
import send_output_fast

def get_current_simulate_id():
    """获取当前正在处理的 simulate_id"""
    # 读取 latest_input.json 获取当前轮次
    try:
        with open('./data/latest_input.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return int(data.get('simulate_id', 0))
    except Exception as e:
        print(f"警告: 无法读取 simulate_id, 将使用默认路径: {e}")
        return None

def main():
    """主函数"""
    """
    1. 加载数据
    2. 处理任务分配（这里面含有模拟时间和模拟距离作对比）
    3. 优化所有员工的任务顺序
    5. 更新迭代
    6. 输出结果
    """
    import time,os
    start_time = time.time()
    print("仓库拣货任务分配与优化系统")
    print("=" * 50)

    # 获取当前 simulate_id
    simulate_id = get_current_simulate_id()

    # ========== 状态追踪: 开始任务分配 ==========
    status_tracker.process_start(simulate_id)

    # 创建配置
    config = Config()

    # 输出当前分配策略
    strategy_name = "距离优先" if config.ALLOCATION_STRATEGY == 'distance_first' else "均衡策略"
    print(f"使用分配策略: {strategy_name} ({config.ALLOCATION_STRATEGY})")
    print(f"当前轮次 simulate_id: {simulate_id}")

    # 创建系统
    system = WarehouseOptimizationSystem(config)

    # 确定数据路径
    if simulate_id is not None:
        data_dir = Path(f'./data/data_{simulate_id}')
        print(f"使用轮次独立目录: {data_dir}")
    else:
        data_dir = Path('./data')
        print(f"使用默认目录: {data_dir}")

    # 加载数据
    try:
        # 加载员工数据
        workers_path = data_dir / 'workers.json'
        with open(workers_path, 'r', encoding='utf-8') as f:
            workers_data = json.load(f)
        system.load_workers_data(workers_data)
        print(f"加载员工数据: {len(system.workers)} 人")

        # 加载任务数据
        tasks_path = data_dir / 'tasks.json'
        with open(tasks_path, 'r', encoding='utf-8') as f:
            tasks_data = json.load(f)
        system.load_tasks_data(tasks_data)
        print(f"加载任务数据: {len(system.tasks)} 个任务")

        # ========== 状态追踪: 数据加载完成 ==========
        status_tracker.process_loading_complete(len(system.tasks), len(system.workers))

    except FileNotFoundError as e:
        error_msg = f"找不到数据文件: {e.filename}"
        print(f"❌ {error_msg}")
        print("请确保 data/workers.json 和 data/tasks.json 文件存在")
        from utils.error_handler import handle_error
        handle_error(
            error_msg,
            e,
            context={"simulate_id": simulate_id, "missing_file": str(e.filename)},
            module="process"
        )
        return
    except Exception as e:
        error_msg = f"加载数据时发生错误"
        print(f"❌ {error_msg}: {e}")
        from utils.error_handler import handle_error
        handle_error(
            error_msg,
            e,
            context={"simulate_id": simulate_id},
            module="process"
        )
        return

    # 处理任务分配(在分配里面其实是经历过优化了所有的任务选择出最佳的方案)
    try:
        system.process_tasks()

        # 检查是否被停止
        if stop_signal.should_stop():
            status_tracker.process_stopped()
            return

        # ========== 状态追踪: 任务分配完成,开始优化 ==========
        status_tracker.process_allocation_complete()

        # 优化所有员工的任务顺序
        system.optimize_all_workers_tasks()

        # 检查是否被停止
        if stop_signal.should_stop():
            status_tracker.process_stopped()
            return

    except Exception as e:
        error_msg = "任务分配或优化过程中发生错误"
        print(f"❌ {error_msg}: {e}")
        logger.exception("详细错误信息:")
        from utils.error_handler import handle_error
        handle_error(
            error_msg,
            e,
            context={
                "simulate_id": simulate_id,
                "workers_count": len(system.workers),
                "tasks_count": len(system.tasks)
            },
            module="process"
        )
        return

    # 获取输出
    output_data = system.get_optimized_output()

    # ========== 状态追踪: 开始保存结果 ==========
    status_tracker.process_saving()

    # 保存输出：写入带时间戳的文件，并更新最新副本 output_assignment.json，同时归档历史
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    out_dir = data_dir  # 使用轮次独立目录
    archive_dir = data_dir / 'archive'
    try:
        os.makedirs(archive_dir, exist_ok=True)
    except Exception:
        pass

    output_file_ts = out_dir / f'output_assignment_{ts}.json'
    output_file_latest = out_dir / 'output_assignment.json'

    # 导入任务合并工具
    from utils.task_merger import merge_task_files

    # 合并历史任务（按时间正序：最旧在前，最新在后）
    merged_tasks = merge_task_files(data_dir)

    # 将当前新分配的任务添加到合并结果末尾（最新的任务）
    # 如果任务已存在，则更新它（特别是"拣货中"任务的distance可能需要更新）
    task_dict = {task['taskId']: task for task in merged_tasks}
    for task in output_data:
        task_id = task['taskId']
        if task_id not in task_dict:
            # 新任务，添加到末尾
            merged_tasks.append(task)
            task_dict[task_id] = task
        else:
            # 任务已存在，更新它（用最新数据覆盖）
            # 找到旧任务并替换
            for i, old_task in enumerate(merged_tasks):
                if old_task['taskId'] == task_id:
                    merged_tasks[i] = task
                    task_dict[task_id] = task
                    break

    try:
        # 保存带时间戳的文件
        with open(output_file_ts, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        # 保存合并后的最新副本
        with open(output_file_latest, 'w', encoding='utf-8') as f:
            json.dump(merged_tasks, f, ensure_ascii=False, indent=2)

        # 复制到归档目录
        try:
            import shutil
            shutil.copy(output_file_ts, os.path.join(archive_dir, os.path.basename(output_file_ts)))
        except Exception:
            pass
    except Exception as e:
        error_msg = "保存输出文件失败"
        print(f"❌ {error_msg}: {e}")
        from utils.error_handler import handle_error
        handle_error(
            error_msg,
            e,
            context={
                "simulate_id": simulate_id,
                "output_file": str(output_file_ts)
            },
            module="process"
        )
        return

    print("\n" + "=" * 50)
    print("任务分配完成!")
    print(f"输出已保存到: {output_file_ts} (并更新最新副本: {output_file_latest})")
    print(f"轮次目录: {data_dir}")
    
    # 显示分配结果
    print("\n分配结果摘要:")
    print("-" * 30)
    # 按员工分组显示任务，
    user_tasks = {}
    for task in output_data:
        user_id = task["userId"]
        if user_id not in user_tasks:
            user_tasks[user_id] = []
        user_tasks[user_id].append(task)
    
    for user_id, tasks in user_tasks.items():
        worker_name = next((w.name for w in system.workers if w.user_id == user_id), "未知")
        print(f"\n员工: {worker_name} (ID: {user_id})")
        print(f"任务数量: {len(tasks)}")
        total_distance = sum(t.get("distance", 0) for t in tasks)
        print(f"总移动距离: {total_distance:.2f} 米")
        
        for i, task in enumerate(tasks, 1):
            print(f"  {i}. 任务ID: {task['taskId']}")
            print(f"     优先级: {'紧急' if any(t for t in system.tasks if t.task_id == task['taskId'] and t.priority == '紧急') else '普通'}")
            print(f"     SKU数量: {len(task['sku_order'])}")
            print(f"     移动距离: {task.get('distance', 0):.2f} 米")



    # ------------- 新增：按人员计算并打印指标 -------------
    print("\n按人员统计指标：")

    # 建立任务ID到原任务对象的映射（用于获取截止时间 timeline）
    task_timeline_map = {t.task_id: t.timeline for t in system.tasks}

    from collections import defaultdict
    for worker in system.workers:
        # 只统计已分配且有预测开始/结束时间的任务
        worker_tasks = [t for t in worker.allocated_tasks if getattr(t, 'predict_start_time', None) and getattr(t, 'predict_complete_time', None)]
        if not worker_tasks:
            continue

        print(f"\n{worker.name}:")

        # 1) 准时交付率
        on_time_count = 0
        total_count = 0
        for t in worker_tasks:
            total_count += 1
            actual = t.predict_complete_time
            deadline = task_timeline_map.get(t.task_id)
            actual_str = actual.strftime("%Y-%m-%d %H:%M:%S") if actual else "-"
            deadline_str = deadline.strftime("%Y-%m-%d %H:%M:%S") if deadline else "-"
            if deadline:
                is_on_time = actual <= deadline
            else:
                is_on_time = False
            if is_on_time:
                on_time_count += 1
            print(f"任务：{t.task_id}，实际完成时间：{actual_str}，任务截止时间：{deadline_str}，是否准时：{'是' if is_on_time else '否'}")

        rate = f"{on_time_count}/{total_count}"
        print(f"准时交付率：{rate}")

        # 2) 单SKU分拣人效：总分拣时间(秒) / SKU个数
        start_times = [t.predict_start_time for t in worker_tasks if t.predict_start_time]
        end_times = [t.predict_complete_time for t in worker_tasks if t.predict_complete_time]
        total_seconds = 0
        if start_times and end_times:
            total_seconds = (max(end_times) - min(start_times)).total_seconds()

        sku_count = 0
        for t in worker_tasks:
            sku_count += len(t.sku_list)

        if sku_count > 0:
            per_sku_time = total_seconds / sku_count
        else:
            per_sku_time = 0

        print(f"单SKU分拣人效：总的分拣时间({int(total_seconds)} 秒)/SKU个数({sku_count}) = {per_sku_time:.2f} 秒/SKU")

        # 3) 单SKU行走距离：总行走距离 / SKU个数
        total_walk = 0
        for t in worker_tasks:
            total_walk += getattr(t, 'distance', 0)

        if sku_count > 0:
            per_sku_walk = total_walk / sku_count
        else:
            per_sku_walk = 0

        print(f"单SKU行走距离：总的行走距离({total_walk:.2f} 米)/SKU个数({sku_count}) = {per_sku_walk:.2f} 米/SKU")
    # ------------- 新增结束 -------------

    # ------------- 新增：全体统计 -------------
    total_on_time = 0
    total_tasks = 0
    total_seconds_all = 0
    total_sku_count_all = 0
    total_walk_all = 0

    for worker in system.workers:
        worker_tasks = [t for t in worker.allocated_tasks if getattr(t, 'predict_start_time', None) and getattr(t, 'predict_complete_time', None)]
        if not worker_tasks:
            continue

        # per-worker time span
        start_times = [t.predict_start_time for t in worker_tasks if t.predict_start_time]
        end_times = [t.predict_complete_time for t in worker_tasks if t.predict_complete_time]
        worker_seconds = 0
        if start_times and end_times:
            worker_seconds = (max(end_times) - min(start_times)).total_seconds()

        worker_sku_count = 0
        for t in worker_tasks:
            worker_sku_count += len(t.sku_list)

        # accumulate walk and on-time
        for t in worker_tasks:
            total_tasks += 1
            actual = t.predict_complete_time
            deadline = task_timeline_map.get(t.task_id)
            if deadline and actual <= deadline:
                total_on_time += 1
            total_walk_all += getattr(t, 'distance', 0)

        total_seconds_all += worker_seconds
        total_sku_count_all += worker_sku_count

    print("\n全体统计：")
    if total_tasks > 0:
        pct = (total_on_time / total_tasks) * 100
        print(f"准时交付率：{total_on_time}/{total_tasks} ({pct:.2f}%)")
    else:
        print("准时交付率：无任务")

    if total_sku_count_all > 0:
        per_sku_time_total = total_seconds_all / total_sku_count_all
        per_sku_walk_total = total_walk_all / total_sku_count_all
    else:
        per_sku_time_total = 0
        per_sku_walk_total = 0
# all_time/sku数量
    print(f"单SKU分拣人效：总的分拣时间({int(total_seconds_all)} 分)/SKU个数({total_sku_count_all}) = {per_sku_time_total/60:.2f} 秒/SKU")
    print(f"单SKU行走距离：总的行走距离({total_walk_all:.2f} 米)/SKU个数({total_sku_count_all}) = {per_sku_walk_total:.2f} 米/SKU")
    # ------------- 全体统计结束 -------------

    # 保存汇总指标到 data/view_metrics.json 供可视化页读取（非侵入式）
    try:
        metrics = {
            "total_on_time": total_on_time,
            "total_tasks": total_tasks,
            "on_time_pct": round((total_on_time / total_tasks * 100) if total_tasks>0 else 0, 2),
            "total_seconds_all": int(total_seconds_all),
            "total_sku_count_all": total_sku_count_all,
            "per_sku_time_total": round(per_sku_time_total, 2),
            "total_walk_all": round(total_walk_all, 2),
            "per_sku_walk_total": round(per_sku_walk_total, 2)
        }
        # 使用轮次目录保存指标
        metrics_path = data_dir / 'view_metrics.json'
        with open(metrics_path, 'w', encoding='utf-8') as mf:
            json.dump(metrics, mf, ensure_ascii=False, indent=2)

        print(f"已保存汇总指标到: {metrics_path}")
        send_output_fast.main()
    except Exception as e:
        print(f"保存汇总指标失败: {e}")

    end_time = time.time()
    all_time = end_time - start_time
    print(f"总运行时间: {all_time:.2f} 秒")

    # ========== 状态追踪: 全部完成 ==========
    status_tracker.process_complete()

if __name__ == "__main__":
    # 计算总运行时间
    main()
    