"""Mouse/stylus painting audio. Only B loops, and only while moving.

P/E are one-shot non-retriggering sounds. Pitch is independently adjustable
from duration; pressure volume is true Wintab pressure where available, or an
explicitly labelled motion-based estimate when not.
"""
import json
import random
import wave
import time
from pathlib import Path
import numpy as np


def _overlap_stretch(data, factor):
    """Short-time overlap/add stretch of broadband drawing textures.

    No restarting or re-attacking a recorded stroke; the original samples
    include a single contact followed by a long synthetic friction texture.
    """
    factor=float(np.clip(factor,.32,4.0))
    if abs(factor-1.)<.015:return data
    size=1024; hop=256
    if len(data)<size:return np.interp(np.linspace(0,len(data)-1,max(1,int(len(data)*factor))),np.arange(len(data)),data).astype('float32')
    length=max(1,int(len(data)*factor))
    out=np.zeros(length+size,dtype='float32')
    norms=np.zeros(length+size,dtype='float32')
    window=np.sqrt(np.hanning(size).astype('float32'))
    frame_count=int(np.ceil(max(0,len(data)-size)*factor/hop))+1
    for i in range(frame_count):
        src=min(len(data)-size,int(i*hop/factor))
        dst=i*hop
        out[dst:dst+size]+=data[src:src+size]*window
        norms[dst:dst+size]+=window
    valid=norms[:length]>1e-4
    out[:length][valid]/=norms[:length][valid]
    return out[:length]


def _pitch_and_speed(data, speed, pitch, brightness):
    """Pitch adjustment (semitones) and time adjustment are independent.

    Operates at source 22.05 kHz, then upsamples to the fixed 44.1 kHz mixer.
    Broadband noise beds tolerate OLA stretching particularly well.
    """
    x=data.astype('float32')/32768.
    semitone=float(pitch)
    p=2.**(semitone/12.)
    if abs(p-1.)>.003:
        target=max(8,int(len(x)/p))
        x=np.interp(np.arange(target,dtype='float32')*p,np.arange(len(x)),x).astype('float32')
    x=_overlap_stretch(x,p/(speed/100.))
    if brightness:
        # Gentle high shelf: brightness does not modify fundamental frequency.
        low=np.convolve(x,np.ones(11,dtype='float32')/11.,mode='same')
        high=x-low
        x=low+high*(1.+brightness/100.*.70)
    # Mixer frequency is twice WAV rate.
    dest=np.arange(len(x)*2,dtype='float32')*.5
    y=np.interp(dest,np.arange(len(x)),x).astype('float32')
    return (np.clip(y,-.96,.96)*32767).astype('<i2')


