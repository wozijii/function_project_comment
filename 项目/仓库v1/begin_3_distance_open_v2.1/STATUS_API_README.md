# 项目状态监控接口使用文档

## 概述

为解决前端业务部门排查项目运行慢的问题,本项目新增了状态监控接口。前端可以实时查询后端的任务分配和仿真的执行状态。

## 接口列表

### 1. 获取全部状态 - `GET /status`

获取 process 和 simulate 的完整运行状态。

**请求示例:**
```bash
curl http://localhost:8000/status
```

**响应示例:**
```json
{
  "success": true,
  "data": {
    "process": {
      "status": "任务分配中",
      "start_time": "2025-12-28 14:30:00",
      "end_time": null,
      "current_task_id": "T001",
      "current_worker_name": "张三",
      "task_progress": 5,
      "total_tasks": 20,
      "worker_optimization_progress": 0,
      "total_workers": 5,
      "error_message": null,
      "simulate_id": 1,
      "event": "任务分配中: 任务 T001 → 张三 (5/20)"
    },
    "simulate": {
      "status": "空闲",
      "start_time": null,
      "end_time": null,
      "current_frame": null,
      "total_frames": null,
      "progress_percent": 0.0,
      "error_message": null,
      "event": "等待仿真"
    },
    "timestamp": "2025-12-28 14:30:05"
  }
}
```

### 2. 获取 Process 状态 - `GET /status/process`

仅获取任务分配( `/process` 接口)的状态。

**请求示例:**
```bash
curl http://localhost:8000/status/process
```

**响应示例:**
```json
{
  "success": true,
  "data": {
    "status": "优化员工顺序中",
    "start_time": "2025-12-28 14:30:00",
    "end_time": null,
    "current_task_id": null,
    "current_worker_name": "李四",
    "task_progress": 20,
    "total_tasks": 20,
    "worker_optimization_progress": 3,
    "total_workers": 5,
    "error_message": null,
    "simulate_id": 1,
    "event": "优化员工顺序中 (3/5)"
  }
}
```

### 3. 获取 Simulate 状态 - `GET /status/simulate`

仅获取仿真( `/simulate` 接口)的状态。

**请求示例:**
```bash
curl http://localhost:8000/status/simulate
```

**响应示例:**
```json
{
  "success": true,
  "data": {
    "status": "渲染视频中",
    "start_time": "2025-12-28 14:35:00",
    "end_time": null,
    "current_frame": 150,
    "total_frames": 500,
    "progress_percent": 30.0,
    "error_message": null,
    "event": "渲染视频中: 150/500 帧 (30.0%)"
  }
}
```

## 状态值说明

### Process 状态 (任务分配)

| 状态值 | 说明 | event 字段示例 |
|--------|------|----------------|
| `空闲` | 未运行 | "等待任务" |
| `加载数据中` | 正在加载 workers.json 和 tasks.json | "加载员工和任务数据中" |
| `任务分配中` | 正在分配任务给员工 | "任务分配中: 任务 T001 → 张三 (5/20)" |
| `优化员工顺序中` | 正在优化员工的任务顺序 | "优化员工顺序中 (3/5)" |
| `保存结果中` | 正在保存输出文件 | "保存分配结果中" |
| `完成` | 任务分配成功完成 | "任务分配完成" |
| `错误` | 发生错误 | "错误: 文件不存在" |
| `已停止` | 被用户停止 | "任务分配已停止" |

### Simulate 状态 (仿真)

| 状态值 | 说明 | event 字段示例 |
|--------|------|----------------|
| `空闲` | 未运行 | "等待仿真" |
| `准备数据中` | 正在准备仿真数据 | "准备仿真数据中" |
| `渲染视频中` | 正在生成 MP4 视频 | "渲染视频中: 150/500 帧 (30.0%)" |
| `完成` | 仿真完成 | "仿真完成" |
| `错误` | 发生错误 | "错误: 渲染超时" |
| `已停止` | 被用户停止 | "仿真已停止" |

## 前端集成示例

### Vue.js 示例

