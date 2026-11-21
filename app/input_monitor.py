"""Clip Studio Paint-only mouse drags and P/B/E shortcut recognition."""
import time
from math import hypot
from PySide6.QtCore import QObject, Signal
from .focus import foreground_paint


class InputEvents(QObject):
    down = Signal(int, int)
    moved = Signal(int, int)
    up = Signal()
    tool = Signal(str)
    pressure = Signal(float)
    issue = Signal(str)


class MouseKeyboardMonitor:
    def __init__(self, bus: InputEvents):
        self.bus=bus
        self.engaged=False
        self.last_emit=0.
        self.mods=set()
        self.mouse_listener=None
        self.keyboard_listener=None

    def start(self):
        from pynput import mouse, keyboard
        self.mouse=mouse
        self.keyboard=keyboard
        self.mouse_listener=mouse.Listener(on_click=self.on_click,on_move=self.on_move)
        self.keyboard_listener=keyboard.Listener(on_press=self.on_key_press,on_release=self.on_key_release)
        self.mouse_listener.start()
        self.keyboard_listener.start()

    def on_click(self,x,y,button,pressed):
        if button!=self.mouse.Button.left:return
        if pressed:
            self.engaged=foreground_paint()
            if self.engaged:self.bus.down.emit(int(x),int(y))
        else:
            if self.engaged:self.bus.up.emit()
            self.engaged=False

    def on_move(self,x,y):
        if not self.engaged:return
        now=time.monotonic()
        if now-self.last_emit<.016:return
        self.last_emit=now
        self.bus.moved.emit(int(x),int(y))

    def _mod_name(self,key):
        k=self.keyboard.Key
        if key in (k.ctrl,k.ctrl_l,k.ctrl_r):return 'ctrl'
        if key in (k.alt,k.alt_l,k.alt_r,k.alt_gr):return 'alt'
        if key in (k.cmd,k.cmd_l,k.cmd_r):return 'win'
        return None

    def on_key_press(self,key):
        modifier=self._mod_name(key)
        if modifier:
            self.mods.add(modifier)
            return
        if self.mods:return
        try:ch=key.char.lower()
        except (AttributeError,TypeError):return
        mapping={'p':'pencil','b':'brush','j':'brush','e':'eraser'}
        if ch in mapping and foreground_paint():
            self.bus.tool.emit(mapping[ch])

    def on_key_release(self,key):
        modifier=self._mod_name(key)
        if modifier:self.mods.discard(modifier)

    def stop(self):
        for listener in (self.mouse_listener,self.keyboard_listener):
            if listener:listener.stop()


class StrokeController:
    """At most one begin_stroke() for each mouse-down/up, for every mode."""
    def __init__(self,audio,settings):
        self.audio=audio
        self.settings=settings
        self.mode='pencil'
        self.active=False
        self.started=False
        self.last_point=(0,0)
        self.last_motion=0.
        self.last_tick_motion=0.
        self.travel=0.

    def change_mode(self,mode):
        if mode not in ('pencil','brush','eraser'):return
        if mode!=self.mode:
            self.audio.stop_stroke()
            self.mode=mode
            self.active=False
            self.started=False

    def mouse_down(self,x,y):
        self.audio.stop_stroke()
        self.active=True
        self.started=False
        self.last_point=(x,y)
        self.last_motion=time.monotonic()
        self.last_tick_motion=self.last_motion
        self.travel=0.

    def mouse_move(self,x,y):
        if not self.active:return
        now=time.monotonic()
        dist=hypot(x-self.last_point[0],y-self.last_point[1])
        dt=max(.016,now-self.last_motion)
        self.last_point=(x,y)
        if dist<1.2:return
        self.travel+=dist
        self.last_motion=now
        self.last_tick_motion=now
        if not self.started and self.travel>=4:
            self.started=True  # Set before audio, never retry in same drag.
            self.audio.begin_stroke(self.mode,self.settings[self.mode+'_id'])
        if self.started:self.audio.update_motion(dist/dt)

    def mouse_up(self):
        if self.active or self.started:self.audio.stop_stroke()
        self.active=False
        self.started=False

    def tick(self,focused):
        if not focused:
            if self.active or self.started:self.audio.stop_stroke()
            self.active=False
            self.started=False
            return
        # Quiet on a mouse pause without stopping or retriggering.
        if self.active and self.started and time.monotonic()-self.last_motion>.10:
            self.audio.update_motion(0)

    def disable(self):
        self.active=False
        self.started=False
        self.audio.stop_all()
