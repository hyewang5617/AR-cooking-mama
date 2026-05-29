"""
Unified cooking scene.

Layout (1280 x 720):
  Left   — cutting station  (cutting board + tomato + knife)
  Center — stirring station (pot + spatula)
  Right  — flipping station (stove + pan)

Task flow:
  grab knife → chop (5x) → grab spatula → stir (3x) → grab pan → flip (2x) → done
"""
import cv2
import math
import time
import numpy as np

from .minigames.base import BaseMiniGame
from .sprites import get_knife, get_spatula, get_tomato, get_bowl, overlay

# ── Task targets ─────────────────────────────────────────────────────────────
CHOP_TARGET  = 5
STIR_TARGET  = 3
FLIP_TARGET  = 2

CHOP_SPEED   = 3.0   # vy world-units/sec for cut detection
FLIP_SPEED   = 3.5   # vy world-units/sec for flip detection
STIR_MIN_R   = 0.40  # world-unit radius minimum for stir detection
GRAB_RADIUS  = 100   # px proximity to grab a tool

# ── Fixed scene positions (for 1280×720) ─────────────────────────────────────
# Cutting station (left)
BOARD_X, BOARD_Y   = 130, 465
BOARD_W, BOARD_H   = 370, 155
KNIFE_REST_X       = 250
KNIFE_REST_Y       = BOARD_Y + 55

# Ingredient
TOMATO_X = 380
TOMATO_Y = BOARD_Y + 55

# Stirring station (center)
POT_X, POT_Y       = 640, 490
POT_WX, POT_WY     = 0.0, -1.5   # world coords of pot centre
SPATULA_REST_X     = 795
SPATULA_REST_Y     = 450

# Flipping station (right)
PAN_X, PAN_Y       = 990, 480
STOVE_CX, STOVE_CY = 990, 530

# ── Phases ─────────────────────────────────────────────────────────────────
PHASES = (
    'grab_knife', 'chopping',
    'grab_spatula', 'stirring',
    'grab_pan', 'flipping',
    'complete',
)

_PHASE_HINTS = {
    'grab_knife':   ('GRAB the knife!',         (0, 200, 255)),
    'chopping':     ('Chop UP ↑↓ DOWN!', (0, 255, 180)),
    'grab_spatula': ('GRAB the spatula!',        (0, 200, 255)),
    'stirring':     ('Stir in CIRCLES!',         (0, 255, 180)),
    'grab_pan':     ('GRAB the pan!',            (0, 200, 255)),
    'flipping':     ('Flick hand UP quickly!',   (50, 200, 255)),
    'complete':     ('ALL DONE!',                (0, 255, 100)),
}


