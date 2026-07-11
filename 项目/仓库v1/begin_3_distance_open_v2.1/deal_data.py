
# 将输入数据进行转化处理，最后输出两个json文件，一个tasks.json，一个workers.json

import json
from pathlib import Path

list_data = []

def deal_data(input_data):
    """
    处理输入数据并按照 simulate_id 分目录保存

    Args:
        input_data: 包含 simulate_id, push_index, last_push, userInfo, taskInfo 的字典
    """
    # 提取数据
    simulate_id = int(input_data["simulate_id"])
    push_index = input_data["push_index"]
    last_push = input_data.get("last_push", False)

    # 记录 simulate_id
    list_data.append(simulate_id)

    # 创建该轮次的独立目录
    data_dir = Path(f"data/data_{simulate_id}")
    data_dir.mkdir(parents=True, exist_ok=True)

    # 分离数据
    userinfo = {"userInfo": input_data["userInfo"]}
    taskinfo = {"taskInfo": input_data["taskInfo"]}

    # 写入 workers.json
    with open(data_dir / "workers.json", "w", encoding="utf-8") as f:
        json.dump(userinfo, f, ensure_ascii=False, indent=2)

    # 写入 tasks.json
    with open(data_dir / "tasks.json", "w", encoding="utf-8") as f:
        json.dump(taskinfo, f, ensure_ascii=False, indent=2)

    # 写入本次 push 的元数据
    push_metadata = {
        "simulate_id": simulate_id,
        "push_index": push_index,
        "last_push": last_push
    }

    # 保存本次 push 的元数据(文件名包含 push_index 以区分不同 push)
    with open(data_dir / f"push_{push_index}_metadata.json", "w", encoding="utf-8") as f:
        json.dump(push_metadata, f, ensure_ascii=False, indent=2)

    # 更新最新的 push_index 记录(用于追踪当前处理到第几个 push)
    with open(data_dir / "latest_push_index.json", "w", encoding="utf-8") as f:
        json.dump({"latest_push_index": push_index}, f, ensure_ascii=False, indent=2)

    return simulate_id, push_index, last_push
def merge_json_files(return_data_path, output_assignment_path):
    # 读取第一个文件
    with open(return_data_path, 'r', encoding='utf-8') as f:
        return_data = json.load(f)
    
    # 读取第二个文件
    with open(output_assignment_path, 'r', encoding='utf-8') as f:
        output_assignment = json.load(f)
    
    # 提取第一个文件中的字段
    simulate_id = None
    push_index = None
    
    for item in return_data:
        if 'simulate_id' in item:
            simulate_id = item['simulate_id']
        elif 'push_index' in item:
            push_index = item['push_index']
    
    # 构建合并后的数据结构
    merged_data = {
        'simulate_id': simulate_id,
        'push_index': push_index,
        'payload': output_assignment  # 第二个文件的内容作为payload
    }
    
    return merged_data

if __name__=="__main__":
    input_data = input()# 接收前端的json数据
    # 转化为json数据形式
    input_data = json.loads(input_data)
    deal_data(input_data)# 目前是分配速度慢
    import json
    # 合并数据
    result = merge_json_files('data/return_data.json', 'data/output_assignment.json')
    
    # 输出结果
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 如果需要保存到文件
    with open('data/merge.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    

