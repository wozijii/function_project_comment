"""
坐标修正类
修正人员位置到最近的可通行位置
"""
from typing import Tuple
from collections import deque
import numpy as np

def snap_to_nearest_free(start_c: int, start_r: int, map_file_path: str = './map.txt') -> Tuple[int, int]:
    """
    修正位置到最近的可通行位置
    
    Args:
        start_c: 起始列坐标
        start_r: 起始行坐标
        map_file_path: 地图文件路径
        
    Returns:
        Tuple[int, int]: 修正后的(col, row)坐标
    """
    try:
        grid = np.loadtxt(map_file_path, dtype=int)
    except Exception as e:
        print(f"错误: 无法加载地图文件 {map_file_path}: {e}")
        return (start_c, start_r)
    
    rows, cols = grid.shape
    
    # 首先检查并修正边界
    start_r = max(0, min(start_r, rows - 1))
    start_c = max(0, min(start_c, cols - 1))
    
    # 如果起始位置可通行，直接返回
    if grid[start_r][start_c] == 0:
        return (start_c, start_r)
    
    # BFS搜索最近的可通行位置
    from collections import deque
    
    queue = deque()
    visited = [[False] * cols for _ in range(rows)]
    queue.append((start_r, start_c))
    visited[start_r][start_c] = True
    
    # 搜索方向：右、下、左、上、四个对角线
    directions = [
        (0, 1), (1, 0), (0, -1), (-1, 0),  # 上下左右
        (1, 1), (1, -1), (-1, 1), (-1, -1)  # 对角线
    ]
    
    while queue:
        r, c = queue.popleft()
        
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            
            # 检查边界
            if 0 <= nr < rows and 0 <= nc < cols and not visited[nr][nc]:
                visited[nr][nc] = True
                
                if grid[nr][nc] == 0:
                    # 找到可通行位置
                    return (nc, nr)
                
                queue.append((nr, nc))
    
    # 如果BFS没有找到，尝试在整个地图中寻找任意可通行位置
    print(f"警告: BFS未找到可通行位置，尝试全局搜索...")
    
    # 首先尝试起点周围更大的范围
    search_radius = min(10, rows, cols)
    for dr in range(-search_radius, search_radius + 1):
        for dc in range(-search_radius, search_radius + 1):
            nr, nc = start_r + dr, start_c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 0:
                print(f"  在半径{search_radius}内找到可通行位置: ({nc}, {nr})")
                return (nc, nr)
    
    # 如果还是没有，在整个地图中查找
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 0:
                print(f"  全局搜索找到可通行位置: ({c}, {r})")
                return (c, r)
    
    # 如果整个地图都没有可通行位置（不可能的情况）
    print(f"严重错误: 整个地图都没有可通行位置!")
    return (start_c, start_r)