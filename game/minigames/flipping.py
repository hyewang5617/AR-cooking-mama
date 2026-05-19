import cv2
import numpy as np
from .base import BaseMiniGame

TARGET = 3


class FlippingGame(BaseMiniGame):
    name = 'Flipping Game'
    instruction = 'Move hand UP quickly to flip the pan!'
    duration = 20.0

    def __init__(self):
        super().__init__()
        self.flips = 0
        self._prev_y = None
        self._cooldown = 0
        self._flash = 0
        self._anim = 0
        self.THRESHOLD = -28

    @property
    def succeeded(self):
        return self.flips >= TARGET

    @property
    def progress_text(self):
        return f'Flips: {self.flips} / {TARGET}'

    def update(self, hand_pos):
        events = []
        if hand_pos is None:
            return events

        y = hand_pos[1]
        if self._prev_y is not None:
            dy = y - self._prev_y
            if self._cooldown > 0:
                self._cooldown -= 1
            elif dy < self.THRESHOLD:
                self.flips += 1
                self._flash = 22
                self._anim = 22
                self._cooldown = 28
                events.append('flip')
        self._prev_y = y

        if self.flips >= TARGET:
            self._complete = True
        return events

    def draw(self, frame, hand_pos):
        h, w = frame.shape[:2]
        pan_cx, pan_cy_base = w // 2, h * 3 // 4

        if self._anim > 0:
            offset = int(np.sin(self._anim / 22 * np.pi) * 80)
            self._anim -= 1
        else:
            offset = 0

        pan_cy = pan_cy_base - offset

        # Handle
        cv2.rectangle(frame, (pan_cx + 85, pan_cy - 9), (pan_cx + 160, pan_cy + 9), (55, 55, 55), -1)
        cv2.rectangle(frame, (pan_cx + 85, pan_cy - 9), (pan_cx + 160, pan_cy + 9), (40, 40, 40), 2)

        # Pan body
        cv2.ellipse(frame, (pan_cx, pan_cy), (85, 26), 0, 0, 360, (75, 75, 80), -1)
        cv2.ellipse(frame, (pan_cx, pan_cy), (85, 26), 0, 0, 360, (45, 45, 50), 3)

        # Food (flies up during flip animation)
        food_offset = -offset // 2 if self._anim > 11 else 0
        food_color = (40, 165, 255) if self._anim > 11 else (30, 140, 230)
        cv2.ellipse(frame, (pan_cx, pan_cy - 12 + food_offset), (42, 16), 0, 0, 360, food_color, -1)
        cv2.ellipse(frame, (pan_cx, pan_cy - 12 + food_offset), (42, 16), 0, 0, 360, (20, 110, 200), 2)

        # Upward arrow cue
        if self._cooldown == 0 and hand_pos:
            ax, ay = hand_pos
            cv2.arrowedLine(frame, (ax, ay + 35), (ax, ay - 35), (80, 255, 160), 3, tipLength=0.35)

        if self._flash > 0:
            self._flash -= 1
            cv2.putText(frame, 'FLIP!', (w // 2 - 60, h // 3),
                        cv2.FONT_HERSHEY_DUPLEX, 2.2, (0, 255, 255), 5)

        return frame
