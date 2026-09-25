"""
Optical Lens Magnifier
----------------------
A physically-simulated magnifying glass with:
  - Lensmaker's equation focal length (symmetric biconvex)
  - Snell's law barrel/pincushion distortion
  - Adjustable: refractive index, curvature, thickness, lens height, zoom
  - Presets via dropdown: Reading Glass, Jeweler's Loupe, Paperweight, Fish-eye, Flat
  - Radial parameter icons around the lens rim with drawn symbols
  - Compact bottom HUD with presets, always-on-top, resize, close
  - Draggable, resizable, always-on-top floating window

Requirements:
    pip install pygame mss numpy
"""

import math
import pygame
import numpy as np
import mss
import sys

# ── Platform-specific imports (consolidated) ──────────────────────────────────

_HAS_WIN32 = False
try:
    import ctypes
    import ctypes.wintypes
    _HAS_WIN32 = hasattr(ctypes, 'windll')
except ImportError:
    pass

# ── Constants ─────────────────────────────────────────────────────────────────

TITLE        = "Optical Magnifier"
DEFAULT_SIZE = 480
MIN_SIZE     = 120
MAX_SIZE     = 800
FPS          = 30

# Default optical parameters.  UI exposes C = 1/R (curvature).
DEFAULT_N    = 1.5
DEFAULT_C    = 0.8
DEFAULT_D    = 0.05
DEFAULT_H    = 0.30
DEFAULT_Z    = 1.0
DEFAULT_CA   = 0.50         # chromatic aberration strength
DEFAULT_EB   = 0.2          # edge blur/softness strength

PARAM_STEP  = {'n': 0.05, 'C': 0.05, 'd': 0.02, 'H': 0.05, 'Z': 0.05,
               'CA': 0.05, 'EB': 0.05}
PARAM_RANGE = {
    'n': (1.0,  3.0),
    'C': (-20.0, 20.0),
    'd': (0.0,  1.0),
    'H': (0.01, 5.0),
    'Z': (0.2,  5.0),
    'CA': (0.0, 2.0),
    'EB': (0.0, 1.0),
}

# ── Presets ───────────────────────────────────────────────────────────────────

PRESETS = {
    'Reading':     {'n': 1.52, 'C': 0.80, 'd': 0.04, 'H': 0.35, 'Z': 1.0, 'CA': 0.05, 'EB': 0.15},
    'Loupe':       {'n': 1.72, 'C': 4.00, 'd': 0.20, 'H': 0.12, 'Z': 1.0, 'CA': 0.10, 'EB': 0.25},
    'Paperweight': {'n': 1.90, 'C': 0.50, 'd': 0.80, 'H': 0.05, 'Z': 1.0, 'CA': 0.10, 'EB': 0.30},
    'Fish-eye':    {'n': 1.40, 'C': 12.0, 'd': 0.10, 'H': 0.60, 'Z': 1.0, 'CA': 0.12, 'EB': 0.40},
    'Flat':        {'n': 1.50, 'C': 0.01, 'd': 0.02, 'H': 0.50, 'Z': 1.0, 'CA': 0.00, 'EB': 0.00},
    'Peephole':    {'n': 1.50, 'C': -2.00, 'd': 0.10, 'H': 0.15, 'Z': 1.0, 'CA': 0.04, 'EB': 0.20},
    'Spoon':       {'n': 1.55, 'C': -3.00, 'd': 0.06, 'H': 0.15, 'Z': 1.5, 'CA': 0.03, 'EB': 0.15},
    'Globe':       {'n': 1.50, 'C': -8.00, 'd': 0.04, 'H': 0.05, 'Z': 3.0, 'CA': 0.10, 'EB': 0.35},
}
PRESET_ORDER = ['Reading', 'Loupe', 'Paperweight', 'Fish-eye', 'Flat',
                'Peephole', 'Spoon', 'Globe']

# ── Colors ────────────────────────────────────────────────────────────────────

C_RIM        = (80, 140, 200)
C_RIM_DARK   = (30, 60, 100)
C_TEXT       = (220, 235, 255)
C_DIM        = (100, 120, 150)
C_HIGHLIGHT  = (255, 200, 80)
C_HANDLE     = (60, 80, 110)
C_HANDLE_HOT = (100, 140, 190)
C_CHECK_ON   = (80, 180, 120)
C_CHECK_OFF  = (60, 70, 90)
C_PRESET     = (50, 70, 100)
C_PRESET_ACT = (90, 140, 200)
C_MAG_TEXT   = (200, 220, 255, 180)
C_ICON_BG    = (10, 14, 22)
C_ICON_BG_HOT = (30, 50, 80)
C_ICON_SELECTED = (255, 200, 80)
C_CLOSE      = (180, 60, 60)
C_CLOSE_HOT  = (220, 80, 80)

FONT_SIZE_SM = 17
FONT_SIZE_MD = 19
FONT_SIZE_ICON = 16         # tooltip text
FONT_SIZE_ICON_VAL = 20     # value readout below icons

HANDLE_SIZE  = 18
PANEL_W      = 240
PANEL_H_SLIM = 38          # slim bottom HUD height (more padding)
PANEL_RAD    = 10
PANEL_FADE_S = 0.20

# Radial icon layout — icons sit at the rim edge, centered on the circle border
ICON_RADIUS_FRAC = 0.88    # fraction of lens radius for icon center
ICON_SIZE        = 48       # diameter of icon circle
ICON_HIT_SIZE    = 56       # hit-test diameter
RADIAL_FADE_S    = 0.15     # seconds for radial icon fade

# Angles (radians) for 7 param icons across the upper semicircle (9 o'clock to 3 o'clock)
# Evenly spaced: 180, 155, 130, 105, 80, 55, 30 degrees (left to right)
PARAM_ANGLES = {
    'n':  math.radians(155),
    'C':  math.radians(135),
    'd':  math.radians(115),
    'H':  math.radians(95),
    'Z':  math.radians(75),
    'CA': math.radians(55),
    'EB': math.radians(35),
}

# Full names for tooltips
PARAM_NAMES = {
    'n': 'index',
    'C': 'curve',
    'd': 'thick',
    'H': 'height',
    'Z': 'zoom',
    'CA': 'chroma',
    'EB': 'edge blur',
}


# ══════════════════════════════════════════════════════════════════════════════
# Icon drawing helpers — each draws a symbolic shape into a surface
# ══════════════════════════════════════════════════════════════════════════════

def _draw_icon_prism(surf, cx, cy, r, color, alpha):
    """n — refractive index: a prism (triangle) with a light ray through it."""
    s = int(r * 0.65)
    # Triangle (prism)
    pts = [(cx, cy - s), (cx - s, cy + s - 2), (cx + s, cy + s - 2)]
    col = (*color, int(255 * alpha))
    pygame.draw.polygon(surf, col, pts, 2)
    # Light ray entering and bending
    ray_col = (*C_HIGHLIGHT[:3], int(180 * alpha))
    pygame.draw.line(surf, ray_col, (cx - s + 2, cy - 2), (cx - 2, cy + 1), 1)
    pygame.draw.line(surf, ray_col, (cx - 1, cy + 1), (cx + s - 3, cy - 4), 1)


