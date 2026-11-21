"""Listen only to mouse left drag + P/B shortcut; no logging or key recording."""
import time
from math import hypot
from PySide6.QtCore import QObject, Signal
from .focus import foreground_paint


class InputEvents(QObject):
    down=Signal(int,int)
    moved=Signal(int,int)
    up=Signal()
    tool=Signal(str)
    issue=Signal(str)


class MouseKeyboardMonitor:
    def __init__(self, bus:InputEvents):
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
        if now-self.last_emit<0.016:return
        self.last_emit=now
        # Recheck focus inside Qt's event loop; don't trigger another app.
        self.bus.moved.emit(int(x),int(y))

    def _mod_name(self,key):
        k=self.keyboard.Key
        if key in (k.ctrl,k.ctrl_l,k.ctrl_r):return 'ctrl'
        if key in (k.alt,k.alt_l,k.alt_r,k.alt_gr):return 'alt'
        if key in (k.cmd,k.cmd_l,k.cmd_r):return 'win'
        return None

    def on_key_press(self,key):
        mod=self._mod_name(key)
        if mod:
            self.mods.add(mod)
            return
        if self.mods:return
        try:
            val=key.char.lower()
        except (AttributeError,TypeError):
            return
        if val in ('p','b') and foreground_paint():
            self.bus.tool.emit('pencil' if val=='p' else 'brush')

    def on_key_release(self,key):
        mod=self._mod_name(key)
        if mod:self.mods.discard(mod)

    def stop(self):
        for listener in (self.mouse_listener,self.keyboard_listener):
            if listener:listener.stop()


class StrokeController:
    """Decisions are triggered by ACTUAL movement while left button is held."""
    def __init__(self,audio, settings):
        self.audio=audio
        self.settings=settings
        self.mode='pencil'
        self.active=False
        self.start_time=0.
        self.last_motion=0.
        self.last_point=(0,0)
        self.travel=0.
        self.started_short=False
        self.started_medium=False

    def change_mode(self,mode):
        if mode not in ('pencil','brush'):return
        if mode!=self.mode:
            self.audio.stop_stroke()
            self.mode=mode
            self.started_short=False
            self.started_medium=False

    def mouse_down(self,x,y):
        self.audio.stop_stroke()
        self.active=True
        self.start_time=time.monotonic()
        self.last_motion=self.start_time
        self.last_point=(x,y)
        self.travel=0.
        self.started_short=False
        self.started_medium=False

    def mouse_move(self,x,y):
        if not self.active:return
        now=time.monotonic()
        distance=hypot(x-self.last_point[0],y-self.last_point[1])
        self.last_point=x,y
        if distance<1.5:return
        self.travel+=distance
        self.last_motion=now
        if self.travel<8:return
        if self.mode=='brush':
            self.audio.start_loop('brush',self.settings['brush_id'])
        else:
            if not self.started_short:
                self.audio.play_short(self.settings['short_id'])
                self.started_short=True
            if (now-self.start_time)>0.19 and self.travel>15 and not self.started_medium:
                self.audio.play_medium(self.settings['medium_id'])
                self.started_medium=True
            if (now-self.start_time)>0.58 and self.travel>28:
                self.audio.channels['medium'].fadeout(65)
                self.audio.start_loop('long',self.settings['long_id'])

    def mouse_up(self):
        self.active=False
        self.audio.stop_stroke()

    def tick(self, focused):
        if not focused:
            if self.active:self.mouse_up()
            self.audio.stop_stroke()
            return
        if self.active and time.monotonic()-self.last_motion>0.19:
            # A held but unmoving mouse shouldn't sound like constant painting.
            self.audio.stop_stroke()

    def disable(self):
        self.active=False
        self.audio.stop_all()
