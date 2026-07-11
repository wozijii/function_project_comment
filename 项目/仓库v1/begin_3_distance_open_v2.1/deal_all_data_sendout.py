# 需要处理 ：
"""
    "simulate_id": 192,
        - 每一次处理的都是处理文件下面simulate_id相同的那一个数据，因为这是属于同一个波次
        - 读取该轮次目录下的 merged_all_outputs.json（由 send_output_fast.py 在 last_push=True 时生成）
"""

def main():
    # 处理所有的数据合并返回，读取当前轮次的合并输出
    import time
    time.sleep(3)
    import json
    from pathlib import Path
    from collections import defaultdict

    # 获取当前轮次的 simulate_id
    try:
        with open('./data/latest_input.json', 'r', encoding='utf-8') as f:
            latest_input = json.load(f)
        simulate_id = int(latest_input.get('simulate_id', 0))
    except Exception as e:
        print(f"错误: 无法读取 simulate_id: {e}")
        return

    print(f"正在处理轮次 {simulate_id} 的数据...")

    # 轮次目录
    round_dir = Path(f"./data/data_{simulate_id}")

    if not round_dir.exists():
        print(f"错误: 轮次目录不存在: {round_dir}")
        return

    # 读取 merged_all_outputs.json（包含该轮次所有 push 的数据）
    merged_file = round_dir / "merged_all_outputs.json"

    if not merged_file.exists():
        print(f"错误: 找不到合并输出文件: {merged_file}")
        print("提示: 该文件应在 last_push=True 时由 send_output_fast.py 生成")
        return

    # 读取合并后的数据
    with open(merged_file, 'r', encoding='utf-8') as f:
        all_data = json.load(f)

    print(f"读取到 {len(all_data)} 条任务记录")

    # 按用户分组并排序
    merged_by_user = defaultdict(list)
    for item in all_data:
        if isinstance(item, dict) and 'userId' in item:
            merged_by_user[item['userId']].append(item)

    # 展平数据（按用户ID排序）
    result = []
    for user_id in sorted(merged_by_user.keys()):
        result.extend(merged_by_user[user_id])

    # 保存到 view 目录用于生图
    output_dir = Path("./view/input_data_old")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "old_data.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"合并完成！共处理 {len(result)} 条记录")
    print(f"结果已保存到: {output_file}")

    # 同时保存一份到轮次目录
    backup_file = round_dir / "final_merged_output.json"
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"备份已保存到: {backup_file}")