"""Global input events, played only when Clip Studio Paint is foreground."""
import time
from math import hypot
from PySide6.QtCore import QObject, Signal
from .focus import foreground_paint


class InputEvents(QObject):
    down = Signal(int, int)
    moved = Signal(int, int)
    up = Signal()
    tool = Signal(str)
    issue = Signal(str)


class MouseKeyboardMonitor:
    def __init__(self, bus: InputEvents):
        self.bus = bus
        self.engaged = False
        self.last_emit = 0.
        self.mods = set()
        self.mouse_listener = None
        self.keyboard_listener = None

    def start(self):
        from pynput import mouse, keyboard
        self.mouse = mouse
        self.keyboard = keyboard
        self.mouse_listener = mouse.Listener(on_click=self.on_click, on_move=self.on_move)
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_key_press, on_release=self.on_key_release
        )
        self.mouse_listener.start()
        self.keyboard_listener.start()

    def on_click(self, x, y, button, pressed):
        if button != self.mouse.Button.left:
            return
        if pressed:
            self.engaged = foreground_paint()
            if self.engaged:
                self.bus.down.emit(int(x), int(y))
        else:
            if self.engaged:
                self.bus.up.emit()
            self.engaged = False

    def on_move(self, x, y):
        if not self.engaged:
            return
        now = time.monotonic()
        if now - self.last_emit < .016:
            return
        self.last_emit = now
        self.bus.moved.emit(int(x), int(y))

    def _mod_name(self, key):
        k = self.keyboard.Key
        if key in (k.ctrl, k.ctrl_l, k.ctrl_r):
            return 'ctrl'
        if key in (k.alt, k.alt_l, k.alt_r, k.alt_gr):
            return 'alt'
        if key in (k.cmd, k.cmd_l, k.cmd_r):
            return 'win'
        return None

    def on_key_press(self, key):
        mod = self._mod_name(key)
        if mod:
            self.mods.add(mod)
            return
        if self.mods:
            return
        try:
            val = key.char.lower()
        except (AttributeError, TypeError):
            return
        if val in ('p', 'b') and foreground_paint():
            self.bus.tool.emit('pencil' if val == 'p' else 'brush')

    def on_key_release(self, key):
        mod = self._mod_name(key)
        if mod:
            self.mods.discard(mod)

    def stop(self):
        for listener in (self.mouse_listener, self.keyboard_listener):
            if listener:
                listener.stop()


class StrokeController:
    """P: one ongoing one-shot per drag. B: loop only while actually moving."""
    def __init__(self, audio, settings):
        self.audio = audio
        self.settings = settings
        self.mode = 'pencil'
        self.active = False
        self.last_motion = 0.
        self.last_point = (0, 0)
        self.travel = 0.
        self.pencil_started = False
        self.pencil_finished = False
        self.brush_playing = False

    def change_mode(self, mode):
        if mode not in ('pencil', 'brush'):
            return
        if mode != self.mode:
            self.audio.stop_stroke()
            self.mode = mode
            self.active = False
            self.pencil_finished = False
            self.pencil_started = False
            self.brush_playing = False

    def mouse_down(self, x, y):
        self.audio.stop_stroke()
        self.active = True
        self.last_motion = time.monotonic()
        self.last_point = (x, y)
        self.travel = 0.
        self.pencil_started = False
        self.pencil_finished = False
        self.brush_playing = False

    def mouse_move(self, x, y):
        if not self.active:
            return
        now = time.monotonic()
        dist = hypot(x-self.last_point[0], y-self.last_point[1])
        self.last_point = (x, y)
        if dist < 1.5:
            return
        self.travel += dist
        self.last_motion = now
        if self.mode == 'brush':
            if self.travel >= 7 and not self.brush_playing:
                self.audio.start_loop('brush', self.settings['brush_id'])
                self.brush_playing = True
        elif self.travel >= 5 and not self.pencil_started and not self.pencil_finished:
            self.audio.start_pencil(
                self.settings['short_id'],
                self.settings['medium_id'],
                self.settings['long_id'],
            )
            self.pencil_started = True

    def mouse_up(self):
        self.active = False
        self.audio.stop_stroke()
        self.brush_playing = False

    def tick(self, focused):
        if not focused:
            self.active = False
            self.pencil_finished = True
            self.pencil_started = False
            self.brush_playing = False
            self.audio.stop_stroke()
            return
        if self.active and time.monotonic()-self.last_motion > .32:
            if self.mode == 'brush' and self.brush_playing:
                self.audio.stop_brush()
                self.brush_playing = False
                self.travel = 0.
            elif self.mode == 'pencil' and self.pencil_started:
                self.audio.stop_stroke()
                # A paused pen drag is still the same stroke: do not re-trigger.
                self.pencil_finished = True

    def disable(self):
        self.active = False
        self.audio.stop_all()
