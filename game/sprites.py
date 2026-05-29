import cv2
import numpy as np
import os

_ASSET_DIR = os.path.join(os.path.dirname(__file__), '..',
    'AR-cooking-mama', 'Assets', 'Food And kitchen Full Packet', 'Textures')

_cache = {}


def get_knife(size=130):
    key = ('knife', size)
    if key not in _cache:
        _cache[key] = _make_knife(size)
    return _cache[key]


def get_tomato(size=160):
    key = ('tomato', size)
    if key not in _cache:
        _cache[key] = _load_tomato(size)
    return _cache[key]


def get_spatula(size=150):
    key = ('spatula', size)
    if key not in _cache:
        _cache[key] = _make_spatula(size)
    return _cache[key]


def get_bowl(w=260, h=140):
    key = ('bowl', w, h)
    if key not in _cache:
        _cache[key] = _make_bowl(w, h)
    return _cache[key]


# ── Sprite loading ────────────────────────────────────────────────────────────

def _make_knife(size):
    """Chef's knife drawn programmatically, blade pointing straight up."""
    img = np.zeros((size, size, 4), dtype=np.uint8)
    cx  = size // 2

    tip_y    = int(size * 0.03)
    root_y   = int(size * 0.60)
    guard_y2 = int(size * 0.68)
    hndl_y2  = int(size * 0.96)
    bl       = cx - int(size * 0.07)   # blade left x
    br       = cx + int(size * 0.11)   # blade right x (spine side)
    hx1      = cx - int(size * 0.09)
    hx2      = cx + int(size * 0.09)

    # ── blade (steel silver) ──────────────────────────────────────────────────
    blade = np.array([[cx, tip_y], [bl, root_y], [br, root_y]])
    cv2.fillPoly(img, [blade], (200, 208, 220, 255))
    # left shiny edge
    cv2.line(img, (cx, tip_y + 2), (bl, root_y), (240, 248, 255, 210), 2)
    # right spine (slightly darker)
    spine = np.array([[cx, tip_y + 3], [br, root_y],
                      [br - 3, root_y], [cx - 2, tip_y + 6]])
    cv2.fillPoly(img, [spine], (158, 165, 178, 255))

    # ── guard / bolster ───────────────────────────────────────────────────────
    cv2.rectangle(img, (bl - 3, root_y), (br + 3, guard_y2), (125, 132, 145, 255), -1)
    cv2.rectangle(img, (bl - 3, root_y), (br + 3, guard_y2), (85, 90, 100, 255), 2)

    # ── handle (dark wood) ────────────────────────────────────────────────────
    cv2.rectangle(img, (hx1, guard_y2), (hx2, hndl_y2), (48, 78, 112, 255), -1)
    mid_x = (hx1 + hx2) // 2
    # three rivets
    for ry in [guard_y2 + int(size * 0.06),
               guard_y2 + int(size * 0.14),
               guard_y2 + int(size * 0.22)]:
        r = max(2, int(size * 0.028))
        cv2.circle(img, (mid_x, ry), r, (82, 112, 148, 255), -1)
        cv2.circle(img, (mid_x, ry), r, (38, 58, 88,  255), 1)
    # wood grain lines
    for i in range(5):
        ly = guard_y2 + int(size * (0.04 + i * 0.06))
        cv2.line(img, (hx1 + 2, ly), (hx2 - 2, ly), (36, 60, 88, 130), 1)
    cv2.rectangle(img, (hx1, guard_y2), (hx2, hndl_y2), (28, 48, 78, 255), 2)

    return img


def _load_tomato(size):
    path = os.path.join(_ASSET_DIR, 'TomatoBaseColor.png')
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        return _placeholder(size, (0, 0, 200, 255))

    ih, iw = img.shape[:2]
    # Sliced tomato is in the bottom-center region of the UV atlas
    tomato = img[int(ih * 0.45):int(ih * 0.90), int(iw * 0.25):int(iw * 0.65)].copy()
    if tomato.shape[2] == 3:
        tomato = cv2.cvtColor(tomato, cv2.COLOR_BGR2BGRA)

    # Near-black background → transparent
    dark = cv2.inRange(tomato[:, :, :3], (0, 0, 0), (30, 30, 30))
    tomato[:, :, 3] = cv2.bitwise_not(dark)

    return cv2.resize(tomato, (size, size))


