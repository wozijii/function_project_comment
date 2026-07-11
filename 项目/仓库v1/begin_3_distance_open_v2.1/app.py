from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from pathlib import Path
import subprocess
import sys
import json as _json
from typing import Optional
import io
from contextlib import redirect_stdout, redirect_stderr
import logging
from concurrent.futures import ThreadPoolExecutor
import time 

from deal_data import deal_data
import shutil
from datetime import datetime
import main as main_module
from utils.stop_signal import stop_signal
from utils.status_tracker import status_tracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# 全局线程和进程管理
executor = ThreadPoolExecutor(max_workers=2)
current_simulate_process = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"


def validate_payload_data(payload: dict) -> tuple[bool, str]:
    """
    验证前端输入数据的类型是否正确

    Args:
        payload: 前端传入的数据字典

    Returns:
        tuple: (is_valid, error_message)
            - is_valid: True表示数据有效,False表示有错误
            - error_message: 错误信息,如果有效则为空字符串
    """
    try:
        # 检查 userInfo
        user_info_list = payload.get("userInfo", [])
        for idx, user in enumerate(user_info_list):
            # 检查必填的时间字段
            for time_field in ["padLocationTime"]:
                time_value = user.get(time_field)
                if time_value is None or time_value == "":
                    return False, f"userInfo[{idx}].{time_field} 不能为空"

            # 检查 pdaLocationX 和 pdaLocationY 是否为数值类型
            for field in ["pdaLocationX", "pdaLocationY"]:
                value = user.get(field)
                if value is not None:
                    # 尝试转换为 float
                    try:
                        float(value)
                    except (ValueError, TypeError):
                        return False, f"userInfo[{idx}].{field} 应为数值类型,当前为: {value} (类型: {type(value).__name__})"

            # 检查 usermoveSpeed
            speed = user.get("usermoveSpeed")
            if speed is not None:
                try:
                    float(speed)
                except (ValueError, TypeError):
                    return False, f"userInfo[{idx}].usermoveSpeed 应为数值类型,当前为: {speed} (类型: {type(speed).__name__})"

            # 检查 allocatedTask 中的 SKU 位置和时间
            for task_idx, task in enumerate(user.get("allocatedTask", [])):
                # 检查任务时间字段
                for time_field in ["timeLine", "predictStartTime", "predictCompleteTime"]:
                    time_value = task.get(time_field)
                    if time_value is None or time_value == "":
                        return False, f"userInfo[{idx}].allocatedTask[{task_idx}].{time_field} 不能为空"

                for sku_idx, sku in enumerate(task.get("skuOrder", [])):
                    for field in ["locationX", "locationY"]:
                        value = sku.get(field)
                        if value is not None:
                            try:
                                float(value)
                            except (ValueError, TypeError):
                                return False, f"userInfo[{idx}].allocatedTask[{task_idx}].skuOrder[{sku_idx}].{field} 应为数值类型,当前为: {value} (类型: {type(value).__name__})"

                    # 检查 skuPickSpeed
                    pick_speed = sku.get("skuPickSpeed")
                    if pick_speed is not None:
                        try:
                            float(pick_speed)
                        except (ValueError, TypeError):
                            return False, f"userInfo[{idx}].allocatedTask[{task_idx}].skuOrder[{sku_idx}].skuPickSpeed 应为数值类型,当前为: {pick_speed} (类型: {type(pick_speed).__name__})"

                    # 检查 inspectedQuantity
                    quantity = sku.get("inspectedQuantity")
                    if quantity is not None:
                        try:
                            int(quantity)
                        except (ValueError, TypeError):
                            return False, f"userInfo[{idx}].allocatedTask[{task_idx}].skuOrder[{sku_idx}].inspectedQuantity 应为整数类型,当前为: {quantity} (类型: {type(quantity).__name__})"

        # 检查 taskInfo
        task_info = payload.get("taskInfo", {})
        task_detail = task_info.get("taskDetail", [])
        for task_idx, task in enumerate(task_detail):
            for sku_idx, sku in enumerate(task.get("skuOrder", [])):
                for field in ["locationX", "locationY"]:
                    value = sku.get(field)
                    if value is not None:
                        try:
                            float(value)
                        except (ValueError, TypeError):
                            return False, f"taskInfo.taskDetail[{task_idx}].skuOrder[{sku_idx}].{field} 应为数值类型,当前为: {value} (类型: {type(value).__name__})"

                pick_speed = sku.get("skuPickSpeed")
                if pick_speed is not None:
                    try:
                        float(pick_speed)
                    except (ValueError, TypeError):
                        return False, f"taskInfo.taskDetail[{task_idx}].skuOrder[{sku_idx}].skuPickSpeed 应为数值类型,当前为: {pick_speed} (类型: {type(pick_speed).__name__})"

                quantity = sku.get("inspectedQuantity")
                if quantity is not None:
                    try:
                        int(quantity)
                    except (ValueError, TypeError):
                        return False, f"taskInfo.taskDetail[{task_idx}].skuOrder[{sku_idx}].inspectedQuantity 应为整数类型,当前为: {quantity} (类型: {type(quantity).__name__})"

        return True, ""

    except Exception as e:
        return False, f"数据验证过程中发生异常: {str(e)}"


