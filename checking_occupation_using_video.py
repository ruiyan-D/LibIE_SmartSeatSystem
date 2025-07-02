import cv2
import json
import time
import numpy as np
import threading
from ultralytics import YOLO

# 初始化YOLO模型
model = YOLO('yolov8l.pt')
PERSON_CLASS = 0
ITEM_CLASSES = {
    24: "backpack", 26: "handbag", 28: "suitcase", 39: "bottle",
    41: "cup", 45: "bowl", 63: "laptop", 64: "mouse", 66: "keyboard",
    67: "cell phone", 73: "book", 75: "vase", 32: "sports ball",
    43: "knife", 46: "banana", 47: "apple", 48: "sandwich", 53: "pizza"
}

# 读取座位配置
with open("seats_config_on_video.json", "r", encoding="utf-8") as f:
    seats_config = json.load(f)

# 获取摄像头列表
camera_ids = [cam_id for cam_id in seats_config.keys() if cam_id.startswith('camera_')]
if not camera_ids:
    print("错误: 配置文件中没有摄像头配置")
    exit()

# -------------- 【改动1】摄像头替换为视频文件 -----------------
caps = {}
for cam_id in camera_ids:
    try:
        video_path = seats_config[cam_id]["video_path"]  # 读取视频路径
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            caps[cam_id] = cap
            print(f"成功打开视频源 {cam_id} ({video_path})")
        else:
            print(f"警告: 无法打开视频文件 {video_path}")
    except Exception as e:
        print(f"警告: {cam_id} 视频路径读取失败: {e}")

if not caps:
    print("错误: 没有可用的视频源")
    exit()
# --------------------------------------------------------------

# 全局变量
seat_status = {}
seat_status_lock = threading.Lock()
latest_frames = {cam_id: None for cam_id in camera_ids}
frame_locks = {cam_id: threading.Lock() for cam_id in camera_ids}
stop_threads = False

# 画布设置
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 720
PADDING = 1  # 画面间距


# 计算网格布局
def calculate_grid(num_cams):
    if num_cams == 0:
        return 0, 0

    best_ratio = float('inf')
    best_rows = 1
    best_cols = 1

    for rows in range(1, num_cams + 1):
        cols = (num_cams + rows - 1) // rows
        if cols == 0:
            continue

        canvas_ratio = CANVAS_WIDTH / CANVAS_HEIGHT
        grid_ratio = (cols * 4) / (rows * 3)
        ratio_diff = abs(canvas_ratio - grid_ratio)

        if ratio_diff < best_ratio:
            best_ratio = ratio_diff
            best_rows = rows
            best_cols = cols

    return best_rows, best_cols


# 摄像头捕获线程（改成读取视频帧）
def capture_thread(cam_id, video_path):
    global stop_threads
    cap = cv2.VideoCapture(video_path)
    while not stop_threads:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
        with frame_locks[cam_id]:
            latest_frames[cam_id] = frame.copy()
        time.sleep(1 / 30)

# 启动线程
threads = []
for cam_id in camera_ids:
    video_path = seats_config[cam_id]["video_path"]
    latest_frames[cam_id] = None
    frame_locks[cam_id] = threading.Lock()
    thread = threading.Thread(target=capture_thread, args=(cam_id, video_path))
    thread.start()
    threads.append(thread)


# 计算布局
rows, cols = calculate_grid(len(caps))
if rows == 0 or cols == 0:
    print("错误: 无法计算布局")
    exit()

print(f"摄像头布局: {rows}行 x {cols}列")

cell_width = (CANVAS_WIDTH - (cols + 1) * PADDING) // cols
cell_height = (CANVAS_HEIGHT - (rows + 1) * PADDING) // rows

cam_seats_by_row = {}
for cam_id in camera_ids:
    cam_config = seats_config[cam_id]
    seats_by_row = {}

    if "seats" in cam_config and isinstance(cam_config["seats"], list):
        for seat in cam_config["seats"]:
            if isinstance(seat, list) and len(seat) == 4:
                row = 1
                coords = seat
            elif isinstance(seat, dict) and "coords" in seat and "row" in seat:
                row = seat["row"]
                coords = seat["coords"]
            else:
                print(f"警告: {cam_id} 的座位格式错误: {seat}")
                continue

            if row not in seats_by_row:
                seats_by_row[row] = []
            seats_by_row[row].append(coords)

    elif "rows" in cam_config and isinstance(cam_config["rows"], dict):
        for row, seats in cam_config["rows"].items():
            try:
                row_num = int(row)
                if row_num not in seats_by_row:
                    seats_by_row[row_num] = []

                for seat in seats:
                    if isinstance(seat, list) and len(seat) == 4:
                        seats_by_row[row_num].append(seat)
                    else:
                        print(f"警告: {cam_id} 行{row_num}的座位格式错误: {seat}")
            except ValueError:
                print(f"警告: {cam_id} 的行号格式错误: {row}")

    cam_seats_by_row[cam_id] = seats_by_row

