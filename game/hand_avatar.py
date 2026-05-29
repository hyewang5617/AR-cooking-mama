"""
White silhouette hand avatar drawn from MediaPipe landmarks.
Open hand → white/blue. Gripped → green tint.
"""
import cv2
import numpy as np

# Finger segments: each sub-list is a chain of landmark indices
_FINGER_SEGS = [
    [0, 1, 2, 3, 4],    # thumb
    [5, 6, 7, 8],       # index
    [9, 10, 11, 12],    # middle
    [13, 14, 15, 16],   # ring
    [17, 18, 19, 20],   # pinky
]
# Palm outline landmark indices
_PALM_IDX = [0, 1, 2, 5, 9, 13, 17]

# Fingertip indices (for highlighting when open)
_TIP_IDX = [4, 8, 12, 16, 20]


def draw_all(frame, hand_states):
    """Draw a white silhouette avatar for every detected hand."""
    for hs in hand_states:
        if hs.detected and hs.landmarks:
            _draw_one(frame, hs)


def _draw_one(frame, hand_state):
    lms     = hand_state.landmarks
    gripped = hand_state.gripped
    H, W    = frame.shape[:2]

    # Map landmarks to display pixels
    pts = [(int(lm.x * W), int(lm.y * H)) for lm in lms]

    # Colors: fill + outline
    if gripped:
        fill    = (160, 255, 160)   # green tint when gripping
        outline = (30,  100, 30)
    else:
        fill    = (235, 235, 255)   # near-white / slight blue
        outline = (60,  60,  90)

    # Find tight bounding box for a local overlay (performance)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    pad = 35
    x1 = max(0, min(xs) - pad)
    y1 = max(0, min(ys) - pad)
    x2 = min(W, max(xs) + pad)
    y2 = min(H, max(ys) + pad)
    if x2 <= x1 or y2 <= y1:
        return

    rw, rh = x2 - x1, y2 - y1
    canvas = np.zeros((rh, rw, 4), dtype=np.uint8)

    # Shift all points to local coordinates
    lp = [(p[0] - x1, p[1] - y1) for p in pts]

    # ── 1) Dark outline (thick) ────────────────────────────────
    oc = (*outline, 230)
    for seg in _FINGER_SEGS:
        for i in range(len(seg) - 1):
            cv2.line(canvas, lp[seg[i]], lp[seg[i+1]], oc, 20)
    palm = np.array([lp[i] for i in _PALM_IDX])
    cv2.fillPoly(canvas, [palm], oc)

    # ── 2) Light fill (slightly thinner) ──────────────────────
    fc = (*fill, 210)
    for seg in _FINGER_SEGS:
        for i in range(len(seg) - 1):
            cv2.line(canvas, lp[seg[i]], lp[seg[i+1]], fc, 13)
    cv2.fillPoly(canvas, [palm], fc)

    # ── 3) Fingertip circles ───────────────────────────────────
    for t in _TIP_IDX:
        cv2.circle(canvas, lp[t], 9, fc, -1)
        cv2.circle(canvas, lp[t], 9, oc, 2)

    # ── 4) Knuckle joints ─────────────────────────────────────
    knuckle_idx = [1, 2, 3, 5, 6, 9, 10, 13, 14, 17, 18]
    for k in knuckle_idx:
        cv2.circle(canvas, lp[k], 6, fc, -1)

    # ── 5) Alpha-blend onto frame ─────────────────────────────
    roi = frame[y1:y2, x1:x2]
    a   = canvas[:, :, 3:4].astype(np.float32) / 255.0
    roi[:] = (canvas[:, :, :3].astype(np.float32) * a +
              roi.astype(np.float32) * (1.0 - a)).astype(np.uint8)
