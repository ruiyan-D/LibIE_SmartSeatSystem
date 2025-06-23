import cv2
import json
import numpy as np
import threading
from ultralytics import YOLO

# 初始化YOLO模型
model = YOLO('yolov8n.pt')
PERSON_CLASS = 0
ITEM_CLASSES = {
    24: "backpack", 26: "handbag", 28: "suitcase", 39: "bottle",
    41: "cup", 45: "bowl", 63: "laptop", 64: "mouse", 66: "keyboard",
    67: "cell phone", 73: "book", 75: "vase", 32: "sports ball",
    43: "knife", 46: "banana", 47: "apple", 48: "sandwich", 53: "pizza"
}

# 读取座位配置
with open("seats_config.json", "r") as f:
    seats_config = json.load(f)

# 获取摄像头列表
camera_ids = [cam_id for cam_id in seats_config.keys() if cam_id.startswith('camera_')]
if not camera_ids:
    print("错误: 配置文件中没有摄像头配置")
    exit()

# 初始化摄像头
caps = {}
for cam_id in camera_ids:
    # 提取摄像头索引（假设配置文件名如camera_0对应索引0）
    try:
        index = int(cam_id.split('_')[1])
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            # 设置摄像头分辨率（降低分辨率提高速度）
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            caps[cam_id] = cap
            print(f"成功打开摄像头 {cam_id} (索引 {index})")

            # 获取实际分辨率以计算缩放比例
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            config_ar = seats_config[cam_id].get("aspect_ratio", 1.33)
            actual_ar = width / height if height > 0 else config_ar

            # 计算缩放比例
            scale_x = width / (config_ar * height) if height > 0 else 1.0
            scale_y = 1.0
            print(
                f"摄像头 {cam_id} 配置宽高比: {config_ar:.4f}, 实际宽高比: {actual_ar:.4f}, 缩放比例: x={scale_x:.4f}, y={scale_y:.4f}")
        else:
            print(f"警告: 无法打开摄像头 {cam_id} (索引 {index})")
    except:
        print(f"警告: 无法解析摄像头ID {cam_id}")

if not caps:
    print("错误: 没有可用的摄像头")
    exit()

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

    # 计算最佳行列数
    best_ratio = float('inf')
    best_rows = 1
    best_cols = 1

    # 尝试不同的行列组合
    for rows in range(1, num_cams + 1):
        cols = (num_cams + rows - 1) // rows
        if cols == 0:
            continue

        # 计算宽高比差异
        canvas_ratio = CANVAS_WIDTH / CANVAS_HEIGHT
        grid_ratio = (cols * 4) / (rows * 3)  # 假设4:3比例
        ratio_diff = abs(canvas_ratio - grid_ratio)

        if ratio_diff < best_ratio:
            best_ratio = ratio_diff
            best_rows = rows
            best_cols = cols

    return best_rows, best_cols


# 摄像头捕获线程
def capture_thread(cam_id, cap):
    global stop_threads
    while not stop_threads:
        ret, frame = cap.read()
        if ret:
            with frame_locks[cam_id]:
                latest_frames[cam_id] = frame.copy()


# 启动摄像头线程
threads = []
for cam_id, cap in caps.items():
    t = threading.Thread(target=capture_thread, args=(cam_id, cap))
    t.daemon = True
    t.start()
    threads.append(t)

# 计算布局
rows, cols = calculate_grid(len(caps))
if rows == 0 or cols == 0:
    print("错误: 无法计算布局")
    exit()

print(f"摄像头布局: {rows}行 x {cols}列")

# 计算每个格子的尺寸
cell_width = (CANVAS_WIDTH - (cols + 1) * PADDING) // cols
cell_height = (CANVAS_HEIGHT - (rows + 1) * PADDING) // rows

