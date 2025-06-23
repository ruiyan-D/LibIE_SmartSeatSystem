import cv2
import json
from ultralytics import YOLO

# 加载预训练的YOLOv8模型
model = YOLO('yolov8n.pt')

# 初始化摄像头
cap = cv2.VideoCapture(1)
assert cap.isOpened(), "无法打开摄像头"

# 用于存储座位坐标
detected_seats = []
CONFIDENCE_THRESHOLD = 0.65

print("正在自动检测座位... 按下 's' 键保存，按下 'q' 键退出")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 使用YOLOv8进行目标检测
    results = model(frame, verbose=False)[0]

    # 清空当前帧的座位列表
    current_frame_seats = []

    # 遍历检测结果
    for result in results:
        # 只处理类别为'chair'的检测结果
        if result.names[result.boxes.cls[0].item()] == 'chair' and result.boxes.conf[0] > CONFIDENCE_THRESHOLD:
            x1, y1, x2, y2 = result.boxes.xyxy[0].tolist()
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            current_frame_seats.append([x1, y1, x2, y2])

            # 绘制检测框和标签
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            confidence = result.boxes.conf[0].item()
            cv2.putText(frame, f'Chair {confidence:.2f}',
                        (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    cv2.imshow('Seat Detection', frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('s'):
        detected_seats = current_frame_seats
        with open('detected_seats.json', 'w') as f:
            json.dump(detected_seats, f, indent=4)
        print(f"检测到 {len(detected_seats)} 个座位，坐标已保存到 detected_seats.json")

    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()