from flask import Flask, render_template, jsonify, request
import json
import threading
import time
import csv
from datetime import datetime, timedelta
import sounddevice as sd
import numpy as np

app = Flask(__name__)

seat_status = {}
data_lock = threading.Lock()

# ========== 热门分析缓存与定时任务 ==========
hot_area_today_cache = []  # [{camera_id, avg_occupancy}]
hot_time_today_cache = []  # [{hour, avg_occupancy}]
cache_lock = threading.Lock()
CACHE_UPDATE_INTERVAL = 600  # 秒

OCCUPANCY_LOG_FILE = 'occupancy_log.csv'

status_path = "seat_status_on_video.json"

# 假设有多个教室，每个教室对应一个麦克风设备索引
CLASSROOM_MIC_DEVICES = {
    'classroom_1': 0,  # 设备索引0
    'classroom_2': 1,  # 设备索引1
    # 可继续添加更多教室
}

# 每个教室的噪声状态
multi_noise_status = {name: {'status': '安静', 'db': 0.0} for name in CLASSROOM_MIC_DEVICES}
noise_lock = threading.Lock()

def update_seat_status():
    global seat_status
    while True:
        try:
            with open(status_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    raise ValueError("seat_status.json is empty")
                data = json.loads(content)
                with data_lock:
                    seat_status = data
        except Exception as e:
            print("读取 seat_status.json 出错:", e)
        time.sleep(0.1)

def analyze_hot_area_and_time():
    """
    分析今日热门教室和热门时段，缓存结果。
    """
    today = datetime.now().date()
    area_stats = {}  # camera_id -> [占用率, ...]
    time_stats = {}  # hour(int) -> [占用率, ...]
    try:
        with open(OCCUPANCY_LOG_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 解析时间
                ts = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
                if ts.date() != today:
                    continue
                camera_id = row['camera_id']
                occ_rate = float(row['occupancy_rate_percent'])
                hour = ts.hour
                # 教室统计
                area_stats.setdefault(camera_id, []).append(occ_rate)
                # 时段统计
                time_stats.setdefault(hour, []).append(occ_rate)
        # 计算教室平均占用率
        area_result = [
            {"camera_id": cid, "avg_occupancy": round(sum(rates)/len(rates), 2)}
            for cid, rates in area_stats.items()
        ]
        area_result.sort(key=lambda x: x['avg_occupancy'], reverse=True)
        # 计算每小时全校平均占用率
        time_result = [
            {"hour": h, "avg_occupancy": round(sum(rates)/len(rates), 2)}
            for h, rates in time_stats.items()
        ]
        time_result.sort(key=lambda x: x['avg_occupancy'], reverse=True)
        with cache_lock:
            global hot_area_today_cache, hot_time_today_cache
            hot_area_today_cache = area_result
            hot_time_today_cache = time_result
    except Exception as e:
        print("分析热门教室/时段出错:", e)

def hot_analysis_worker():
    while True:
        analyze_hot_area_and_time()
        time.sleep(CACHE_UPDATE_INTERVAL)

def noise_monitor_classroom(classroom, device):
    def callback(indata, frames, time, status):
        db = get_db(indata)
        status_str = '安静' if db <= 40 else '嘈杂'
        with noise_lock:
            multi_noise_status[classroom]['status'] = status_str
            multi_noise_status[classroom]['db'] = float(db)
            multi_noise_status[classroom]['last_update'] = time_module.time()  # 记录更新时间
        print(f"{classroom} 当前分贝: {db:.2f}，状态: {status_str}")
    import time as time_module
    with sd.InputStream(callback=callback, channels=1, samplerate=44100, blocksize=1024, device=device):
        while True:
            sd.sleep(1000)

def get_db(audio):
    rms = np.sqrt(np.mean(np.square(audio)))
    db = 20 * np.log10(rms + 1e-6) + 100
    return db

# 启动每个教室的噪声监测线程
for classroom, device in CLASSROOM_MIC_DEVICES.items():
    threading.Thread(target=noise_monitor_classroom, args=(classroom, device), daemon=True).start()

threading.Thread(target=update_seat_status, daemon=True).start()
threading.Thread(target=hot_analysis_worker, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')
@app.route("/room.html")
def room_page():
    return render_template("room.html")

@app.route("/api/seat_status_raw/<camera_id>")
def api_seat_status_raw(camera_id):
    with data_lock:
        return jsonify(seat_status.get(camera_id, {}))
@app.route("/api/summary")
def api_summary():
    with data_lock:
        summary = {}
        for camera_id, camera_data in seat_status.items():
            total = 0
            occupied = 0
            for row_seats in camera_data.values():  # row_seats 是一个列表
                for seat in row_seats:
                    total += 1
                    if seat["status"] in ["occupied", "item_only"]:
                        occupied += 1
            summary[camera_id] = {
                "total": total,
                "occupied": occupied
            }
        return jsonify(summary)
@app.route('/hot-times/<room_id>')

def hot_times(room_id):
    # 模拟 16 段 × 7 天（周一至周日）的颜色矩阵（用于热力图）
    # 颜色深浅代表人数多少，白色表示无人，越红表示越多人
    heat_colors = [
        ["#ffffff", "#ffeeee", "#ffdddd", "#ffcccc", "#ffbbbb", "#ffeeee", "#ffffff"],
        ["#ffeeee"] * 7,
        ["#ffdddd"] * 7,
        ["#ffcccc"] * 7,
        ["#ff9999"] * 7,
        ["#ffaaaa"] * 7,
        ["#ffeeee"] * 7,
        ["#ffffff"] * 7,
        ["#ffcccc"] * 7,
        ["#ffdddd"] * 7,
        ["#ffbbbb"] * 7,
        ["#ffaaaa"] * 7,
        ["#ff8888"] * 7,
        ["#ffaaaa"] * 7,
        ["#ffeeee"] * 7,
        ["#ffffff"] * 7,
    ]
    return render_template("times.html", room_id=room_id, heat_colors=heat_colors)

@app.route('/api/hot_area_today')
def api_hot_area_today():
    with cache_lock:
        return jsonify(hot_area_today_cache)

@app.route('/api/hot_time_today')
def api_hot_time_today():
    with cache_lock:
        return jsonify(hot_time_today_cache)

@app.route('/hot_area_today.html')
def hot_area_today_page():
    return render_template('hot_area_today.html')

@app.route('/hot_time_today.html')
def hot_time_today_page():
    return render_template('hot_time_today.html')

@app.route('/api/clear_hot_cache', methods=['POST'])
def clear_hot_cache():
    with cache_lock:
        global hot_area_today_cache, hot_time_today_cache
        hot_area_today_cache = []
        hot_time_today_cache = []
    return jsonify({'status': 'ok', 'msg': '缓存已清空'})

@app.route('/api/room_heatmap/<room_id>')
def api_room_heatmap(room_id):
    # 如果 room_id 没有 'camera_' 前缀，自动加上
    if not room_id.startswith('camera_'):
        room_id = f'camera_{room_id}'
    # ...后续逻辑不变...
    # 1. 初始化16x7矩阵
    matrix = [[[] for _ in range(7)] for _ in range(16)]
    try:
        with open('occupancy_log.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['camera_id'] != room_id:
                    continue
                ts = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
                weekday = ts.weekday()  # 0=周一
                hour = ts.hour
                # 计算属于哪个时段
                slot = hour - 7  # 07:00–08:00为第0段
                if 0 <= slot < 16:
                    occ = float(row['occupancy_rate_percent'])
                    matrix[slot][weekday].append(occ)
        # 计算每格平均值
        avg_matrix = [
            [
                round(sum(cell)/len(cell), 2) if cell else 0
                for cell in row
            ] for row in matrix
        ]
        return jsonify({'occupancy_matrix': avg_matrix})
    except Exception as e:
        print("生成热力图数据出错:", e)
        return jsonify({'occupancy_matrix': [[0]*7 for _ in range(16)]})

@app.route('/api/noise_status')
def get_noise_status():
    try:
        with noise_lock:
            now = time.time()
            result = {}
            for classroom, info in multi_noise_status.items():
                # 默认安静
                status = info.get('status', '安静')
                db = info.get('db', 0.0)
                last_update = info.get('last_update', now)
                # 如果超时（如30秒没更新），也强制显示“安静”
                if now - last_update > 30:
                    status = '安静'
                result[classroom] = {'status': status, 'db': db, 'last_update': last_update}
            return jsonify({
                'status': 'success',
                'data': result,
                'timestamp': now
            })
    except Exception as e:
        print(f"获取噪音状态出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '无法获取噪音状态'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
