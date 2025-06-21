import cv2
import json

# 初始化全局变量
seats = []
current_seat = []
is_drawing = False

current_camera_id = 0  # camera_0 开始
seats_config = {"camera_0": [], "camera_1": [], "camera_2": []}

def draw_seat(event, x, y, flags, param):
    global current_seat, is_drawing, frame, temp_frame

    if event == cv2.EVENT_LBUTTONDOWN:
        is_drawing = True
        current_seat = [(x, y)]

    elif event == cv2.EVENT_MOUSEMOVE and is_drawing:
        temp_frame = frame.copy()
        cv2.rectangle(temp_frame, current_seat[0], (x, y), (0, 255, 0), 2)
        cv2.imshow('Mark Seats', temp_frame)

    elif event == cv2.EVENT_LBUTTONUP:
        is_drawing = False
        current_seat.append((x, y))
        seat_coords = [current_seat[0][0], current_seat[0][1], current_seat[1][0], current_seat[1][1]]
        seats_config[f"camera_{current_camera_id}"].append(seat_coords)
        cv2.rectangle(frame, current_seat[0], current_seat[1], (0, 255, 0), 2)
        cv2.imshow('Mark Seats', frame)

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    cv2.putText(frame, f"Marking camera_{current_camera_id}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
    
    for seat in seats_config[f"camera_{current_camera_id}"]:
        x1, y1, x2, y2 = seat
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    cv2.imshow('Mark Seats', frame)
    cv2.setMouseCallback('Mark Seats', draw_seat)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('n'):  # 切换到下一个“逻辑摄像头”
        current_camera_id = (current_camera_id + 1) % 3
        print(f"切换到 camera_{current_camera_id}")
    elif key == ord('s'):  # 保存
        with open('seats_config.json', 'w') as f:
            json.dump(seats_config, f, indent=4)
        print("座位配置已保存。")
    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
