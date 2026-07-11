def main():
    import json
    # 读取JSON数据
    with open('input_data_old/old_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    # 提取payload
    result = data['payload']

    # 保存处理后的数据
    with open('input_data_old/old_data.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    # 提取simulate_id并保存到txt文件
    simulate_id = data['simulate_id']
    with open('input_data_old/simulate_id.txt', 'w', encoding='utf-8') as f:
        f.write(str(simulate_id))
def make():
    with open('input_data_old/simulate_id.txt', 'r', encoding='utf-8') as f:
        num = int(f.read())
    return num

    