```javascript
// 使用轮询方式获取状态 (每秒查询一次)
async function pollStatus() {
  const interval = setInterval(async () => {
    try {
      const response = await fetch('http://localhost:8000/status');
      const result = await response.json();

      if (result.success) {
        const { process, simulate, timestamp } = result.data;

        console.log('查询时间:', timestamp);
        console.log('Process状态:', process.status);
        console.log('Process事件:', process.event);
        console.log('Simulate状态:', simulate.status);

        // 根据状态更新 UI
        updateStatusDisplay(process, simulate);

        // 如果都完成了,停止轮询
        if (process.status === '完成' || process.status === '错误' || process.status === '已停止') {
          clearInterval(interval);
        }
      }
    } catch (error) {
      console.error('获取状态失败:', error);
    }
  }, 1000); // 每1秒查询一次
}

function updateStatusDisplay(process, simulate) {
  // 更新 process 状态显示
  document.getElementById('process-status').textContent = process.status;
  document.getElementById('process-event').textContent = process.event;

  // 显示进度条
  if (process.total_tasks > 0) {
    const progress = (process.task_progress / process.total_tasks) * 100;
    document.getElementById('process-progress').style.width = progress + '%';
  }

  // 更新 simulate 状态显示
  document.getElementById('simulate-status').textContent = simulate.status;
  document.getElementById('simulate-event').textContent = simulate.event;

  // 显示视频渲染进度
  if (simulate.progress_percent > 0) {
    document.getElementById('simulate-progress').style.width = simulate.progress_percent + '%';
  }
}

// 启动轮询
pollStatus();
```

### React 示例

```jsx
import { useState, useEffect } from 'react';

function StatusMonitor() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch('http://localhost:8000/status');
        const result = await response.json();
        if (result.success) {
          setStatus(result.data);
        }
      } catch (error) {
        console.error('获取状态失败:', error);
      } finally {
        setLoading(false);
      }
    };

    // 立即查询一次
    fetchStatus();

    // 设置定时轮询
    const interval = setInterval(fetchStatus, 1000);

    // 清理函数
    return () => clearInterval(interval);
  }, []);

  if (loading || !status) {
    return <div>加载中...</div>;
  }

  const { process, simulate, timestamp } = status;

  return (
    <div className="status-monitor">
      <h3>项目运行状态</h3>
      <p>查询时间: {timestamp}</p>

      <div className="status-section">
        <h4>任务分配 (Process)</h4>
        <p>状态: {process.status}</p>
        <p>事件: {process.event}</p>
        {process.total_tasks > 0 && (
          <progress value={process.task_progress} max={process.total_tasks} />
        )}
      </div>

      <div className="status-section">
        <h4>仿真 (Simulate)</h4>
        <p>状态: {simulate.status}</p>
        <p>事件: {simulate.event}</p>
        {simulate.progress_percent > 0 && (
          <progress value={simulate.progress_percent} max={100} />
        )}
      </div>
    </div>
  );
}

export default StatusMonitor;
```

## 错误处理

所有接口在发生错误时都会返回以下格式:

```json
{
  "success": false,
  "error": "错误描述信息"
}
```

常见错误:
- `500`: 状态追踪器内部错误
- 网络错误: 后端服务未启动

## 注意事项

1. **轮询频率**: 建议前端每 1-2 秒查询一次状态,过于频繁会增加服务器负担
2. **状态重置**: 每次调用 `/process` 或 `/simulate` 接口时会重置对应的状态追踪器
3. **线程安全**: 状态追踪器使用线程锁,支持并发查询
4. **停止信号**: 当用户点击停止按钮时,状态会更新为"已停止"

## 开发和测试

### 本地测试

```bash
# 1. 启动后端服务
python app.py

# 2. 在另一个终端测试状态查询接口
curl http://localhost:8000/status
curl http://localhost:8000/status/process
curl http://localhost:8000/status/simulate

# 3. 触发一个任务分配
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d @data/test_payload.json

# 4. 实时查看状态变化
watch -n 1 'curl -s http://localhost:8000/status | jq'
```

### Python 测试脚本

```python
import requests
import time
import json

def test_status_monitoring():
    """测试状态监控功能"""
    base_url = "http://localhost:8000"

    # 1. 检查初始状态
    print("1. 初始状态:")
    response = requests.get(f"{base_url}/status")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

    # 2. 触发任务分配 (异步)
    print("\n2. 触发任务分配...")
    with open('data/test_payload.json', 'r') as f:
        payload = json.load(f)

    # 使用线程池异步请求
    import threading
    def run_process():
        try:
            requests.post(f"{base_url}/process", json=payload, timeout=600)
        except Exception as e:
            print(f"Process 请求异常: {e}")

    thread = threading.Thread(target=run_process)
    thread.start()

    # 3. 轮询状态
    print("\n3. 实时监控状态:")
    for i in range(60):  # 最多监控60秒
        time.sleep(1)
        response = requests.get(f"{base_url}/status/process")
        data = response.json()['data']

        print(f"[{i+1}s] {data['status']} - {data['event']}")

        # 如果完成则退出
        if data['status'] in ['完成', '错误', '已停止']:
            break

    thread.join()
    print("\n测试完成!")

if __name__ == "__main__":
    test_status_monitoring()
```

## 文件清单

新增/修改的文件:
- `status_tracker.py` - 状态追踪核心模块
- `main.py` - 集成状态追踪
- `app.py` - 添加状态查询接口
- `STATUS_API_README.md` - 本文档