def _draw_icon_curve(surf, cx, cy, r, color, alpha):
    """C — curvature: a curved arc (lens profile)."""
    col = (*color, int(255 * alpha))
    s = int(r * 0.7)
    # Draw an arc representing a curved lens surface
    arc_rect = pygame.Rect(cx - s * 2, cy - s, s * 2, s * 2)
    pygame.draw.arc(surf, col, arc_rect, -math.pi / 3, math.pi / 3, 2)
    # Mirror arc on right side
    arc_rect2 = pygame.Rect(cx, cy - s, s * 2, s * 2)
    pygame.draw.arc(surf, col, arc_rect2, math.pi * 2 / 3, math.pi * 4 / 3, 2)


def _draw_icon_thickness(surf, cx, cy, r, color, alpha):
    """d — thickness: two vertical lines with a horizontal double-arrow."""
    col = (*color, int(255 * alpha))
    s = int(r * 0.55)
    # Two vertical bars
    pygame.draw.line(surf, col, (cx - s, cy - s), (cx - s, cy + s), 2)
    pygame.draw.line(surf, col, (cx + s, cy - s), (cx + s, cy + s), 2)
    # Horizontal double-arrow
    arrow_col = (*C_HIGHLIGHT[:3], int(180 * alpha))
    pygame.draw.line(surf, arrow_col, (cx - s + 2, cy), (cx + s - 2, cy), 1)
    # Arrowheads
    ah = 3
    pygame.draw.line(surf, arrow_col, (cx - s + 2, cy), (cx - s + 2 + ah, cy - ah), 1)
    pygame.draw.line(surf, arrow_col, (cx - s + 2, cy), (cx - s + 2 + ah, cy + ah), 1)
    pygame.draw.line(surf, arrow_col, (cx + s - 2, cy), (cx + s - 2 - ah, cy - ah), 1)
    pygame.draw.line(surf, arrow_col, (cx + s - 2, cy), (cx + s - 2 - ah, cy + ah), 1)


def _draw_icon_height(surf, cx, cy, r, color, alpha):
    """H — lens height: a vertical arrow with a lens outline."""
    col = (*color, int(255 * alpha))
    s = int(r * 0.6)
    # Vertical arrow
    pygame.draw.line(surf, col, (cx, cy - s), (cx, cy + s), 2)
    ah = 3
    # Top arrowhead
    pygame.draw.line(surf, col, (cx, cy - s), (cx - ah, cy - s + ah + 1), 2)
    pygame.draw.line(surf, col, (cx, cy - s), (cx + ah, cy - s + ah + 1), 2)
    # Bottom arrowhead
    pygame.draw.line(surf, col, (cx, cy + s), (cx - ah, cy + s - ah - 1), 2)
    pygame.draw.line(surf, col, (cx, cy + s), (cx + ah, cy + s - ah - 1), 2)
    # Small lens outline to the side
    lens_col = (*color, int(140 * alpha))
    pygame.draw.arc(surf, lens_col,
                    pygame.Rect(cx + 3, cy - s + 2, s, s * 2 - 4),
                    -math.pi / 2.5, math.pi / 2.5, 1)


