import cv2
import json
import numpy as np

# 初始化摄像头列表
cameras = []
camera_ids = [0, 1, 2]  # 初始摄像头ID列表，可扩展

# 尝试初始化所有摄像头
for cam_id in camera_ids:
    cap = cv2.VideoCapture(cam_id)
    if cap.isOpened():
        # 获取实际分辨率以计算宽高比
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        aspect_ratio = width / height

        cameras.append({
            "id": cam_id,
            "cap": cap,
            "frame": None,
            "seats": [],
            "aspect_ratio": aspect_ratio,
            "display_scale": 1.0,
            "display_offset": (0, 0)
        })
    else:
        print(f"警告: 无法打开摄像头 {cam_id}")

if not cameras:
    print("错误: 没有可用的摄像头")
    exit()

# 全局变量
current_cam_idx = 0
is_drawing = False
start_point = None
end_point = None
current_mouse_pos = None
THUMBNAIL_HEIGHT = 120  # 缩略图高度
MAIN_HEIGHT = 600  # 主画面高度
MIN_THUMBNAIL_WIDTH = 100  # 最小缩略图宽度
WINDOW_WIDTH = 800  # 窗口宽度

# 创建窗口
cv2.namedWindow('Camera Seat Marker')
cv2.resizeWindow('Camera Seat Marker', WINDOW_WIDTH, MAIN_HEIGHT + THUMBNAIL_HEIGHT + 50)


def mouse_callback(event, x, y, flags, param):
    global is_drawing, start_point, end_point, current_mouse_pos

    # 更新当前鼠标位置
    current_mouse_pos = (x, y)

    # 检查是否在缩略图区域
    if y < THUMBNAIL_HEIGHT:
        # 只在鼠标点击时切换摄像头
        if event == cv2.EVENT_LBUTTONDOWN:
            # 计算点击的是哪个摄像头缩略图
            total_thumb_width = 0
            for i, cam in enumerate(cameras):
                thumb_width = get_thumbnail_width(cam)
                if total_thumb_width <= x < total_thumb_width + thumb_width:
                    switch_camera(i)
                    break
                total_thumb_width += thumb_width
        return

    # 调整坐标到主画面区域
    y -= THUMBNAIL_HEIGHT

    # 只处理主画面区域的事件
    if event == cv2.EVENT_LBUTTONDOWN:
        is_drawing = True
        # 转换到原始图像坐标
        orig_x, orig_y = display_to_original_coords(x, y)
        start_point = (orig_x, orig_y)

    elif event == cv2.EVENT_LBUTTONUP and is_drawing:
        is_drawing = False
        # 转换到原始图像坐标
        orig_x, orig_y = display_to_original_coords(x, y)
        end_point = (orig_x, orig_y)

        # 确保坐标正确排序 (左上角到右下角)
        x1, y1 = min(start_point[0], end_point[0]), min(start_point[1], end_point[1])
        x2, y2 = max(start_point[0], end_point[0]), max(start_point[1], end_point[1])

        # 保存座位坐标
        cameras[current_cam_idx]["seats"].append([x1, y1, x2, y2])
        print(f"摄像头 {current_cam_idx} 添加座位: [{x1}, {y1}, {x2}, {y2}]")

        # 重置点
        start_point = None
        end_point = None


def display_to_original_coords(display_x, display_y):
    """将显示坐标转换为原始图像坐标"""
    cam = cameras[current_cam_idx]
    if "display_info" not in cam:
        return display_x, display_y

    display_info = cam["display_info"]
    start_x, start_y = display_info["start_x"], display_info["start_y"]
    scale = display_info["scale"]

    # 减去偏移量并除以缩放比例
    orig_x = int((display_x - start_x) / scale)
    orig_y = int((display_y - start_y) / scale)

    # 确保坐标在有效范围内
    frame = cam["frame"]
    if frame is not None:
        h, w = frame.shape[:2]
        orig_x = max(0, min(w - 1, orig_x))
        orig_y = max(0, min(h - 1, orig_y))

    return orig_x, orig_y


