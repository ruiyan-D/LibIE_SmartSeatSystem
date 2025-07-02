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
            cv2.rectangle(temp, (r[0], r[1]), (r[2], r[3]), (0, 255, 0), 2)
            cv2.putText(temp, f"Row {r[4]}", (r[0], r[1] - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
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

   # frame_read = cv2.resize(frame_read, (CANVAS_WIDTH, CANVAS_HEIGHT))  # 统一尺寸（可选）
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
    global current_row, camera_index

    cv2.namedWindow('Frame')

    if not process_video(camera_index):
        return

    while True:
        display = frame.copy()
        for r in rectangles:
            cv2.rectangle(display, (r[0], r[1]), (r[2], r[3]), (0, 255, 0), 2)
            cv2.putText(display, f"Row {r[4]}", (r[0], r[1] - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        # 显示当前状态文字
        info_text = f"Camera: {camera_index} | Row: {current_row} | +:rows+1 -:rows-1 s:save n:next camera q:exit"
        cv2.putText(display, info_text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

        cv2.imshow('Frame', display)
        key = cv2.waitKey(10) & 0xFF

        if key == ord('+'):
            current_row += 1
            print(f"➡️ 当前排数：{current_row}")

        elif key == ord('-'):
            current_row = max(1, current_row - 1)
            print(f"⬅️ 当前排数：{current_row}")

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
