import cv2
import json
from ultralytics import YOLO

# 加载模型
model = YOLO('yolov8l.pt')

# 读取座位配置
with open("seats_config.json", "r") as f:
    seats_list = json.load(f)

# 转换为字典


# 打开视频文件
cap = cv2.VideoCapture('D:/creative/c_video2.MP4')
assert cap.isOpened(), "无法打开视频文件"

seats = {}
seat_status = {}

for i, seat_data in enumerate(seats_list):
    coords = seat_data.get("coords")
    row = seat_data.get("row", 1)
    if not coords or len(coords) != 4:
        print(f"跳过无效座位数据: {seat_data}")
        continue

    seat_id = f"seat_{i}"
    seats[seat_id] = {
        "coords": coords,
        "row": row
    }

    seat_status[seat_id] = {
        "coords": coords,
        "row": row,
        "status": "empty",
        "items": []
    }


# 类别定义
PERSON_CLASS = 0
ITEM_CLASSES = [24, 26, 63, 67, 73]  # backpack, handbag, laptop, phone, book
label_map = {
    24: "backpack",
    26: "handbag",
    63: "laptop",
    67: "phone",
    73: "book"
}

frame_count = 0
skip_rate = 2
last_detected_persons = []
last_detected_items = []

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (640, 480))

    if frame_count % skip_rate == 0:
        results = model(frame, stream=True)
        last_detected_persons = []
        last_detected_items = []

        for result in results:
            for box in result.boxes:
                cls = int(box.cls[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                if cls == PERSON_CLASS:
                    last_detected_persons.append((x1, y1, x2, y2))
                elif cls in ITEM_CLASSES:
                    last_detected_items.append((x1, y1, x2, y2, cls))

    # 绘制结果（基于上一帧检测）
    for seat_id, info in seat_status.items():
        x1, y1, x2, y2 = info["coords"]

        has_person = any(not (px2 < x1 or px1 > x2 or py2 < y1 or py1 > y2)
                         for px1, py1, px2, py2 in last_detected_persons)

        items_in_seat = [
            label_map.get(cls, "item")
            for px1, py1, px2, py2, cls in last_detected_items
            if not (px2 < x1 or px1 > x2 or py2 < y1 or py1 > y2)
        ]

        # 状态更新
        if has_person:
            status = "occupied"
            color = (0, 0, 255)
        elif items_in_seat:
            status = "item_only"
            color = (0, 165, 255)
        else:
            status = "empty"
            color = (0, 255, 0)

        seat_status[seat_id]["status"] = status
        seat_status[seat_id]["items"] = items_in_seat

        # 绘图
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
      #  cv2.putText(frame, f"{seat_id} ({status})", (x1, y1 - 5),
      #             cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)

    # 显示检测框
   # for (x1, y1, x2, y2) in last_detected_persons:
    #    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 1)

    #for (x1, y1, x2, y2, cls) in last_detected_items:
    #   label = label_map.get(cls, "item")
    #  cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 165, 255), 1)
    # cv2.putText(frame, label, (x1, y1 - 5),
    #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)

    cv2.imshow("Seat Detection from Video", frame)

    # 写状态文件
    with open('seat_status.json', 'w') as f:
        json.dump(seat_status, f, indent=4)

    frame_count += 1

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