async def _log_get_request(endpoint: str):
    """
    记录GET请求信息到日志文件

    Args:
        endpoint: 请求的端点路径
    """
    try:
        # 读取最新的输入数据
        latest_input = DATA_DIR / "latest_input.json"

        if latest_input.exists():
            input_data = _json.loads(latest_input.read_text(encoding='utf-8'))
        else:
            input_data = {}

        # 使用新的日志系统获取目录
        from utils.logger import get_log_directories
        daily_dirs = get_log_directories()
        status_dir = daily_dirs['STATUS']

        # 生成带时间戳的日志文件名
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        log_file = status_dir / f'get_{endpoint.replace("/", "_")}_{ts}.log'

        # 准备日志内容
        log_content = f"""GET请求日志
{'='*60}
请求端点: {endpoint}
请求时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
时间戳: {ts}

当前输入数据:
{_json.dumps(input_data, ensure_ascii=False, indent=2)}
{'='*60}
"""

        # 写入日志文件
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        # 追加到全局日志
        try:
            with open(ROOT / 'logs' / 'all.log', 'a', encoding='utf-8') as af:
                af.write(f"\n{log_content}\n")
        except Exception:
            pass

        logger.info(f"GET请求日志已保存到: {log_file}")

    except Exception as e:
        logger.error(f"保存GET请求日志失败: {e}")