def _brush_loop(pcm, rate=22050):
    """Build a seamless *brush-only* texture, excluding the contact onset.

    Preserve one playback for the whole mouse-down, even while paused.
    """
    start=int(.85*rate); stop=int(6.8*rate)
    body=pcm[start:stop].copy().astype('float32')
    if len(body)<rate:body=pcm.copy().astype('float32')
    overlap=min(int(.15*rate),len(body)//5)
    if overlap:
        t=np.linspace(0,1,overlap,dtype='float32')
        # Crossfade tail into the *preceding* samples of the next loop.
        # Drop those preceding samples so the loop seam is between two
        # consecutive source samples, avoiding a discontinuity/click.
        tail=body[-overlap:].copy()
        head=body[:overlap].copy()
        body=body[overlap:].copy()
        body[-overlap:]=tail*(1-t)+head*t
    return body.astype('<i2')


def _finish_loop(pcm,rate=44100):
    """Make the finished, pitch-shifted B stream join without a seam click."""
    n=min(int(.12*rate),len(pcm)//5)
    if n<8:return pcm
    x=pcm.astype('float32')
    t=np.linspace(0,1,n,dtype='float32')
    tail=x[-n:].copy();head=x[:n].copy()
    x=x[n:].copy()
    x[-n:]=tail*(1-t)+head*t
    return np.clip(x,-32768,32767).astype('<i2')


class AudioEngine:
    MODES=('pencil','brush','eraser')

    def __init__(self,sounds_folder:Path):
        import pygame
        self.pg=pygame
        pygame.mixer.pre_init(frequency=44100,size=-16,channels=1,buffer=512)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(5)
        self.channels={mode:pygame.mixer.Channel(i) for i,mode in enumerate(self.MODES)}
        self.preview_channel=pygame.mixer.Channel(3)
        self.folder=Path(sounds_folder)
        library=json.loads((self.folder/'library.json').read_text(encoding='utf8'))
        self.samples={s['id']:s for s in library['samples']}
        self.by_category={cat:[s['id'] for s in library['samples'] if s['category']==cat] for cat in self.MODES}
        if any(not self.by_category[c] for c in self.MODES):raise ValueError('Missing samples for a P/B/E tool')
        self.last_random={};self.cache={};self.active_mode=None
        self.volume=.76;self.speed=55;self.pitch=0;self.brightness=0
        self.dynamic=70;self.tool_volumes={m:100 for m in self.MODES}
        self.muted=False
        self.motion_gate=.0;self.pressure=0.5;self.motion_estimate=.5
        self.real_pressure=False;self.pressure_time=0.

    def select(self,category,desired):
        choices=self.by_category[category]
        if desired in choices:return desired
        previous=self.last_random.get(category)
        ident=random.choice([x for x in choices if x!=previous] or choices)
        self.last_random[category]=ident
        return ident

    def _load_pcm(self,filename):
        with wave.open(str(self.folder/filename),'rb') as wav:
            if (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())!=(1,2,22050):
                raise ValueError('Expected mono 16-bit 22,050 Hz WAV: '+filename)
            return np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2')

    def _sound(self,ident,kind):
        key=(ident,kind,self.speed,self.pitch,self.brightness)
        if key not in self.cache:
            sample=self.samples[ident]
            pcm=self._load_pcm(sample['preview_file' if kind=='preview' else 'file'])
            if kind=='loop':pcm=_brush_loop(pcm)
            pcm=_pitch_and_speed(pcm,self.speed,self.pitch,self.brightness)
            if kind=='loop':pcm=_finish_loop(pcm)
            if len(self.cache)>=6:self.cache.clear()
            self.cache[key]=self.pg.mixer.Sound(buffer=pcm.tobytes())
        return self.cache[key]

    def begin_stroke(self,category,desired):
        if self.muted or self.active_mode is not None or category not in self.MODES:return False
        ident=self.select(category,desired)
        ch=self.channels[category]
        # P/E: exactly one stream. B: one uninterrupted looping texture; no
        # individual brushes triggered on mouse movement.
        ch.play(self._sound(ident,'loop' if category=='brush' else 'held'),
                loops=(-1 if category=='brush' else 0),fade_ms=30)
        self.active_mode=category
        self.motion_gate=.70
        self.refresh_volume()
        return True

    def update_motion(self,px_per_sec):
        if self.active_mode is None:return
        moving=px_per_sec>5
        # The sound is truly inaudible during a brush pause, with smooth ramp.
        self.motion_gate=.28*self.motion_gate+.72*(1. if moving else 0.)
        # Fallback is *not* pen force; it is a motion estimate.
        self.motion_estimate=.65*self.motion_estimate+.35*min(1.,max(.06,px_per_sec/950.))
        self.refresh_volume()

    def set_pressure(self,pressure,real=True):
        self.pressure=max(0.,min(1.,float(pressure)))
        self.real_pressure=bool(real)
        self.pressure_time=time.monotonic()
        self.refresh_volume()

    def refresh_volume(self):
        base=0. if self.muted else self.volume
        # Windows drivers may stop sending packets while Paint is foreground.
        # Never hold an old pressure reading indefinitely.
        if self.real_pressure and time.monotonic()-self.pressure_time>.6:
            self.real_pressure=False
        pressure=self.pressure if self.real_pressure else self.motion_estimate
        response=.15+.85*(pressure**.68)
        sensitivity=self.dynamic/100.
        strength=(1.-sensitivity)+sensitivity*response
        for mode,ch in self.channels.items():
            multiplier=(self.tool_volumes[mode]/100.)
            if mode==self.active_mode:
                multiplier*=self.motion_gate*strength
            ch.set_volume(min(1.,base*multiplier))
        self.preview_channel.set_volume(base*.85)

    def stop_stroke(self,fade_ms=100):
        if self.active_mode is not None:
            ch=self.channels[self.active_mode]
            if ch.get_busy():ch.fadeout(fade_ms)
        self.active_mode=None;self.motion_gate=0.

    def stop_all(self):
        self.stop_stroke(75)
        for ch in self.channels.values():
            if ch.get_busy():ch.fadeout(75)
        self.preview_channel.fadeout(75)

    def set_volume(self,value):
        self.volume=max(0,min(100,int(value)))/100.
        self.refresh_volume()

    def set_tool_volume(self,mode,value):
        if mode in self.MODES:self.tool_volumes[mode]=max(0,min(100,int(value)))
        self.refresh_volume()

    def set_dynamics(self,value):
        self.dynamic=max(0,min(100,int(value)))
        self.refresh_volume()

    def set_speed(self,value):
        self.speed=max(45,min(120,int(value)))
        self._change_processing()

    def set_pitch(self,value):
        self.pitch=max(-8,min(8,int(value)))
        self._change_processing()

    def set_brightness(self,value):
        self.brightness=max(-100,min(100,int(value)))
        self._change_processing()

    def _change_processing(self):
        self.stop_stroke()
        self.preview_channel.stop()
        self.cache.clear()

    def preview(self,category,desired):
        ident=self.select(category,desired)
        self.preview_channel.stop()
        self.preview_channel.play(self._sound(ident,'preview'),loops=0,fade_ms=18)
        self.refresh_volume()
        return self.samples[ident]['label']

    def close(self):
        self.stop_all()
        self.pg.mixer.quit()