def original_to_display_coords(orig_x, orig_y):
    """将原始图像坐标转换为显示坐标"""
    cam = cameras[current_cam_idx]
    if "display_info" not in cam:
        return orig_x, orig_y

    display_info = cam["display_info"]
    start_x, start_y = display_info["start_x"], display_info["start_y"]
    scale = display_info["scale"]

    # 乘以缩放比例并加上偏移量
    display_x = int(orig_x * scale) + start_x
    display_y = int(orig_y * scale) + start_y

    return display_x, display_y


def switch_camera(new_idx):
    global current_cam_idx
    if 0 <= new_idx < len(cameras):
        current_cam_idx = new_idx
        print(f"切换到摄像头 {new_idx} (ID: {cameras[new_idx]['id']})")


def get_thumbnail_width(cam):
    """根据宽高比计算缩略图宽度"""
    aspect_ratio = cam["aspect_ratio"]
    # 保持宽高比计算宽度
    return max(MIN_THUMBNAIL_WIDTH, int(THUMBNAIL_HEIGHT * aspect_ratio))


def draw_ui(combined_frame):
    """绘制用户界面元素"""
    # 绘制顶部缩略图区域分隔线
    cv2.line(combined_frame, (0, THUMBNAIL_HEIGHT),
             (combined_frame.shape[1], THUMBNAIL_HEIGHT),
             (100, 100, 255), 2)

    # 添加底部状态信息
    status_y = THUMBNAIL_HEIGHT + MAIN_HEIGHT + 30
    cv2.putText(combined_frame, "操作说明:", (10, status_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    cv2.putText(combined_frame, "点击缩略图切换摄像头 | 在主画面拖动标记座位", (120, status_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 255), 1)
    cv2.putText(combined_frame, "按键: 's'保存 | 'c'清除当前座位 | 'a'添加摄像头 | 'r'移除摄像头 | 'q'退出",
                (10, status_y + 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 255), 1)


def add_camera(cam_id):
    """添加新摄像头"""
    # 检查是否已存在
    for cam in cameras:
        if cam["id"] == cam_id:
            print(f"摄像头 {cam_id} 已存在")
            return False

    cap = cv2.VideoCapture(cam_id)
    if cap.isOpened():
        # 获取实际分辨率以计算宽高比
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        aspect_ratio = width / height

        cameras.append({
            "id": cam_id,
            "cap": cap,
            "frame": None,
            "seats": [],
            "aspect_ratio": aspect_ratio,
            "display_scale": 1.0,
            "display_offset": (0, 0)
        })
        print(f"成功添加摄像头 {cam_id} (宽高比: {aspect_ratio:.2f})")
        return True
    else:
        print(f"无法打开摄像头 {cam_id}")
        return False


def remove_current_camera():
    """移除当前摄像头"""
    global current_cam_idx

    if len(cameras) <= 1:
        print("不能移除最后一个摄像头")
        return

    # 释放摄像头资源
    cameras[current_cam_idx]["cap"].release()

    # 从列表中移除
    removed_id = cameras[current_cam_idx]["id"]
    cameras.pop(current_cam_idx)

    # 调整当前索引
    current_cam_idx = max(0, current_cam_idx - 1)

    print(f"已移除摄像头 {removed_id}，当前摄像头: {current_cam_idx}")


def create_thumbnail(cam, idx, is_current):
    """创建保持比例的缩略图"""
    thumb_width = get_thumbnail_width(cam)

    # 创建灰色背景
    thumbnail = np.zeros((THUMBNAIL_HEIGHT, thumb_width, 3), dtype=np.uint8) + 50

    if cam["frame"] is not None:
        # 保持宽高比缩放
        h, w = cam["frame"].shape[:2]
        scale = THUMBNAIL_HEIGHT / h

        # 计算居中位置
        new_width = int(w * scale)
        start_x = (thumb_width - new_width) // 2

        # 缩放图像并居中放置
        resized = cv2.resize(cam["frame"], (new_width, THUMBNAIL_HEIGHT))
        thumbnail[:, start_x:start_x + new_width] = resized

        # 在缩略图上绘制座位
        for seat in cam["seats"]:
            # 缩放座位坐标到缩略图尺寸
            x1 = int((seat[0] * scale) + start_x)
            y1 = int(seat[1] * scale)
            x2 = int((seat[2] * scale) + start_x)
            y2 = int(seat[3] * scale)
            cv2.rectangle(thumbnail, (x1, y1), (x2, y2), (0, 255, 0), 1)

        # 添加摄像头标识
        cv2.putText(thumbnail, f"Cam {idx}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.putText(thumbnail, f"ID: {cam['id']}", (10, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 0), 1)
        cv2.putText(thumbnail, f"Seats: {len(cam['seats'])}", (10, 85),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 255), 1)

    else:
        # 无画面时的显示
        cv2.putText(thumbnail, f"Cam {idx}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        cv2.putText(thumbnail, "No Feed", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    # 如果是当前摄像头，添加边框
    if is_current:
        cv2.rectangle(thumbnail, (0, 0), (thumb_width - 1, THUMBNAIL_HEIGHT - 1), (0, 0, 255), 2)

    return thumbnail


def create_main_frame():
    """创建主画面，保持原始比例"""
    cam = cameras[current_cam_idx]

    # 创建灰色背景
    main_frame = np.zeros((MAIN_HEIGHT, WINDOW_WIDTH, 3), dtype=np.uint8) + 50

    if cam["frame"] is not None:
        # 保持宽高比缩放
        h, w = cam["frame"].shape[:2]
        scale = min(WINDOW_WIDTH / w, MAIN_HEIGHT / h)
        new_width = int(w * scale)
        new_height = int(h * scale)

        # 计算居中位置
        start_x = (WINDOW_WIDTH - new_width) // 2
        start_y = (MAIN_HEIGHT - new_height) // 2

        # 存储显示信息用于坐标转换
        cam["display_info"] = {
            "start_x": start_x,
            "start_y": start_y,
            "scale": scale,
            "new_width": new_width,
            "new_height": new_height
        }

        # 缩放图像并居中放置
        resized = cv2.resize(cam["frame"], (new_width, new_height))
        main_frame[start_y:start_y + new_height, start_x:start_x + new_width] = resized

        # 绘制已标记的座位（使用原始坐标）
        for seat in cam["seats"]:
            # 转换坐标到显示位置
            x1 = int(seat[0] * scale) + start_x
            y1 = int(seat[1] * scale) + start_y
            x2 = int(seat[2] * scale) + start_x
            y2 = int(seat[3] * scale) + start_y
            cv2.rectangle(main_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # 绘制当前正在绘制的矩形
        if is_drawing and start_point:
            # 转换起始点到显示坐标
            disp_x1, disp_y1 = original_to_display_coords(start_point[0], start_point[1])

            # 如果有当前鼠标位置，使用它作为结束点
            if current_mouse_pos:
                # 当前鼠标位置已经是显示坐标，但需要调整Y坐标
                mouse_x, mouse_y = current_mouse_pos
                mouse_y -= THUMBNAIL_HEIGHT  # 调整到主画面坐标

                # 绘制矩形
                cv2.rectangle(main_frame, (disp_x1, disp_y1), (mouse_x, mouse_y), (0, 0, 255), 2)

        # 添加摄像头信息
        cv2.putText(main_frame, f"Camera {cam['id']} - Marking Mode",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.putText(main_frame, f"Seats marked: {len(cam['seats'])}",
                    (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
    else:
        # 无画面时的显示
        cv2.putText(main_frame, f"Camera {cam['id']} - No Feed",
                    (WINDOW_WIDTH // 2 - 150, MAIN_HEIGHT // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    return main_frame


# 设置鼠标回调
cv2.setMouseCallback('Camera Seat Marker', mouse_callback)

print("摄像头座位标记工具")
print("=" * 50)
print(f"已初始化 {len(cameras)} 个摄像头")
print("操作说明:")
print("1. 点击顶部缩略图切换摄像头")
print("2. 在主画面中拖动鼠标标记座位")
print("3. 按键功能:")
print("   's' - 保存配置")
print("   'c' - 清除当前摄像头的所有座位")
print("   'a' - 添加新摄像头")
print("   'r' - 移除当前摄像头")
print("   'q' - 退出程序")
print("=" * 50)

while True:
    # 读取所有摄像头
    for cam in cameras:
        ret, frame = cam["cap"].read()
        if ret:
            cam["frame"] = frame
            # 更新宽高比
            h, w = frame.shape[:2]
            cam["aspect_ratio"] = w / h

    # 创建顶部缩略图区域
    thumbnail_row = []
    total_width = 0

    # 计算所有缩略图的总宽度
    for cam in cameras:
        total_width += get_thumbnail_width(cam)

    # 如果总宽度超过窗口宽度，自动调整缩略图大小
    thumbnail_height_adj = THUMBNAIL_HEIGHT
    if total_width > WINDOW_WIDTH:
        scale_factor = WINDOW_WIDTH / total_width
        thumbnail_height_adj = int(THUMBNAIL_HEIGHT * scale_factor)

    # 创建缩略图
    for i, cam in enumerate(cameras):
        thumb = create_thumbnail(cam, i, i == current_cam_idx)

        # 如果调整了高度，重新缩放缩略图
        if thumbnail_height_adj != THUMBNAIL_HEIGHT:
            thumb_width = get_thumbnail_width(cam)
            # 保持宽高比缩放
            new_thumb_width = int(thumb_width * scale_factor)
            thumb = cv2.resize(thumb, (new_thumb_width, thumbnail_height_adj))

        thumbnail_row.append(thumb)

    # 水平拼接缩略图
    top_panel = np.hstack(thumbnail_row) if thumbnail_row else np.zeros((thumbnail_height_adj, WINDOW_WIDTH, 3),
                                                                        dtype=np.uint8)

    # 如果缩略图总宽度小于窗口宽度，添加灰色背景
    if top_panel.shape[1] < WINDOW_WIDTH:
        padding = np.zeros((thumbnail_height_adj, WINDOW_WIDTH - top_panel.shape[1], 3), dtype=np.uint8) + 50
        top_panel = np.hstack([top_panel, padding])
    # 如果缩略图高度不一致，确保高度一致
    elif top_panel.shape[0] != thumbnail_height_adj:
        top_panel = cv2.resize(top_panel, (WINDOW_WIDTH, thumbnail_height_adj))

    # 创建主画面
    main_frame = create_main_frame()

    # 垂直拼接顶部和主画面
    combined_frame = np.vstack([top_panel, main_frame])

    # 添加UI元素
    draw_ui(combined_frame)

    # 显示最终画面
    cv2.imshow('Camera Seat Marker', combined_frame)

    # 处理键盘输入
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):  # 退出
        break
    elif key == ord('s'):  # 保存配置
        config = {}
        for cam in cameras:
            config[f"camera_{cam['id']}"] = {
                "seats": cam["seats"],
                "aspect_ratio": cam["aspect_ratio"]
            }

        with open('seats_config.json', 'w') as f:
            json.dump(config, f, indent=4)
        print("配置已保存到 seats_config.json")
    elif key == ord('c'):  # 清除当前摄像头座位
        cameras[current_cam_idx]["seats"] = []
        print(f"已清除摄像头 {current_cam_idx} 的所有座位")
    elif key == ord('a'):  # 添加新摄像头
        # 尝试添加下一个可用的摄像头ID
        new_id = max(cam["id"] for cam in cameras) + 1 if cameras else 0
        if add_camera(new_id):
            print(f"已添加摄像头 {new_id}，总数: {len(cameras)}")
    elif key == ord('r'):  # 移除当前摄像头
        remove_current_camera()
    elif key in [ord(str(i)) for i in range(10)]:  # 数字键切换摄像头
        num = key - ord('0')
        if num < len(cameras):
            switch_camera(num)

# 释放所有摄像头资源
for cam in cameras:
    if "cap" in cam and cam["cap"].isOpened():
        cam["cap"].release()
cv2.destroyAllWindows()