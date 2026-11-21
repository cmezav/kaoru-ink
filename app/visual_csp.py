"""Optional pixel-only CSP tool recognition via Windows GDI.

Calibrated to 1920x1080 primary and current left toolbar. Samples 120 pixels
within the toolbar only, never the canvas, and never writes screenshot files.
"""
from __future__ import annotations

import ctypes
import os
import time

# Two P buttons deliberately map to the SAME audio mode.
TOOL_POINTS = (
    ('P1', 'pencil', 166),
    ('P2', 'pencil', 196),
    ('B',  'brush', 222),
    ('J',  'brush', 340),
    ('E',  'eraser', 272),
)
# These points avoid pale icon strokes; 24 pixels per tool instead of 9.
# Offline calibration: P1=20, P2=19, B=21, J=14, E=14 out of 24.
X_POINTS = (12, 14, 18, 20, 24, 25, 33, 35)
Y_OFFSETS = (-3, 0, 3)
MIN_SCORES = {'P1':10, 'P2':10, 'B':10, 'J':10, 'E':10}
STRONG_SNAPSHOT = 10
STABLE_READS = 2


def is_selected_rgb(rgb):
    r, g, b = rgb
    return 70 <= r <= 135 and b - r >= 20 and g - r >= 5


def choose_tool(scores, *, min_score=None):
    """Select the unique highlighted button, never a runner-up or hover."""
    threshold = MIN_SCORES if min_score is None else {k:min_score for k in MIN_SCORES}
    candidates = [key for key, _, _ in TOOL_POINTS
                  if scores.get(key, 0) >= threshold[key]]
    if len(candidates) != 1:
        return None
    winner = candidates[0]
    # Readings from a second highlighted button must be substantially weaker.
    if any(scores.get(other, 0) >= max(6, scores[winner]-5)
           for other, _, _ in TOOL_POINTS if other != winner):
        return None
    return winner

def mode_for_key(key):
    return next((mode for name, mode, _ in TOOL_POINTS if key == name), None)


class VisualStabilizer:
    """Consecutive selected readings required; uncertainty preserves prior mode."""
    def __init__(self):
        self.candidate = None
        self.consecutive = 0
        self.selected = None

    def reset(self):
        self.candidate = None
        self.consecutive = 0
        self.selected = None

    def feed(self, key):
        if key is None:
            self.candidate = None
            self.consecutive = 0
            return None  # Hold previous tool rather than guessing.
        if key == self.candidate:
            self.consecutive += 1
        else:
            self.candidate = key
            self.consecutive = 1
        if self.consecutive >= STABLE_READS:
            self.selected = key
            return mode_for_key(key)
        return None


class CspVisualDetector:
    """Poll selected pixels only when CSP foreground, no screenshot storage.

    It is deliberately fail-closed on other resolutions and window layouts.
    Keyboard shortcuts and UI tool buttons remain functional independently.
    """
    def __init__(self, enabled=True, clock=time.monotonic):
        self.enabled = enabled
        self.clock = clock
        self.stable = VisualStabilizer()
        self.last_check = 0.0
        self.last_key = None
        self.last_score = 0
        self.reason = 'pendiente'
        self._win = None
        self._gdi = None
        if os.name == 'nt':
            self._win = ctypes.WinDLL('user32', use_last_error=True)
            self._gdi = ctypes.WinDLL('gdi32', use_last_error=True)
            self._win.GetForegroundWindow.restype = ctypes.c_void_p
            self._win.GetWindowRect.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
            self._win.GetWindowRect.restype = ctypes.c_int
            self._win.GetSystemMetrics.argtypes = (ctypes.c_int,)
            self._win.GetSystemMetrics.restype = ctypes.c_int
            self._win.GetDC.argtypes = (ctypes.c_void_p,)
            self._win.GetDC.restype = ctypes.c_void_p
            self._win.ReleaseDC.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
            self._gdi.GetPixel.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_int)
            self._gdi.GetPixel.restype = ctypes.c_uint32

    def reset(self):
        self.stable.reset()
        self.last_key = None
        self.last_score = 0
        self.last_check = 0.0

    def _layout_supported(self):
        if self._win is None:
            self.reason = 'solo Windows'
            return False
        if (self._win.GetSystemMetrics(0), self._win.GetSystemMetrics(1)) != (1920, 1080):
            self.reason = 'calibrada para 1920x1080'
            return False
        hwnd = self._win.GetForegroundWindow()
        if not hwnd:
            return False
        rect = (ctypes.c_long * 4)()
        if not self._win.GetWindowRect(hwnd, ctypes.byref(rect)):
            return False
        l, top, right, bottom = rect
        if not (l <= 10 and top <= 10 and right >= 1900 and bottom >= 1060):
            self.reason = 'CSP debe estar maximizado en pantalla principal'
            return False
        return True

    def _read_scores(self):
        dc = self._win.GetDC(None)
        if not dc:
            raise OSError('No se pudo leer la region de herramientas de CSP')
        scores = {}
        try:
            for key, _mode, y in TOOL_POINTS:
                hits = 0
                for x in X_POINTS:
                    for dy in Y_OFFSETS:
                        color = int(self._gdi.GetPixel(dc, x, y + dy))
                        if color == 0xffffffff:
                            continue
                        # COLORREF is packed as 0x00BBGGRR.
                        rgb = (color & 255, (color >> 8) & 255, (color >> 16) & 255)
                        hits += is_selected_rgb(rgb)
                scores[key] = hits
        finally:
            self._win.ReleaseDC(None, dc)
        return scores

    def snapshot_mode(self, csp_focused):
        """Strong synchronous read right before a canvas stroke begins.

        A toolbar click can be followed by drawing before 2 background polls.
        A confident snapshot at pen-down prevents that first stroke using P.
        Unknown/moved UI fails closed without switching.
        """
        if not self.enabled or not csp_focused or not self._layout_supported():
            return None
        try:
            scores = self._read_scores()
        except OSError:
            return None
        key = choose_tool(scores, min_score=STRONG_SNAPSHOT)
        if key is None:
            return None
        self.stable.candidate = key
        self.stable.consecutive = STABLE_READS
        self.stable.selected = key
        self.last_key = key
        self.last_score = scores[key]
        self.reason = f'{key} -> {mode_for_key(key)} ({self.last_score}/24)'
        return mode_for_key(key)

    def poll(self, csp_focused):
        """Return confirmed audio mode or None; never guesses on uncertainty."""
        if not self.enabled or not csp_focused:
            self.reset()
            self.reason = 'desactivada' if not self.enabled else 'esperando CSP'
            return None
        now = self.clock()
        if self.last_check and now - self.last_check < .16:
            return None
        self.last_check = now
        if not self._layout_supported():
            self.stable.reset()
            return None
        try:
            scores = self._read_scores()
        except OSError:
            self.reason = 'lectura no disponible'
            self.stable.reset()
            return None
        key = choose_tool(scores)
        mode = self.stable.feed(key)
        if mode is not None:
            self.last_key = key
            self.last_score = scores[key]
            self.reason = f'{key} -> {mode} ({self.last_score}/24)'
        elif key is None:
            self.reason = 'sin lectura segura; teclado disponible'
        else:
            self.reason = 'verificando seleccion...'
        return mode