def _make_spatula(size):
    """Wooden paddle spatula drawn programmatically."""
    W, H = size // 3, size
    img = np.zeros((H, W, 4), dtype=np.uint8)

    hw = max(W // 3, 3)
    cx = W // 2

    # Handle (dark wood brown)
    cv2.rectangle(img, (cx - hw, H // 3), (cx + hw, H - 6), (40, 80, 130, 255), -1)
    cv2.rectangle(img, (cx - hw, H // 3), (cx + hw, H - 6), (20, 50, 90, 255), 2)
    for i in range(3):
        gy = H // 3 + 10 + i * 18
        cv2.line(img, (cx - hw + 2, gy), (cx + hw - 2, gy), (30, 60, 100, 180), 1)

    # Paddle head (light wood)
    cv2.rectangle(img, (2, 4), (W - 3, H // 3 + 4), (80, 140, 200, 255), -1)
    cv2.rectangle(img, (2, 4), (W - 3, H // 3 + 4), (50, 100, 150, 255), 2)

    # Expand to square canvas
    canvas = np.zeros((H, H, 4), dtype=np.uint8)
    xo = (H - W) // 2
    canvas[:, xo:xo + W] = img
    return cv2.resize(canvas, (size, size))


def _make_bowl(W, H):
    """Side-view pot/bowl drawn programmatically."""
    canvas = np.zeros((H + 20, W, 4), dtype=np.uint8)
    cx = W // 2

    body = np.array([[20, H - 10], [W - 20, H - 10], [W - 50, 20], [50, 20]])
    cv2.fillPoly(canvas, [body], (165, 168, 175, 255))
    cv2.polylines(canvas, [body], True, (110, 112, 118, 255), 3)

    # Rim ellipse
    cv2.ellipse(canvas, (cx, 20), (cx - 45, 14), 0, 0, 360, (190, 192, 198, 255), -1)
    cv2.ellipse(canvas, (cx, 20), (cx - 45, 14), 0, 0, 360, (120, 122, 128, 255), 2)

    # Inner rim
    cv2.ellipse(canvas, (cx, 20), (cx - 65, 9), 0, 0, 360, (140, 142, 150, 255), -1)

    # Highlight
    cv2.line(canvas, (60, H // 2), (W - 60, H // 2 - 8), (220, 222, 228, 180), 3)

    return canvas


def _placeholder(size, color):
    img = np.zeros((size, size, 4), dtype=np.uint8)
    cv2.circle(img, (size // 2, size // 2), size // 2 - 4, color, -1)
    return img


# ── Rendering ─────────────────────────────────────────────────────────────────

def overlay(frame, sprite_bgra, cx, cy, size=None, angle=0.0):
    """Alpha-blend a BGRA sprite centered at pixel (cx, cy) onto a BGR frame."""
    if sprite_bgra is None:
        return
    s = sprite_bgra.copy()

    if size is not None:
        oh, ow = s.shape[:2]
        ratio = size / max(ow, oh)
        nw, nh = max(1, int(ow * ratio)), max(1, int(oh * ratio))
        s = cv2.resize(s, (nw, nh))

    if angle != 0.0:
        sh, sw = s.shape[:2]
        M = cv2.getRotationMatrix2D((sw / 2, sh / 2), angle, 1.0)
        s = cv2.warpAffine(s, M, (sw, sh), flags=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))

    sh, sw = s.shape[:2]
    fh, fw = frame.shape[:2]
    x1, y1 = cx - sw // 2, cy - sh // 2
    x2, y2 = x1 + sw, y1 + sh

    bx1, by1 = max(0, x1), max(0, y1)
    bx2, by2 = min(fw, x2), min(fh, y2)
    if bx2 <= bx1 or by2 <= by1:
        return

    sx1, sy1 = bx1 - x1, by1 - y1
    sx2, sy2 = sx1 + (bx2 - bx1), sy1 + (by2 - by1)

    roi = frame[by1:by2, bx1:bx2]
    spr = s[sy1:sy2, sx1:sx2]
    a   = spr[:, :, 3:4].astype(np.float32) / 255.0
    roi[:] = (spr[:, :, :3].astype(np.float32) * a +
              roi.astype(np.float32) * (1.0 - a)).astype(np.uint8)
