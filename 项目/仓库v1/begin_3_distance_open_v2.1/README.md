更新过程：

- 1. 不更新的人员任分配

- 2. 更新人员任务分配

warehouse_optimization/
├── main.py                      * 主程序入口
├── config.py                    * 配置文件
├── requirements.txt             * 依赖包列表
├── map.txt                      * 仓库地图文件
│
├── core/                        * 核心算法模块
│   ├── __init__.py
│   ├── path_finder.py          * A*路径规划算法
│   ├── task_optimizer.py       * 任务优化与排序算法
│   ├── task_allocator.py       * 任务分配算法
│   └── tsp_solver.py           * TSP问题求解器(使用or-tools)
│
├── models/                      * 数据模型模块
│   ├── __init__.py
│   ├── worker.py               * 拣货人员模型
│   ├── task.py                 * 任务模型
│   ├── sku.py                  * SKU商品模型
│   └── warehouse.py            * 仓库地图模型
│
├── utils/                       * 工具函数模块
│   ├── __init__.py
│   ├── map_converter.py        * 坐标转换类(已有)
│   ├── coordinate_fixer.py     * 坐标修正类(已有)
│   ├── time_utils.py           * 时间处理工具
│   ├── distance_calculator.py  * 距离计算工具
│   └── output_formatter.py     * 输出格式化工具
│
├── data/                        * 数据目录
│   ├── input_example.json      * 输入数据示例
│   └── output_example.json     * 输出数据示例

主要流程：

- 加载配置项

  - 地图数据
  - 全局变量（真实地图大小，文件输入输出路径）

- 加载员工数据（load_workers_data）

  - 获取基本信息
  - 获取已经已分配未完成的任务数据（就是加载输入进来的东西）

- 加载任务数据

  - 获取输入的所有的任务信息存起来
  - 先获取sku，再将skulist存到task这样一个任务就读取完毕

- 处理任务分配（将任务分配给最先完成的员工）

  - 处理分配（遍历任务，传入员工列表和当前任务当任务分配器进行任务的分配allocate_task）

    ```python
    allocation_result = self.task_allocator.allocate_task(self.workers, task)
    ```

  - 任务分配器遍历所有的员工，查看每个员工完成当前任务所需要的最短时间，谁最快就分配给谁（其中需要查看任务是否紧急）-->这个其实也算是一种模拟测试

    - 紧急任务（插到员工已分配未开始的最前面进行时间的计算看看谁先完成）calculate_urgent_insertion
      - 判断是否有正在执行的任务，要是有则在它的后面，没有就在第一个
      - 获取员工位置作为起点，然后创建临时任务表，将当前这个任务放进去（上一步已经计算好了插入的位置）， 计算完成所有任务的时间和距离（这里面是将整个任务表进行一起算最优）
      - 通过任务优化器task_optimizer优化所有的顺序，，优化sku顺序optimize_sku_order_in_task
      - 通过A*计算所有的距离，然后使用TSP优化器求解出最短最快的一种方式
    - 不紧急差不多只是插入的方式是不同的
      - 插入的方式是每一种都插入一遍

  - 任务开始

    - 跟测试的差不多分组显示出不同员工的任务情况······