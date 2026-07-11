"""
配置文件
存储系统配置参数和常量
"""
"""
    数组地图的大小：
        X:262
        Y:149

    X方向: res_x = 66.417 / 262 = 0.2535 米/网格
    Y方向: res_y = 37.7715 / 149 = 0.2535 米/网格

    注意：X和Y方向的分辨率完全相同（1:1比例）
"""

class Config:
    # 地图配置
    MAP_FILE_PATH = './map.txt'# 地图路径随时修改
    REAL_X_MAX = 66.417  # 仓库实际最大X坐标(米) - 已修正
    REAL_Y_MAX = 37.7715 # 仓库实际最大Y坐标(米) - 已修正
    # 路径规划配置
    MOVEMENT_SPEED = 0.83  # 人员移动速度(米/秒)
    
    # 分配策略: 'load_balance' (负载均衡), 'distance_first' (距离优先), 'hybrid' (混合策略)
    ALLOCATION_STRATEGY = 'hybrid'

    # 混合策略配置
    HYBRID_ALPHA = 1  # 负载均衡系数，0=纯距离优先，越大越倾向于负载均衡 20260121 修改为1

    # 紧急任务配置
    URGENT_TASK_PENALTY = 1000  # 紧急任务延迟惩罚系数
    MAX_TASK_DELAY = 300  # 最大允许延迟时间(秒)
    # 输入输出
    OUTPUT_FILE = './data/output_assignment.json'
    WORKERS_FILE = './data/workers.json'
    TASKS_FILE = './data/tasks.json'