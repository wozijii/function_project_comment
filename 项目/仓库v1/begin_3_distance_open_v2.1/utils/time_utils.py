"""
时间处理工具
处理时间转换和计算
"""
from datetime import datetime, timedelta
def parse_datetime(time_value) -> datetime:
    """
    解析时间字符串或返回时间对象
    Args:
        time_value: 时间字符串或时间对象
    Returns:
        datetime: 时间对象
    """
    try:
        # 如果已经是datetime对象，直接返回
        if isinstance(time_value, datetime):
            return time_value
        
        # 尝试多种格式
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d:%H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y%m%d %H:%M:%S"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_value, fmt)
            except ValueError:
                continue
        # 如果都不匹配，返回当前时间
        print(f"警告: 无法解析时间字符串 '{time_value}'，使用当前时间")
        return datetime.now()
    except Exception as e:
        print(f"时间解析错误: {e}")
        return datetime.now()
def calculate_time_difference(start_time: datetime, end_time: datetime) -> float:
    """
    计算时间差(秒)
    Args:
        start_time: 开始时间
        end_time: 结束时间
    Returns:
        float: 时间差(秒)
    """
    if start_time and end_time:
        return (end_time - start_time).total_seconds()
    return 0.0
def add_seconds_to_time(base_time: datetime, seconds: float) -> datetime:
    """
    给时间添加秒数
    Args:
        base_time: 基准时间
        seconds: 要添加的秒数
    Returns:
        datetime: 添加后的时间
    """
    return base_time + timedelta(seconds=seconds)
def format_datetime(dt: datetime) -> str:
    """
    格式化时间为字符串
    Args:
        dt: 时间对象
        
    Returns:
        str: 格式化后的时间字符串
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")