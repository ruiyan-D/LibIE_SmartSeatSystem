import cv2
import json
from ultralytics import YOLO

# 加载模型
model = YOLO('yolov8l.pt')  # 你可以换成 yolov8s.pt 或 yolov8l.pt 提升精度

# 物品类别 ID（来自 COCO 数据集）
PERSON_CLASS = 0
ITEM_CLASSES = {
    24: "backpack",   # 书包
    41: "cup",        # 水杯
    63: "laptop",     # 笔记本电脑
    73: "book"        # 书本
}

# 读取座位配置
with open("seats_config.json", "r") as f:
    seats_list = json.load(f)

seats = {f"seat_{i}": coords for i, coords in enumerate(seats_list)} if isinstance(seats_list, list) else seats_list
seat_status = {seat_id: {"coords": coords, "status": "empty"} for seat_id, coords in seats.items()}

# 打开摄像头
cap = cv2.VideoCapture(0)
assert cap.isOpened(), "无法打开摄像头"

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, stream=True)

    detected_persons = []
    detected_items = []

    for result in results:
        for box in result.boxes:
            cls = int(box.cls[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            if cls == PERSON_CLASS:
                detected_persons.append((x1, y1, x2, y2))
            elif cls in ITEM_CLASSES:
                detected_items.append((x1, y1, x2, y2, cls))  # 包含类别 ID

    for seat_id, info in seat_status.items():
        x1, y1, x2, y2 = info["coords"]

        has_person = any(not (px2 < x1 or px1 > x2 or py2 < y1 or py1 > y2)
                         for px1, py1, px2, py2 in detected_persons)

        item_classes_in_seat = [
            cls for px1, py1, px2, py2, cls in detected_items
            if not (px2 < x1 or px1 > x2 or py2 < y1 or py1 > y2)
        ]

        has_item = len(item_classes_in_seat) > 0

        if has_person:
            seat_status[seat_id]["status"] = "occupied"
            color = (0, 0, 255)  # 红色
        elif has_item:
            seat_status[seat_id]["status"] = "item_only"
            color = (0, 165, 255)  # 橙色
        else:
            seat_status[seat_id]["status"] = "empty"
            color = (0, 255, 0)  # 绿色

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, f"{seat_id}", (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)

    # 显示图像
    cv2.imshow("Real-time Seat Occupancy Detection", frame)

    # 保存状态
    with open('seat_status.json', 'w') as f:
        json.dump(seat_status, f, indent=4)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
