# 这个代码用于读取data/latest_input.json文件，读取里面的last_push这个字段，返回它的值
import json

# 读取JSON文件
def find_last_push():
    with open('data/latest_input.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    # 获取last_push的值
    last_push_value = data['last_push']
    return str(last_push_value)
