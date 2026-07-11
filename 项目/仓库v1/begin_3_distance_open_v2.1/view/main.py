# main.py
import json
from datetime import datetime
from simulation_engine.simulation_engine import SimulationEngine
from utils.visualization import Visualization
from utils.callback import send_video_callback

import deal_old_data

def main():
    """主程序"""
    try:
        print("=== 拣货顺序仿真系统 ===")
        deal_old_data.main()
        simulate_id = deal_old_data.make()

        # 读取输入数据
        try:
            with open('./input_data_old/old_data.json', 'r', encoding='utf-8') as f:
                input_data = json.load(f)
            print("✓ 成功加载输入数据")
        except Exception as e:
            error_msg = "读取输入数据失败"
            print(f"✗ {error_msg}: {e}")
            from utils.error_handler import handle_error
            handle_error(
                error_msg,
                e,
                context={"file": "./input_data_old/old_data.json"},
                module="simulate"
            )
            return

        # 创建仿真引擎
        print("初始化仿真引擎...")
        try:
            engine = SimulationEngine(map_file_path='./map.txt')
            engine.initialize_workers(input_data)
            sim_info = engine.get_simulation_info()
            print(f"✓ 仿真引擎初始化完成")
            print(f"  工作人员数量: {sim_info['worker_count']}")
            print(f"  地图尺寸: {sim_info['map_size'][0]}x{sim_info['map_size'][1]}")
        except Exception as e:
            error_msg = "仿真引擎初始化失败"
            print(f"✗ {error_msg}: {e}")
            import traceback
            traceback.print_exc()
            from utils.error_handler import handle_error
            handle_error(
                error_msg,
                e,
                context={
                    "map_file": "./map.txt",
                    "worker_count": len(input_data.get('userInfo', [])) if input_data else 0
                },
                module="simulate"
            )
            return

        # 生成移动帧
        print("\n生成移动帧数据...")
        try:
            frames = engine.generate_movement_frames()
            print(f"✓ 成功生成 {len(frames)} 帧数据")
        except Exception as e:
            error_msg = "生成移动帧失败"
            print(f"✗ {error_msg}: {e}")
            from utils.error_handler import handle_error
            handle_error(
                error_msg,
                e,
                context={
                    "worker_count": len(engine.workers) if hasattr(engine, 'workers') else 0
                },
                module="simulate"
            )
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
            print("✓ 可视化初始化完成")
        except Exception as e:
            error_msg = "可视化初始化失败"
            print(f"✗ {error_msg}: {e}")
            from utils.error_handler import handle_error
            handle_error(
                error_msg,
                e,
                context={
                    "map_size": engine.map_converter.grid.shape if hasattr(engine.map_converter, 'grid') else None
                },
                module="simulate"
            )
            return

        # 生成输出文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f'./output_mp4/原始顺序仿真_{timestamp}.mp4'

        # 创建并保存动画
        print(f"\n开始创建动画 -> {output_file}")
        try:
            # 计算每位工作人员的行走距离与完成时间,并构建 overlay 文本
            overlay_lines = []
            try:
                res_x = getattr(engine.map_converter, 'res_x', 1.0)
                res_y = getattr(engine.map_converter, 'res_y', 1.0)

                # build per-worker summaries by scanning frames to determine completion frame
                frames_by_worker = {}
                for fi, frame in enumerate(frames):
                    for wdata in frame:
                        wid = wdata.get('id')
                        if wid not in frames_by_worker:
                            frames_by_worker[wid] = []
                        frames_by_worker[wid].append((fi, tuple(wdata.get('pos')) if wdata.get('pos') is not None else None, list(wdata.get('traveled_path', []))))

                overlay_lines.append('')
                all_dist = 0.0  # 总的距离
                for w in engine.workers:
                    wid = getattr(w, 'id', None)
                    path_pts = [tuple(p) for p in getattr(w, 'path', [])]
                    # compute total walked distance from traveled_path (final)
                    traveled = getattr(w, 'traveled_path', [])
                    total_dist = 0.0
                    for i in range(1, len(traveled)):
                        x0, y0 = traveled[i-1]
                        x1, y1 = traveled[i]
                        dx = (x1 - x0) * res_x
                        dy = (y1 - y0) * res_y
                        total_dist += (dx*dx + dy*dy) ** 0.5
                    all_dist += total_dist
                    # determine completion frame: first frame where all task points visited
                    completion_frame = None
                    if wid in frames_by_worker:
                        for fi, pos, traveled_path in frames_by_worker[wid]:
                            visited = set(tuple(p) for p in traveled_path) if traveled_path else set()
                            if set(path_pts).issubset(visited):
                                completion_frame = fi
                                break

                    if completion_frame is None:  # 没有完成
                        completion_time_s = len(frames) * engine.frame_interval / 1000.0
                    else:
                        completion_time_s = completion_frame * engine.frame_interval / 1000.0

                    overlay_lines.append(f"{wid}: dist={total_dist:.1f} m, {len(path_pts)} sku")
            except Exception:
                overlay_lines = []

            viz.create_animation(frames, output_file, engine.frame_interval, overlay_texts=overlay_lines)
            print("✓ 动画创建完成")
        except Exception as e:
            error_msg = "动画创建失败"
            print(f"✗ {error_msg}: {e}")
            import traceback
            traceback.print_exc()
            from utils.error_handler import handle_error
            handle_error(
                error_msg,
                e,
                context={
                    "output_file": output_file,
                    "frames_count": len(frames) if frames else 0
                },
                module="simulate"
            )
            return

        # 回调通知(将可被前端访问的 URL 发送出去)
        # 优先发送绝对 URL,如果环境变量 SIM_PUBLIC_HOST 设置了服务外网/内网访问地址则拼接
        public_host = None
        try:
            import os
            public_host = os.environ.get('SIM_PUBLIC_HOST')
        except Exception:
            public_host = None

        # 发送服务器本地文件路径(绝对路径)作为回调内容
        import os
        abs_path = os.path.abspath(output_file)
        print(f"回调本地视频路径 -> {abs_path}")
        distance = all_dist  # float
        try:
            cb_resp = send_video_callback(video_path=abs_path, simulate_id=simulate_id, type=1, distance=distance)
            print(f"回调结果: {cb_resp}")
        except Exception as e:
            error_msg = "视频回调失败"
            print(f"✗ {error_msg}: {e}")
            from utils.error_handler import handle_error
            handle_error(
                error_msg,
                e,
                context={
                    "video_path": abs_path,
                    "simulate_id": simulate_id,
                    "distance": distance
                },
                module="simulate"
            )

        # 打印统计信息
        print_statistics(engine, frames)

    except Exception as e:
        error_msg = "仿真主流程异常"
        print(f"✗ {error_msg}: {e}")
        import traceback
        traceback.print_exc()
        from utils.error_handler import handle_error
        handle_error(error_msg, e, module="simulate")


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

    print(f"\n✓ 仿真完成!")


if __name__ == "__main__":
    main()