# 主循环
while True:
    # 创建空白画布
    canvas = np.zeros((CANVAS_HEIGHT, CANVAS_WIDTH, 3), dtype=np.uint8) + 50

    # 处理每个摄像头
    seat_status.clear()

    for i, (cam_id, cap) in enumerate(caps.items()):
        # 获取最新帧
        with frame_locks[cam_id]:
            frame = latest_frames[cam_id]

        if frame is None:
            continue

        # 获取配置中的宽高比
        config_ar = seats_config[cam_id].get("aspect_ratio", 1.33)
        h, w = frame.shape[:2]
        actual_ar = w / h

        # 计算缩放比例
        scale_x = w / (config_ar * h) if h > 0 else 1.0
        scale_y = 1.0

        # 复制帧用于处理
        display_frame = frame.copy()

        # 运行YOLO检测
        results = model(display_frame, stream=True, conf=0.1)

        detected_persons = []
        detected_items = []

        # 收集检测结果
        for result in results:
            for box in result.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])

                if conf < 0.1:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0])

                # 应用缩放
                x1 = int(x1 * scale_x)
                y1 = int(y1 * scale_y)
                x2 = int(x2 * scale_x)
                y2 = int(y2 * scale_y)

                if cls == PERSON_CLASS:
                    detected_persons.append((x1, y1, x2, y2))
                elif cls in ITEM_CLASSES:
                    detected_items.append((x1, y1, x2, y2, cls))

        # 处理座位
        seats_list = seats_config[cam_id].get("seats", [])
        local_seat_status = {}

        # 处理座位配置
        for seat_idx, seat_data in enumerate(seats_list):
            # 确保是坐标列表
            if isinstance(seat_data, list) and len(seat_data) == 4:
                coords = seat_data
            else:
                print(f"警告: 未知的座位格式 {cam_id} 座位 {seat_idx}")
                continue

            # 确保有4个坐标值
            if len(coords) != 4:
                print(f"警告: 坐标数量错误 {cam_id} 座位 {seat_idx}: {coords}")
                continue

            x1, y1, x2, y2 = coords

            # 检查是否有人
            has_person = any(not (px2 < x1 or px1 > x2 or py2 < y1 or py1 > y2)
                             for px1, py1, px2, py2 in detected_persons)

            # 检查是否有物品
            has_item = any(not (ix2 < x1 or ix1 > x2 or iy2 < y1 or iy1 > y2)
                           for ix1, iy1, ix2, iy2, cls in detected_items)

            # 确定状态
            status = "empty"
            color = (0, 255, 0)  # 绿色：空位
            if has_person:
                status = "occupied"
                color = (0, 0, 255)  # 红色：有人
            elif has_item:
                status = "item_only"
                color = (0, 165, 255)  # 橙色：物品

            # 存储状态
            local_seat_status[f"seat_{seat_idx}"] = {
                "coords": coords,
                "status": status
            }

            # 在帧上绘制座位框
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(display_frame, f"Seat {seat_idx}", (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # 更新全局状态
        with seat_status_lock:
            seat_status[cam_id] = local_seat_status

        # 在帧上添加摄像头ID
        cv2.putText(display_frame, cam_id, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        # 将帧缩放到格子大小，保持比例
        h, w = display_frame.shape[:2]
        aspect_ratio = w / h

        # 计算缩放后尺寸
        if aspect_ratio > cell_width / cell_height:
            # 宽度受限
            new_width = cell_width
            new_height = int(new_width / aspect_ratio)
        else:
            # 高度受限
            new_height = cell_height
            new_width = int(new_height * aspect_ratio)

        # 缩放图像
        if new_width > 0 and new_height > 0:
            resized_frame = cv2.resize(display_frame, (new_width, new_height))
        else:
            print(f"错误: 无效的尺寸 {new_width}x{new_height} 对于 {cam_id}")
            continue

        # 计算在画布上的位置
        row = i // cols
        col = i % cols

        # 计算起始位置（居中放置）
        start_x = PADDING + col * (cell_width + PADDING) + (cell_width - new_width) // 2
        start_y = PADDING + row * (cell_height + PADDING) + (cell_height - new_height) // 2

        # 确保位置在画布范围内
        if start_x < 0 or start_y < 0 or start_x + new_width > CANVAS_WIDTH or start_y + new_height > CANVAS_HEIGHT:
            print(f"警告: {cam_id} 位置超出画布范围")
            continue

        # 将帧复制到画布
        canvas[start_y:start_y + new_height, start_x:start_x + new_width] = resized_frame

    # 显示总画布
    cv2.imshow("Multi-Camera Seat Monitoring", canvas)

    # 保存状态
    with open('seat_status.json', 'w') as f:
        json.dump(seat_status, f, indent=4)

    # 检查退出
    if cv2.waitKey(1) & 0xFF == ord('q'):
        stop_threads = True
        break

# 释放资源
for cap in caps.values():
    cap.release()
cv2.destroyAllWindows()

# 等待线程结束
for t in threads:
    t.join(timeout=1.0)

print("程序已退出")