def _draw_icon_zoom(surf, cx, cy, r, color, alpha):
    """Z — zoom: a magnifying glass with +."""
    col = (*color, int(255 * alpha))
    s = int(r * 0.45)
    # Circle (lens)
    pygame.draw.circle(surf, col, (cx - 2, cy - 2), s, 2)
    # Handle
    hx = cx - 2 + int(s * 0.7)
    hy = cy - 2 + int(s * 0.7)
    pygame.draw.line(surf, col, (hx, hy), (hx + s - 1, hy + s - 1), 2)
    # Plus sign inside
    plus_col = (*C_HIGHLIGHT[:3], int(180 * alpha))
    ps = max(2, s // 2)
    pygame.draw.line(surf, plus_col, (cx - 2 - ps, cy - 2), (cx - 2 + ps, cy - 2), 1)
    pygame.draw.line(surf, plus_col, (cx - 2, cy - 2 - ps), (cx - 2, cy - 2 + ps), 1)


ICON_DRAW_FUNCS = {
    'n': _draw_icon_prism,
    'C': _draw_icon_curve,
    'd': _draw_icon_thickness,
    'H': _draw_icon_height,
    'Z': _draw_icon_zoom,
    'CA': lambda surf, cx, cy, r, color, alpha: _draw_icon_chroma(surf, cx, cy, r, color, alpha),
    'EB': lambda surf, cx, cy, r, color, alpha: _draw_icon_blur(surf, cx, cy, r, color, alpha),
}


def _draw_icon_chroma(surf, cx, cy, r, color, alpha):
    """CA — chromatic aberration: overlapping R/G/B circles, slightly offset."""
    s = int(r * 0.35)
    off = max(2, int(r * 0.15))
    # Red circle offset left
    r_col = (255, 80, 80, int(140 * alpha))
    pygame.draw.circle(surf, r_col, (cx - off, cy), s, 1)
    # Green circle centered
    g_col = (80, 255, 80, int(140 * alpha))
    pygame.draw.circle(surf, g_col, (cx, cy - off // 2), s, 1)
    # Blue circle offset right
    b_col = (80, 80, 255, int(140 * alpha))
    pygame.draw.circle(surf, b_col, (cx + off, cy), s, 1)
    # White center dot
    w_col = (*color, int(200 * alpha))
    pygame.draw.circle(surf, w_col, (cx, cy), max(1, s // 3))


def _draw_icon_blur(surf, cx, cy, r, color, alpha):
    """EB — edge blur: a circle that fades/feathers at the edge."""
    s = int(r * 0.55)
    col = (*color, int(200 * alpha))
    # Sharp inner circle
    pygame.draw.circle(surf, col, (cx, cy), s - 2, 2)
    # Progressively lighter outer rings to suggest blur/feather
    for i in range(3):
        ring_a = int((140 - i * 40) * alpha)
        ring_col = (*color[:3], max(0, ring_a)) if len(color) >= 3 else (*color, max(0, ring_a))
        pygame.draw.circle(surf, ring_col, (cx, cy), s + i * 2, 1)


# ══════════════════════════════════════════════════════════════════════════════
# Optics math (unchanged)
# ══════════════════════════════════════════════════════════════════════════════

def lensmaker_focal_length(n: float, R: float, d: float) -> float:
    if abs(R) < 1e-6:
        return 1e6
    R1, R2 = R, -R
    inv_f = (n - 1) * (1.0 / R1 - 1.0 / R2 + (n - 1) * d / (n * R1 * R2))
    if abs(inv_f) < 1e-8:
        return 1e6
    return 1.0 / inv_f


def magnification(f: float, dist: float) -> float:
    denom = f - dist
    if abs(denom) < 1e-4:
        return 12.0 if denom >= 0 else -12.0
    m = f / denom
    return max(-12.0, min(m, 12.0))


def build_distortion_map(size: int, n: float, C: float, d: float, H: float, Z: float = 1.0):
    if abs(C) < 1e-6:
        R = 1e6 if C >= 0 else -1e6
    else:
        R = 1.0 / C
    f = lensmaker_focal_length(n, R, d)
    M = magnification(f, H)

    abs_R = abs(R)
    R_pow = math.copysign(abs_R ** 1.5, R) if abs_R > 1e-6 else math.copysign(1e9, R)
    k2 = -(n - 1.0) * 0.18 / R_pow
    k4 = k2 * 0.3

    half = size / 2.0
    lin = (np.arange(size) - half + 0.5) / half
    px, py = np.meshgrid(lin, lin)
    r2 = px ** 2 + py ** 2
    r4 = r2 * r2

    distort = 1.0 + k2 * r2 + k4 * r4
    safe_M = M if abs(M) > 1e-6 else (1e-6 if M >= 0 else -1e-6)
    scale = (1.0 / safe_M) * distort * (1.0 / Z)

    inside = r2 <= 1.0
    max_scale = float(np.max(np.abs(scale[inside]))) if inside.any() else abs(1.0 / (safe_M * Z))
    oversample = min(6.0, max(1.0, max_scale * 1.08))

    capture_half = half * oversample
    src_x = (px * scale * half + capture_half).astype(np.float32)
    src_y = (py * scale * half + capture_half).astype(np.float32)

    outside = ~inside
    src_x[outside] = capture_half
    src_y[outside] = capture_half

    return src_x, src_y, M, f, oversample


def apply_lens(crop: np.ndarray, src_x: np.ndarray, src_y: np.ndarray) -> np.ndarray:
    H, W = crop.shape[:2]
    x0 = np.clip(src_x.astype(np.int32), 0, W - 2)
    y0 = np.clip(src_y.astype(np.int32), 0, H - 2)
    x1 = x0 + 1
    y1 = y0 + 1
    fx = (src_x - x0).astype(np.float32)[..., np.newaxis]
    fy = (src_y - y0).astype(np.float32)[..., np.newaxis]
    c00 = crop[y0, x0].astype(np.float32)
    c10 = crop[y0, x1].astype(np.float32)
    c01 = crop[y1, x0].astype(np.float32)
    c11 = crop[y1, x1].astype(np.float32)
    out = (c00 * (1 - fx) * (1 - fy) +
           c10 * fx       * (1 - fy) +
           c01 * (1 - fx) * fy       +
           c11 * fx       * fy)
    return np.clip(out, 0, 255).astype(np.uint8)


def apply_chromatic_aberration(img: np.ndarray, ca_strength: float) -> np.ndarray:
    """Shift R and B channels radially outward/inward from center.
    Fades effect near the rim to avoid boundary clamp artifacts."""
    if ca_strength < 0.005:
        return img
    h, w = img.shape[:2]
    half_y, half_x = h / 2.0, w / 2.0
    yy, xx = np.mgrid[0:h, 0:w]
    dx = (xx - half_x) / half_x
    dy = (yy - half_y) / half_y
    r2 = dx * dx + dy * dy

    r = np.sqrt(r2)
    ca_fade = np.clip((0.98 - r) / 0.13, 0, 1).astype(np.float32)

    shift = ca_strength * r2 * 0.3 * ca_fade

    r_sx = dx * (1.0 + shift) * half_x + half_x
    r_sy = dy * (1.0 + shift) * half_y + half_y
    b_sx = dx * (1.0 - shift * 0.6) * half_x + half_x
    b_sy = dy * (1.0 - shift * 0.6) * half_y + half_y

    out = img.copy()

    r_x0 = np.clip(r_sx.astype(np.int32), 0, w - 2)
    r_y0 = np.clip(r_sy.astype(np.int32), 0, h - 2)
    r_x1 = r_x0 + 1
    r_y1 = r_y0 + 1
    r_fx = np.clip(r_sx - r_x0, 0, 1).astype(np.float32)
    r_fy = np.clip(r_sy - r_y0, 0, 1).astype(np.float32)
    out[:, :, 0] = np.clip(
        img[r_y0, r_x0, 0] * (1 - r_fx) * (1 - r_fy) +
        img[r_y0, r_x1, 0] * r_fx * (1 - r_fy) +
        img[r_y1, r_x0, 0] * (1 - r_fx) * r_fy +
        img[r_y1, r_x1, 0] * r_fx * r_fy,
        0, 255).astype(np.uint8)

    b_x0 = np.clip(b_sx.astype(np.int32), 0, w - 2)
    b_y0 = np.clip(b_sy.astype(np.int32), 0, h - 2)
    b_x1 = b_x0 + 1
    b_y1 = b_y0 + 1
    b_fx = np.clip(b_sx - b_x0, 0, 1).astype(np.float32)
    b_fy = np.clip(b_sy - b_y0, 0, 1).astype(np.float32)
    out[:, :, 2] = np.clip(
        img[b_y0, b_x0, 2] * (1 - b_fx) * (1 - b_fy) +
        img[b_y0, b_x1, 2] * b_fx * (1 - b_fy) +
        img[b_y1, b_x0, 2] * (1 - b_fx) * b_fy +
        img[b_y1, b_x1, 2] * b_fx * b_fy,
        0, 255).astype(np.uint8)
    return out


def _box_blur_channel(ch: np.ndarray, radius: int) -> np.ndarray:
    """Fast box blur on a 2D float32 array using cumulative sums."""
    if radius < 1:
        return ch
    h, w = ch.shape
    k = 2 * radius + 1
    # Horizontal pass
    padded = np.pad(ch, ((0, 0), (radius, radius)), mode='edge')
    cs = np.cumsum(padded, axis=1)
    horiz = (cs[:, k:] - cs[:, :-k]) / k
    # Crop to original width (cumsum output may be wider)
    horiz = horiz[:, :w] if horiz.shape[1] >= w else np.pad(horiz, ((0, 0), (0, w - horiz.shape[1])), mode='edge')
    # Vertical pass
    padded = np.pad(horiz, ((radius, radius), (0, 0)), mode='edge')
    cs = np.cumsum(padded, axis=0)
    vert = (cs[k:] - cs[:-k]) / k
    vert = vert[:h, :] if vert.shape[0] >= h else np.pad(vert, ((0, h - vert.shape[0]), (0, 0)), mode='edge')
    return vert


def apply_edge_blur(img: np.ndarray, eb_strength: float) -> np.ndarray:
    """Blur the image progressively toward the circular edge."""
    if eb_strength < 0.01:
        return img
    h, w = img.shape[:2]
    half_y, half_x = h / 2.0, w / 2.0
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx - half_x) / half_x) ** 2 + ((yy - half_y) / half_y) ** 2)

    # Blend mask: 0 (sharp) at center, 1 (fully blurred) at rim
    onset = max(0.05, 1.0 - eb_strength)
    blend = np.clip((r - onset) / max(0.01, 1.0 - onset), 0, 1).astype(np.float32)

    # Blur radius scales with strength — bigger strength = wider blur kernel
    blur_radius = max(2, int(eb_strength * 16))

    img_f = img.astype(np.float32)

    # Blur each channel independently with two-pass box blur (2 iterations for smoother result)
    blurred = np.empty_like(img_f)
    for c in range(3):
        ch = img_f[:, :, c]
        for _ in range(2):
            ch = _box_blur_channel(ch, blur_radius)
        blurred[:, :, c] = ch

    # Blend: sharp in center, blurred at edges
    blend_3 = blend[..., np.newaxis]
    out = img_f * (1.0 - blend_3) + blurred * blend_3
    return np.clip(out, 0, 255).astype(np.uint8)


# ══════════════════════════════════════════════════════════════════════════════
# Main app
# ══════════════════════════════════════════════════════════════════════════════

class LensMagnifier:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)

        self.size = DEFAULT_SIZE
        self.n    = DEFAULT_N
        self.C    = DEFAULT_C
        self.d    = DEFAULT_D
        self.H    = DEFAULT_H
        self.Z    = DEFAULT_Z
        self.CA   = DEFAULT_CA
        self.EB   = DEFAULT_EB

        self.params_order   = ['n', 'C', 'd', 'H', 'Z', 'CA', 'EB']
        self.selected_param = 'C'

        # Bottom HUD state
        self.panel_alpha       = 0.0
        self._panel_shown      = False
        self._prev_dropdown    = False

        # Radial icons state
        self.radial_alpha      = 0.0
        self._hovered_param    = None
        self._icon_dragging    = None
        self._icon_drag_start_x = 0         # screen X at drag start
        self._icon_drag_start_y = 0         # screen Y at drag start
        self._icon_drag_start_val = 0.0

        self.always_on_top     = True
        self.screenshot_mode   = False   # F9: freeze frame + allow capture
        self._f9_was_down      = False

        self.dragging          = False
        self.drag_offset       = (0, 0)
        self.win_pos           = (200, 200)
        self.resizing          = False
        self.resize_start      = (0, 0)
        self.resize_start_dist = 0.0      # radial distance at drag start
        self.resize_size0      = self.size
        self._pending_size     = self.size
        self._resize_expanded  = False
        self._resize_expand_off = 0
        self._resize_bg_snap   = None

        self.active_preset     = None
        self.dropdown_open     = False
        self._dropdown_rects   = []
        self._dropdown_btn_rect = pygame.Rect(0, 0, 0, 0)
        self._aot_checkbox_rect = pygame.Rect(0, 0, 0, 0)
        self._close_btn_rect    = pygame.Rect(0, 0, 0, 0)
        self._handle_rect       = pygame.Rect(0, 0, 0, 0)

        self._apply_preset('Reading')

        self._win_flags = pygame.NOFRAME
        max_dim = self._max_surface_dim()
        self.screen = pygame.display.set_mode(
            (max_dim, max_dim), self._win_flags)
        self._sync_win32_size()
        self._set_always_on_top(True)
        self._exclude_from_capture()
        self._apply_window_region()

        self.clock   = pygame.time.Clock()
        self.sct     = mss.mss()
        self.font_sm = pygame.font.SysFont("Consolas", FONT_SIZE_SM)
        self.font_md = pygame.font.SysFont("Consolas", FONT_SIZE_MD, bold=True)
        self.font_icon = pygame.font.SysFont("Consolas", FONT_SIZE_ICON, bold=True)
        self.font_icon_val = pygame.font.SysFont("Consolas", FONT_SIZE_ICON_VAL, bold=True)

        self._map_buf_x = np.empty((self.size, self.size), dtype=np.float32)
        self._map_buf_y = np.empty((self.size, self.size), dtype=np.float32)

        self._map_key    = None
        self._src_x      = self._src_y = None
        self._M          = self._f = None
        self._oversample = 1.0
        self._rebuild_map()

        self._running = True

    # ── presets ────────────────────────────────────────────────────────────────

    def _apply_preset(self, name):
        p = PRESETS[name]
        self.n, self.C, self.d, self.H, self.Z = p['n'], p['C'], p['d'], p['H'], p['Z']
        self.CA, self.EB = p['CA'], p['EB']
        self.active_preset = name

    def _check_preset_match(self):
        for name, p in PRESETS.items():
            if all(abs(getattr(self, k) - p[k]) < 0.001
                   for k in ('n', 'C', 'd', 'H', 'Z', 'CA', 'EB')):
                self.active_preset = name
                return
        self.active_preset = None

    # ── helpers ───────────────────────────────────────────────────────────────

    def _max_win_h(self):
        return self.size + PANEL_H_SLIM + len(PRESET_ORDER) * 22 + 20

    def _max_surface_dim(self):
        full = MAX_SIZE + 16
        return full + PANEL_H_SLIM + len(PRESET_ORDER) * 22 + 20

    def _panel_content_h(self):
        base = PANEL_H_SLIM
        if self.dropdown_open:
            base += len(PRESET_ORDER) * 22 + 6
        return base

    def _get_abs_mouse(self):
        if _HAS_WIN32:
            try:
                pt = ctypes.wintypes.POINT()
                ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                return pt.x, pt.y
            except Exception:
                pass
        return pygame.mouse.get_pos()

    def _get_window_mouse_pos(self):
        ax, ay = self._get_abs_mouse()
        wx, wy = self.win_pos
        return ax - wx, ay - wy

    def _clamp_param(self, key, val):
        lo, hi = PARAM_RANGE[key]
        return round(max(lo, min(hi, val)), 4)

    def _radial_dist_from_center(self):
        """Distance of the absolute mouse position from the lens center."""
        ax, ay = self._get_abs_mouse()
        wx, wy = self.win_pos
        s = self.size
        cx, cy = wx + s / 2.0, wy + s / 2.0
        return math.sqrt((ax - cx) ** 2 + (ay - cy) ** 2)

    # ── radial icon positions ─────────────────────────────────────────────────

    def _icon_center(self, key):
        """Return (cx, cy) of a radial icon in window-local coords."""
        s = self.size
        half = s / 2.0
        r = half * ICON_RADIUS_FRAC
        angle = PARAM_ANGLES[key]
        cx = half + r * math.cos(angle)
        cy = half - r * math.sin(angle)
        return int(cx), int(cy)

    def _icon_hit_test(self, mx, my):
        """Return the param key whose icon contains (mx, my), or None."""
        hit_r = ICON_HIT_SIZE / 2.0
        for key in self.params_order:
            cx, cy = self._icon_center(key)
            if (mx - cx) ** 2 + (my - cy) ** 2 <= hit_r ** 2:
                return key
        return None

    # ── win32 window management ───────────────────────────────────────────────

    def _get_hwnd(self):
        if not _HAS_WIN32:
            return None, None
        try:
            return ctypes.windll.user32, pygame.display.get_wm_info()["window"]
        except Exception:
            return None, None

    def _set_always_on_top(self, on_top):
        user32, hwnd = self._get_hwnd()
        if not hwnd:
            return
        SWP = 0x0002 | 0x0001
        user32.SetWindowPos(hwnd, ctypes.c_void_p(-1 if on_top else -2),
                            0, 0, 0, 0, SWP)

    def _move_window(self, x, y):
        self.win_pos = (x, y)
        if not _HAS_WIN32:
            return
        try:
            hwnd = pygame.display.get_wm_info()["window"]
            w, h = self._current_win_wh()
            ctypes.windll.user32.MoveWindow(hwnd, x, y, w, h, False)
        except Exception:
            pass

    def _current_win_wh(self):
        if self._resize_expanded:
            full = self.size + self._resize_expand_off * 2
            return full, full + PANEL_H_SLIM + len(PRESET_ORDER) * 22 + 20
        return self.size, self._max_win_h()

    def _sync_win32_size(self):
        if not _HAS_WIN32:
            return
        try:
            hwnd = pygame.display.get_wm_info()["window"]
            wx, wy = self.win_pos
            w, h = self._current_win_wh()
            ctypes.windll.user32.MoveWindow(hwnd, wx, wy, w, h, False)
        except Exception:
            pass

    def _exclude_from_capture(self):
        user32, hwnd = self._get_hwnd()
        if not hwnd:
            return
        # WDA_EXCLUDEFROMCAPTURE (0x11) hides us from our own mss grab (and
        # from screenshot tools).  In screenshot mode use WDA_NONE (0) so the
        # lens is visible to Snipping Tool etc.
        affinity = 0x00000000 if self.screenshot_mode else 0x00000011
        try:
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, affinity)
        except Exception:
            pass

    def _toggle_screenshot_mode(self):
        """Freeze the current frame and make the window capturable."""
        self.screenshot_mode = not self.screenshot_mode
        self._exclude_from_capture()

    def _apply_window_region(self):
        if not _HAS_WIN32:
            return
        user32, hwnd = self._get_hwnd()
        if not hwnd:
            return
        gdi32 = ctypes.windll.gdi32
        s = self.size
        show_panel = self.panel_alpha > 0.05

        rgn = gdi32.CreateEllipticRgn(0, 0, s, s)

        if show_panel:
            pw = min(PANEL_W, s - 8)
            px = (s - pw) // 2
            ph = self._panel_content_h()
            rgn_p = gdi32.CreateRoundRectRgn(
                px, s - PANEL_RAD, px + pw, s + ph,
                PANEL_RAD * 2, PANEL_RAD * 2)
            gdi32.CombineRgn(rgn, rgn, rgn_p, 2)
            gdi32.DeleteObject(rgn_p)
            self._panel_shown = True
        else:
            self._panel_shown = False

        user32.SetWindowRgn(hwnd, rgn, True)

    def _enter_resize_expand(self):
        if self._resize_expanded:
            return False
        s = self.size
        expand = (MAX_SIZE - s) // 2 + 8
        full = s + expand * 2
        wx, wy = self.win_pos

        raw = self.sct.grab({
            "top": wy - expand, "left": wx - expand,
            "width": full, "height": full,
        })
        bg_img = np.frombuffer(raw.raw, dtype=np.uint8).reshape(
            raw.height, raw.width, 4)[:, :, 2::-1]
        self._resize_bg_snap = pygame.surfarray.make_surface(
            np.transpose(bg_img, (1, 0, 2)))

        self._resize_expand_off = expand
        self._resize_expanded = True

        old_content = self.screen.subsurface(
            pygame.Rect(0, 0, s, min(s, self.screen.get_height()))).copy()
        self.screen.fill((0, 0, 0, 0))
        self.screen.blit(self._resize_bg_snap, (0, 0))
        self.screen.blit(old_content, (expand, expand))
        pygame.display.flip()

        if _HAS_WIN32:
            user32, hwnd = self._get_hwnd()
            if hwnd:
                gdi32 = ctypes.windll.gdi32
                rgn = gdi32.CreateRectRgn(0, 0, full, full)
                user32.SetWindowRgn(hwnd, rgn, True)
                max_h = full + PANEL_H_SLIM + len(PRESET_ORDER) * 22 + 20
                ctypes.windll.user32.MoveWindow(
                    hwnd, wx - expand, wy - expand, full, max_h, False)

        return True

    def _leave_resize_expand(self):
        if not self._resize_expanded:
            return
        self._resize_expanded = False
        self._resize_bg_snap = None
        self._resize_expand_off = 0

        self._sync_win32_size()
        self._set_always_on_top(self.always_on_top)
        self._exclude_from_capture()
        self._apply_window_region()

    def _resize_window(self, new_size):
        new_size = max(MIN_SIZE, min(MAX_SIZE, new_size))
        old_size = self.size
        self._leave_resize_expand()
        if new_size == old_size:
            return
        delta = new_size - old_size
        wx, wy = self.win_pos
        self.win_pos = (wx - delta // 2, wy - delta // 2)
        self.size = new_size
        self._sync_win32_size()
        self._set_always_on_top(self.always_on_top)
        self._exclude_from_capture()
        self._apply_window_region()
        self._rebuild_map()

    # ── distortion map ────────────────────────────────────────────────────────

    def _rebuild_map(self):
        key = (self.size, round(self.n, 4), round(self.C, 4),
               round(self.d, 4), round(self.H, 4), round(self.Z, 4))
        if key == self._map_key:
            return
        self._map_key = key
        if self._map_buf_x.shape[0] != self.size:
            self._map_buf_x = np.empty((self.size, self.size), dtype=np.float32)
            self._map_buf_y = np.empty((self.size, self.size), dtype=np.float32)
        self._src_x, self._src_y, self._M, self._f, self._oversample = \
            build_distortion_map(self.size, self.n, self.C, self.d, self.H, self.Z)

    # ── screen capture ────────────────────────────────────────────────────────

    def _capture_region(self, cx, cy):
        s = self.size
        capture_size = max(s, int(s * self._oversample + 0.5))
        capture_size += capture_size % 2
        half = capture_size // 2
        raw = self.sct.grab({
            "top": cy - half, "left": cx - half,
            "width": capture_size, "height": capture_size,
        })
        img = np.frombuffer(raw.raw, dtype=np.uint8).reshape(
            raw.height, raw.width, 4)
        return img[:, :, 2::-1]

    # ── render ────────────────────────────────────────────────────────────────

    def render(self):
        mx, my = self._get_window_mouse_pos()
        wx, wy = self.win_pos
        s = self.size

        if self.resizing and self._pending_size > self.size:
            if self._enter_resize_expand():
                return

        off = self._resize_expand_off if self._resize_expanded else 0

        screen_cx = wx + s // 2
        screen_cy = wy + s // 2

        crop = self._capture_region(screen_cx, screen_cy)
        distorted = apply_lens(crop, self._src_x, self._src_y)

        # Post-processing: chromatic aberration and edge blur
        if self.CA > 0.005:
            distorted = apply_chromatic_aberration(distorted, self.CA)
        if self.EB > 0.01:
            distorted = apply_edge_blur(distorted, self.EB * 0.4)

        pg_img = pygame.surfarray.make_surface(
            np.transpose(distorted, (1, 0, 2)))

        # Circular clip
        mask = pygame.Surface((s, s), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (s // 2, s // 2), s // 2)
        clipped = pygame.Surface((s, s), pygame.SRCALPHA)
        clipped.blit(pg_img, (0, 0))
        clipped.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        self.screen.fill((0, 0, 0, 0))

        if self._resize_expanded and self._resize_bg_snap is not None:
            self.screen.blit(self._resize_bg_snap, (0, 0))
            self.screen.blit(clipped, (off, off))
        else:
            self.screen.blit(clipped, (0, 0))

        # Resize preview ring
        if self.resizing and self._pending_size != self.size:
            self._draw_resize_preview()

        # Rim
        rim_cx = off + s // 2
        rim_cy = off + s // 2
        pygame.draw.circle(self.screen, C_RIM, (rim_cx, rim_cy), s // 2, 3)
        pygame.draw.circle(self.screen, C_RIM_DARK, (rim_cx, rim_cy), s // 2 - 3, 1)

        # Magnification readout
        self._draw_rim_mag()

        # Radial icons (inside lens, not in expanded mode)
        if not self._resize_expanded:
            self._update_radial_hover(mx, my)
            if self.radial_alpha > 0.02:
                self._draw_radial_icons()

        # Bottom HUD panel (not in expanded mode)
        if not self._resize_expanded:
            self._update_panel_hover(mx, my)
            if self.panel_alpha > 0.02:
                self._draw_panel()
                self._draw_handle()

            should_show = self.panel_alpha > 0.05
            if should_show != self._panel_shown:
                self._apply_window_region()
            elif should_show and self._prev_dropdown != self.dropdown_open:
                self._apply_window_region()
            self._prev_dropdown = self.dropdown_open

        pygame.display.flip()

    def _draw_resize_preview(self):
        s = self.size
        ps = self._pending_size
        off = self._resize_expand_off if self._resize_expanded else 0
        cx = off + s // 2
        cy = off + s // 2
        preview_r = ps // 2
        surf_w, surf_h = self.screen.get_size()

        num_dots = max(24, ps // 6)
        for i in range(num_dots):
            if i % 2 == 0:
                angle = 2 * math.pi * i / num_dots
                dx = int(cx + preview_r * math.cos(angle))
                dy = int(cy + preview_r * math.sin(angle))
                if 0 <= dx < surf_w and 0 <= dy < surf_h:
                    pygame.draw.circle(self.screen, C_RIM, (dx, dy), 2)

        txt = self.font_md.render(f"{ps}px", True, C_TEXT)
        tr = txt.get_rect(center=(cx, cy))
        pill = tr.inflate(14, 6)
        bg = pygame.Surface((pill.w, pill.h), pygame.SRCALPHA)
        pygame.draw.rect(bg, (0, 0, 0, 160), bg.get_rect(), border_radius=6)
        self.screen.blit(bg, pill.topleft)
        self.screen.blit(txt, tr)

    def _draw_rim_mag(self):
        s = self.size
        off = self._resize_expand_off if self._resize_expanded else 0
        m = self._M
        sign = "" if m >= 0 else "-"
        label = f"{sign}{abs(m):.1f}x"
        surf = self.font_md.render(label, True, C_MAG_TEXT[:3])
        surf.set_alpha(C_MAG_TEXT[3])
        rect = surf.get_rect(center=(off + s // 2, off + s - 14))
        pill = rect.inflate(12, 4)
        ps = pygame.Surface((pill.w, pill.h), pygame.SRCALPHA)
        pygame.draw.rect(ps, (0, 0, 0, 120), ps.get_rect(), border_radius=6)
        self.screen.blit(ps, pill.topleft)
        self.screen.blit(surf, rect)

    # ── radial icon hover / fade ──────────────────────────────────────────────

    def _update_radial_hover(self, mx, my):
        s = self.size
        dt = self.clock.get_time() / 1000.0
        speed = 1.0 / RADIAL_FADE_S

        half = s / 2.0
        dist = math.sqrt((mx - half) ** 2 + (my - half) ** 2)
        near_rim = (half * 0.45) <= dist <= (half + 20)

        hovering_icon = self._icon_hit_test(mx, my) is not None
        should_show = near_rim or hovering_icon or self._icon_dragging is not None

        if should_show:
            self.radial_alpha = min(1.0, self.radial_alpha + speed * dt)
        else:
            self.radial_alpha = max(0.0, self.radial_alpha - speed * dt)

        if self._icon_dragging is None:
            self._hovered_param = self._icon_hit_test(mx, my)

    # ── radial icon drawing ───────────────────────────────────────────────────

    def _draw_radial_icons(self):
        a = self.radial_alpha
        if a < 0.02:
            return

        for key in self.params_order:
            cx, cy = self._icon_center(key)
            is_selected = (key == self.selected_param)
            is_hovered = (key == self._hovered_param)
            is_dragging = (key == self._icon_dragging)

            r = ICON_SIZE // 2
            surf_sz = ICON_SIZE + 4
            icon_surf = pygame.Surface((surf_sz, surf_sz), pygame.SRCALPHA)
            ic = surf_sz // 2

            # Background circle
            if is_dragging or is_hovered:
                bg_col = (*C_ICON_BG_HOT, int(230 * a))
            else:
                bg_col = (*C_ICON_BG, int(190 * a))
            pygame.draw.circle(icon_surf, bg_col, (ic, ic), r)

            # Border
            if is_selected:
                border_col = (*C_ICON_SELECTED, int(255 * a))
                pygame.draw.circle(icon_surf, border_col, (ic, ic), r, 2)
            elif is_hovered or is_dragging:
                border_col = (*C_RIM, int(220 * a))
                pygame.draw.circle(icon_surf, border_col, (ic, ic), r, 2)
            else:
                border_col = (*C_RIM, int(120 * a))
                pygame.draw.circle(icon_surf, border_col, (ic, ic), r, 1)

            # Draw the symbolic icon
            icon_col = C_ICON_SELECTED if is_selected else C_TEXT
            draw_fn = ICON_DRAW_FUNCS[key]
            draw_fn(icon_surf, ic, ic, r, icon_col, a)

            self.screen.blit(icon_surf, (cx - surf_sz // 2, cy - surf_sz // 2))

            # Always-visible value readout centered below the icon
            val = getattr(self, key)
            val_str = f"{val:.2f}"
            val_col = C_ICON_SELECTED if is_selected else C_TEXT
            val_surf = self.font_icon_val.render(val_str, True, val_col)
            val_surf.set_alpha(int(220 * a))

            # Centered directly below the icon circle
            val_gap = 3
            val_x = cx - val_surf.get_width() // 2
            val_y = cy + r + val_gap

            # Clamp inside lens
            val_x = max(4, min(val_x, self.size - val_surf.get_width() - 4))
            val_y = max(4, min(val_y, self.size - val_surf.get_height() - 4))

            # Pill background for readability
            val_rect = val_surf.get_rect(topleft=(val_x, val_y))
            pill = val_rect.inflate(6, 2)
            pill_bg = pygame.Surface((pill.w, pill.h), pygame.SRCALPHA)
            pygame.draw.rect(pill_bg, (0, 0, 0, int(140 * a)),
                             pill_bg.get_rect(), border_radius=4)
            self.screen.blit(pill_bg, pill.topleft)
            self.screen.blit(val_surf, val_rect)

            # Name tooltip on hover / drag, centered below the value
            if is_hovered or is_dragging:
                full_label = PARAM_NAMES[key]
                tip_surf = self.font_icon.render(full_label, True, C_DIM)
                tip_surf.set_alpha(int(200 * a))

                tip_x = cx - tip_surf.get_width() // 2
                tip_y = val_y + val_surf.get_height() + 2

                tip_x = max(4, min(tip_x, self.size - tip_surf.get_width() - 4))
                tip_y = max(4, min(tip_y, self.size - tip_surf.get_height() - 4))

                tip_rect = tip_surf.get_rect(topleft=(tip_x, tip_y))
                tip_pill = tip_rect.inflate(6, 2)
                tip_bg = pygame.Surface((tip_pill.w, tip_pill.h), pygame.SRCALPHA)
                pygame.draw.rect(tip_bg, (0, 0, 0, int(130 * a)),
                                 tip_bg.get_rect(), border_radius=3)
                self.screen.blit(tip_bg, tip_pill.topleft)
                self.screen.blit(tip_surf, tip_rect)

    # ── panel hover (bottom HUD) ──────────────────────────────────────────────

    def _update_panel_hover(self, mx, my):
        s = self.size
        dt = self.clock.get_time() / 1000.0
        speed = 1.0 / PANEL_FADE_S

        margin = 40
        near_bottom = (my >= s * 0.7) and (
            (mx - s / 2) ** 2 + (my - s / 2) ** 2 <= ((s / 2) + margin) ** 2)
        pw = min(PANEL_W, s - 8)
        px = (s - pw) // 2
        ph = self._panel_content_h()
        in_panel = ((px - margin <= mx <= px + pw + margin)
                    and (s - PANEL_RAD - margin <= my <= s + ph + margin))
        should_show = near_bottom or in_panel or self.resizing

        if should_show:
            self.panel_alpha = min(1.0, self.panel_alpha + speed * dt)
        else:
            self.panel_alpha = max(0.0, self.panel_alpha - speed * dt)
            if self.panel_alpha < 0.1:
                self.dropdown_open = False

    # ── panel drawing (slim bottom HUD) ───────────────────────────────────────

    def _draw_handle(self):
        s = self.size
        pw = min(PANEL_W, s - 8)
        px = (s - pw) // 2
        hw = HANDLE_SIZE
        a = self.panel_alpha
        ph = self._panel_content_h()
        hx = px + pw - hw
        hy = s + ph - hw
        rect = pygame.Rect(hx, hy, hw, hw)
        hot = rect.collidepoint(pygame.mouse.get_pos())
        col = C_HANDLE_HOT if hot else C_HANDLE
        hs = pygame.Surface((hw, hw), pygame.SRCALPHA)
        pygame.draw.rect(hs, (*col, int(255 * a)), hs.get_rect(), border_radius=3)
        for i in range(3, hw - 2, 4):
            pygame.draw.line(hs, (*C_RIM, int(200 * a)),
                             (i, hw - 3), (hw - 3, i), 1)
        self.screen.blit(hs, rect.topleft)
        self._handle_rect = rect

    def _draw_panel(self):
        s = self.size
        a = self.panel_alpha
        pw = min(PANEL_W, s - 8)
        px = (s - pw) // 2

        total_h = self._panel_content_h()
        panel = pygame.Surface((s, total_h), pygame.SRCALPHA)

        # Round-rect background
        bg = pygame.Rect(px, 0, pw, total_h)
        pygame.draw.rect(panel, (10, 14, 22, int(220 * a)), bg,
                         border_radius=PANEL_RAD)
        pygame.draw.rect(panel, (*C_RIM_DARK, int(180 * a)), bg, 1,
                         border_radius=PANEL_RAD)

        y = 9

        # ── Row: [X close] [Preset dropdown ▼] [✓ Pin] ───────────────────────
        close_sz = 18
        aot_sz = 14
        spacing = 8
        inner_pad = 8   # padding from panel edges

        # Measure the Pin section width
        pin_lbl = self.font_sm.render("Pin", True, C_DIM)
        aot_section_w = aot_sz + 4 + pin_lbl.get_width()

        # Close button width
        close_section_w = close_sz

        # Dropdown gets remaining space
        dd_w = pw - inner_pad * 2 - close_section_w - spacing - aot_section_w - spacing
        dd_h = 24

        # -- Close button (far left) --
        close_x = px + inner_pad
        close_y = y + (dd_h - close_sz) // 2
        close_rect_local = pygame.Rect(close_x, close_y, close_sz, close_sz)
        close_hot = close_rect_local.move(0, s).collidepoint(
            *self._get_window_mouse_pos())
        close_col = C_CLOSE_HOT if close_hot else C_CLOSE
        pygame.draw.rect(panel, (*close_col, int(200 * a)),
                         close_rect_local, border_radius=3)
        xm = 4
        x1, y1_ = close_rect_local.left + xm, close_rect_local.top + xm
        x2, y2_ = close_rect_local.right - xm, close_rect_local.bottom - xm
        pygame.draw.line(panel, (255, 255, 255, int(255 * a)),
                         (x1, y1_), (x2, y2_), 2)
        pygame.draw.line(panel, (255, 255, 255, int(255 * a)),
                         (x2, y1_), (x1, y2_), 2)
        self._close_btn_rect = pygame.Rect(close_x, s + close_y, close_sz, close_sz)

        # -- Preset dropdown (center) --
        dd_x = close_x + close_sz + spacing
        preset_label = self.active_preset or "Custom"
        dd_text = self.font_sm.render(f"{preset_label} \u25BC", True, C_TEXT)
        dd_text.set_alpha(int(255 * a))
        dd_rect = pygame.Rect(dd_x, y, dd_w, dd_h)
        dd_col = C_PRESET_ACT if self.dropdown_open else C_PRESET
        pygame.draw.rect(panel, (*dd_col, int(200 * a)), dd_rect,
                         border_radius=4)
        pygame.draw.rect(panel, (*C_RIM_DARK, int(180 * a)), dd_rect, 1,
                         border_radius=4)
        # Center the text vertically in the dropdown
        txt_y = y + (dd_h - dd_text.get_height()) // 2
        panel.blit(dd_text, (dd_x + 6, txt_y))
        self._dropdown_btn_rect = pygame.Rect(dd_x, s + y, dd_w, dd_h)

        # -- Always-on-top checkbox (right side) --
        aot_x = dd_x + dd_w + spacing
        aot_y = y + (dd_h - aot_sz) // 2
        fc = (*C_CHECK_ON, int(200 * a)) if self.always_on_top \
            else (*C_CHECK_OFF, int(120 * a))
        pygame.draw.rect(panel, fc, (aot_x, aot_y, aot_sz, aot_sz),
                         border_radius=2)
        pygame.draw.rect(panel, (*C_RIM, int(255 * a)),
                         (aot_x, aot_y, aot_sz, aot_sz), 1, border_radius=2)
        if self.always_on_top:
            pts = [(aot_x + 3, aot_y + aot_sz // 2),
                   (aot_x + aot_sz // 2 - 1, aot_y + aot_sz - 3),
                   (aot_x + aot_sz - 2, aot_y + 2)]
            pygame.draw.lines(panel, (255, 255, 255, int(255 * a)),
                              False, pts, 2)
        pin_lbl_r = self.font_sm.render("Pin", True, C_DIM)
        pin_lbl_r.set_alpha(int(255 * a))
        panel.blit(pin_lbl_r, (aot_x + aot_sz + 3,
                                aot_y + (aot_sz - pin_lbl_r.get_height()) // 2))
        self._aot_checkbox_rect = pygame.Rect(
            aot_x, s + aot_y, aot_section_w, aot_sz + 4)

        y += dd_h + 3

        # ── Dropdown items ────────────────────────────────────────────────────
        self._dropdown_rects.clear()
        if self.dropdown_open:
            item_w = pw - inner_pad * 2
            for name in PRESET_ORDER:
                active = name == self.active_preset
                itxt = self.font_sm.render(name, True,
                                           C_TEXT if active else C_DIM)
                itxt.set_alpha(int(255 * a))
                ih = itxt.get_height() + 4
                ir = pygame.Rect(px + inner_pad, y, item_w, ih)
                ic = C_PRESET_ACT if active else (20, 24, 35)
                pygame.draw.rect(panel, (*ic, int(210 * a)), ir)
                pygame.draw.rect(panel, (*C_RIM_DARK, int(120 * a)), ir, 1)
                panel.blit(itxt, (px + inner_pad + 6, y + 2))
                self._dropdown_rects.append(
                    (name, pygame.Rect(px + inner_pad, s + y, item_w, ih)))
                y += ih

        self.screen.blit(panel, (0, s))

    # ── input ─────────────────────────────────────────────────────────────────

    def _adjust_param(self, key, delta_steps):
        """Adjust a parameter by delta_steps increments."""
        step = PARAM_STEP[key]
        val = getattr(self, key) + step * delta_steps
        setattr(self, key, self._clamp_param(key, val))
        self._check_preset_match()
        self._rebuild_map()

    def handle_event(self, event):
        s = self.size
        mx, my = self._get_window_mouse_pos()

        if event.type == pygame.QUIT:
            self._running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._running = False
            elif event.key == pygame.K_F9 and not _HAS_WIN32:
                # On Windows F9 is polled globally in _poll_hotkeys()
                self._toggle_screenshot_mode()
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3,
                               pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7):
                idx = event.key - pygame.K_1
                if idx < len(self.params_order):
                    self.selected_param = self.params_order[idx]

        elif event.type == pygame.MOUSEWHEEL:
            d = 1 if event.y > 0 else -1
            m = 3 if abs(event.y) > 2 else 1

            hovered = self._icon_hit_test(mx, my)
            if hovered and self.radial_alpha > 0.3:
                self._adjust_param(hovered, d * m)
            else:
                self._adjust_param(self.selected_param, d * m)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Resize handle
            if self._handle_rect.collidepoint(mx, my) and self.panel_alpha > 0.3:
                self.resizing = True
                self.resize_start = self._get_abs_mouse()
                self.resize_start_dist = self._radial_dist_from_center()
                self.resize_size0 = self.size
                self._pending_size = self.size
                return

            # Close button
            if self._close_btn_rect.collidepoint(mx, my) and self.panel_alpha > 0.3:
                self._running = False
                return

            # Dropdown items
            if self.dropdown_open and self.panel_alpha > 0.3:
                for name, rect in self._dropdown_rects:
                    if rect.collidepoint(mx, my):
                        self._apply_preset(name)
                        self._rebuild_map()
                        self.dropdown_open = False
                        return

            # Dropdown button
            if self._dropdown_btn_rect.collidepoint(mx, my) and self.panel_alpha > 0.3:
                self.dropdown_open = not self.dropdown_open
                return

            # Always-on-top checkbox
            if self._aot_checkbox_rect.collidepoint(mx, my) and self.panel_alpha > 0.3:
                self.always_on_top = not self.always_on_top
                self._set_always_on_top(self.always_on_top)
                return

            # Radial icon click — select or start drag
            icon_key = self._icon_hit_test(mx, my)
            if icon_key and self.radial_alpha > 0.3:
                self._icon_dragging = icon_key
                abs_pos = self._get_abs_mouse()
                self._icon_drag_start_x = abs_pos[0]
                self._icon_drag_start_y = abs_pos[1]
                self._icon_drag_start_val = getattr(self, icon_key)
                self.selected_param = icon_key
                return

            # Drag the whole lens
            self.dragging = True
            abs_mx, abs_my = self._get_abs_mouse()
            wx, wy = self.win_pos
            self.drag_offset = (wx - abs_mx, wy - abs_my)

        elif event.type == pygame.MOUSEBUTTONUP:
            if self._icon_dragging:
                self._icon_dragging = None

            if self.resizing:
                if self._pending_size != self.size:
                    self._resize_window(self._pending_size)
                else:
                    self._leave_resize_expand()
            self.dragging = False
            self.resizing = False

        elif event.type == pygame.MOUSEMOTION:
            if self._icon_dragging:
                abs_pos = self._get_abs_mouse()
                dx = abs_pos[0] - self._icon_drag_start_x   # right = positive
                dy = self._icon_drag_start_y - abs_pos[1]    # up = positive
                # Dominant axis wins
                if abs(dx) >= abs(dy):
                    dominant = dx
                else:
                    dominant = dy
                key = self._icon_dragging
                step = PARAM_STEP[key]
                delta = dominant / 10.0
                new_val = self._icon_drag_start_val + step * delta
                setattr(self, key, self._clamp_param(key, new_val))
                self._check_preset_match()
                self._rebuild_map()
            elif self.resizing:
                # Radial resize: distance from center determines size
                current_dist = self._radial_dist_from_center()
                delta_dist = current_dist - self.resize_start_dist
                # Map pixel distance change to size change (2x because diameter)
                self._pending_size = max(MIN_SIZE, min(MAX_SIZE,
                                          self.resize_size0 + int(delta_dist * 2)))

    def _update_drag(self):
        if not self.dragging:
            return
        if _HAS_WIN32 and ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000 == 0:
            self.dragging = False
            return
        abs_mx, abs_my = self._get_abs_mouse()
        wx = abs_mx + self.drag_offset[0]
        wy = abs_my + self.drag_offset[1]
        if (wx, wy) != self.win_pos:
            self._move_window(wx, wy)

    # ── focus handling ────────────────────────────────────────────────────────

    def _check_focus(self):
        if not _HAS_WIN32:
            return
        user32 = ctypes.windll.user32
        _, hwnd = self._get_hwnd()
        if not hwnd:
            return
        if user32.GetAsyncKeyState(0x01) & 0x8000 == 0:
            return
        if user32.GetForegroundWindow() == hwnd:
            return
        pt = ctypes.wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        wx, wy = self.win_pos
        s = self.size
        cx, cy = wx + s // 2, wy + s // 2
        if (pt.x - cx) ** 2 + (pt.y - cy) ** 2 <= (s // 2) ** 2:
            user32.SetForegroundWindow(hwnd)
            self.dragging = True
            self.drag_offset = (wx - pt.x, wy - pt.y)

    def _poll_hotkeys(self):
        """Global F9 toggle (works even when the lens isn't focused)."""
        if not _HAS_WIN32:
            return
        down = bool(ctypes.windll.user32.GetAsyncKeyState(0x78) & 0x8000)  # VK_F9
        if down and not self._f9_was_down:
            self._toggle_screenshot_mode()
        self._f9_was_down = down

    # ── main loop ─────────────────────────────────────────────────────────────

    def run(self):
        if _HAS_WIN32:
            try:
                hwnd = pygame.display.get_wm_info()["window"]
                rect = ctypes.wintypes.RECT()
                ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                self.win_pos = (rect.left, rect.top)
            except Exception:
                pass
        self._set_always_on_top(self.always_on_top)
        self._exclude_from_capture()
        self._apply_window_region()

        try:
            while self._running:
                self._check_focus()
                self._poll_hotkeys()
                for event in pygame.event.get():
                    self.handle_event(event)
                self._update_drag()
                # In screenshot mode the window is visible to capture, so
                # grabbing the screen would feed the lens back into itself.
                # Keep showing the last rendered frame instead.
                if not self.screenshot_mode:
                    self.render()
                self.clock.tick(FPS)
        finally:
            # Always clean up the window region on exit, even on crash/Ctrl+C
            user32, hwnd = self._get_hwnd()
            if hwnd:
                ctypes.windll.user32.SetWindowRgn(hwnd, 0, True)
            self.sct.close()
            pygame.quit()
            sys.exit()


if __name__ == "__main__":
    LensMagnifier().run()
