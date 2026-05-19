import cv2
import numpy as np

FONT = cv2.FONT_HERSHEY_DUPLEX
COLOR_PRIMARY = (30, 190, 255)
COLOR_SUCCESS = (60, 220, 60)
COLOR_DANGER  = (60, 60, 220)
COLOR_WHITE   = (255, 255, 255)
COLOR_GREY    = (150, 150, 150)


def draw_text(frame, text, pos, scale=1.0, color=COLOR_WHITE, thickness=2):
    x, y = pos
    cv2.putText(frame, text, (x + 1, y + 1), FONT, scale, (0, 0, 0), thickness + 2)
    cv2.putText(frame, text, (x, y), FONT, scale, color, thickness)


def draw_text_centered(frame, text, y, scale=1.0, color=COLOR_WHITE, thickness=2):
    size = cv2.getTextSize(text, FONT, scale, thickness)[0]
    x = (frame.shape[1] - size[0]) // 2
    draw_text(frame, text, (x, y), scale, color, thickness)


def draw_progress_bar(frame, x, y, w, h, progress, color=COLOR_SUCCESS):
    cv2.rectangle(frame, (x, y), (x + w, y + h), (50, 50, 50), -1)
    fill = int(w * max(0.0, min(1.0, progress)))
    if fill > 0:
        cv2.rectangle(frame, (x, y), (x + fill, y + h), color, -1)
    cv2.rectangle(frame, (x, y), (x + w, y + h), COLOR_WHITE, 1)


def draw_panel(frame, x, y, w, h, alpha=0.65, color=(15, 15, 15)):
    fh, fw = frame.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(fw, x + w), min(fh, y + h)
    if x2 <= x1 or y2 <= y1:
        return
    roi = frame[y1:y2, x1:x2]
    bg = np.empty_like(roi)
    bg[:] = color
    frame[y1:y2, x1:x2] = cv2.addWeighted(bg, alpha, roi, 1 - alpha, 0)


def dim(frame, alpha=0.5):
    overlay = np.zeros_like(frame)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
