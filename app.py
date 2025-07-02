from flask import Flask, render_template, jsonify, request
import json
import threading
import time
import csv
from datetime import datetime, timedelta

app = Flask(__name__)

seat_status = {}
data_lock = threading.Lock()

# ========== 热门分析缓存与定时任务 ==========
hot_area_today_cache = []  # [{camera_id, avg_occupancy}]
hot_time_today_cache = []  # [{hour, avg_occupancy}]
cache_lock = threading.Lock()
CACHE_UPDATE_INTERVAL = 600  # 秒

OCCUPANCY_LOG_FILE = 'occupancy_log.csv'

def update_seat_status():
    global seat_status
    while True:
        try:
            with open("seat_status.json", "r", encoding="utf-8") as f:
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)
