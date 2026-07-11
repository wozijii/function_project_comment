def main1():
    import json
    from pathlib import Path

    # 获取项目根目录(无论从哪里运行都能正确找到)
    # 获取当前文件的绝对路径
    current_file = Path(__file__).resolve()
    # view 目录的父目录就是项目根目录
    project_root = current_file.parent.parent

    # 获取当前轮次的 simulate_id
    try:
        latest_input_path = project_root / 'data' / 'latest_input.json'
        with open(latest_input_path, 'r', encoding='utf-8') as f:
            latest_input = json.load(f)
        simulate_id = int(latest_input.get('simulate_id', 0))
    except Exception as e:
        print(f"警告: 无法读取 simulate_id, 将使用默认路径: {e}")
        simulate_id = None

    # 确定数据目录
    if simulate_id is not None:
        data_dir = project_root / 'data' / f"data_{simulate_id}"
        print(f"使用轮次 {simulate_id} 的数据目录: {data_dir}")
    else:
        data_dir = project_root / 'data'
        print(f"使用默认数据目录: {data_dir}")

    # 读取 workers.json 文件
    workers_path = data_dir / "workers.json"
    with open(workers_path, "r", encoding="utf-8") as f:
        input_data = json.load(f)

    # 处理数据
    output_data = [
        {
            "userId": user["userId"],
            "name": user["name"],
            "location_X": user["pdaLocationX"],
            "location_Y": user["pdaLocationY"],
        }
        for user in input_data["userInfo"]
    ]

    print(f"从 workers.json 读取到 {len(output_data)} 个用户:")
    for user in output_data:
        print(f"  - {user['name']} ({user['userId']})")

    # 读取优化后的视频仿真数据
    nice_data = output_data

    # 新输入的文件信息 - 读取 deal_all_data_sendout.py 生成的 old_data.json
    # old_data.json 包含该轮次所有 push 的合并数据
    old_data_path = project_root / 'view' / 'input_data_old' / 'old_data.json'

    if not old_data_path.exists():
        print(f"错误: 找不到 {old_data_path}")
        print("提示: 请确保 deal_all_data_sendout.main() 已成功运行")
        return

    with open(old_data_path, 'r', encoding='utf-8') as f:
        new_data = json.load(f)

    print(f"读取到 {len(new_data)} 条任务分配记录")

    # 创建一个字典，用于快速查找 nice_data 中的用户
    user_dict = {user['userId']: user for user in nice_data}

    # 遍历新数据，更新 nice_data 中的用户信息
    for task in new_data:
        user_id = task['userId']
        if user_id in user_dict:
            user = user_dict[user_id]
            # 如果用户还没有 path 字段，初始化为空列表
            if 'path' not in user:
                user['path'] = []
            # 追加新的位置信息
            user['path'].extend([{"locationX": item['locationX'], "locationY": item['locationY']} for item in task['sku_order']])

    # 确保所有用户都有 path 字段(即使没有任务)
    for user in nice_data:
        if 'path' not in user:
            user['path'] = []
            print(f"警告: 用户 {user['name']} ({user['userId']}) 没有分配任何任务,path 设置为空列表")

    # 将更新后的数据保存到 view/input_data_nice/nice_data.json
    # 使用绝对路径确保无论从哪里运行都能正确保存
    output_path_absolute = current_file.parent / 'input_data_nice' / 'nice_data.json'
    output_path_absolute.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path_absolute, 'w', encoding='utf-8') as file:
        json.dump(nice_data, file, indent=4, ensure_ascii=False)

    print(f"已保存处理后的数据到: {output_path_absolute}")
