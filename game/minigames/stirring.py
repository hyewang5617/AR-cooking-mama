import cv2
import numpy as np
import math
import time
from .base import BaseMiniGame
from ..sprites import get_spatula, get_bowl, overlay

TARGET = 5

# Bowl center in world coordinates
BOWL_WX, BOWL_WY = 0.0, -1.5


def _world_to_screen(wx, wy, W=1280, H=720):
    sx = int((wx / 8.0 + 1.0) * W / 2)
    sy = int((-wy / 4.5 + 1.0) * H / 2)
    return sx, sy


class StirringGame(BaseMiniGame):
    name        = 'Stirring Game'
    instruction = 'GRIP the spatula and stir in CIRCLES!'
    duration    = 25.0

    def __init__(self):
        super().__init__()
        self.stirs       = 0
        self._total_ang  = 0.0
        self._prev_ang   = None
        self._flash      = 0
        self._trail      = []
        self._spatula    = get_spatula(size=150)
        self._bowl       = get_bowl(W=280, H=150)

    @property
    def succeeded(self):
        return self.stirs >= TARGET

    @property
    def progress_text(self):
        return f'Stirs: {self.stirs} / {TARGET}'

    def update(self, hand):
        events = []
        if not hand.detected or not hand.gripped:
            self._prev_ang = None
            return events

        self._trail.append((hand.screen_x, hand.screen_y))
        if len(self._trail) > 50:
            self._trail.pop(0)

        dx = hand.x - BOWL_WX
        dy = hand.y - BOWL_WY
        if math.sqrt(dx * dx + dy * dy) < 0.4:
            return events

        angle = math.atan2(dy, dx)
        if self._prev_ang is not None:
            delta = angle - self._prev_ang
            if delta > math.pi:
                delta -= 2 * math.pi
            elif delta < -math.pi:
                delta += 2 * math.pi
            self._total_ang += delta
            new_stirs = int(abs(self._total_ang) / (2 * math.pi))
            if new_stirs > self.stirs:
                self.stirs  = new_stirs
                self._flash = 18
                events.append('stir')

        self._prev_ang = angle
        if self.stirs >= TARGET:
            self._complete = True
        return events

    def draw(self, frame, hand):
        h, w = frame.shape[:2]
        bowl_sx, bowl_sy = _world_to_screen(BOWL_WX, BOWL_WY, w, h)

        # Bowl sprite
        overlay(frame, self._bowl, bowl_sx, bowl_sy)

        # Bubbles (animated)
        for i in range(6):
            bx = bowl_sx + int((i - 2.5) * 28)
            by = bowl_sy - int(abs(math.sin(time.time() * 2.5 + i)) * 16) - 8
            cv2.circle(frame, (bx, by), 7, (170, 185, 255), -1)

        # Trail
        if len(self._trail) > 1:
            for i in range(1, len(self._trail)):
                a     = i / len(self._trail)
                color = (int(60 * a), int(200 * a), 255)
                cv2.line(frame, self._trail[i - 1], self._trail[i],
                         color, max(1, int(a * 4)), cv2.LINE_AA)

        # Progress arc around bowl
        frac    = (abs(self._total_ang) % (2 * math.pi)) / (2 * math.pi)
        arc_end = int(frac * 360)
        if arc_end > 0:
            bowl_bh = self._bowl.shape[0]
            bowl_bw = self._bowl.shape[1]
            rx, ry  = bowl_bw // 2 + 20, bowl_bh // 4 + 10
            cv2.ellipse(frame, (bowl_sx, bowl_sy), (rx, ry), 0,
                        -90, -90 + arc_end, (0, 220, 180), 4)

        # Grip indicator
        if hand.detected:
            label = 'GRIP' if hand.gripped else 'open  (grip spatula)'
            color = (50, 220, 50) if hand.gripped else (80, 80, 220)
            cv2.putText(frame, label, (18, h - 20), cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 2)

        # Spatula sprite follows hand; rotate toward bowl center
        if hand.detected:
            dx  = hand.screen_x - bowl_sx
            dy  = hand.screen_y - bowl_sy
            ang = math.degrees(math.atan2(dy, dx)) if (abs(dx) + abs(dy)) > 5 else 0.0
            overlay(frame, self._spatula, hand.screen_x, hand.screen_y, size=130, angle=ang)

        if self._flash > 0:
            self._flash -= 1
            cv2.putText(frame, f'STIR! {self.stirs}/{TARGET}', (w // 2 - 100, 90),
                        cv2.FONT_HERSHEY_DUPLEX, 1.4, (0, 230, 190), 3)

        return frame
