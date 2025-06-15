from flask import Flask, render_template, jsonify
import json
import threading
import time

app = Flask(__name__)

seat_status = {}
data_lock = threading.Lock()


def update_seat_status():
    global seat_status
    while True:
        try:
            with open("seat_status.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                with data_lock:
                    seat_status = data
        except Exception as e:
            print("读取 seat_status.json 出错:", e)
        time.sleep(0.1)


def calculate_grid_layout(seats):
    rows = {}
    for seat_id, info in seats.items():
        row_key = info.get("row", 0)  # 直接使用 row 字段
        if row_key not in rows:
            rows[row_key] = []
        rows[row_key].append((seat_id, info["coords"], info["status"]))

    # 排序：行号从大到小（摄像头最下为第1排）
    sorted_rows = sorted(rows.items(), reverse=True)
    grid = [sorted(seat_list, key=lambda s: s[1][0]) for _, seat_list in sorted_rows]
    return grid



threading.Thread(target=update_seat_status, daemon=True).start()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/seat_status')
def get_seat_status():
    with data_lock:
        grid_layout = calculate_grid_layout(seat_status)
        return jsonify(grid_layout)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
