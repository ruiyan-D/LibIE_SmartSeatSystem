from flask import Flask, render_template, jsonify, request
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
                content = f.read().strip()
                if not content:
                    raise ValueError("seat_status.json is empty")
                data = json.loads(content)
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
@app.route("/room.html")
def room_page():
    return render_template("room.html")

@app.route('/api/seat_status')
def get_seat_status():
    with data_lock:
        grid_layout = calculate_grid_layout(seat_status)
        return jsonify(grid_layout)
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



if __name__ == '__main__':
    app.run(debug=True, port=5000)
