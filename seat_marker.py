import cv2
import json
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# 初始化全局变量
seats = []
current_seat = []
is_drawing = False
current_row = 1  # 从第1排开始

# 鼠标回调函数
def draw_seat(event, x, y, flags, param):
    global current_seat, is_drawing, seats, frame

    if event == cv2.EVENT_LBUTTONDOWN:
        is_drawing = True
        current_seat = [(x, y)]

    elif event == cv2.EVENT_MOUSEMOVE and is_drawing:
        temp_frame = frame.copy()
        cv2.rectangle(temp_frame, current_seat[0], (x, y), (0, 255, 0), 2)
        temp_frame = draw_text(temp_frame)
        cv2.imshow('Mark Seats', temp_frame)

    elif event == cv2.EVENT_LBUTTONUP:
        is_drawing = False
        current_seat.append((x, y))
        x1, y1 = current_seat[0]
        x2, y2 = current_seat[1]
        seat_coords = {
            "row": current_row,
            "coords": [x1, y1, x2, y2]
        }
        seats.append(seat_coords)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        updated_frame = draw_text(frame.copy())
        cv2.imshow('Mark Seats', updated_frame)

# 显示当前排数的提示文字
def draw_text(img):
    # 转为PIL格式（RGB）
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)

    # 加载中文字体（Windows系统一般有这些字体）
    # 路径需要改成你系统上存在的字体文件路径
    font_path = "C:/Windows/Fonts/simhei.ttf"
    font = ImageFont.truetype(font_path, 24)  # 字体大小24

    text = f"当前您标记的是第{current_row}排，按 'a' 切换下一排"
    draw.text((20, 10), text, font=font, fill=(0, 255, 255, 255))

    # 转回OpenCV格式（BGR）
    img = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    return img

# 打开视频并读取第一帧
cap = cv2.VideoCapture('D:/creative/c_video2.MP4')
ret, frame = cap.read()
if not ret:
    print("无法读取视频帧")
    exit()
frame = cv2.resize(frame, (640, 480))
cap.release()

cv2.namedWindow('Mark Seats')
cv2.setMouseCallback('Mark Seats', draw_seat)

# 显示初始提示
init_display = draw_text(frame.copy())
cv2.imshow('Mark Seats', init_display)

print("使用鼠标框选座位区域：")
print(" - 按 'a' 切换到下一排")
print(" - 按 's' 保存所有标记")
print(" - 按 'q' 退出")

while True:
    key = cv2.waitKey(1) & 0xFF

    if key == ord('a'):
        current_row += 1
        updated_frame = draw_text(frame.copy())
        cv2.imshow('Mark Seats', updated_frame)

    elif key == ord('s'):
        with open('seats_config.json', 'w', encoding='utf-8') as f:
            json.dump(seats, f, indent=4, ensure_ascii=False)
        print("座位区域已保存到 seats_config.json 文件中。")

    elif key == ord('q'):
        break

cv2.destroyAllWindows()
