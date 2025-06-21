import cv2
import json
import threading
from ultralytics import YOLO

# 加载YOLO模型（建议使用yolov8x.pt，如显卡性能允许）
model = YOLO('yolov8l.pt')  # 也可以换 yolov8x.pt

PERSON_CLASS = 0
ITEM_CLASSES = {24: "backpack", 41: "cup", 63: "laptop", 73: "book"}

cap = cv2.VideoCapture(0)  # 单个物理摄像头

# 读取camera_0、camera_1、camera_2的配置
with open("seats_config.json", "r") as f:
    seats_config = json.load(f)

seat_status = {}
seat_status_lock = threading.Lock()

while True:
    ret, frame = cap.read()
    if not ret:
        print("摄像头读取失败，退出")
        break

    # 降低YOLO置信度阈值到0.1（默认0.25）
    results = model(frame, stream=True, conf=0.1)

    detected_persons = []
    detected_items = []

    # 只跑1次YOLO，收集所有符合置信度的框
    for result in results:
        for box in result.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])  # 置信度

            if conf < 0.1:  # 丢弃低置信度框
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            if cls == PERSON_CLASS:
                detected_persons.append((x1, y1, x2, y2))
            elif cls in ITEM_CLASSES:
                detected_items.append((x1, y1, x2, y2, cls))

    for camera_id in ["camera_0", "camera_1", "camera_2"]:
        seats_list = seats_config.get(camera_id, [])
        if not seats_list:
            continue

        local_seat_status = {}
        display_frame = frame.copy()  # 每个camera_x显示整张frame+自己的框

        for i, coords in enumerate(seats_list):
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

            local_seat_status[f"seat_{i}"] = {"coords": coords, "status": status}

            # 在整张frame上画出该camera负责的框
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(display_frame, f"{camera_id}_seat_{i}", (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # 更新状态
        with seat_status_lock:
            seat_status[camera_id] = local_seat_status

        # 显示camera_x窗口（全图+局部框）
        cv2.imshow(camera_id, display_frame)

    # 保存最新状态
    with open('seat_status.json', 'w') as f:
        json.dump(seat_status, f, indent=4)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
