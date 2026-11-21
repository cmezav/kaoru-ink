"""Mouse-only audio: exactly one playback per drag in P/B/E; no loops."""
import json
import random
import wave
from pathlib import Path

import numpy as np


class AudioEngine:
    MODES = ('pencil','brush','eraser')

    def __init__(self, sounds_folder: Path):
        import pygame
        self.pg = pygame
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=1, buffer=512)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(5)
        self.channels = {mode:pygame.mixer.Channel(i) for i, mode in enumerate(self.MODES)}
        self.preview_channel = pygame.mixer.Channel(3)
        self.folder = Path(sounds_folder)
        library=json.loads((self.folder/'library.json').read_text(encoding='utf8'))
        self.samples={s['id']:s for s in library['samples']}
        self.by_category={category:[s['id'] for s in library['samples'] if s['category']==category]
                          for category in self.MODES}
        if any(not self.by_category[c] for c in self.MODES):
            raise ValueError('Missing samples for a P/B/E tool')
        self.last_random={}
        self.cache={}
        self.last_preview=None
        self.active_mode=None
        self.volume=.76
        self.speed=55
        self.muted=False
        self.motion_gain=.75

    def select(self,category,desired):
        choices=self.by_category[category]
        if desired in choices:return desired
        previous=self.last_random.get(category)
        sample=random.choice([x for x in choices if x!=previous] or choices)
        self.last_random[category]=sample
        return sample

    def _load_pcm(self,filename):
        with wave.open(str(self.folder/filename),'rb') as wav:
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1,2,22050):
                raise ValueError('Expected mono 16-bit 22,050 Hz WAV: '+filename)
            return np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2')

    def _sound(self,ident,kind):
        key=(ident,kind,self.speed)
        if key not in self.cache:
            field='file' if kind=='held' else 'preview_file'
            pcm=self._load_pcm(self.samples[ident][field])
            # Resample to 44.1k mixer rate, changing speed + tone in one action.
            ratio=(self.speed/100.)/2.
            size=max(4,int(len(pcm)/ratio))
            positions=np.arange(size,dtype=np.float32)*ratio
            out=np.interp(positions,np.arange(len(pcm)),pcm).clip(-32768,32767).astype('<i2')
            if len(self.cache)>=5:self.cache.clear()
            self.cache[key]=self.pg.mixer.Sound(buffer=out.tobytes())
        return self.cache[key]

    def begin_stroke(self,category,desired):
        """Called only once when the mouse first MOVES during a held click."""
        if self.muted or self.active_mode is not None or category not in self.MODES:
            return False
        ident=self.select(category,desired)
        ch=self.channels[category]
        # One 26-second unique friction stream. NEVER repeats or switches sources.
        ch.play(self._sound(ident,'held'), loops=0, fade_ms=35)
        self.active_mode=category
        self.motion_gain=.75
        self.refresh_volume()
        return True

    def update_motion(self,px_per_sec):
        if self.active_mode is None:return
        # Movement affects volume, not sound playback. Stopping/starting within
        # a held mouse press does not cause an additional event.
        goal=.04 if px_per_sec<=1 else min(1.,.34+px_per_sec/850.)
        self.motion_gain=.5*self.motion_gain+.5*goal
        self.refresh_volume()

    def stop_stroke(self,fade_ms=105):
        if self.active_mode is not None:
            channel=self.channels[self.active_mode]
            if channel.get_busy():channel.fadeout(fade_ms)
        self.active_mode=None

    def stop_all(self):
        self.stop_stroke(75)
        for ch in self.channels.values():
            if ch.get_busy():ch.fadeout(75)
        self.preview_channel.fadeout(75)

    def set_volume(self,value):
        self.volume=max(0,min(100,int(value)))/100.
        self.refresh_volume()

    def refresh_volume(self):
        v=0. if self.muted else self.volume
        for name,ch in self.channels.items():
            ch.set_volume(v*self.motion_gain if name==self.active_mode else v)
        self.preview_channel.set_volume(v*.85)

    def set_speed(self,value):
        self.stop_stroke()
        self.preview_channel.stop()
        self.speed=max(45,min(120,int(value)))
        self.cache.clear()

    def preview(self,category,desired):
        ident=self.select(category,desired)
        self.preview_channel.stop()
        # One isolated real source excerpt, never a loop.
        self.preview_channel.play(self._sound(ident,'preview'),loops=0,fade_ms=18)
        self.refresh_volume()
        return self.samples[ident]['label']

    def close(self):
        self.stop_all()
        self.pg.mixer.quit()
