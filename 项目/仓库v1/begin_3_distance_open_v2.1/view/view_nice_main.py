# main.py
import json
from datetime import datetime
from pathlib import Path
# import simulation_engine.simulation_engine
try:
    from .simulation_engine.simulation_engine import SimulationEngine
    from .utils.visualization import Visualization
    from .utils.callback import send_video_callback
except ImportError:
    from simulation_engine.simulation_engine import SimulationEngine
    from utils.visualization import Visualization
    from utils.callback import send_video_callback

def main():
    """主程序"""
    print("=== 拣货顺序仿真系统 ===")
    
    import time
    try:
        from . import deal_nice_data
    except ImportError:
        import deal_nice_data
    deal_nice_data.main1()
    time.sleep(3)
    # 读取输入数据
    try:
        # 使用相对路径，与 deal_nice_data.py 保持一致
        current_file = Path(__file__).resolve()
        nice_data_path = current_file.parent / 'input_data_nice' / 'nice_data.json'
        with open(nice_data_path, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
        print("OK 成功加载输入数据")
    except Exception as e:
        print(f"Error 读取输入数据失败: {e}")
        return
    
    # 创建仿真引擎
    print("初始化仿真引擎(优化后)...")
    try:
        engine = SimulationEngine(map_file_path='./map.txt')
        engine.initialize_workers(input_data)
        sim_info = engine.get_simulation_info()
        print(f"OK 仿真引擎初始化完成")
        print(f"  工作人员数量: {sim_info['worker_count']}")
        print(f"  地图尺寸: {sim_info['map_size'][0]}x{sim_info['map_size'][1]}")
    except Exception as e:
        print(f"Error 仿真引擎初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 读取 simulate_id 和 simulate 字段（在生成视频前检查）
    simulate = False
    simulate_id = None
    try:
        project_root = Path(__file__).parent.parent
        latest_input_path = project_root / 'data' / 'latest_input.json'
        with open(latest_input_path, 'r', encoding='utf-8') as file:
            input_data = json.load(file)
        simulate_id = input_data.get('simulate_id')
        simulate = input_data.get('simulate', False)  # 读取 simulate 字段,默认 False
        print(f"OK 读取 simulate 配置: {simulate}")
    except Exception as e:
        print(f"警告: 无法读取 simulate 配置: {e}")
        simulate = True  # 默认生成视频

    # 只在 simulate=True 时生成视频
    if not simulate:
        print("\nsimulate=False, 跳过视频生成")
        return

    # 生成移动帧
    print("\n生成移动帧数据...")
    try:
        frames = engine.generate_movement_frames()
        print(f"OK 成功生成 {len(frames)} 帧数据")
    except Exception as e:
        print(f"Error 生成移动帧失败: {e}")
        return

    # 创建可视化
    print("\n初始化可视化...")
    try:
        viz = Visualization(
            map_grid=engine.map_converter.grid,
            workers=engine.workers,
            colors=engine.colors,
            map_converter=engine.map_converter,
            minimal=True
        )
        print("OK 可视化初始化完成")
    except Exception as e:
        print(f"Error 可视化初始化失败: {e}")
        return

# 将服务器地址修改为本地地址
    # 生成输出文件名（使用本地相对路径）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(__file__).parent / 'output_mp4'
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = str(output_dir / f'优化后顺序仿真_{timestamp}.mp4')

    # 创建并保存动画
    print(f"\n开始创建动画 -> {output_file}")
    # 读取主流程计算的汇总指标（如果存在），并把文本 overlay 传入可视化
    overlay_lines = []
    try:
        import os
        metrics_path = os.path.normpath(os.path.join('..', 'data', 'view_metrics.json'))
        if os.path.exists(metrics_path):
            with open(metrics_path, 'r', encoding='utf-8') as mf:
                metrics = json.load(mf)
          
        print("指标传输成功：")
        print(overlay_lines)
        print("=================================")
    except Exception:
        overlay_lines = []
    try:
        # 简化 overlay：只显示比例、速度与每人 userId / distance / sku_count
        try:
            res_x = getattr(engine.map_converter, 'res_x', 1.0)
            res_y = getattr(engine.map_converter, 'res_y', 1.0)
            overlay_lines = []
            # overlay_lines.append(f"Scale: {res_x:.3f} m/col, {res_y:.3f} m/row")
            # overlay_lines.append(f"Speed: {engine.speed} steps/frame, Interval: {engine.frame_interval} ms")
            overlay_lines.append('')
            for w in engine.workers:
                uid = getattr(w, 'id', getattr(w, 'userId', ''))
                traveled = getattr(w, 'traveled_path', [])
                total_dist = 0.0
                for i in range(1, len(traveled)):
                    x0, y0 = traveled[i-1]
                    x1, y1 = traveled[i]
                    dx = (x1 - x0) * res_x
                    dy = (y1 - y0) * res_y
                    total_dist += (dx*dx + dy*dy) ** 0.5
                sku_count = len(getattr(w, 'path', []))
                overlay_lines.append(f"{uid}: dist={total_dist:.1f} m, {sku_count} sku")
            print()
        except Exception:
            overlay_lines = [] 

        viz.create_animation(frames, output_file, engine.frame_interval, overlay_texts=overlay_lines)
        print("OK 动画创建完成")
    except Exception as e:
        print(f"Error 动画创建失败: {e}")
        import traceback
        traceback.print_exc()
        return

#     # 回调视频给前端
#     import os
#     abs_path = os.path.abspath(output_file)
#     print(f"回调视频路径 -> {abs_path}")
#     try:
#         cb_resp = send_video_callback(abs_path, type=2, simulate_id=simulate_id, distance=0.0, simulate=True)
#         print(f"OK 回调结果: {cb_resp}")
#     except Exception as e:
#         print(f"Error 回调异常: {e}")

    # 打印统计信息
    print_statistics(engine, frames)


def print_statistics(engine: SimulationEngine, frames: list) -> None:
    """打印仿真统计信息"""
    print("\n" + "="*60)
    print("仿真统计信息")
    print("="*60)
    
    print(f"\n总体信息:")
    print(f"  总帧数: {len(frames)}")
    print(f"  仿真时长: {len(frames) * engine.frame_interval / 1000:.1f} 秒")
    print(f"  地图尺寸: {engine.map_converter.H}x{engine.map_converter.W}")
    print(f"  移动速度: {engine.speed} 步/帧")
    print(f"  帧率: {int(1000/engine.frame_interval)} fps")
    
    print(f"\n工作人员详情:")
    for i, worker in enumerate(engine.workers, 1):
        status = "已完成" if worker.completed else "未完成"
        final_pos = worker.current_pos if worker.completed else "N/A"
        
        print(f"  {i}. {worker.name} ({worker.id}):")
        print(f"     起点: {worker.start}")
        print(f"     任务点数量: {len(worker.path)}")
        print(f"     状态: {status}")
        print(f"     最终位置: {final_pos}")
    
    print(f"\nOK 仿真完成！")
if __name__ == "__main__":
    main()