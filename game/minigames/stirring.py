import cv2
import numpy as np
import time
from .base import BaseMiniGame

TARGET = 5


class StirringGame(BaseMiniGame):
    name = 'Stirring Game'
    instruction = 'Move hand in CIRCLES to stir!'
    duration = 25.0

    def __init__(self):
        super().__init__()
        self.stirs = 0
        self._total_angle = 0.0
        self._prev_angle = None
        self._flash = 0
        self._trail = []
        self._center = (320, 240)

    @property
    def succeeded(self):
        return self.stirs >= TARGET

    @property
    def progress_text(self):
        return f'Stirs: {self.stirs} / {TARGET}'

    def update(self, hand_pos):
        events = []
        if hand_pos is None:
            return events

        self._trail.append(hand_pos)
        if len(self._trail) > 50:
            self._trail.pop(0)

        cx, cy = self._center
        dx, dy = hand_pos[0] - cx, hand_pos[1] - cy
        if np.sqrt(dx * dx + dy * dy) < 25:
            return events

        angle = np.arctan2(dy, dx)
        if self._prev_angle is not None:
            delta = angle - self._prev_angle
            if delta > np.pi:
                delta -= 2 * np.pi
            elif delta < -np.pi:
                delta += 2 * np.pi
            self._total_angle += delta
            new_stirs = int(abs(self._total_angle) / (2 * np.pi))
            if new_stirs > self.stirs:
                self.stirs = new_stirs
                self._flash = 18
                events.append('stir')
        self._prev_angle = angle

        if self.stirs >= TARGET:
            self._complete = True
        return events

    def draw(self, frame, hand_pos):
        h, w = frame.shape[:2]
        self._center = (w // 2, h // 2 + 30)
        cx, cy = self._center
        r = min(h, w) // 5

        # Pot body
        cv2.ellipse(frame, (cx, cy + r // 2), (r + 10, r // 3 + 5), 0, 0, 360, (50, 55, 70), -1)
        cv2.ellipse(frame, (cx, cy), (r, r // 2), 0, 0, 360, (70, 75, 95), -1)
        cv2.ellipse(frame, (cx, cy), (r, r // 2), 0, 0, 360, (40, 42, 55), 4)

        # Handles
        cv2.rectangle(frame, (cx - r - 30, cy - 10), (cx - r, cy + 10), (55, 58, 75), -1)
        cv2.rectangle(frame, (cx + r, cy - 10), (cx + r + 30, cy + 10), (55, 58, 75), -1)

        # Bubbles
        for i in range(6):
            bx = cx + int((i - 2.5) * 25)
            by = cy - int(abs(np.sin(time.time() * 2.5 + i)) * 18) - 5
            cv2.circle(frame, (bx, by), 7, (170, 185, 255), -1)

        # Trail
        if len(self._trail) > 1:
            for i in range(1, len(self._trail)):
                a = i / len(self._trail)
                color = (int(60 * a), int(200 * a), 255)
                cv2.line(frame, self._trail[i - 1], self._trail[i], color, max(1, int(a * 4)))

        # Progress arc for current rotation
        progress_frac = (abs(self._total_angle) % (2 * np.pi)) / (2 * np.pi)
        arc_end = int(progress_frac * 360)
        if arc_end > 0:
            cv2.ellipse(frame, (cx, cy), (r + 25, r // 2 + 14), 0, -90, -90 + arc_end,
                        (0, 220, 180), 4)

        # Spoon following hand
        if hand_pos:
            sx, sy = hand_pos
            cv2.line(frame, (sx, sy), (cx, cy), (190, 170, 140), 4)
            cv2.circle(frame, (sx, sy), 13, (200, 180, 150), -1)
            cv2.circle(frame, (sx, sy), 13, (150, 130, 100), 2)

        if self._flash > 0:
            self._flash -= 1
            cv2.putText(frame, f'STIR! {self.stirs}/{TARGET}', (w // 2 - 90, 90),
                        cv2.FONT_HERSHEY_DUPLEX, 1.4, (0, 230, 190), 3)

        return frame