class CookingScene(BaseMiniGame):
    name        = 'Cooking!'
    instruction = 'Grab tools and cook the meal!'
    duration    = 120.0
    grab_phase  = True   # timer starts on first grab

    def __init__(self):
        super().__init__()
        self._phase     = 'grab_knife'
        self._held_tool = None   # 'knife' | 'spatula' | 'pan' | None
        self._held_by   = -1    # hand index (0 or 1) that holds the tool

        # Counters
        self.chops = 0
        self.stirs = 0
        self.flips = 0

        # Action trackers
        self._prev_vy   = 0.0
        self._cooldown  = 0
        self._prev_ang  = None
        self._total_ang = 0.0

        # Mutable tool positions (follow hand when held)
        self._knife_pos   = [KNIFE_REST_X,   KNIFE_REST_Y]
        self._spatula_pos = [SPATULA_REST_X, SPATULA_REST_Y]
        self._pan_pos     = [PAN_X,          PAN_Y]

        # Visual
        self._flash    = 0
        self._flash_lbl = ''
        self._flash_col = (255, 255, 255)
        self._trail    = []
        self._anim_pan = 0   # frames of pan bounce

        # Sprites
        self._knife_spr   = get_knife(size=120)
        self._spatula_spr = get_spatula(size=120)
        self._tomato_spr  = get_tomato(size=150)
        self._bowl_spr    = get_bowl(W=260, H=130)

    # ── BaseMiniGame interface ────────────────────────────────────────────────

    @property
    def succeeded(self):
        return self._phase == 'complete'

    @property
    def progress_text(self):
        p = self._phase
        if p == 'grab_knife':    return f'Step 1/3 — Grab the knife!'
        if p == 'chopping':      return f'Step 1/3 — Chop  {self.chops}/{CHOP_TARGET}'
        if p == 'grab_spatula':  return f'Step 2/3 — Grab the spatula!'
        if p == 'stirring':      return f'Step 2/3 — Stir  {self.stirs}/{STIR_TARGET}'
        if p == 'grab_pan':      return f'Step 3/3 — Grab the pan!'
        if p == 'flipping':      return f'Step 3/3 — Flip  {self.flips}/{FLIP_TARGET}'
        return 'ALL DONE!'

    def update(self, hands):
        events = []
        if self._flash > 0:
            self._flash -= 1
        if self._anim_pan > 0:
            self._anim_pan -= 1

        # Update motion trail for the active (held) hand
        active = self._get_active_hand(hands)
        if active:
            self._trail.append((active.screen_x, active.screen_y))
        else:
            self._trail.clear()
        if len(self._trail) > 35:
            self._trail.pop(0)

        # Dispatch by phase
        if self._phase == 'grab_knife':
            events += self._try_grab(hands, self._knife_pos, 'knife', 'chopping')

        elif self._phase == 'chopping':
            self._sync_tool_pos(active)
            if active:
                events += self._do_chop(active)
            else:
                self._prev_vy = 0.0

        elif self._phase == 'grab_spatula':
            events += self._try_grab(hands, self._spatula_pos, 'spatula', 'stirring')

        elif self._phase == 'stirring':
            self._sync_tool_pos(active)
            if active:
                events += self._do_stir(active)
            else:
                self._prev_ang = None

        elif self._phase == 'grab_pan':
            events += self._try_grab(hands, self._pan_pos, 'pan', 'flipping')

        elif self._phase == 'flipping':
            self._sync_tool_pos(active)
            if active:
                events += self._do_flip(active)
            else:
                self._prev_vy = 0.0

        return events

    # ── Private helpers ───────────────────────────────────────────────────────

    def _try_grab(self, hands, rest_pos, tool, next_phase):
        for i, hand in enumerate(hands):
            if not hand.detected or not hand.gripped:
                continue
            dx = hand.screen_x - rest_pos[0]
            dy = hand.screen_y - rest_pos[1]
            if dx * dx + dy * dy < GRAB_RADIUS ** 2:
                self._held_tool = tool
                self._held_by   = i
                self._phase     = next_phase
                self._begin_timer()
                self._prev_vy   = 0.0
                self._prev_ang  = None
                self._total_ang = 0.0
                self._cooldown  = 0
                self._flash_event('GRAB!', (0, 220, 255), 8)
                return ['grab']
        return []

    def _get_active_hand(self, hands):
        if self._held_by < 0:
            return None
        if self._held_by >= len(hands):
            self._held_by   = -1
            self._held_tool = None
            return None
        hand = hands[self._held_by]
        if not hand.detected or not hand.gripped:
            self._held_by   = -1
            self._held_tool = None
            return None
        return hand

    def _sync_tool_pos(self, hand):
        if hand is None:
            return
        if self._held_tool == 'knife':
            self._knife_pos = [hand.screen_x, hand.screen_y]
        elif self._held_tool == 'spatula':
            self._spatula_pos = [hand.screen_x, hand.screen_y]
        elif self._held_tool == 'pan':
            self._pan_pos = [hand.screen_x, hand.screen_y]

    def _do_chop(self, hand):
        vy = hand.vy
        if self._cooldown > 0:
            self._cooldown -= 1
            self._prev_vy = vy
            return []
        changed = (self._prev_vy >  CHOP_SPEED and vy < -CHOP_SPEED) or \
                  (self._prev_vy < -CHOP_SPEED and vy >  CHOP_SPEED)
        self._prev_vy = vy
        if changed:
            self.chops    += 1
            self._cooldown = 6
            self._flash_event('CHOP!', (0, 255, 200), 12)
            if self.chops >= CHOP_TARGET:
                self._held_tool = None
                self._held_by   = -1
                self._phase     = 'grab_spatula'
            return ['cut']
        return []

    def _do_stir(self, hand):
        dx = hand.x - POT_WX
        dy = hand.y - POT_WY
        if math.sqrt(dx * dx + dy * dy) < STIR_MIN_R:
            return []
        angle = math.atan2(dy, dx)
        if self._prev_ang is not None:
            delta = angle - self._prev_ang
            if delta >  math.pi: delta -= 2 * math.pi
            if delta < -math.pi: delta += 2 * math.pi
            self._total_ang += delta
            new_stirs = int(abs(self._total_ang) / (2 * math.pi))
            if new_stirs > self.stirs:
                self.stirs = new_stirs
                self._flash_event('STIR!', (0, 230, 180), 14)
                if self.stirs >= STIR_TARGET:
                    self._held_tool = None
                    self._held_by   = -1
                    self._phase     = 'grab_pan'
                    self._prev_ang  = None
                    return ['stir']
        self._prev_ang = angle
        return []

    def _do_flip(self, hand):
        vy = hand.vy
        if self._cooldown > 0:
            self._cooldown -= 1
            self._prev_vy = vy
            return []
        if vy > FLIP_SPEED:
            self.flips    += 1
            self._cooldown = 28
            self._anim_pan = 22
            self._flash_event('FLIP!', (255, 200, 50), 18)
            if self.flips >= FLIP_TARGET:
                self._held_tool = None
                self._held_by   = -1
                self._phase     = 'complete'
                self._complete  = True
            return ['flip']
        self._prev_vy = vy
        return []

    def _flash_event(self, label, color, frames):
        self._flash     = frames
        self._flash_lbl = label
        self._flash_col = color

    # ── Drawing ───────────────────────────────────────────────────────────────

    def draw(self, frame, hands):
        h, w = frame.shape[:2]

        # Kitchen counter background strip
        _draw_counter(frame, w, h)

        # --- Stations ---
        _draw_cutting_station(frame, w, h)
        self._draw_stirring_station(frame)
        self._draw_flipping_station(frame)

        # --- Ingredient ---
        self._draw_tomato(frame)

        # --- Tools (static or following hand) ---
        self._draw_tools(frame)

        # --- Motion trail ---
        if len(self._trail) > 1:
            for i in range(1, len(self._trail)):
                a = i / len(self._trail)
                cv2.line(frame, self._trail[i - 1], self._trail[i],
                         (int(50 * a), int(180 * a), 255), max(1, int(a * 4)), cv2.LINE_AA)

        # --- Flash label ---
        if self._flash > 0:
            cx = w // 2
            cy = h // 3
            _shadow_text(frame, self._flash_lbl, cx, cy, 2.4, self._flash_col, 5, center=True)

        # --- Task hint banner ---
        self._draw_hint(frame, w, h)

        return frame

    def _draw_tomato(self, frame):
        overlay(frame, self._tomato_spr, TOMATO_X, TOMATO_Y, size=150)
        if self.chops > 0:
            n = min(self.chops, CHOP_TARGET)
            for i in range(n):
                ang = math.radians(i * 30 - (n - 1) * 15 + 90)
                r   = 62
                x1  = int(TOMATO_X + math.cos(ang) * r)
                y1  = int(TOMATO_Y + math.sin(ang) * r)
                x2  = int(TOMATO_X - math.cos(ang) * r)
                y2  = int(TOMATO_Y - math.sin(ang) * r)
                cv2.line(frame, (x1, y1), (x2, y2), (180, 210, 255), 2, cv2.LINE_AA)

    def _draw_stirring_station(self, frame):
        # Pot sprite
        overlay(frame, self._bowl_spr, POT_X, POT_Y)
        # Animated bubbles
        for i in range(6):
            bx = POT_X + int((i - 2.5) * 28)
            by = POT_Y - int(abs(math.sin(time.time() * 2.5 + i)) * 14) - 5
            cv2.circle(frame, (bx, by), 6, (170, 185, 255), -1)
        # Stir arc progress
        frac    = (abs(self._total_ang) % (2 * math.pi)) / (2 * math.pi)
        arc_end = int(frac * 360)
        if arc_end > 0 and self._phase == 'stirring':
            bh = self._bowl_spr.shape[0]
            bw = self._bowl_spr.shape[1]
            rx, ry = bw // 2 + 18, bh // 4 + 10
            cv2.ellipse(frame, (POT_X, POT_Y), (rx, ry), 0,
                        -90, -90 + arc_end, (0, 220, 180), 4)

    def _draw_flipping_station(self, frame):
        # Stove ring
        cv2.ellipse(frame, (STOVE_CX, STOVE_CY), (90, 28), 0, 0, 360, (50, 50, 55), -1)
        cv2.ellipse(frame, (STOVE_CX, STOVE_CY), (90, 28), 0, 0, 360, (80, 80, 90), 2)
        cv2.ellipse(frame, (STOVE_CX, STOVE_CY), (65, 20), 0, 0, 360, (60, 40, 40), 2)

        # Pan with bounce animation
        anim_off = int(math.sin(self._anim_pan / 22 * math.pi) * 70) if self._anim_pan > 0 else 0
        px, py   = self._pan_pos[0], self._pan_pos[1] - anim_off

        # Handle
        cv2.rectangle(frame, (px + 70, py - 9), (px + 150, py + 9), (55, 55, 55), -1)
        cv2.rectangle(frame, (px + 70, py - 9), (px + 150, py + 9), (40, 40, 40), 2)
        # Pan body
        cv2.ellipse(frame, (px, py), (80, 24), 0, 0, 360, (75, 75, 80), -1)
        cv2.ellipse(frame, (px, py), (80, 24), 0, 0, 360, (45, 45, 50), 3)
        # Food on pan
        food_off   = -anim_off // 2 if self._anim_pan > 11 else 0
        food_color = (40, 165, 255) if self._anim_pan > 11 else (30, 140, 230)
        cv2.ellipse(frame, (px, py - 10 + food_off), (38, 14), 0, 0, 360, food_color, -1)

        # Upward arrow cue
        if self._phase == 'flipping' and self._held_tool == 'pan' and self._cooldown == 0:
            cv2.arrowedLine(frame, (px, py + 40), (px, py - 40),
                            (80, 255, 160), 3, tipLength=0.35)

    def _draw_tools(self, frame):
        p = self._phase

        # Knife: upright when held, lying flat (90°) when at rest
        knife_ang = 0 if self._held_tool == 'knife' else 90
        overlay(frame, self._knife_spr,
                self._knife_pos[0], self._knife_pos[1], size=120, angle=knife_ang)
        if p == 'grab_knife':
            _grab_ring(frame, self._knife_pos)

        # Spatula: visible once knife phase is done
        if self.chops >= CHOP_TARGET or p not in ('grab_knife', 'chopping'):
            spatula_ang = 0 if self._held_tool == 'spatula' else -45
            overlay(frame, self._spatula_spr,
                    self._spatula_pos[0], self._spatula_pos[1], size=120, angle=spatula_ang)
            if p == 'grab_spatula':
                _grab_ring(frame, self._spatula_pos)

        # Pan grab hint
        if p == 'grab_pan':
            _grab_ring(frame, self._pan_pos)

    def _draw_hint(self, frame, w, h):
        p     = self._phase
        text, color = _PHASE_HINTS.get(p, ('', (255, 255, 255)))
        if not text:
            return
        # Semi-transparent banner behind text
        _panel(frame, 0, 82, w, 44)
        count_str = ''
        if p == 'chopping':    count_str = f'  ({self.chops}/{CHOP_TARGET})'
        elif p == 'stirring':  count_str = f'  ({self.stirs}/{STIR_TARGET})'
        elif p == 'flipping':  count_str = f'  ({self.flips}/{FLIP_TARGET})'
        _shadow_text(frame, text + count_str, w // 2, 116, 0.9, color, 2, center=True)


# ── Scene drawing helpers (module-level) ─────────────────────────────────────

def _draw_counter(frame, w, h):
    cy = int(h * 0.60)
    roi = frame[cy:, :]
    bg  = np.full_like(roi, (38, 33, 28))
    cv2.addWeighted(roi, 0.55, bg, 0.45, 0, roi)
    cv2.line(frame, (0, cy), (w, cy), (75, 65, 55), 3)


def _draw_cutting_station(frame, w, h):
    bx, by, bw, bh = BOARD_X, BOARD_Y, BOARD_W, BOARD_H
    cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (55, 100, 45), -1)
    cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (35, 70, 25), 3)
    for i in range(1, 5):
        lx = bx + bw * i // 5
        cv2.line(frame, (lx, by + 4), (lx, by + bh - 4), (45, 85, 35), 1)


