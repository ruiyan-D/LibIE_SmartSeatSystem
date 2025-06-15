import cv2

def find_available_cameras(max_index=10):
    for i in range(max_index):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            print(f"摄像头可用：编号 {i}")
            cap.release()
        else:
            print(f"摄像头不可用：编号 {i}")

find_available_cameras()
