"""
解析process日志,提取任务分配的关键指标
输出为CSV格式,方便数据分析
"""

import re
import csv
from datetime import datetime
from typing import List, Dict
import sys


class ProcessLogParser:
    """解析process日志的解析器"""

    def __init__(self, log_file_path: str):
        self.log_file_path = log_file_path
        self.simulate_id = None
        self.tasks_allocation = []  # 分配阶段数据

    def parse(self) -> List[Dict]:
        """解析日志文件"""
        with open(self.log_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 提取simulate_id
        for line in lines:
            match = re.search(r'simulate_id:\s*(\d+)', line)
            if match:
                self.simulate_id = match.group(1)
                break

        # 解析分配阶段
        self._parse_allocation_phase(lines)

        return self.tasks_allocation

    def _parse_allocation_phase(self, lines: List[str]):
        """解析任务分配阶段

        时间戳规则：
        1. 员工评估时间：从 '员工 某某 当前位置:' 上面的 'time: xxx' 开始，
                          到下一个员工的时间戳结束
        2. 任务分配时间：从 '分配任务:' 左边的时间戳开始，
                          到下一个 '分配任务:' 左边的时间戳结束
        """
        i = 0
        while i < len(lines):
            line = lines[i]

            # 匹配任务开始分配
            task_match = re.search(r'分配任务[：:]\s*(\S+)\s*\(优先级[：:]\s*(\d+)\)', line)
            if task_match:
                task_id = task_match.group(1)
                priority = task_match.group(2)
                task_start_time = self._extract_time(line)

                # 查找该任务的评估时间和分配结果
                worker_evaluations = []  # 格式: {'worker_name': str, 'eval_start': str, 'eval_end': str}
                assigned_worker = None
                task_end_time = None

                j = i + 1

                while j < len(lines) and j < i + 20000:  # 限制搜索范围
                    line_j = lines[j]

                    # 检查是否到达下一个任务（当前任务结束）
                    next_task_match = re.search(r'分配任务[：:]\s*\S+', line_j)
                    if next_task_match and j > i + 1:
                        # 提取下一个任务的时间戳作为当前任务的结束时间
                        task_end_time = self._extract_time(line_j)
                        break

                    # 查找"分配给:"标记
                    assign_match = re.search(r'分配给[：:]\s*(\S+)\s*\(插入的索引位置[：:]\s*\d+\)', line_j)
                    if assign_match:
                        assigned_worker = assign_match.group(1)
                        j += 1
                        continue

                    # 查找员工评估块
                    # 格式：
                    # time: 2025-12-29 22:06:48
                    # 员工 滕亮 当前位置:
                    time_match = re.search(r'^time[：:]\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line_j)
                    if time_match and j + 1 < len(lines):
                        eval_start_time = time_match.group(1)

                        # 检查下一行是否是员工当前位置
                        worker_match = re.search(r'员工\s*(\S+)\s+当前位置:', lines[j + 1])
                        if worker_match:
                            worker_name = worker_match.group(1)

                            # 查找这个员工评估的结束时间（下一个time行）
                            eval_end_time = eval_start_time  # 默认值
                            k = j + 1
                            while k < len(lines) and k < j + 1000:
                                next_time_match = re.search(r'^time[：:]\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', lines[k])
                                if next_time_match:
                                    eval_end_time = next_time_match.group(1)
                                    break
                                # 如果遇到分配任务或分配给，也停止
                                if re.search(r'分配任务[：:]|分配给[：:]', lines[k]):
                                    break
                                k += 1

                            worker_evaluations.append({
                                'worker_name': worker_name,
                                'eval_start': eval_start_time,
                                'eval_end': eval_end_time
                            })

                    j += 1

                # 如果没有找到task_end_time，尝试从最后的员工评估时间推断
                if not task_end_time and worker_evaluations:
                    task_end_time = worker_evaluations[-1]['eval_end']

                # 生成每条评估记录
                for eval_data in worker_evaluations:
                    worker_name = eval_data['worker_name']
                    eval_start = eval_data['eval_start']
                    eval_end = eval_data['eval_end']

                    # 计算评估时长
                    eval_duration = self._calculate_duration(eval_start, eval_end)

                    # 计算任务分配总时长
                    total_task_duration = 0
                    if task_end_time:
                        total_task_duration = self._calculate_duration(task_start_time, task_end_time)

                    self.tasks_allocation.append({
                        'simulate_id': self.simulate_id,
                        'task_id': task_id,
                        'priority': priority,
                        'evaluated_worker': worker_name,
                        'assigned_worker': assigned_worker if worker_name == assigned_worker else '',
                        'eval_start_time': eval_start,
                        'eval_end_time': eval_end,
                        'eval_duration': eval_duration,
                        'task_start_time': task_start_time,
                        'task_end_time': task_end_time if task_end_time else task_start_time,
                        'total_task_duration': total_task_duration
                    })

            i += 1

    def _extract_time(self, line: str) -> str:
        """从行中提取时间戳"""
        # 匹配多种时间格式，优先匹配完整的time：格式
        patterns = [
            r'time[：:]\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',  # time：或time:开头
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',  # 纯时间戳
        ]

        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(1)

        return ""

    def _calculate_duration(self, start_time: str, end_time: str) -> float:
        """计算持续时间(秒)"""
        if not start_time or not end_time:
            return 0.0

        try:
            start = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
            return round((end - start).total_seconds(), 2)
        except:
            return 0.0

    def export_allocation_csv(self, output_file: str):
        """导出分配阶段数据到CSV"""
        if not self.tasks_allocation:
            print("没有分配阶段数据")
            return

        with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)

            # 写入表头
            writer.writerow([
                'Simulate_ID',
                'Task_ID',
                'Priority',
                'Evaluated_Worker',
                'Assigned_Worker',
                'Eval_Start_Time',
                'Eval_End_Time',
                'Eval_Duration_Seconds',
                'Task_Start_Time',
                'Task_End_Time',
                'Total_Task_Duration_Seconds'
            ])

            # 写入数据
            for task in self.tasks_allocation:
                writer.writerow([
                    task['simulate_id'],
                    task['task_id'],
                    task['priority'],
                    task['evaluated_worker'],
                    task['assigned_worker'],
                    task['eval_start_time'],
                    task['eval_end_time'],
                    task['eval_duration'],
                    task['task_start_time'],
                    task['task_end_time'],
                    task['total_task_duration']
                ])

        print(f"✓ 分配阶段数据已导出到: {output_file}")

        # 统计信息
        total_evals = len(self.tasks_allocation)
        unique_tasks = len(set(t['task_id'] for t in self.tasks_allocation))
        assigned_count = sum(1 for t in self.tasks_allocation if t['assigned_worker'])

        print(f"  总评估记录: {total_evals}")
        print(f"  唯一任务数: {unique_tasks}")
        print(f"  实际分配数: {assigned_count}")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python parse_process_log.py <日志文件路径>")
        sys.exit(1)

    log_file = sys.argv[1]

    print(f"正在解析日志文件: {log_file}")
    parser = ProcessLogParser(log_file)
    parser.parse()

    # 生成输出文件名(输出到原日志文件所在目录)
    import os
    log_dir = os.path.dirname(log_file)
    log_filename = os.path.basename(log_file)
    base_name = os.path.splitext(log_filename)[0]

    if log_dir:
        allocation_file = os.path.join(log_dir, f"{base_name}_allocation.csv")
    else:
        allocation_file = f"{base_name}_allocation.csv"

    # 导出CSV
    parser.export_allocation_csv(allocation_file)

    print("\n✓ 所有数据导出完成!")


if __name__ == "__main__":
    main()
