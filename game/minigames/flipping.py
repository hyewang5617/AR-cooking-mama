import cv2
import numpy as np
import math
from .base import BaseMiniGame

TARGET    = 3
FLIP_SPEED = 4.0   # upward vy threshold (world-units/sec, positive = up)


class FlippingGame(BaseMiniGame):
    name        = 'Flipping Game'
    instruction = 'GRIP the pan and flick UP quickly!'
    duration    = 20.0

    def __init__(self):
        super().__init__()
        self.flips     = 0
        self._prev_vy  = 0.0
        self._cooldown = 0
        self._flash    = 0
        self._anim     = 0

    @property
    def succeeded(self):
        return self.flips >= TARGET

    @property
    def progress_text(self):
        return f'Flips: {self.flips} / {TARGET}'

    def update(self, hand):
        events = []
        if not hand.detected:
            self._prev_vy = 0.0
            return events

        vy = hand.vy
        if self._cooldown > 0:
            self._cooldown -= 1
        elif hand.gripped and vy > FLIP_SPEED:
            self.flips    += 1
            self._flash    = 22
            self._anim     = 22
            self._cooldown = 28
            events.append('flip')

        self._prev_vy = vy
        if self._flash > 0:
            self._flash -= 1

        if self.flips >= TARGET:
            self._complete = True
        return events

    def draw(self, frame, hand):
        h, w = frame.shape[:2]
        pan_cx  = w // 2
        pan_cy0 = h * 3 // 4

        if self._anim > 0:
            offset    = int(math.sin(self._anim / 22 * math.pi) * 80)
            self._anim -= 1
        else:
            offset = 0

        pan_cy = pan_cy0 - offset

        # Handle
        cv2.rectangle(frame, (pan_cx + 85, pan_cy - 9), (pan_cx + 160, pan_cy + 9),
                      (55, 55, 55), -1)
        cv2.rectangle(frame, (pan_cx + 85, pan_cy - 9), (pan_cx + 160, pan_cy + 9),
                      (40, 40, 40), 2)

        # Pan body
        cv2.ellipse(frame, (pan_cx, pan_cy), (85, 26), 0, 0, 360, (75, 75, 80), -1)
        cv2.ellipse(frame, (pan_cx, pan_cy), (85, 26), 0, 0, 360, (45, 45, 50), 3)

        # Food
        food_off   = -offset // 2 if self._anim > 11 else 0
        food_color = (40, 165, 255) if self._anim > 11 else (30, 140, 230)
        cv2.ellipse(frame, (pan_cx, pan_cy - 12 + food_off), (42, 16), 0, 0, 360,
                    food_color, -1)
        cv2.ellipse(frame, (pan_cx, pan_cy - 12 + food_off), (42, 16), 0, 0, 360,
                    (20, 110, 200), 2)

        # Upward arrow when ready
        if hand.detected and self._cooldown == 0:
            ax, ay = hand.screen_x, hand.screen_y
            cv2.arrowedLine(frame, (ax, ay + 35), (ax, ay - 35),
                            (80, 255, 160), 3, tipLength=0.35)

        # Grip indicator
        if hand.detected:
            label = 'GRIP' if hand.gripped else 'open  (grip pan)'
            color = (50, 220, 50) if hand.gripped else (80, 80, 220)
            cv2.putText(frame, label, (18, h - 20), cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 2)

        if self._flash > 0:
            cv2.putText(frame, 'FLIP!', (w // 2 - 60, h // 3),
                        cv2.FONT_HERSHEY_DUPLEX, 2.2, (0, 255, 255), 5)

        return frame
