import cv2
import json
import time
import torch
import logging  # 确保导入 logging 模块
from ultralytics import YOLO

# 禁用 YOLO 的详细日志输出
logging.getLogger("ultralytics").setLevel(logging.WARNING)

# 加载 YOLO 模型
model = YOLO('yolov8n.pt')

# 禁用 YOLO 输出的推理信息
model.verbose = False

# 读取座位标记信息
with open("seats_config.json", "r") as f:
    seats = json.load(f)

# 确保座位坐标有四个值 [x1, y1, x2, y2]
if isinstance(seats, list):
    seats = {f"seat_{i}": coords for i, coords in enumerate(seats)}

# 检查座位坐标是否正确
for seat_id, coords in seats.items():
    if len(coords) != 4:
        print(f"座位 {seat_id} 坐标不正确，应该有四个值 [x1, y1, x2, y2]")
        continue

# 初始化视频流
cap = cv2.VideoCapture("D:/creative/video2.mp4")
assert cap.isOpened(), "无法打开视频文件"

# 存储占用状态
seat_status = {seat_id: False for seat_id in seats}
occupied_seats = []

# 初始化计时器
last_time = time.time()

# 逐帧处理
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # 模型推理
    results = model(frame, stream=True)

    # 遍历检测结果，找出人
    detected_persons = []
    for result in results:
        for box in result.boxes:
            cls = int(box.cls[0])
            if cls == 0:  # 类别0代表人
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detected_persons.append((x1, y1, x2, y2))

    # 检测每个座位区域是否有重叠
    for seat_id, coords in seats.items():
        x1, y1, x2, y2 = coords
        is_occupied = False
        for px1, py1, px2, py2 in detected_persons:
            if not (px2 < x1 or px1 > x2 or py2 < y1 or py1 > y2):  # 检测是否有交叉
                is_occupied = True
                break

        # 更新状态
        seat_status[seat_id] = is_occupied
        # 标注座位状态（红色表示占用，绿色表示空闲）
        if is_occupied:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
        else:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # 显示座位编号
        cv2.putText(frame, f"{seat_id}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # 显示检测结果
    cv2.imshow("Seat Occupancy Detection", frame)

    # 每5秒输出一次所有座位的占用情况
    if time.time() - last_time >= 5:
        last_time = time.time()  # 更新计时器
        # 获取当前视频时间戳（单位秒）
        current_time = int(cap.get(cv2.CAP_PROP_POS_FRAMES) / cap.get(cv2.CAP_PROP_FPS))

        print(f"\n第 {current_time} 秒 当前座位占用情况：")
        for seat_id, coords in seats.items():
            is_occupied = "占用" if seat_status[seat_id] else "空闲"
            print(f"座位编号: {seat_id} 座位坐标: {coords} 是否被占用: {is_occupied}")

    # 按 'q' 键退出
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 释放资源
cap.release()
cv2.destroyAllWindows()

# 将占用的座位传给后台
occupied_seats = [seat_id for seat_id, occupied in seat_status.items() if occupied]
print("占用的座位:", occupied_seats)
