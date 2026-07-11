# visualization.py
import matplotlib
matplotlib.use('Agg')  # 使用非交互后端
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Polygon, Circle, Rectangle
from typing import List, Dict, Tuple
import numpy as np
import imageio_ffmpeg

# 设置 ffmpeg 路径
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
matplotlib.animation.FFMpegWriter._base_cmd = [FFMPEG_EXE]

# 设置字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei']
matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['axes.unicode_minus'] = False

class Visualization:
    def __init__(self, map_grid: np.ndarray, workers: List, colors: List[str], map_converter=None, minimal: bool = False):
        """Initialize visualization"""
        self.map_grid = map_grid
        self.workers = workers
        self.colors = colors
        self.fig, self.ax = plt.subplots(figsize=(14, 10))
        
        # Set style
        plt.style.use('seaborn-v0_8-whitegrid')
        
        # Store references to dynamic elements
        self.worker_patches = []
        self.worker_texts = []
        self.coordinate_texts = []
        self.stats_text = None
        self.start_time = None
        # store map converter or resolution if provided so stats use real distances
        self.map_converter = map_converter
        if map_converter is not None:
            try:
                self.res_x = getattr(map_converter, 'res_x', 1.0)
                self.res_y = getattr(map_converter, 'res_y', 1.0)
            except Exception:
                self.res_x = 1.0
                self.res_y = 1.0
        else:
            self.res_x = 1.0
            self.res_y = 1.0

        # minimal mode: only draw workers as big dots and minimal overlay
        self.minimal = bool(minimal)

        self._init_start_time()
    
    def init_animation(self, frames: List[List[Dict]]) -> List:
        """Initialize animation"""
        self.ax.clear()
        self.worker_patches = []
        
        self.worker_texts = []
        self.coordinate_texts = []
        
        height, width = self.map_grid.shape
        
        # Create custom colormap: 0=white (aisle), 1=black (obstacle)
        custom_cmap = plt.cm.colors.ListedColormap(['white', 'black'])
        
        # Draw map background - white aisles, black obstacles
        self.ax.imshow(self.map_grid, cmap=custom_cmap, 
                      vmin=0, vmax=1,  # Ensure only 0 and 1 values
                      origin='lower',
                      interpolation='nearest',
                      alpha=0.9)
        
        # Add grid lines
        self.ax.grid(True, which='both', color='lightgray', 
                    linestyle=':', linewidth=0.5, alpha=0.7)
        
        # Set axis limits
        self.ax.set_xlim(-0.5, width - 0.5)
        self.ax.set_ylim(-0.5, height - 0.5)
        
        # Draw task points (goods locations) with worker colors
        self.draw_task_points()
        
        # Draw starting points
        self.draw_start_points()
        
        # Set title and labels (use smaller pad so we can place stats above)
        self.ax.set_title('Picking Sequence Simulation', fontsize=18, fontweight='bold', pad=8)
        self.ax.set_xlabel('Grid Column Coordinate', fontsize=12, fontweight='bold')
        self.ax.set_ylabel('Grid Row Coordinate', fontsize=12, fontweight='bold')
        
        # no legend as per user request
        
        # Add map information
        self.add_map_info(width, height)
        # Draw overlay texts if provided
        try:
            self._draw_overlay()
        except Exception:
            pass
        
        # leave extra top margin so figure-level texts (stats) are visible
        try:
            self.fig.subplots_adjust(top=0.75)
        except Exception:
            pass

        return []
    
    def draw_task_points(self):
        """Draw task points (goods locations) as triangles with worker colors - larger size"""
        # Always draw SKU/task points even in minimal mode
        for worker in self.workers:
            color = self.colors[worker.color_idx % len(self.colors)]

            # 获取原始位置列表（如果存在）
            original_positions = getattr(worker, 'original_positions', [])

            # 绘制每个任务点
            for i, (point_col, point_row) in enumerate(worker.path):
                # 如果有原始位置信息，且原始位置与修正位置不同
                if i < len(original_positions):
                    original_col, original_row = original_positions[i]

                    # 只有当原始位置和修正位置不同时才绘制连接线和原始点
                    if (original_col, original_row) != (point_col, point_row):
                        # 绘制连接线（从原始位置到修正位置）
                        from matplotlib.lines import Line2D
                        connection_line = Line2D(
                            [original_col, point_col],
                            [original_row, point_row],
                            color='red',
                            linewidth=1.5,
                            linestyle='--',
                            alpha=0.6,
                            zorder=3
                        )
                        self.ax.add_line(connection_line)

                        # 绘制原始位置点（圆圈，透明度较高）
                        original_circle = Circle(
                            (original_col, original_row),
                            0.5,
                            facecolor='red',
                            edgecolor='darkred',
                            alpha=0.6,  # 原始点透明度不太透明
                            linewidth=1.5,
                            zorder=4
                        )
                        self.ax.add_patch(original_circle)

                # 绘制修正后的任务点（三角形）
                task_triangle = Polygon([
                    [point_col, point_row + 0.8],
                    [point_col - 0.8, point_row - 0.8],
                    [point_col + 0.8, point_row - 0.8]
                ], facecolor=color, alpha=0.8, zorder=5)
                self.ax.add_patch(task_triangle)
    
    def draw_start_points(self):
        """Draw starting points - only triangle, no label"""
        if self.minimal:
            return
        for worker in self.workers:
            color = self.colors[worker.color_idx % len(self.colors)]
            start_col, start_row = worker.start
            start_triangle = Polygon([
                [start_col, start_row + 0.6],
                [start_col - 0.6, start_row - 0.6],
                [start_col + 0.6, start_row - 0.6]
            ], facecolor=color, edgecolor='black', 
               alpha=0.9, linewidth=2, zorder=5)
            self.ax.add_patch(start_triangle)
    
    def add_legend(self):
        """Add legend with red color"""
        from matplotlib.patches import Patch
        from matplotlib.lines import Line2D
        
        # Create custom legend handles - all using red color
        legend_elements = [
            Patch(facecolor='white', edgecolor='red', label='Aisle (Passable)'),
            Patch(facecolor='black', edgecolor='red', label='Obstacle (Impassable)'),
            Patch(facecolor='red', alpha=0.9, label='Goods Location'),
            Line2D([0], [0], marker='^', color='red', markerfacecolor='red',
                  markersize=12, label='Worker Start'),
            # Line2D([0], [0], color='red', linewidth=2, label='Travel Path')
        ]
        
        # Create legend with red frame
        legend = self.ax.legend(handles=legend_elements, loc='upper right', 
                               fontsize=10, framealpha=0.95, fancybox=True)
        
        # Set legend frame to red
        legend.get_frame().set_edgecolor('red')
        legend.get_frame().set_linewidth(2)
        
        # Set legend text color to dark red for better visibility
        for text in legend.get_texts():
            text.set_color('darkred')
            text.set_fontweight('bold')
    
    def add_map_info(self, width: int, height: int):
        """Add map information"""
        total_goods = sum(len(w.path) for w in self.workers)
        info_text = f"Map Size: {height}×{width}\n"
        info_text += f"Workers: {len(self.workers)}\n"
        info_text += f"Total Goods: {total_goods}"
        
        self.ax.text(0.02, 0.98, info_text,
                    transform=self.ax.transAxes,
                    fontsize=10,
                    verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='lightgray', 
                             edgecolor='red', alpha=0.8, linewidth=1.5))
    
    def update_animation(self, frame_idx: int, frames: List[List[Dict]]) -> List:
        """Update animation frame"""
        if frame_idx >= len(frames):
            return []
        
        # Clear previous dynamic elements
        self.clear_previous_elements()
        
        frame_data = frames[frame_idx]
        
        # Draw each worker
        for data in frame_data:
            if data['type'] == 'worker':
                self.draw_worker(data, frame_idx, len(frames))

        # draw aggregated stats once per frame
        try:
            self._draw_stats(frame_idx, frames_total=len(frames))
        except Exception:
            pass

        return []
    
    def draw_worker(self, data: Dict, frame_idx: int, total_frames: int):
        """Draw single worker and their path"""
        color = self.colors[data['color_idx'] % len(self.colors)]
        col, row = data['pos']
        # Traveling path visualization removed as requested
        if self.minimal:
            # Draw single large dot for worker and no labels (increased size)
            dot = Circle((col, row), 1.6, facecolor=color, edgecolor='black', linewidth=1.5, zorder=12)
            self.ax.add_patch(dot)
            self.worker_patches.append(dot)
            # Update title to show progress
            progress = (frame_idx + 1) / total_frames * 100
            self.ax.set_title(f'Picking Sequence Simulation - Progress: {progress:.1f}% ({frame_idx + 1}/{total_frames} frames)', 
                     fontsize=16, fontweight='bold', pad=8)
            return

        # Draw current worker position (triangle)
        worker_triangle = Polygon([
            [col, row + 0.6],
            [col - 0.6, row - 0.6],
            [col + 0.6, row - 0.6]
        ], facecolor=color, edgecolor='black', 
           alpha=0.95, linewidth=2, zorder=10)
        self.ax.add_patch(worker_triangle)
        self.worker_patches.append(worker_triangle)
        
        
        # Update title to show progress
        progress = (frame_idx + 1) / total_frames * 100
        self.ax.set_title(f'Picking Sequence Simulation - Progress: {progress:.1f}% ({frame_idx + 1}/{total_frames} frames)', 
                 fontsize=16, fontweight='bold', pad=8)
        
    
    def clear_previous_elements(self):
        """Clear previous dynamic elements"""
        # No path lines to clear (removed)
        
        # Clear previous worker triangles
        for patch in self.worker_patches:
            patch.remove()
        self.worker_patches = []
        
        # Clear previous texts
        for text in self.worker_texts + self.coordinate_texts:
            try:
                text.remove()
            except Exception:
                pass
        self.worker_texts = []
        self.coordinate_texts = []
        # clear previous stats text
        if self.stats_text is not None:
            try:
                self.stats_text.remove()
            except Exception:
                pass
            self.stats_text = None
    
    def create_animation(self, frames: List[List[Dict]], output_file: str,
                        frame_interval: int = 100, overlay_texts: List[str] = None) -> None:
        """Create and save animation as MP4 using imageio-ffmpeg"""
        import imageio
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        print(f"Starting animation creation, total {len(frames)} frames...")

        # store overlay texts (optional)
        self.overlay_texts = overlay_texts
        # record frame interval for stats timing
        self.frame_interval = frame_interval

        # 获取 ffmpeg 路径
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        print(f"Using imageio-ffmpeg from: {ffmpeg_path}")

        # 初始化动画背景（第一帧）
        print("Initializing animation background...")
        self.init_animation(frames)

        # 生成所有帧图像
        print("Generating frames...")
        frame_images = []
        for i in range(len(frames)):
            self.update_animation(i, frames)
            # 使用 savefig 保存到内存
            from io import BytesIO
            buf = BytesIO()
            self.fig.savefig(buf, format='png', dpi=100, bbox_inches='tight', pad_inches=0.1)
            buf.seek(0)
            from PIL import Image
            img = np.array(Image.open(buf))
            buf.close()
            frame_images.append(img)
            print(f"  Generated frame {i+1}/{len(frames)}")

        # 确保输出文件是 .mp4 后缀
        if not output_file.lower().endswith('.mp4'):
            mp4_file = output_file.replace('.gif', '.mp4') if '.gif' in output_file else output_file + '.mp4'
        else:
            mp4_file = output_file

        # 使用 imageio 保存为 MP4
        print(f"Saving MP4 to: {mp4_file}...")
        try:
            # 计算 FPS
            fps = int(1000 / frame_interval) if frame_interval > 0 else 10
            print(f"Using FPS: {fps}")

            # 使用 imageio v3 API 保存 MP4 (H.264 编码)
            with imageio.imopen(mp4_file, "w", plugin="pyav", codec="h264") as file:
                for img in frame_images:
                    file.write(img, fps=fps)
            print(f"OK MP4 saved successfully!")
        except Exception as e:
            print(f"Error MP4 保存失败：{e}")
            # 尝试使用旧 API
            try:
                writer = imageio.get_writer(mp4_file, fps=fps,
                                           codec='libx264',
                                           ffmpeg_params=['-preset', 'medium', '-crf', '23',
                                                         '-pix_fmt', 'yuv420p'])
                for img in frame_images:
                    writer.append_data(img)
                writer.close()
                print(f"OK MP4 saved successfully (legacy API)!")
            except Exception as e2:
                print(f"MP4 保存失败 (legacy): {e2}")

        plt.close(self.fig)

    # 在初始化时如果有 overlay_texts 就绘制到左上角
    def _draw_overlay(self):
        if not hasattr(self, 'overlay_texts') or not self.overlay_texts:
            return
        # Draw overlay texts in the figure top-left (outside the map, near title)
        # Use figure coordinates so text appears relative to the whole figure
        x_fig = 0.02
        y_fig_top = 0.96
        line_spacing = 0.04
        for idx, line in enumerate(self.overlay_texts):
            y = y_fig_top - idx * line_spacing
            # use fig.text to place outside axes (near title left)
            self.fig.text(x_fig, y, line,
                          fontsize=11, color='black', ha='left', va='top',
                          bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='black'))

    def _init_start_time(self):
        """Try to read the earliest CONFIRMEDAT from input data as simulation start time"""
        try:
            import json, os
            p = os.path.join(os.getcwd(), 'input_data_old', 'old_data.json')
            if not os.path.exists(p):
                # try parent view folder
                p = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'input_data_old', 'old_data.json')
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f)
            times = []
            from datetime import datetime
            for w in data:
                for task in w.get('path', []):
                    t = task.get('CONFIRMEDAT') or task.get('confirmedAt') or task.get('confirmed_at')
                    if t:
                        try:
                            times.append(datetime.strptime(t, '%Y-%m-%d %H:%M:%S'))
                        except Exception:
                            pass
            if times:
                self.start_time = min(times)
        except Exception:
            self.start_time = None

    def _draw_stats(self, frame_idx: int, frames_total: int):
        """Draw per-worker statistics above the title using current frame data"""
        # Build a nicely aligned table-like string: header + rows
        # Columns: person_id | time | over_num | all_num | now_distance(m) | cost_time(s)
        # use stored resolutions from init (provided by SimulationEngine.map_converter)
        res_x = getattr(self, 'res_x', 1.0)
        res_y = getattr(self, 'res_y', 1.0)

        # Column widths for neat alignment (monospace font used)
        col_w = {
            'id': 14,
            'time': 10,
            'over': 9,
            'all': 7,
            'dist': 14,
            'cost': 10
        }

        header = f"{ 'person_id':<{col_w['id']} }{ 'time':<{col_w['time']} }{ 'over_num':>{col_w['over']} }{ 'all_num':>{col_w['all']} }{ 'now_distance(m)':>{col_w['dist']} }{ 'cost_time(s)':>{col_w['cost']} }"
        lines = [header]

        # compute elapsed seconds for this frame
        frame_interval = getattr(self, 'frame_interval', 100)
        elapsed_seconds = frame_idx * frame_interval / 1000.0

        # build rows
        for worker in self.workers:
            try:
                user_id = getattr(worker, 'id', getattr(worker, 'worker_id', ''))
                all_num = len(worker.path) if hasattr(worker, 'path') else 0

                # over_num: use current_target_idx (number of completed targets)
                over_num = getattr(worker, 'current_target_idx', None)
                if over_num is None:
                    # fallback: count unique visited task points
                    task_set = set(worker.path) if hasattr(worker, 'path') else set()
                    traveled_set = set(getattr(worker, 'traveled_path', []))
                    over_num = len(task_set & traveled_set)

                # compute real-world traveled distance using map resolution
                traveled = getattr(worker, 'traveled_path', [])
                now_distance_m = 0.0
                for i in range(1, len(traveled)):
                    x0, y0 = traveled[i-1]
                    x1, y1 = traveled[i]
                    dx = (x1 - x0) * res_x
                    dy = (y1 - y0) * res_y
                    now_distance_m += (dx*dx + dy*dy) ** 0.5

                # cost_time starts from zero (elapsed_seconds)
                cost_seconds = int(elapsed_seconds)

                # time display: prefer simulation absolute time if available, otherwise elapsed
                if self.start_time is not None:
                    from datetime import timedelta
                    sim_time = self.start_time + timedelta(seconds=cost_seconds)
                    time_str = sim_time.strftime('%H:%M:%S')
                else:
                    hrs = cost_seconds // 3600
                    mins = (cost_seconds % 3600) // 60
                    secs = cost_seconds % 60
                    time_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"

                # build row using safe string methods to avoid f-string dynamic-width pitfalls
                id_str = str(user_id)[:col_w['id']].ljust(col_w['id'])
                time_str_fmt = time_str[:col_w['time']].ljust(col_w['time'])
                over_str = str(int(over_num)).rjust(col_w['over'])
                all_str = str(int(all_num)).rjust(col_w['all'])
                now_dist_str = f"{now_distance_m:.2f}".rjust(col_w['dist'])
                cost_str = str(int(cost_seconds)).rjust(col_w['cost'])

                line = id_str + time_str_fmt + over_str + all_str + now_dist_str + cost_str
                lines.append(line)
            except Exception:
                continue

        # compose text block
        text_block = '\n'.join(lines)
        # remove previous stats text if any
        if self.stats_text is not None:
            try:
                self.stats_text.remove()
            except Exception:
                pass
        # place centered near the top (above the title) using monospace font to keep alignment
        # choose y high (0.98) while subplots_adjust(top=0.86) ensures the title is below
        self.stats_text = self.fig.text(0.5, 0.98, text_block, ha='center', va='top', fontsize=10, fontfamily='monospace', bbox=dict(facecolor='white', alpha=0.95, edgecolor='black'))
