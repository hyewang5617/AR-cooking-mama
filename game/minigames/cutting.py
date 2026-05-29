import cv2
import numpy as np
import math
from .base import BaseMiniGame
from ..sprites import get_knife, get_tomato, overlay

TARGET    = 8
CUT_SPEED = 3.0   # world-units/sec vy threshold


class CuttingGame(BaseMiniGame):
    name        = 'Cutting Game'
    instruction = 'GRIP the knife and chop UP-DOWN!'
    duration    = 20.0

    def __init__(self):
        super().__init__()
        self.cuts      = 0
        self._prev_vy  = 0.0
        self._cooldown = 0
        self._flash    = 0
        self._trail    = []
        self._knife    = get_knife(size=130)
        self._tomato   = get_tomato(size=160)

    @property
    def succeeded(self):
        return self.cuts >= TARGET

    @property
    def progress_text(self):
        return f'Chops: {self.cuts} / {TARGET}'

    def update(self, hand):
        events = []
        if not hand.detected:
            self._prev_vy = 0.0
            return events

        if hand.gripped:
            self._trail.append((hand.screen_x, hand.screen_y))
        if len(self._trail) > 18:
            self._trail.pop(0)

        if not hand.gripped:
            self._prev_vy = hand.vy
            return events

        vy = hand.vy
        if self._cooldown > 0:
            self._cooldown -= 1
        else:
            changed = (self._prev_vy >  CUT_SPEED and vy < -CUT_SPEED) or \
                      (self._prev_vy < -CUT_SPEED and vy >  CUT_SPEED)
            if changed:
                self.cuts     += 1
                self._flash    = 12
                self._cooldown = 6
                events.append('cut')

        self._prev_vy = vy
        if self._flash > 0:
            self._flash -= 1
        if self.cuts >= TARGET:
            self._complete = True
        return events

    def draw(self, frame, hand):
        h, w = frame.shape[:2]

        # Cutting board
        bx, by = w // 4, h // 2 + 20
        bw, bh = w // 2, h // 5
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (55, 100, 45), -1)
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (35, 70, 25), 3)
        # Wood grain
        for i in range(1, 5):
            lx = bx + bw * i // 5
            cv2.line(frame, (lx, by + 4), (lx, by + bh - 4), (45, 85, 35), 1)

        # Tomato sprite centered on board
        tom_cx = bx + bw // 2
        tom_cy = by + bh // 2
        overlay(frame, self._tomato, tom_cx, tom_cy, size=min(bw - 40, bh + 20))

        # Cut lines accumulate on top of the tomato
        if self.cuts > 0:
            n = min(self.cuts, TARGET)
            for i in range(n):
                angle_deg = (i * 25) - (n - 1) * 12.5
                rad = math.radians(angle_deg + 90)
                r   = 70
                x1  = int(tom_cx + math.cos(rad) * r)
                y1  = int(tom_cy + math.sin(rad) * r)
                x2  = int(tom_cx - math.cos(rad) * r)
                y2  = int(tom_cy - math.sin(rad) * r)
                cv2.line(frame, (x1, y1), (x2, y2), (180, 200, 255), 2, cv2.LINE_AA)

        # Hand trail
        for i, pt in enumerate(self._trail):
            t = i / max(len(self._trail), 1)
            cv2.circle(frame, pt, max(2, int(t * 5)), (int(80 * t), int(160 * t), 255), -1)

        # Knife sprite follows hand
        if hand.detected:
            overlay(frame, self._knife, hand.screen_x, hand.screen_y, size=130)

        # Grip indicator
        if hand.detected:
            label = 'GRIP' if hand.gripped else 'open  (grip to cut)'
            color = (50, 220, 50) if hand.gripped else (80, 80, 220)
            cv2.putText(frame, label, (18, h - 20), cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 2)

        # Flash on cut
        if self._flash > 0:
            cv2.putText(frame, 'CHOP!', (w // 2 - 60, h // 2 - 20),
                        cv2.FONT_HERSHEY_DUPLEX, 1.8, (0, 255, 255), 4)

        return frame
