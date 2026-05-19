import cv2
import numpy as np
from .base import BaseMiniGame

TARGET = 10


class CuttingGame(BaseMiniGame):
    name = 'Cutting Game'
    instruction = 'Move hand LEFT-RIGHT fast to chop!'
    duration = 20.0

    def __init__(self):
        super().__init__()
        self.cuts = 0
        self._prev_x = None
        self._prev_dx = 0
        self._cooldown = 0
        self._flash = 0
        self._trail = []

    @property
    def succeeded(self):
        return self.cuts >= TARGET

    @property
    def progress_text(self):
        return f'Chops: {self.cuts} / {TARGET}'

    def update(self, hand_pos):
        events = []
        if hand_pos is None:
            return events

        self._trail.append(hand_pos)
        if len(self._trail) > 18:
            self._trail.pop(0)

        x = hand_pos[0]
        if self._prev_x is not None:
            dx = x - self._prev_x
            if self._cooldown > 0:
                self._cooldown -= 1
            else:
                speed = 20
                changed = (
                    self._prev_dx > speed and dx < -speed or
                    self._prev_dx < -speed and dx > speed
                )
                if changed:
                    self.cuts += 1
                    self._flash = 12
                    self._cooldown = 8
                    events.append('cut')
            if abs(dx) > 4:
                self._prev_dx = dx
        self._prev_x = x

        if self._flash > 0:
            self._flash -= 1
        if self.cuts >= TARGET:
            self._complete = True
        return events

    def draw(self, frame, hand_pos):
        h, w = frame.shape[:2]

        # Cutting board
        bx, by = w // 4, h // 2 + 20
        bw, bh = w // 2, h // 5
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (55, 100, 45), -1)
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (35, 70, 25), 3)

        # Ingredient (carrot-like)
        ix, iy = bx + 20, by + 15
        iw, ih = bw - 40, bh - 30
        ratio = min(self.cuts / TARGET, 1.0)
        whole_w = int(iw * (1 - ratio))

        if whole_w > 4:
            cv2.rectangle(frame, (ix, iy), (ix + whole_w, iy + ih), (0, 120, 220), -1)
            cv2.rectangle(frame, (ix, iy), (ix + whole_w, iy + ih), (0, 90, 180), 2)

        if self.cuts > 0:
            slices = min(self.cuts, 20)
            sliced_w = iw - whole_w
            gap = 3
            sw = max(4, (sliced_w - gap * slices) // max(slices, 1))
            for i in range(slices):
                sx = ix + whole_w + gap + i * (sw + gap)
                if sx + sw <= ix + iw:
                    cv2.rectangle(frame, (sx, iy + 2), (sx + sw, iy + ih - 2), (30, 140, 230), -1)
                    cv2.rectangle(frame, (sx, iy + 2), (sx + sw, iy + ih - 2), (0, 100, 190), 1)

        # Trail
        for i, pt in enumerate(self._trail):
            t = i / len(self._trail)
            cv2.circle(frame, pt, max(2, int(t * 6)), (int(80 * t), int(160 * t), 255), -1)

        # Knife following hand
        if hand_pos:
            kx, ky = hand_pos
            cv2.rectangle(frame, (kx - 4, ky - 45), (kx + 4, ky + 5), (210, 210, 210), -1)
            cv2.rectangle(frame, (kx - 5, ky + 5), (kx + 5, ky + 22), (70, 45, 25), -1)

        if self._flash > 0:
            cv2.putText(frame, 'CHOP!', (w // 2 - 60, h // 2 - 10),
                        cv2.FONT_HERSHEY_DUPLEX, 1.8, (0, 255, 255), 4)

        return frame