@app.get("/status")
async def get_status():
    """
    获取项目运行状态

    返回当前 process 和 simulate 的运行状态
    包括:
    - 时间戳
    - 事件描述
    - 进度信息
    - 错误信息(如果有)
    - 服务器响应时间

    同时保存当前请求信息到日志
    """
    try:
        # 保存GET请求信息到日志
        await _log_get_request("/status")

        all_status = status_tracker.get_all_status()

        # 添加服务器响应时间
        response_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        logger.info(f"获取成功111: {all_status}")

        return JSONResponse({
            "success": True,
            "data": all_status,
            "response_time": response_time
        })
    except Exception as e:
        logger.error(f"获取状态失败: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.get("/status/process")
async def get_process_status():
    """
    仅获取 Process(任务分配)状态
    """
    try:
        # 保存GET请求信息到日志
        await _log_get_request("/status/process")

        process_status = status_tracker.get_process_status()

        # 添加服务器响应时间
        response_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return JSONResponse({
            "success": True,
            "data": process_status,
            "response_time": response_time
        })
    except Exception as e:
        logger.error(f"获取 process 状态失败: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.get("/status/simulate")
async def get_simulate_status():
    """
    仅获取 Simulate(仿真)状态
    """
    try:
        # 保存GET请求信息到日志
        await _log_get_request("/status/simulate")

        simulate_status = status_tracker.get_simulate_status()

        # 添加服务器响应时间
        response_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return JSONResponse({
            "success": True,
            "data": simulate_status,
            "response_time": response_time
        })
    except Exception as e:
        logger.error(f"获取 simulate 状态失败: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)



@app.post("/stop")
async def stop_current_task():
    """停止当前正在运行的任务（分配或仿真）"""
    global current_simulate_process
    logger.info("收到停止请求")
    # 设置全局停止标志
    stop_signal.request_stop()
    message = "停止信号已发送"

    # 终止仿真 subprocess
    if current_simulate_process:
        try:
            current_simulate_process.terminate()
            current_simulate_process.wait(timeout=2)
            message += "，仿真进程已终止"
            logger.info("仿真进程已成功终止")
        except Exception as e:
            try:
                current_simulate_process.kill()
                message += "，仿真进程已强制终止"
                logger.warning(f"仿真进程强制终止: {e}")
            except Exception as e2:
                logger.error(f"终止仿真进程失败: {e2}")
        current_simulate_process = None

    return JSONResponse({
        "success": True,
        "message": message
    })


def _run_process_task(payload, simulate_id, ts):
    """在后台线程中运行任务分配"""
    # 在重定向 stdout/stderr 之前导入日志模块
    from utils.logger import get_log_directories, log_error

    # 使用新的日志系统获取目录
    daily_dirs = get_log_directories()
    process_dir = daily_dirs['process']

    # 文件名格式: 时间戳_simulate_id.log
    run_log = process_dir / f'{ts}_{simulate_id}.log'

    # 重定向输出到日志文件
    log_file = open(run_log, 'a', encoding='utf-8')

    try:
        # 记录开始时间
        log_file.write(f"\n{'='*60}\n")
        log_file.write(f"任务分配开始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write(f"simulate_id: {simulate_id}\n")
        log_file.write(f"{'='*60}\n\n")
        log_file.flush()

        # 重定向 stdout 和 stderr
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = log_file
        sys.stderr = log_file

        # 执行任务
        deal_data(payload)
        main_module.main()

        # 记录完成时间
        log_file.write(f"\n{'='*60}\n")
        log_file.write(f"任务分配完成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write(f"{'='*60}\n")

    except Exception as e:
        # 记录错误到 process 日志
        log_file.write(f"\n错误: {e}\n")
        status_tracker.process_error(str(e))

        # 先恢复 stdout/stderr,否则无法记录错误日志
        sys.stdout = original_stdout
        sys.stderr = original_stderr

        # 使用新的错误日志系统记录错误,包含输入数据上下文
        log_error(
            f"任务分配失败 (simulate_id={simulate_id})",
            e,
            context={
                "simulate_id": simulate_id,
                "timestamp": ts,
                "input_payload": payload
            }
        )

        raise

    finally:
        # 恢复 stdout 和 stderr
        if sys.stdout != original_stdout:
            sys.stdout = original_stdout
        if sys.stderr != original_stderr:
            sys.stderr = original_stderr
        log_file.close()

        # 追加到全局日志
        try:
            with open(ROOT / 'logs' / 'all.log', 'a', encoding='utf-8') as af:
                with open(run_log, 'r', encoding='utf-8') as lf:
                    af.write(lf.read())
        except Exception:
            pass


@app.post("/process")
async def process(request: Request):
    """启动任务分配（立即返回，后台运行）"""
    try:
        payload = await request.json()
    except Exception as e:
        # 记录JSON解析错误
        from utils.logger import log_error
        log_error(
            "process接口: 前端输入数据JSON解析失败",
            e,
            context={
                "error": "JSON解析失败",
                "request_body": "无法解析的JSON数据"
            }
        )
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # 获取 simulate_id 用于创建独立目录
    simulate_id = payload.get('simulate_id', 0)
    push_index = payload.get('push_index', 0)

    # 验证数据类型
    is_valid, error_msg = validate_payload_data(payload)
    if not is_valid:
        from utils.logger import log_error
        log_error(
            "process接口: 前端输入数据类型验证失败",
            None,
            context={
                "simulate_id": simulate_id,
                "validation_error": error_msg,
                "input_payload": payload
            }
        )
        raise HTTPException(status_code=400, detail=f"数据验证失败: {error_msg}")

    # 重置停止标志
    stop_signal.reset()

    # 重置状态追踪器
    status_tracker.process_reset()

    # 保存归档输入（带时间戳），同时保持最新副本
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    archive_dir = DATA_DIR / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    input_archive_path = archive_dir / f"input_{ts}.json"
    latest_input = DATA_DIR / "latest_input.json"
    try:
        with open(input_archive_path, 'w', encoding='utf-8') as f:
            _json.dump(payload, f, ensure_ascii=False, indent=2)
        with open(latest_input, 'w', encoding='utf-8') as f:
            _json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        # 记录保存输入数据失败
        from utils.logger import log_error
        log_error(
            "process接口: 保存输入数据失败",
            e,
            context={
                "simulate_id": simulate_id,
                "timestamp": ts,
                "input_payload": payload
            }
        )
        logger.error(f"保存输入数据失败: {e}")

    # 在后台线程运行任务（不阻塞请求）
    executor.submit(_run_process_task, payload, simulate_id, ts)

    # 立即返回，告知任务已开始
    logger.info(f"任务分配已启动，simulate_id={simulate_id}")

    return JSONResponse({
        "success": True,
        "message": "任务分配已开始",
        "simulate_id": simulate_id,
        "push_index": push_index,
        "note": "请使用 GET /status 查询进度"
    })


@app.get("/process/result/{simulate_id}")
async def get_process_result(simulate_id: int):
    """获取任务分配结果（任务完成后调用）"""
    try:
        # 使用轮次独立目录的路径
        round_data_dir = DATA_DIR / f"data_{simulate_id}"
        output_path = round_data_dir / "output_assignment.json"
        workers_path = round_data_dir / "workers.json"
        tasks_path = round_data_dir / "tasks.json"

        # 检查任务是否完成
        current_status = status_tracker.get_process_status()
        if current_status["status"] not in ["完成", "错误", "已停止"]:
            return JSONResponse({
                "success": False,
                "message": "任务尚未完成",
                "current_status": current_status["status"]
            }, status_code=202)

        # 构建结果
        result = {}
        if output_path.exists():
            result_data = json.loads(output_path.read_text(encoding="utf-8"))
            result["output"] = result_data
        else:
            result["output"] = None

        if workers_path.exists():
            result["workers"] = json.loads(workers_path.read_text(encoding="utf-8"))
        else:
            result["workers"] = None

        if tasks_path.exists():
            result["tasks"] = json.loads(tasks_path.read_text(encoding="utf-8"))
        else:
            result["tasks"] = None

        result["downloads"] = {
            "output": f"/download/{simulate_id}/output_assignment.json",
            "workers": f"/download/{simulate_id}/workers.json",
            "tasks": f"/download/{simulate_id}/tasks.json",
        }
        result["simulate_id"] = simulate_id
        result["status"] = current_status

        return JSONResponse(result)

    except Exception as e:
        logger.error(f"获取结果失败: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.post("/simulate")
async def simulate(request: Request):
    """接受前端仿真原始数据，写入 view/input_data_old/updated_nice_data.json，运行 view/main.py 生成视频并返回日志与下载链接。"""
    try:
        payload = await request.json()
    except Exception as e:
        # 记录JSON解析错误
        from utils.logger import log_error
        log_error(
            "仿真接口: 前端输入数据JSON解析失败",
            e,
            context={
                "error": "JSON解析失败",
                "request_body": "无法解析的JSON数据"
            }
        )
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # 获取 simulate_id
    simulate_id = payload.get('simulate_id', 0)

    # 验证数据类型
    is_valid, error_msg = validate_payload_data(payload)
    if not is_valid:
        from utils.logger import log_error
        log_error(
            "仿真接口: 前端输入数据类型验证失败",
            None,
            context={
                "simulate_id": simulate_id,
                "validation_error": error_msg,
                "input_payload": payload
            }
        )
        raise HTTPException(status_code=400, detail=f"数据验证失败: {error_msg}")

    # 重置停止标志
    stop_signal.reset()

    # 重置状态追踪器
    status_tracker.simulate_reset()

    ROOT_VIEW = ROOT / "view"
    input_dir = ROOT_VIEW / "input_data_old"
    input_dir.mkdir(parents=True, exist_ok=True)
    # 写入归档输入并保留 latest 副本，避免覆盖历史
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    archive_dir = ROOT_VIEW / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    input_archive_path = archive_dir / f"old_data_{ts}.json"
    input_path = input_dir / "old_data.json"
    try:
        with open(input_archive_path, 'w', encoding='utf-8') as f:
            _json.dump(payload, f, ensure_ascii=False, indent=2)
        with open(input_path, 'w', encoding='utf-8') as f:
            _json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        # 记录文件写入错误
        from utils.logger import log_error
        log_error(
            "仿真接口: 写入输入文件失败",
            e,
            context={
                "simulate_id": simulate_id,
                "timestamp": ts,
                "input_payload": payload
            }
        )
        raise HTTPException(status_code=500, detail=f"Write input file error: {e}")

    global current_simulate_process

    try:
        current_simulate_process = subprocess.Popen(
            [sys.executable, 'main.py'],
            cwd=str(ROOT_VIEW),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # 等待进程完成（带超时和停止检查）
        timeout = 600  # 10分钟
        start_time = time.time()

        while current_simulate_process.poll() is None:
            if stop_signal.should_stop():
                current_simulate_process.terminate()
                try:
                    current_simulate_process.wait(timeout=2)
                except:
                    current_simulate_process.kill()
                logger.info("仿真被用户停止")
                raise HTTPException(status_code=499, detail="仿真已被用户停止")

            if time.time() - start_time > timeout:
                current_simulate_process.terminate()
                raise HTTPException(status_code=500, detail="仿真超时")

            time.sleep(0.1)  # 每 100ms 检查一次

        stdout, stderr = current_simulate_process.communicate()

    except HTTPException:
        # HTTPException 直接抛出（包括 499 停止状态）
        logs = "[仿真被停止]"
        try:
            # 使用新的日志系统获取目录
            from utils.logger import get_log_directories
            daily_dirs = get_log_directories()
            simulate_dir = daily_dirs['simulate']

            # 文件名格式: 时间戳_simulate_id.log
            run_log_v = simulate_dir / f'{ts}_{simulate_id}.log'
            with open(run_log_v, 'a', encoding='utf-8') as vf:
                vf.write(logs)
            global_logs = ROOT / 'logs' / 'all.log'
            with open(global_logs, 'a', encoding='utf-8') as gf:
                gf.write(logs)
        except Exception:
            pass
        raise

    except Exception as e:
        if stop_signal.should_stop():
            logger.info("仿真被用户停止")
            raise HTTPException(status_code=499, detail="仿真已被用户停止")

        # 使用新的错误日志系统记录错误,包含输入数据上下文
        from utils.logger import log_error
        log_error(
            "仿真运行失败",
            e,
            context={
                "simulate_id": simulate_id,
                "timestamp": ts,
                "input_payload": payload
            }
        )

        raise HTTPException(status_code=500, detail=f"Run simulation error: {e}")
    finally:
        current_simulate_process = None

    logs = stdout.decode('utf-8') + '\n' + stderr.decode('utf-8')
    # 保存模拟日志到新的日志目录与全局 logs
    try:
        # 使用新的日志系统获取目录
        from utils.logger import get_log_directories
        daily_dirs = get_log_directories()
        simulate_dir = daily_dirs['simulate']

        # 文件名格式: 时间戳_simulate_id.log
        run_log_v = simulate_dir / f'{ts}_{simulate_id}.log'
        with open(run_log_v, 'a', encoding='utf-8') as vf:
            vf.write(logs)
        # append to global logs
        global_logs = ROOT / 'logs' / 'all.log'
        with open(global_logs, 'a', encoding='utf-8') as gf:
            gf.write(logs)
    except Exception:
        pass
    
    out_dir = ROOT_VIEW / "output_mp4"
    mp4_files = list(out_dir.glob('*.mp4')) if out_dir.exists() else []
    if not mp4_files:
        return JSONResponse({"success": True, "logs": logs, "video": None})

    latest = max(mp4_files, key=lambda p: p.stat().st_mtime)
    video_name = latest.name
    # 将视频与输入/输出拷贝到 archive
    try:
        run_archive = archive_dir / ts
        run_archive.mkdir(parents=True, exist_ok=True)
        shutil.copy(str(latest), str(run_archive / video_name))
        # copy input (already saved) and, if present, view metrics or other outputs
        metrics = ROOT_VIEW / 'data' / 'view_metrics.json'
        if metrics.exists():
            shutil.copy(str(metrics), str(run_archive / 'view_metrics.json'))
    except Exception:
        pass

    return JSONResponse({
        "success": True,
        "logs": logs,
        "video": f"/simulate/download/{video_name}"
    })