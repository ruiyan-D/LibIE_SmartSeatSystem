# seat_analyzer.py

import json
import csv
import os
import time
from datetime import datetime

# --- 配置区 ---
# 你可以在这里修改文件名和时间间隔
INPUT_JSON_FILE = 'seat_status.json'
SEAT_COUNT_FILE = 'classroom_seat_counts.json' # 用于存储每个教室座位总数的文件
OCCUPANCY_LOG_FILE = 'occupancy_log.csv'       # 用于记录历史占用数据的CSV文件
LOGGING_INTERVAL_SECONDS = 600                 # 时间间隔（单位：秒），10分钟 = 600秒

# --- 功能函数区 ---

def analyze_seat_data(data):
    """
    分析从JSON加载的数据，返回每个教室的详细统计信息。

    Args:
        data (dict): 从JSON文件加载的字典数据。

    Returns:
        dict: 一个字典，键是 camera_id，值是包含统计信息的字典。
              例如: {'camera_0': {'total': 6, 'occupied': 0, ...}, ...}
    """
    analysis_result = {}

    # 遍历每个摄像头（教室）
    for camera_id, camera_data in data.items():
        # 初始化这个教室的计数器
        stats = {
            'occupied': 0,
            'item_only': 0,
            'empty': 0,
            'total': 0
        }

        # 遍历这个教室里的所有座位分组（比如 "1", "2", "3"）
        for seat_group in camera_data.values():
            # 累加座位总数
            stats['total'] += len(seat_group)
            # 遍历分组里的每个座位
            for seat in seat_group:
                status = seat.get('status', 'empty') # 使用.get()以防万一没有status字段
                if status in stats:
                    stats[status] += 1

        analysis_result[camera_id] = stats

    return analysis_result

def write_seat_counts_to_file(analysis):
    """
    将每个教室的座位总数写入到一个专用的JSON文件中。
    这个函数通常只需要在第一次运行时执行一次。

    Args:
        analysis (dict): analyze_seat_data 函数返回的结果。
    """
    seat_counts = {camera_id: stats['total'] for camera_id, stats in analysis.items()}

    try:
        with open(SEAT_COUNT_FILE, 'w', encoding='utf-8') as f:
            # json.dump 可以将字典漂亮地写入文件
            # indent=4 让JSON文件格式更美观，易于阅读
            json.dump(seat_counts, f, indent=4, ensure_ascii=False)
        print(f"成功将各教室座位总数写入到文件: {SEAT_COUNT_FILE}")
    except IOError as e:
        print(f"错误：无法写入座位总数文件 {SEAT_COUNT_FILE}。原因: {e}")

def append_log_to_csv(analysis):
    """
    将当前时间的占用数据追加写入到CSV日志文件中。

    Args:
        analysis (dict): analyze_seat_data 函数返回的结果。
    """
    # 获取当前时间，并格式化为 "年-月-日 时:分:秒"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 检查CSV文件是否存在，如果不存在，我们就需要先写入表头
    file_exists = os.path.exists(OCCUPANCY_LOG_FILE)

    try:
        # 使用 'a' (append) 模式来追加内容，而不是覆盖
        # newline='' 是写入CSV文件时的标准做法，防止出现空行
        with open(OCCUPANCY_LOG_FILE, 'a', newline='', encoding='utf-8') as f:
            # 创建一个CSV写入对象
            writer = csv.writer(f)

            # 如果文件是新建的，就先写入表头
            if not file_exists:
                header = [
                    'timestamp', 'camera_id', 'total_seats',
                    'occupied', 'item_only', 'empty', 'occupancy_rate_percent'
                ]
                writer.writerow(header)

            # 遍历分析结果，为每个教室写入一行数据
            for camera_id, stats in analysis.items():
                total = stats['total']
                occupied = stats['occupied']

                # 计算占用率，注意处理分母为0的情况，防止程序出错
                if total > 0:
                    occupancy_rate = (occupied / total) * 100
                else:
                    occupancy_rate = 0

                # 准备要写入的一行数据
                row = [
                    timestamp,
                    camera_id,
                    total,
                    occupied,
                    stats['item_only'],
                    stats['empty'],
                    f"{occupancy_rate:.2f}" # 格式化为保留两位小数的字符串
                ]
                writer.writerow(row)

        print(f"[{timestamp}] 成功记录当前占用数据到 {OCCUPANCY_LOG_FILE}")

    except IOError as e:
        print(f"错误：无法写入日志文件 {OCCUPANCY_LOG_FILE}。原因: {e}")

# --- 主程序入口 ---

def main():
    """
    主执行函数
    """
    print("教室座位占用情况分析程序已启动。")
    print(f"将从 '{INPUT_JSON_FILE}' 读取数据。")
    print(f"每隔 {LOGGING_INTERVAL_SECONDS} 秒记录一次数据到 '{OCCUPANCY_LOG_FILE}'。")
    print("按 Ctrl+C 可以停止程序。")

    # 首次运行时，先执行一次座位总数统计
    # 这样即使后面JSON文件变了，我们也有个初始的座位数记录
    try:
        with open(INPUT_JSON_FILE, 'r', encoding='utf-8') as f:
            initial_data = json.load(f)
        initial_analysis = analyze_seat_data(initial_data)
        write_seat_counts_to_file(initial_analysis)
    except FileNotFoundError:
        print(f"警告：初始运行时未找到输入文件 '{INPUT_JSON_FILE}'。将在主循环中继续尝试。")
    except json.JSONDecodeError:
        print(f"警告：初始运行时文件 '{INPUT_JSON_FILE}' 内容不是有效的JSON。")
    except Exception as e:
        print(f"初始化时发生未知错误: {e}")

    # 进入主循环，定时记录数据
    while True:
        try:
            # 1. 读取JSON文件
            with open(INPUT_JSON_FILE, 'r', encoding='utf-8') as f:
                current_data = json.load(f)

            # 2. 分析数据
            current_analysis = analyze_seat_data(current_data)

            # 3. 将分析结果追加到CSV日志
            append_log_to_csv(current_analysis)

        except FileNotFoundError:
            # 这个错误很常见，比如大模型程序还没生成第一个文件
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 等待输入文件 '{INPUT_JSON_FILE}'...")
        except json.JSONDecodeError:
            # 如果文件正在被写入，可能会读到一半，导致JSON格式错误，短暂等待后重试即可
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 读取JSON文件时出错，可能文件正在写入中。稍后重试。")
        except Exception as e:
            # 捕获其他所有未知错误，保证程序不会轻易崩溃
            print(f"发生未知错误: {e}")

        # 4. 等待指定的时间
        time.sleep(LOGGING_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()