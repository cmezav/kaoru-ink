"""Low-latency, pitch-adjustable sound playback using preloaded PCM clips."""
import json
import random
from pathlib import Path
import numpy as np


class AudioEngine:
    def __init__(self, sounds_folder:Path):
        import pygame
        self.pg=pygame
        self.pg.mixer.pre_init(frequency=44100, size=-16, channels=1, buffer=512)
        self.pg.mixer.init()
        self.pg.mixer.set_num_channels(8)
        self.channels = {
            'short': self.pg.mixer.Channel(0),
            'medium': self.pg.mixer.Channel(4),
            'long': self.pg.mixer.Channel(1),
            'brush': self.pg.mixer.Channel(2),
            'preview': self.pg.mixer.Channel(3),
        }
        data=json.loads((sounds_folder/'library.json').read_text(encoding='utf-8'))
        self.samples={s['id']:s for s in data['samples']}
        self.by_category={c:[s['id'] for s in data['samples'] if s['category']==c] for c in ('short','medium','long','brush')}
        self.pcm={}
        for ident, sample in self.samples.items():
            # Already single-channel signed 16-bit PCM WAV; strip WAV header via wave.
            import wave
            with wave.open(str(sounds_folder / sample['file']), 'rb') as wav:
                assert wav.getframerate()==44100 and wav.getnchannels()==1 and wav.getsampwidth()==2
                self.pcm[ident]=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').copy()
        self.cache={}
        self.volume=.76
        self.speed=100
        self.muted=False
        self.current={'long':None,'brush':None}
        self.last_random={}

    def select(self, category, desired):
        if desired in self.by_category[category]:
            return desired
        choices=self.by_category[category]
        previous=self.last_random.get(category)
        candidate=random.choice([c for c in choices if c!=previous] or choices)
        self.last_random[category]=candidate
        return candidate

    def sound(self, sample_id):
        key=(sample_id,self.speed)
        if key not in self.cache:
            original=self.pcm[sample_id]
            if self.speed==100:
                result=original
            else:
                # Time-scale with pitch shift, intentionally like a tape speed knob.
                factor=self.speed/100.
                n=max(16, int(round(len(original)/factor)))
                result=np.interp(np.arange(n)*factor,
                                 np.arange(len(original)),original, left=0,right=0).astype('<i2')
            if len(self.cache)>180:
                self.cache.clear()
            self.cache[key]=self.pg.mixer.Sound(buffer=result.tobytes())
        return self.cache[key]

    def set_volume(self, percent):
        self.volume=percent/100.
        self.refresh_volume()

    def refresh_volume(self):
        v=0.0 if self.muted else self.volume
        for name,ch in self.channels.items():
            ch.set_volume(v * (0.9 if name=='preview' else 1.0))

    def set_speed(self, value):
        self.speed=value
        self.cache.clear()

    def play_short(self, desired):
        if self.muted:return
        ident=self.select('short',desired)
        self.channels['short'].play(self.sound(ident))
        self.refresh_volume()

    def play_medium(self, desired):
        if self.muted:return
        self.channels['short'].fadeout(65)
        ident=self.select('medium',desired)
        self.channels['medium'].play(self.sound(ident))
        self.refresh_volume()

    def start_loop(self, category, desired):
        if self.muted:return
        ch=self.channels[category]
        if ch.get_busy():
            if self.current[category] is not None:return
            ch.stop()  # Stop a previous fadeout, if a new drag just began.
        ident=self.select(category,desired)
        self.current[category]=ident
        ch.play(self.sound(ident),loops=-1,fade_ms=90)
        self.refresh_volume()

    def stop_loop(self, category,fade_ms=130):
        ch=self.channels[category]
        if ch.get_busy():ch.fadeout(fade_ms)
        self.current[category]=None

    def stop_stroke(self):
        self.stop_loop('long')
        self.stop_loop('brush')
        self.channels['medium'].fadeout(120)
        # Short attacks finish their own designed fade; no hard cut.

    def stop_all(self):
        for c in self.channels.values():c.fadeout(100)
        self.current={'long':None,'brush':None}

    def preview(self, category,desired):
        ident=self.select(category,desired)
        ch=self.channels['preview']
        ch.stop()
        ch.play(self.sound(ident),loops=1 if self.samples[ident]['loop'] else 0,fade_ms=60)
        self.refresh_volume()
        return self.samples[ident]['label']

    def refresh_live_loop(self,category,desired):
        if self.current[category]:
            self.stop_loop(category,70)
            # Avoid playing on a fading channel: pygame replaces it after fade.
            self.start_loop(category,desired)

    def close(self):
        self.stop_all()
        self.pg.mixer.quit()
