"""Optional, screenshot-free-in-storage CSP tool recognition via Windows GDI.

Calibrated to the user's 1920x1080 primary monitor and fixed left toolbar.
This reads 45 pixels at most, only when CSP is foreground. It never saves
screenshots, changes CSP, or accesses the drawing canvas.
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
X_POINTS = (33, 35, 37)
Y_OFFSETS = (-2, 0, 2)
MIN_SCORES = {'P1':5, 'P2':5, 'B':4, 'J':5, 'E':5}
# B is only 4/9 in one real screenshot; E=3/9 in the log is unreliable.
STABLE_READS = 3


def is_selected_rgb(rgb):
    r, g, b = rgb
    return 70 <= r <= 135 and b - r >= 20 and g - r >= 5


def choose_tool(scores):
    """Accept exactly one strong selected icon, reject ambiguous hover states."""
    candidates = [key for key, _, _ in TOOL_POINTS
                  if scores.get(key, 0) >= MIN_SCORES[key]]
    # If a second button has a near-selected appearance, don't guess.
    runners = [key for key, _, _ in TOOL_POINTS if scores.get(key, 0) >= 4]
    if len(candidates) != 1 or len(runners) != 1:
        return None
    return candidates[0]


def mode_for_key(key):
    return next((mode for name, mode, _ in TOOL_POINTS if key == name), None)


class VisualStabilizer:
    """Three matching samples required; uncertain samples never change modes."""
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
    """Poll small screen area at most ~6 times/sec, only when CSP foreground.

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
            self.reason = f'{key} -> {mode} ({self.last_score}/9)'
        elif key is None:
            self.reason = 'sin lectura segura; teclado disponible'
        else:
            self.reason = 'verificando seleccion...'
        return mode