def _grab_ring(frame, pos):
    t = time.time()
    r = int(52 + 14 * math.sin(t * 5))
    cv2.circle(frame, (int(pos[0]), int(pos[1])), r, (0, 200, 255), 2, cv2.LINE_AA)
    _shadow_text(frame, 'GRAB', int(pos[0]), int(pos[1]) - r - 10, 0.55, (0, 200, 255), 1, center=True)


def _panel(frame, x, y, w, h, color=(15, 15, 15), alpha=0.6):
    fh, fw = frame.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(fw, x + w), min(fh, y + h)
    if x2 <= x1 or y2 <= y1:
        return
    roi = frame[y1:y2, x1:x2]
    bg  = np.empty_like(roi)
    bg[:] = color
    frame[y1:y2, x1:x2] = cv2.addWeighted(bg, alpha, roi, 1 - alpha, 0)


def _shadow_text(frame, text, x, y, scale, color, thickness=2, center=False):
    font = cv2.FONT_HERSHEY_DUPLEX
    if center:
        tw, _ = cv2.getTextSize(text, font, scale, thickness)[0]
        x = x - tw // 2
    cv2.putText(frame, text, (x + 2, y + 2), font, scale, (0, 0, 0), thickness + 2)
    cv2.putText(frame, text, (x, y), font, scale, color, thickness)
