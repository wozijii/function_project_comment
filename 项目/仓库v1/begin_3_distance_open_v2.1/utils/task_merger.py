import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

def merge_task_files(data_dir: Path) -> List[Dict[str, Any]]:
    """
    倒序读取并合并所有历史任务文件，去重保留最新版本
    
    Args:
        data_dir: 轮次数据目录路径
    
    Returns:
        合并后的任务列表
    """
    # 获取所有历史任务文件
    task_files = []
    for file in data_dir.glob("output_assignment_*.json"):
        if file.name != "output_assignment.json":  # 排除最终输出文件
            # 提取时间戳用于排序
            try:
                # 文件名格式: output_assignment_YYYYMMDD_HHMMSS_ffffff.json
                timestamp_str = file.name.replace("output_assignment_", "").replace(".json", "")
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S_%f")
                task_files.append((file, timestamp))
            except ValueError:
                continue  # 跳过不符合格式的文件
    
    # 按时间正序排序（最旧在前）
    task_files.sort(key=lambda x: x[1], reverse=False)

    # 用于存储已处理的任务ID，避免重复
    processed_task_ids = set()
    merged_tasks = []

    # 按时间正序处理每个文件（从最旧到最新）
    for file_path, _ in task_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tasks = json.load(f)

            # 遍历当前文件中的任务
            for task in tasks:
                task_id = task.get("taskId")
                if task_id and task_id not in processed_task_ids:
                    # 如果任务ID未处理过，添加到结果末尾
                    merged_tasks.append(task)
                    processed_task_ids.add(task_id)
                    
        except Exception as e:
            print(f"警告: 读取文件 {file_path} 失败: {e}")
            continue
    
    return merged_tasks