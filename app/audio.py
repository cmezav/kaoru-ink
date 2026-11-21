"""Playback for Kaoru Ink: P=one isolated scrape; B=clean loop only."""
import json
import random
import wave
from pathlib import Path

import numpy as np


class AudioEngine:
    def __init__(self, sounds_folder: Path):
        import pygame
        self.pg=pygame
        pygame.mixer.pre_init(frequency=44100,size=-16,channels=1,buffer=512)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(6)
        self.channels={
            'pencil':pygame.mixer.Channel(0),
            'brush':pygame.mixer.Channel(1),
            'preview':pygame.mixer.Channel(2),
        }
        data=json.loads((sounds_folder/'library.json').read_text(encoding='utf-8'))
        self.samples={s['id']:s for s in data['samples']}
        self.by_category={c:[s['id'] for s in data['samples'] if s['category']==c]
                          for c in ('pencil','brush')}
        self.pcm={}
        for ident,sample in self.samples.items():
            with wave.open(str(sounds_folder/sample['file']),'rb') as wav:
                if (wav.getframerate(),wav.getnchannels(),wav.getsampwidth()) != (44100,1,2):
                    raise ValueError(f'Invalid WAV format: {ident}')
                self.pcm[ident]=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').copy()
        self.cache={}
        self.last_random={}
        self.volume=.76
        self.speed=55
        self.muted=False
        self.current_brush=None

    def select(self,category,desired):
        choices=self.by_category[category]
        if desired in choices:return desired
        previous=self.last_random.get(category)
        ident=random.choice([x for x in choices if x!=previous] or choices)
        self.last_random[category]=ident
        return ident

    def sound(self,ident):
        key=(ident,self.speed)
        if key not in self.cache:
            original=self.pcm[ident]
            ratio=self.speed/100.
            if ratio==1:
                pcm=original
            else:
                count=max(16,int(len(original)/ratio))
                at=np.arange(count,dtype='float32')*ratio
                pcm=np.clip(np.interp(at,np.arange(len(original)),original),-32768,32767).astype('<i2')
            if len(self.cache)>32:self.cache.clear()
            self.cache[key]=self.pg.mixer.Sound(buffer=pcm.tobytes())
        return self.cache[key]

    def start_pencil(self,desired):
        """Only ONE recorded contact, played ONCE; no intro/mid/body layers."""
        if self.muted:return
        ident=self.select('pencil',desired)
        channel=self.channels['pencil']
        channel.play(self.sound(ident),loops=0,fade_ms=30)
        self.refresh_volume()

    def start_loop(self,category,desired):
        if category!='brush':raise ValueError('Only B / brush may loop')
        if self.muted or self.current_brush is not None:return
        ident=self.select('brush',desired)
        self.current_brush=ident
        channel=self.channels['brush']
        channel.stop()
        channel.play(self.sound(ident),loops=-1,fade_ms=80)
        self.refresh_volume()

    def stop_brush(self,fade_ms=130):
        channel=self.channels['brush']
        if channel.get_busy():channel.fadeout(fade_ms)
        self.current_brush=None

    def stop_stroke(self):
        channel=self.channels['pencil']
        if channel.get_busy():channel.fadeout(110)
        self.stop_brush()

    def stop_all(self):
        for channel in self.channels.values():channel.fadeout(100)
        self.current_brush=None

    def set_volume(self,percent):
        self.volume=percent/100.
        self.refresh_volume()

    def refresh_volume(self):
        v=0. if self.muted else self.volume
        for key,ch in self.channels.items():ch.set_volume(v*(.9 if key=='preview' else 1.))

    def set_speed(self,value):
        self.stop_stroke()
        self.speed=int(value)
        self.cache.clear()

    def preview(self,category,desired):
        ident=self.select(category,desired)
        self.channels['preview'].stop()
        self.channels['preview'].play(self.sound(ident),loops=1 if category=='brush' else 0,fade_ms=40)
        self.refresh_volume()
        return self.samples[ident]['label']

    def refresh_live_loop(self,category,desired):
        if category=='brush' and self.current_brush:
            self.stop_brush(70)
            self.start_loop(category,desired)

    def close(self):
        self.stop_all()
        self.pg.mixer.quit()
