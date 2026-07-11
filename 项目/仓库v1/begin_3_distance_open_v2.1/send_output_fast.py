import json
import requests
import Judgment_last_true
import sys
from pathlib import Path
from typing import List, Dict, Any

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def get_current_simulate_id() -> int:
    """获取当前正在处理的 simulate_id"""
    try:
        with open('./data/latest_input.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return int(data.get('simulate_id', 0))
    except Exception as e:
        print(f"警告: 无法读取 simulate_id: {e}")
        from utils.error_handler import handle_error
        handle_error(
            "无法读取 simulate_id",
            e,
            context={"file": "./data/latest_input.json"},
            module="send_output"
        )
        return None


def collect_all_outputs_for_round(simulate_id: int) -> List[Dict[str, Any]]:
    """
    收集某个轮次的所有 push 的输出结果并合并

    Args:
        simulate_id: 轮次ID

    Returns:
        合并后的所有任务的输出列表
    """
    try:
        data_dir = Path(f'./data/data_{simulate_id}')
        if not data_dir.exists():
            error_msg = f"轮次目录不存在: {data_dir}"
            print(f"❌ {error_msg}")
            from utils.error_handler import handle_error
            handle_error(
                error_msg,
                None,
                context={"simulate_id": simulate_id, "data_dir": str(data_dir)},
                module="send_output"
            )
            return []

        # 查找所有的 push_*_metadata.json 文件
        metadata_files = sorted(data_dir.glob('push_*_metadata.json'))

        if not metadata_files:
            print(f"警告: 在 {data_dir} 中没有找到任何 push metadata 文件")
            # 如果没有历史 push,读取当前的 output_assignment.json
            output_file = data_dir / 'output_assignment.json'
            if output_file.exists():
                with open(output_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []

        # 收集所有 push 的输出
        all_outputs = []

        # 读取当前的 output_assignment.json (最新的 push)
        output_file = data_dir / 'output_assignment.json'
        if output_file.exists():
            with open(output_file, 'r', encoding='utf-8') as f:
                current_output = json.load(f)
                all_outputs.extend(current_output)
                print(f"读取当前 push 的输出: {len(current_output)} 条记录")
        else:
            print(f"警告: 找不到 output_assignment.json")

        # 注意: 由于每个 push 会覆盖 workers.json 和 tasks.json,
        # output_assignment.json 实际上已经包含了该 push 的所有任务分配
        # 所以这里直接返回最新的 output_assignment.json 即可

        return all_outputs

    except Exception as e:
        error_msg = "收集轮次输出失败"
        print(f"❌ {error_msg}: {e}")
        from utils.error_handler import handle_error
        handle_error(
            error_msg,
            e,
            context={"simulate_id": simulate_id},
            module="send_output"
        )
        return []


def merge_json_files(simulate_id: int, push_index: int) -> Dict[str, Any]:
    """
    合并 simulate_id, push_index 和 output_assignment 数据

    Args:
        simulate_id: 轮次ID
        push_index: push索引

    Returns:
        合并后的数据字典
    """
    try:
        data_dir = Path(f'./data/data_{simulate_id}')
        output_assignment_path = data_dir / 'output_assignment.json'

        # 读取 output_assignment
        if not output_assignment_path.exists():
            error_msg = f"找不到文件: {output_assignment_path}"
            print(f"❌ {error_msg}")
            from utils.error_handler import handle_error
            handle_error(
                error_msg,
                None,
                context={"simulate_id": simulate_id, "file_path": str(output_assignment_path)},
                module="send_output"
            )
            return {}

        with open(output_assignment_path, 'r', encoding='utf-8') as f:
            output_assignment = json.load(f)

        # 读取 latest_input.json 获取 simulate 字段
        simulate = False
        try:
            with open('./data/latest_input.json', 'r', encoding='utf-8') as f:
                latest_input = json.load(f)
            simulate = latest_input.get('simulate', False)
        except Exception as e:
            print(f"警告: 无法读取 simulate 字段: {e}")
            from utils.error_handler import handle_error
            handle_error(
                "无法读取 simulate 字段",
                e,
                context={"file": "./data/latest_input.json"},
                module="send_output",
                notify_frontend=False  # 警告级别,不通知前端
            )

        # 构建合并后的数据结构
        merged_data = {
            'simulate_id': simulate_id,
            'push_index': push_index,
            'simulate': simulate,  # 添加 simulate 字段
            'payload': output_assignment  # output_assignment 的内容作为payload
        }

        return merged_data

    except Exception as e:
        error_msg = "合并JSON文件失败"
        print(f"❌ {error_msg}: {e}")
        from utils.error_handler import handle_error
        handle_error(
            error_msg,
            e,
            context={"simulate_id": simulate_id, "push_index": push_index},
            module="send_output"
        )
        return {}


def main():
    """主函数"""
    try:
        # 获取当前轮次信息
        simulate_id = get_current_simulate_id()
        if simulate_id is None:
            error_msg = "无法获取 simulate_id"
            print(f"❌ {error_msg}")
            from utils.error_handler import handle_error
            handle_error(
                error_msg,
                None,
                context={},
                module="send_output"
            )
            return

        # 读取 latest_input.json 获取 push_index 和 last_push
        try:
            with open(f'./data/latest_input.json', 'r', encoding='utf-8') as f:
                input_data = json.load(f)
            push_index = input_data.get('push_index', 0)
            last_push = input_data.get('last_push', False)
        except Exception as e:
            error_msg = "读取 latest_input.json 失败"
            print(f"❌ {error_msg}: {e}")
            from utils.error_handler import handle_error
            handle_error(error_msg, e, module="send_output")
            return

        print(f"当前轮次: {simulate_id}, Push索引: {push_index}, 是否最后push: {last_push}")

        # 合并当前 push 的数据
        result = merge_json_files(simulate_id, push_index)

        if not result:
            error_msg = "合并数据失败,结果为空"
            print(f"❌ {error_msg}")
            from utils.error_handler import handle_error
            handle_error(error_msg, None, context={"simulate_id": simulate_id}, module="send_output")
            return

        # 保存合并结果到轮次目录
        data_dir = Path(f'./data/data_{simulate_id}')
        merge_file = data_dir / 'merge.json'
        with open(merge_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"已保存合并数据到: {merge_file}")

        # 读取合并后的数据用于发送
        with open(merge_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
# http://10.10.82.46:3000
        # 发送 POST 请求到回调接口
        url = "http://10.100.200.241:18002/api/v1/virtual-simulation/callback"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        response = requests.post(url, json=data, headers=headers, timeout=30)

        # 检查结果
        if response.status_code == 200:
            print("✅ 回调成功:", response.json())
        else:
            error_msg = f"回调失败,状态码: {response.status_code}"
            print(f"❌ {error_msg}")
            print("响应内容:", response.text)
            from utils.error_handler import handle_error
            handle_error(
                error_msg,
                None,
                context={
                    "status_code": response.status_code,
                    "response": response.text
                },
                module="send_output",
                notify_frontend=True
            )
            return  # 如果回调失败,不继续后续流程

        # 判断是否为最后一个 push
        sys.path.insert(0, '.')
        import view.view_nice_main as vv
        print('✓ 导入成功')

        if last_push == True:
            print(f"\n这是轮次 {simulate_id} 的最后一个 push,开始生图流程...")

            # 收集该轮次的所有 push 数据
            all_outputs = collect_all_outputs_for_round(simulate_id)

            if not all_outputs:
                print("警告: 没有收集到任何输出数据")
                return

            print(f"总共收集到 {len(all_outputs)} 条任务记录")

            # 保存合并后的所有输出到轮次目录
            merged_output_file = data_dir / 'merged_all_outputs.json'
            with open(merged_output_file, 'w', encoding='utf-8') as f:
                json.dump(all_outputs, f, ensure_ascii=False, indent=2)
            print(f"已保存所有合并输出到: {merged_output_file}")

            # 运行 view_nice_main
            import time
            time.sleep(3)  # 等待3秒,确保之前的进程完全结束

            # 数据处理
            import deal_all_data_sendout
            deal_all_data_sendout.main()

            time.sleep(6)  # 确保之前的进程完全结束
            vv.main()
        else:
            print(f"\n当前不是最后一个 push (push_index={push_index}),等待下一个 push...")

    except Exception as e:
        error_msg = "send_output_fast 主流程异常"
        print(f"❌ {error_msg}: {e}")
        import traceback
        traceback.print_exc()
        from utils.error_handler import handle_error
        handle_error(error_msg, e, module="send_output")


if __name__ == "__main__":
    main()
