# 替换整个output_formatter.py文件：

"""
输出格式化工具
"""

from typing import List, Dict
from models.task import Task
from models.worker import Worker

class OutputFormatter:
    @staticmethod
    def format_worker_optimized_schedule(workers: List[Worker]) -> List[Dict]:
        """
        格式化每个工人的优化任务排序
        """
        output = []
        
        for worker in workers:
            for task in worker.allocated_tasks:
                # ********** 新增代码开始 **********
                # 只输出未完成的任务
                if task.task_status in ["已完成", "已取消", "已关闭"]:
                    continue
                # ********** 新增代码结束 **********
                
                # 根据优化顺序获取SKU
                ordered_skus = []
                
                if task.optimized_sku_order:
                    # 使用优化后的顺序
                    for idx in task.optimized_sku_order:
                        if 0 <= idx < len(task.sku_list):
                            sku = task.sku_list[idx]
                            ordered_skus.append({
                                "skuCode": sku.sku_code,
                                "locationX": sku.location_x,
                                "locationY": sku.location_y,
                                "skuPickSpeed": sku.sku_pick_speed,
                                "inspectedQuantity": sku.inspected_quantity,  # 添加包数量
                                "taskDetailId": sku.task_detail_id  # 添加 taskDetailId
                            })
                else:
                    # 使用原始顺序
                    for sku in task.sku_list:
                        ordered_skus.append({
                            "skuCode": sku.sku_code,
                            "locationX": sku.location_x,
                            "locationY": sku.location_y,
                            "skuPickSpeed": sku.sku_pick_speed,
                            "inspectedQuantity": sku.inspected_quantity,  # 添加包数量
                            "taskDetailId": sku.task_detail_id  # 添加 taskDetailId
                        })
                
                # 创建任务输出
                task_dict = {
                    "taskId": task.task_id,
                    "userId": task.user_id,
                    "mainId":task.mainId,
                    "sku_order": ordered_skus,
                    "predictStartTime": task.predict_start_time.strftime("%Y-%m-%d %H:%M:%S") if task.predict_start_time else None,
                    "predictStartLocationX": task.predict_start_location_x,
                    "predictStartLocationY": task.predict_start_location_y,
                    "predictCompleteTime": task.predict_complete_time.strftime("%Y-%m-%d %H:%M:%S") if task.predict_complete_time else None,
                    "predictCompleteLocationX": task.predict_complete_location_x,
                    "predictCompleteLocationY": task.predict_complete_location_y,
                    "distance": round(task.distance, 2) if hasattr(task, 'distance') else 0.0,
                    "taskStatus": task.task_status  # 添加任务状态
                }
                
                output.append(task_dict)
        
        return output
    
