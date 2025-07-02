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


threading.Thread(target=update_seat_status, daemon=True).start()


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



if __name__ == '__main__':
    app.run(debug=True, port=5000)
