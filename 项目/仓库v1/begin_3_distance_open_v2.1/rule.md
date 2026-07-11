# 仓库拣货任务分配与优化规则说明

## 目录
1. [系统概述](#系统概述)
2. [任务分配阶段](#任务分配阶段)
3. [任务优化阶段](#任务优化阶段)
4. [核心算法](#核心算法)
5. [数据流程](#数据流程)
6. [关键参数配置](#关键参数配置)

---

## 系统概述

本系统是一个仓库拣货任务分配与优化系统，主要功能包括：
- 根据员工位置、任务优先级和分配策略自动分配拣货任务
- 使用A*算法计算路径距离
- 使用TSP（旅行商问题）优化SKU拣货顺序
- 支持距离优先和负载均衡两种分配策略

---

## 任务分配阶段

### 1. 分配流程

当有新任务到来时，系统会为每个员工评估最佳分配方案：

```
新任务到达
    ↓
遍历所有员工
    ↓
对每个员工：
    ├─ 判断任务类型（紧急/普通）
    ├─ 计算最佳插入位置
    ├─ 计算完成时间和距离
    └─ 记录评估结果
    ↓
选择最优员工（根据策略）
    ↓
将任务插入到该员工任务队列
```

### 2. 紧急任务 vs 普通任务

#### 紧急任务（priority > 0）
```python
def calculate_urgent_insertion(worker, urgent_task):
    # 1. 查找正在执行的任务
    executing_task_index = 查找状态为"执行中"的任务索引

    # 2. 确定插入位置
    if 有正在执行的任务:
        insert_position = executing_task_index + 1  # 插入到执行中任务后面
    else:
        insert_position = 0  # 插入到最前面

    # 3. 计算完成时间和距离
    return insert_position, total_time, total_distance
```

**特点**：
- 只能插入到当前执行任务之后（如果有）
- 优先级最高，不受其他任务影响
- 如果会超期完成，会增加惩罚时间

#### 普通任务（priority = 0）
```python
def calculate_best_insertion(worker, new_task):
    # 1. 获取员工当前位置
    start_grid = worker.get_current_grid_location()

    # 2. 确定候选插入位置
    if 任务数 <= 10:
        尝试所有位置 (0, 1, 2, ..., n)
    else:
        # 智能筛选：只尝试最可能的位置
        - 位置0（最前面）
        - 位置n（最后面）
        - 最接近任务的前后位置（±1, ±2）

    # 3. 对每个候选位置
    for insert_pos in candidate_positions:
        创建临时任务列表 = [已有任务] + 新任务插入到insert_pos
        计算总完成时间和距离（优化每个任务的SKU顺序）
        选择时间/距离最短的位置

    return best_position, best_time, best_distance
```

**特点**：
- 可以插入到任务队列的任何位置
- 智能选择候选位置，避免计算量过大
- 会考虑任务间的路径距离

### 3. 员工选择策略

系统根据配置选择最优员工：

```python
for worker in workers:
    计算该员工的完成时间和距离

    if ALLOCATION_STRATEGY == 'distance_first':
        # 距离优先：选择总移动距离最短的员工
        best_metric = total_distance
    else:
        # 负载均衡：选择完成时间最短的员工
        best_metric = completion_time

    if current_metric < best_metric:
        best_worker = worker
```

**策略对比**：

| 策略 | 优化目标 | 适用场景 |
|------|---------|---------|
| `distance_first` | 最小化总移动距离 | 关注节省行走路径 |
| `load_balance` | 最小化完成时间 | 关注任务快速完成 |

### 4. 任务分配阶段的优化内容

✅ **优化的内容**：
1. **SKU顺序优化**：对每个任务（包括新任务和已有任务）进行TSP优化
2. **新任务插入位置**：尝试多个候选位置，选择最优的

❌ **不优化的内容**：
1. **已有任务顺序**：已有任务（allocated_tasks）的相对顺序保持不变
2. **任务重排**：不会重新排列已有任务的顺序

**示例**：
```


分配阶段会尝试：
- [D, A, B, C] ✅ 会尝试
- [A, D, B, C] ✅ 会尝试
- [A, B, D, C] ✅ 会尝试
- [A, B, C, D] ✅ 会尝试

但不会尝试：
- [A, C, B, D] ❌ 不会重排已有任务
- [B, A, C, D] ❌ 不会重排已有任务
```

---

## 任务优化阶段

### 1. 优化触发时机

所有新任务分配完成后，系统进入优化阶段：

```python
def optimize_all_workers_tasks():
    for worker in workers:
        优化该员工的所有任务
```

### 2. 优化流程

```python
def optimize_worker_tasks(worker):
    # 1. 分离任务
    urgent_tasks = [task for task in worker.allocated_tasks if task.is_urgent()]
    non_urgent_tasks = [task for task in worker.allocated_tasks if not task.is_urgent()]

    # 2. 获取起点
    start_grid = worker.get_current_grid_location()
    current_grid = start_grid

    # 3. 处理紧急任务（保持原有顺序）
    for task in urgent_tasks:
        优化任务内的SKU顺序（TSP）
        更新current_grid为任务结束位置
        optimized_tasks.append(task)

    # 4. 处理非紧急任务（按距离排序）
    计算每个非紧急任务到current_grid的距离
    按距离从小到大排序

    for task in sorted_non_urgent_tasks:
        优化任务内的SKU顺序（TSP）
        更新current_grid为任务结束位置
        optimized_tasks.append(task)

    return optimized_tasks
```

### 3. 任务优化阶段的优化内容

✅ **优化的内容**：
1. **任务顺序重排**：
   - 紧急任务：保持原有顺序（不打断紧急任务的执行顺序）
   - 非紧急任务：按照距离排序（选择最近的任务先执行）

2. **SKU顺序优化**：
   - 对每个任务进行TSP优化
   - 找到最短拣货路径

**示例**：
```
优化前员工任务：[紧急A, 普通B, 普通C, 普通D]

优化后：
- 紧急A：保持位置不变
- 普通B、C、D：根据距离重新排序

假设距离：
- 员工当前位置 → B: 10米
- 员工当前位置 → C: 15米
- 员工当前位置 → D: 8米

优化后顺序：[紧急A, 普通D, 普通B, 普通C]
```

---

## 核心算法

### 1. TSP（旅行商问题）优化

#### 目的
优化单个任务内多个SKU的拣货顺序，找到最短路径。

#### 算法流程

```python
def optimize_sku_order_in_task(task, start_grid):
    """
    task: 任务对象，包含多个SKU
    start_grid: 起点位置（员工当前位置），格式为 (row, col)

    返回: (SKU顺序索引, 最短距离)
    例如: ([2, 0, 1, 3], 45.6) 表示按SKU2→0→1→3的顺序拣货，总距离45.6米
    """

    # 特殊情况处理
    if SKU数量 <= 1:
        直接返回距离

    # 1. 坐标转换
    SKU真实坐标 → 网格坐标 (col, row)
    网格坐标 → 修正到可通行位置
    转换格式 → (row, col)

    # 2. 构建距离矩阵
    all_points = [start_grid] + [SKU1_grid, SKU2_grid, ..., SKU_n_grid]
    distance_matrix = [[0] * n for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i != j:
                distance_matrix[i][j] = A*算法计算距离(all_points[i], all_points[j])

    # 3. TSP求解
    tsp_solver = TSPSolver(distance_matrix)
    route, total_distance = tsp_solver.solve()
    # route格式: [0, 3, 1, 4, 2]
    # 0表示起点，3,1,4,2表示SKU索引

    # 4. 提取SKU顺序
    sku_order = [node - 1 for node in route if node > 0]

    # 5. 修正距离（减去返回起点的距离）
    total_distance = total_distance - distance(last_sku, start)

    return sku_order, total_distance
```

#### TSP起点说明

**重要**：TSP的起点是**动态计算的员工当前位置**

```
TSP起点 = worker.get_current_grid_location()
    ↓
1. 查找最后一个"已完成"任务的完成位置
   - 如果找到：返回该位置 (predict_complete_location_x, predict_complete_location_y)
2. 否则：返回PDA位置 (pda_location_x, pda_location_y)
    ↓
转换为网格坐标并修正
    ↓
作为TSP起点（节点0）
```

**为什么有时总是显示PDA位置？**
- 因为从JSON加载的任务状态不是"已完成"
- 可能是："未开始"、"执行中"、"待分配"、"已分配"
- 这些状态的任务不会被 `get_current_location()` 识别

### 2. A*路径规划

#### 目的
计算两点之间的最短路径距离（考虑障碍物）。

#### 启发函数
```python
heuristic = 曼哈顿距离 = |x1 - x2| + |y1 - y2|
```

#### 距离计算
```python
distance = (path_length - 1) × meters_per_grid_step
```

---

## 数据流程

### 1. 任务分配阶段数据流

```
新任务 (new_task)
    ↓
TaskAllocator.allocate_task(workers, new_task)
    ↓
for each worker:
    ├─ worker.get_current_grid_location() → 获取起点
    ├─ calculate_best_insertion() 或 calculate_urgent_insertion()
    │   ├─ 创建临时任务列表
    │   ├─ calculate_total_completion()
    │   │   └─ for each task:
    │   │       └─ task_optimizer.calculate_task_completion_time()
    │   │           ├─ optimize_sku_order_in_task() → TSP优化SKU
    │   │           ├─ 计算移动时间 = 距离 / 1.2
    │   │           └─ 计算拣货时间 = Σ(sku_pick_speed × inspected_quantity)
    │   └─ 返回 (insert_pos, total_time, total_distance)
    └─ 记录评估结果
    ↓
选择最优员工（根据策略）
    ↓
update_worker_schedule() → 插入任务到员工队列
```

### 2. 任务优化阶段数据流

```
所有任务分配完成
    ↓
TaskAllocator.optimize_all_workers_tasks()
    ↓
for each worker:
    ├─ 分离紧急/非紧急任务
    ├─ worker.get_current_grid_location() → 获取起点
    ├─ 处理紧急任务（保持顺序）
    │   └─ optimize_sku_order_in_task() → TSP优化
    ├─ 处理非紧急任务（按距离排序）
    │   ├─ 计算到当前点的距离
    │   ├─ 按距离排序
    │   └─ for each task:
    │       └─ optimize_sku_order_in_task() → TSP优化
    └─ 返回优化后的任务列表
    ↓
计算预测时间和位置
    ↓
输出结果到JSON文件
```

### 3. SKU数量与DEBUG输出

| SKU数量 | TSP计算 | DEBUG输出 |
|---------|---------|-----------|
| 0个 | ❌ 不执行 | ✅ "任务无SKU，距离 = 0.0 米" |
| 1个 | ❌ 不执行 | ✅ "任务 XXX 只有 1 个SKU，跳过TSP优化"<br>✅ "单SKU距离 = XX.XX 米" |
| 2+个 | ✅ 执行TSP | ✅ "TSP route = [0, 2, 1, ...]"<br>✅ "TSP total_distance_cm = ..."<br>✅ "路径段 0->2: ...米"<br>✅ "修正后距离 = ..." |

---

## 关键参数配置

### 1. 分配策略

```python
# config.py
ALLOCATION_STRATEGY = 'load_balance'  # 或 'distance_first'
```

- `load_balance`（默认）：负载均衡，选择完成时间最短的员工
- `distance_first`：距离优先，选择总移动距离最短的员工

### 2. 移动速度

```python
MOVEMENT_SPEED = 1.2  # 米/秒
```

用于计算：移动时间 = 距离 / 1.2

### 3. 拣货时间

```python
拣货时间 = Σ(sku_pick_speed × inspected_quantity)
```

- `sku_pick_speed`：每包拣货时间（秒）
- `inspected_quantity`：包数

### 4. 紧急任务惩罚

```python
URGENT_TASK_PENALTY = 1000  # 惩罚系数
```

如果紧急任务预计超期完成：
```
惩罚时间 = 超期秒数 × URGENT_TASK_PENALTY
总时间 = 原时间 + 惩罚时间
```

### 5. 候选位置筛选阈值

```python
if 任务数 <= 5:
    尝试所有位置
else:
    只尝试候选位置（两端 + 最接近任务的前后）
```

---

## 关键文件说明

### 核心模块

| 文件 | 功能 |
|------|------|
| `core/task_allocator.py` | 任务分配器，负责选择员工和插入位置 |
| `core/task_optimizer.py` | 任务优化器，负责TSP优化和顺序计算 |
| `core/path_finder.py` | 路径规划器，使用A*算法计算距离 |
| `core/tsp_solver.py` | TSP求解器，使用OR-Tools求解旅行商问题 |
| `models/worker.py` | 员工模型，管理员工信息和任务队列 |
| `models/task.py` | 任务模型，管理任务信息和SKU列表 |
| `utils/map_converter.py` | 坐标转换器，真实坐标 ↔ 网格坐标 |
| `utils/coordinate_fixer.py` | 坐标修正器，修正到可通行位置 |

### 数据文件

| 文件 | 说明 |
|------|------|
| `data/workers.json` | 输入：员工数据（含已分配任务） |
| `data/tasks.json` | 输入：新任务列表 |
| `data/output_assignment.json` | 输出：分配结果（最新副本） |
| `data/archive/*/output_assignment.json` | 输出：历史分配结果（带时间戳归档） |
| `data/view_metrics.json` | 输出：汇总指标 |

---

## 总结

### 任务分配阶段
- ✅ 优化新任务的插入位置
- ✅ 优化每个任务的SKU顺序（TSP）
- ❌ 不重排已有任务顺序
- 目标：快速找到合理的分配方案

### 任务优化阶段
- ✅ 重排非紧急任务顺序（按距离）
- ✅ 保持紧急任务顺序不变
- ✅ 优化每个任务的SKU顺序（TSP）
- 目标：获得全局最优的任务执行顺序

### 两个阶段的关系
```
分配阶段（增量优化）
    ↓
所有任务分配完成
    ↓
优化阶段（全局优化）
```

**设计理念**：
1. 分配阶段追求效率，快速找到可接受的方案
2. 优化阶段追求质量，找到全局最优解
3. 两阶段分离，避免重复计算，提高性能
