import cv2
import json

# 初始化全局变量
seats = []
current_seat = []
is_drawing = False

# 鼠标回调函数
def draw_seat(event, x, y, flags, param):
    global current_seat, is_drawing, seats, frame, temp_frame

    if event == cv2.EVENT_LBUTTONDOWN:
        is_drawing = True
        current_seat = [(x, y)]  # 记录第一个点击位置 (x1, y1)

    elif event == cv2.EVENT_MOUSEMOVE and is_drawing:
        # 每次绘制时更新临时框
        temp_frame = frame.copy()
        cv2.rectangle(temp_frame, current_seat[0], (x, y), (0, 255, 0), 2)  # 实时画矩形
        cv2.imshow('Mark Seats', temp_frame)

    elif event == cv2.EVENT_LBUTTONUP:
        is_drawing = False
        current_seat.append((x, y))  # 记录第二个点击位置 (x2, y2)
        # 保存坐标，确保为四个数值（x1, y1, x2, y2）
        seat_coords = [current_seat[0][0], current_seat[0][1], current_seat[1][0], current_seat[1][1]]
        seats.append(seat_coords)  # 将坐标添加到座位列表
        # 在最终的帧上绘制矩形
        cv2.rectangle(frame, current_seat[0], current_seat[1], (0, 255, 0), 2)
        cv2.imshow('Mark Seats', frame)

# 初始化摄像头
cap = cv2.VideoCapture(0)  # 使用默认摄像头
assert cap.isOpened(), "无法打开摄像头"

# 读取第一帧
ret, frame = cap.read()
if not ret:
    print("无法读取摄像头视频流")
    cap.release()
    exit()

# 创建一个全局变量来保存视频帧
temp_frame = frame.copy()

cv2.imshow('Mark Seats', frame)
cv2.setMouseCallback('Mark Seats', draw_seat)

print("请使用鼠标框选座位区域，按下 's' 键保存，按下 'q' 键退出。")

while True:
    ret, frame = cap.read()  # 读取摄像头每一帧
    if not ret:
        break

    # 保证每一帧都能显示之前绘制的座位框
    for seat in seats:
        x1, y1, x2, y2 = seat
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    cv2.imshow('Mark Seats', frame)  # 显示摄像头画面

    key = cv2.waitKey(1) & 0xFF
    if key == ord('s'):  # 按 's' 键保存座位区域
        with open('seats_config.json', 'w') as f:
            json.dump(seats, f, indent=4)
        print("座位区域已保存到 seats_config.json 文件中。")
    elif key == ord('q'):  # 按 'q' 键退出
        break

cap.release()  # 释放摄像头资源
cv2.destroyAllWindows()
