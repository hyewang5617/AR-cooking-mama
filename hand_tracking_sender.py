import cv2
import json
import math
import socket
import time
import urllib.request
import os
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision

UDP_IP   = "127.0.0.1"
UDP_PORT = 5052

PINCH_THRESHOLD = 0.09

PALM_REAL_M = 0.085  # 손목~중지MCP 실제 거리 (미터)
Z_REF_M     = 0.55   # 기준 깊이 (이 거리에서 Unity Z=0)
UNITY_SCALE = 9.0

MODEL_PATH = "hand_landmarker.task"
MODEL_URL  = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)

def ensure_model():
    if not os.path.exists(MODEL_PATH):
        print("Downloading hand landmark model (~8 MB)...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Done.")

def to_unity_xy(nx, ny, fw, fh):
    # 웹캠 정규화 좌표 → 카메라 정규화 좌표 → Unity XY
    # fx ≈ fw * 0.87 (일반 웹캠 ~60° FOV 근사)
    fx = fw * 0.87
    cx, cy = fw / 2.0, fh / 2.0
    x_n = (nx * fw - cx) / fx
    y_n = (ny * fh - cy) / fx
    ux = float(max(-8.0,  min(8.0,   x_n * UNITY_SCALE)))
    uy = float(max(-4.5,  min(4.5,  -y_n * UNITY_SCALE)))
    return round(ux, 4), round(uy, 4)

def calc_depth_z(landmarks, fw, fh):
    # Pinhole Model 역산: Z = fx * D_real / d_pixels
    fx = fw * 0.87
    w0, m9 = landmarks[0], landmarks[9]
    d_px = math.sqrt((w0.x * fw - m9.x * fw)**2 + (w0.y * fh - m9.y * fh)**2)
    if d_px < 1:
        return 0.0
    Z_m = fx * PALM_REAL_M / d_px
    uz  = (Z_REF_M - Z_m) * 6.0
    return round(float(max(-4.0, min(4.0, uz))), 4)

def calc_pinch(landmarks):
    d = math.sqrt((landmarks[4].x - landmarks[8].x)**2 +
                  (landmarks[4].y - landmarks[8].y)**2)
    return d < PINCH_THRESHOLD, round(d, 4)

def calc_palm_center(landmarks):
    return (landmarks[0].x + landmarks[9].x) / 2, \
           (landmarks[0].y + landmarks[9].y) / 2

class PositionSmoother:
    def __init__(self, alpha=0.5):
        self.alpha = alpha
        self._x = self._y = None

    def update(self, x, y):
        if self._x is None:
            self._x, self._y = x, y
        else:
            self._x = self.alpha * x + (1 - self.alpha) * self._x
            self._y = self.alpha * y + (1 - self.alpha) * self._y
        return round(self._x, 4), round(self._y, 4)

class VelocityTracker:
    def __init__(self):
        self._prev = None
        self._t    = None

    def update(self, x, y):
        now = time.time()
        vx = vy = 0.0
        if self._prev and self._t:
            dt = now - self._t
            if dt > 0:
                vx = (x - self._prev[0]) / dt
                vy = (y - self._prev[1]) / dt
        self._prev, self._t = (x, y), now
        return round(vx, 4), round(vy, 4)

CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (5,9),(9,10),(10,11),(11,12),
    (9,13),(13,14),(14,15),(15,16),
    (13,17),(17,18),(18,19),(19,20),
    (0,17),
]

def draw_hand(frame, landmarks, pinched):
    h, w = frame.shape[:2]
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
    color = (0, 80, 255) if pinched else (255, 200, 0)
    for a, b in CONNECTIONS:
        cv2.line(frame, pts[a], pts[b], color, 2)
    for pt in pts:
        cv2.circle(frame, pt, 4, (0, 230, 120), -1)
    cv2.line(frame, pts[4], pts[8], (0, 255, 255), 3)

def main():
    ensure_model()

    base_options = mp_tasks.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.7,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    landmarker = vision.HandLandmarker.create_from_options(options)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    cap = None
    for idx in range(3):
        c = cv2.VideoCapture(idx)
        if c.isOpened():
            ret, _ = c.read()
            if ret:
                cap = c
                print(f"Camera index {idx}")
                break
            c.release()
    if cap is None:
        print("Error: No camera found.")
        return

    smoother = PositionSmoother(alpha=0.5)
    velocity  = VelocityTracker()

    PROC_W, PROC_H = 640, 360
    fps_timer, fps_count, fps_display = time.time(), 0, 0

    cv2.namedWindow("Hand Tracking Sender", cv2.WINDOW_NORMAL)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        small = cv2.resize(frame, (PROC_W, PROC_H))

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=cv2.cvtColor(small, cv2.COLOR_BGR2RGB),
        )
        result = landmarker.detect_for_video(mp_image, int(time.time() * 1000))

        display = cv2.resize(frame, (1280, 720))
        payload = {"detected": False}

        if result.hand_landmarks:
            lms = result.hand_landmarks[0]
            pinched, pinch_dist = calc_pinch(lms)
            px, py = calc_palm_center(lms)
            ux, uy = to_unity_xy(px, py, PROC_W, PROC_H)
            ux, uy = smoother.update(ux, uy)
            vx, vy = velocity.update(ux, uy)
            uz     = calc_depth_z(lms, PROC_W, PROC_H)

            payload = {
                "detected":   True,
                "x":          ux,
                "y":          uy,
                "z":          uz,
                "vx":         vx,
                "vy":         vy,
                "pinched":    pinched,
                "pinch_dist": pinch_dist,
            }

            draw_hand(display, lms, pinched)
            label = f"({'PINCH' if pinched else 'open'})  x={ux:.1f}  y={uy:.1f}  z={uz:.1f}  FPS:{fps_display}"
            cv2.putText(display, label, (20, 40), cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 200), 2)
        else:
            cv2.putText(display, f"No hand  FPS:{fps_display}", (20, 40),
                        cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 80, 255), 2)

        sock.sendto(json.dumps(payload).encode(), (UDP_IP, UDP_PORT))

        fps_count += 1
        if time.time() - fps_timer >= 1.0:
            fps_display = fps_count
            fps_count   = 0
            fps_timer   = time.time()

        cv2.imshow("Hand Tracking Sender", display)
        if cv2.waitKey(1) & 0xFF in (27, ord("q")):
            break

    cap.release()
    sock.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