while True:
    canvas = np.zeros((CANVAS_HEIGHT, CANVAS_WIDTH, 3), dtype=np.uint8) + 50
    seat_status.clear()

    for i, (cam_id, cap) in enumerate(caps.items()):
        with frame_locks[cam_id]:
            frame = latest_frames[cam_id]

        if frame is None:
            continue

        config_ar = seats_config[cam_id].get("aspect_ratio", 1.33)
        h, w = frame.shape[:2]
        actual_ar = w / h

        scale_x = w / (config_ar * h) if h > 0 else 1.0
        scale_y = 1.0

        display_frame = frame.copy()

        results = model(display_frame, stream=True, conf=0.1)

        detected_persons = []
        detected_items = []

        for result in results:
            for box in result.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                if conf < 0.1:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                x1 = int(x1 * scale_x)
                y1 = int(y1 * scale_y)
                x2 = int(x2 * scale_x)
                y2 = int(y2 * scale_y)

                if cls == PERSON_CLASS:
                    detected_persons.append((x1, y1, x2, y2))
                elif cls in ITEM_CLASSES:
                    detected_items.append((x1, y1, x2, y2, cls))

        seats_by_row = cam_seats_by_row.get(cam_id, {})
        local_seat_status = {}

        for row, seats_in_row in seats_by_row.items():
            row_seat_status = []

            for seat_idx, coords in enumerate(seats_in_row):
                if len(coords) != 4:
                    print(f"警告: {cam_id} 行{row}座位{seat_idx}坐标错误: {coords}")
                    continue

                x1, y1, x2, y2 = coords

                has_person = any(not (px2 < x1 or px1 > x2 or py2 < y1 or py1 > y2)
                                 for px1, py1, px2, py2 in detected_persons)
                has_item = any(not (ix2 < x1 or ix1 > x2 or iy2 < y1 or iy1 > y2)
                               for ix1, iy1, ix2, iy2, cls in detected_items)

                status = "empty"
                color = (0, 255, 0)  # 绿色：空位
                if has_person:
                    status = "occupied"
                    color = (0, 0, 255)  # 红色：有人
                elif has_item:
                    status = "item_only"
                    color = (0, 165, 255)  # 橙色：物品

                row_seat_status.append({
                    "coords": coords,
                    "status": status
                })

                cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
                seat_text = f"Row{row} Seat{seat_idx + 1}"
                cv2.putText(display_frame, seat_text, (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            local_seat_status[row] = row_seat_status

        with seat_status_lock:
            seat_status[cam_id] = local_seat_status

        cam_text = f"Cam: {cam_id.split('_')[1]}"
        cv2.putText(display_frame, cam_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        total_seats = sum(len(row_seats) for row_seats in seats_by_row.values())
        occupied = sum(1 for row_seats in local_seat_status.values()
                       for seat in row_seats if seat["status"] == "occupied")
        stats_text = f"Seats: {occupied}/{total_seats} occupied"
        cv2.putText(display_frame, stats_text, (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)

        h, w = display_frame.shape[:2]
        aspect_ratio = w / h

        if aspect_ratio > cell_width / cell_height:
            new_width = cell_width
            new_height = int(new_width / aspect_ratio)
        else:
            new_height = cell_height
            new_width = int(new_height * aspect_ratio)

        if new_width > 0 and new_height > 0:
            resized_frame = cv2.resize(display_frame, (new_width, new_height))
        else:
            print(f"错误: 无效的尺寸 {new_width}x{new_height} 对于 {cam_id}")
            continue

        row_idx = i // cols
        col_idx = i % cols

        start_x = PADDING + col_idx * (cell_width + PADDING) + (cell_width - new_width) // 2
        start_y = PADDING + row_idx * (cell_height + PADDING) + (cell_height - new_height) // 2

        if start_x < 0 or start_y < 0 or start_x + new_width > CANVAS_WIDTH or start_y + new_height > CANVAS_HEIGHT:
            print(f"警告: {cam_id} 位置超出画布范围")
            continue

        canvas[start_y:start_y + new_height, start_x:start_x + new_width] = resized_frame

    # -------------- 【改动2】显示按键提示 -----------------
    instructions = "q:exit"
    cv2.putText(canvas, instructions, (10, CANVAS_HEIGHT - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    # -----------------------------------------------------
    with seat_status_lock:
        try:
            with open("seat_status_on_video.json", "w", encoding="utf-8") as f:
                json.dump(seat_status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"写入 seat_status_on_video.json 失败: {e}")
    cv2.imshow("Classroom Seats", canvas)
    key = cv2.waitKey(30) & 0xFF
    if key == ord('q'):
        stop_threads = True
        break
    # 这里可以加入 + - s 按键处理代码


# 释放资源
for cap in caps.values():
    cap.release()
cv2.destroyAllWindows()
