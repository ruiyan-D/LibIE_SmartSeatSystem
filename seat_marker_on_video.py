import cv2
import os
import json

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 720

# 视频路径列表
video_paths = [
    "test_videos/class1.mp4",
    "test_videos/class2.mp4",
    "test_videos/class3.mp4"
]

# 配置文件路径
config_path = "seats_config_on_video.json"

# 加载或初始化配置
if os.path.exists(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        seat_config = json.load(f)
else:
    seat_config = {}

# 全局变量
drawing = False
ix, iy = -1, -1
rectangles = []
current_row = 1
frame = None
camera_index = 0

# 颜色循环定义（绿色、黄色、蓝色）
ROW_COLORS = [
    (0, 255, 0),      # 绿色
    (0, 255, 255),    # 黄色
    (255, 0, 0)       # 蓝色
]

# 鼠标事件回调
def draw_rectangle(event, x, y, flags, param):
    global ix, iy, drawing, rectangles, frame

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix, iy = x, y

    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        temp = frame.copy()
        cv2.rectangle(temp, (ix, iy), (x, y), (0, 255, 0), 2)
        for r in rectangles:
            color = ROW_COLORS[(r[4] - 1) % len(ROW_COLORS)]
            cv2.rectangle(temp, (r[0], r[1]), (r[2], r[3]), color, 2)
            cv2.putText(temp, f"Row {r[4]}", (r[0], r[1] - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        cv2.imshow('Frame', temp)

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        rectangles.append((ix, iy, x, y, current_row))

# 加载并显示视频的第一帧
def process_video(index):
    global frame, rectangles, current_row, camera_index

    camera_index = index
    video_path = video_paths[camera_index]
    rectangles = []
    current_row = 1

    cap = cv2.VideoCapture(video_path)
    ret, frame_read = cap.read()
    cap.release()

    if not ret:
        print(f"❌ 无法读取视频：{video_path}")
        return False

    frame = frame_read.copy()
    cv2.setMouseCallback('Frame', draw_rectangle)

    print(f"🎥 当前摄像头：camera_{camera_index}（按 n 切换）")
    return True

# 保存当前摄像头的座位配置
def save_current_seats():
    global camera_index, rectangles, frame

    video_path = video_paths[camera_index]
    cap = cv2.VideoCapture(video_path)
    aspect_ratio = round(cap.get(cv2.CAP_PROP_FRAME_WIDTH) / cap.get(cv2.CAP_PROP_FRAME_HEIGHT), 10)
    cap.release()

    key = f"camera_{camera_index}"
    seat_config[key] = {
        "video_path": video_path.replace("\\", "/"),
        "seats": [],
        "aspect_ratio": aspect_ratio
    }
    for r in rectangles:
        seat_config[key]["seats"].append({
            "coords": [r[0], r[1], r[2], r[3]],
            "row": r[4]
        })

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(seat_config, f, indent=4)
    print(f"✅ 已保存 camera_{camera_index} 到 seats_config_on_video.json")

# 主程序
def main():
    global current_row, camera_index, rectangles

    cv2.namedWindow('Frame')

    if not process_video(camera_index):
        return

    while True:
        display = frame.copy()
        for r in rectangles:
            color = ROW_COLORS[(r[4] - 1) % len(ROW_COLORS)]
            cv2.rectangle(display, (r[0], r[1]), (r[2], r[3]), color, 2)
            cv2.putText(display, f"Row {r[4]}", (r[0], r[1] - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

        # === 顶部中央摄像头名称 ===
        camera_label = f"camera_{camera_index}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_scale = 1.2
        thickness = 3
        text_color = (255, 255, 255)

        (text_width, text_height), _ = cv2.getTextSize(camera_label, font, text_scale, thickness)
        text_x = (display.shape[1] - text_width) // 2
        text_y = text_height + 10  # 距离顶部10像素

        cv2.putText(display, camera_label, (text_x, text_y), font, text_scale, text_color, thickness, cv2.LINE_AA)

        # === 左上角状态说明文字（黑色） ===
        info_texts = [
            "a: the number of rows increases",
            "z: the number of rows decreases",
            "c: reset the current mark",
            "s: save the current mark",
            "n: next video",
            "q: exit"
        ]

        y0 = 50  # 避开顶部标题
        for i, text in enumerate(info_texts):
            y = y0 + i * 25
            cv2.putText(display, text, (10, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2, cv2.LINE_AA)

        cv2.imshow('Frame', display)
        key = cv2.waitKey(10) & 0xFF

        if key == ord('a'):
            current_row += 1
            print(f"➡️ 当前排数：{current_row}")

        elif key == ord('z'):
            current_row = max(1, current_row - 1)
            print(f"⬅️ 当前排数：{current_row}")

        elif key == ord('c'):
            rectangles = []
            print(f"♻️ 已重置 camera_{camera_index} 的标定数据")

        elif key == ord('s'):
            save_current_seats()

        elif key == ord('n'):
            camera_index += 1
            if camera_index >= len(video_paths):
                print("📽️ 所有摄像头已处理完毕。")
                break
            cv2.namedWindow('Frame', cv2.WINDOW_NORMAL)
            if not process_video(camera_index):
                break

        elif key == ord('q'):
            print("🛑 已退出程序")
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
