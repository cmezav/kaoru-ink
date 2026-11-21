"""Kaoru Ink: gesture-driven, one-shot sound playback.

This module deliberately NEVER restarts a sound on a timer. P gets one natural
recording per press/release. B/J and E can start a NEW one-shot only after
StrokeController confirms an actual new directional pass. The old sound fades
out while the new one comes in. This is event-based and finite: without new
passes, a source eventually ends; indefinite nonrepeating audio is impossible
with a finite catalogue of recordings.
"""
import json
import random
import time
import wave
from pathlib import Path

import numpy as np


def _overlap_stretch(data, factor):
    """Apply optional user-requested speed changes, not automatic sustain."""
    factor=float(np.clip(factor,.32,4.))
    if abs(factor-1.) < .015:
        return data
    size,hop=1024,256
    if len(data)<size:
        return np.interp(np.linspace(0,len(data)-1,max(1,int(len(data)*factor))),
                         np.arange(len(data)),data).astype('float32')
    length=max(1,int(len(data)*factor))
    out=np.zeros(length+size,dtype='float32')
    norms=np.zeros(length+size,dtype='float32')
    window=np.sqrt(np.hanning(size).astype('float32'))
    nframes=int(np.ceil(max(0,len(data)-size)*factor/hop))+1
    for i in range(nframes):
        src=min(len(data)-size,int(i*hop/factor))
        dst=i*hop
        out[dst:dst+size]+=data[src:src+size]*window
        norms[dst:dst+size]+=window
    valid=norms[:length]>1e-4
    out[:length][valid]/=norms[:length][valid]
    return out[:length]


def _pitch_and_speed(data,speed,pitch,brightness):
    """At neutral settings the PCM is copied bit for bit, never pitch-shifted."""
    if speed==100 and pitch==0 and brightness==0:
        return data
    x=data.astype('float32')/32768.
    factor=2.**(float(pitch)/12.)
    if abs(factor-1.)>.003:
        target=max(8,int(len(x)/factor))
        x=np.interp(np.arange(target,dtype='float32')*factor,np.arange(len(x)),x).astype('float32')
    x=_overlap_stretch(x,factor/(speed/100.))
    if brightness:
        low=np.convolve(x,np.ones(11,dtype='float32')/11.,mode='same')
        x=low+(x-low)*(1.+brightness/100.*.70)
    return (np.clip(x,-.999,.999)*32767).astype('<i2')


class GestureVoice:
    """Two channels, used only for fades on genuine user gesture changes."""
    def __init__(self,channels,sound_for):
        self.channels=tuple(channels)
        self.sound_for=sound_for
        self.slot=0
        self.current_id=None
        self.previous_id=None
        self.active=False

    def start(self,ident):
        self.stop(0)
        self.slot=0
        self.active=True
        self.current_id=ident
        self.previous_id=None
        self.channels[0].play(self.sound_for(ident,'held'),loops=0,fade_ms=30)

    def change(self,ident,fade_ms=100):
        """Only called by an actual brush/eraser direction-change event."""
        if not self.active or ident==self.current_id:
            return False
        old=self.channels[self.slot]
        if old.get_busy():
            old.fadeout(fade_ms)
        self.slot=1-self.slot
        new=self.channels[self.slot]
        new.stop()
        new.play(self.sound_for(ident,'held'),loops=0,fade_ms=fade_ms)
        self.previous_id=self.current_id
        self.current_id=ident
        return True

    def set_level(self,amount):
        volume=max(0.,min(1.,float(amount)))
        for c in self.channels:
            c.set_volume(volume)

    def stop(self,fade_ms=100):
        self.active=False
        for c in self.channels:
            if c.get_busy():
                if fade_ms:
                    c.fadeout(fade_ms)
                else:
                    c.stop()


class AudioEngine:
    MODES=('pencil','brush','eraser')

    def __init__(self,sounds_folder:Path):
        import pygame
        self.pg=pygame
        pygame.mixer.pre_init(frequency=44100,size=-16,channels=1,buffer=512)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(9)
        self.folder=Path(sounds_folder)
        library=json.loads((self.folder/'library.json').read_text(encoding='utf8'))
        self.samples={s['id']:s for s in library['samples']}
        self.by_category={cat:[s['id'] for s in library['samples'] if s['category']==cat]
                          for cat in self.MODES}
        if any(not self.by_category[cat] for cat in self.MODES):
            raise ValueError('Missing P/B/E samples')
        self.mixer_channels=[pygame.mixer.Channel(i) for i in range(9)]
        self.preview_channel=self.mixer_channels[8]
        self.layers={
            'pencil':GestureVoice(self.mixer_channels[0:2],self._sound),
            'brush':GestureVoice(self.mixer_channels[2:4],self._sound),
            'eraser':GestureVoice(self.mixer_channels[4:6],self._sound),
        }
        self.last_random={}
        self.cache={}
        self.active_mode=None
        self.active_desired='auto'
        self.preview_mode=None
        self.volume=.76
        self.effects={m:{'volume':100,'speed':100,'pitch':0,'brightness':0,'dynamics':70} for m in self.MODES}
        self.muted=False
        self.motion_gate=0.
        self.pressure=.5
        self.motion_estimate=.5
        self.real_pressure=False
        self.pressure_time=0.
        self.clock=time.monotonic
        self.last_direction='horizontal'

    def _pool(self,category,direction=None):
        ids=[s for s in self.by_category[category] if self.samples[s].get('auto_eligible',True)]
        if direction:
            directional=[x for x in ids if self.samples[x].get('direction')==direction]
            if directional:
                ids=directional
        if category=='pencil':
            # Longest natural recordings, minimizing premature silence for P.
            ids=[s for s in ids if self.samples[s].get('duration_sec',0)>=4.8] or ids
        return ids or self.by_category[category]

    def _pick(self,category,previous=None,direction=None):
        opts=self._pool(category,direction)
        choices=[s for s in opts if s!=previous] or opts
        weights=[3 if self.samples[s].get('favorite') else 1 for s in choices]
        return random.choices(choices,weights=weights,k=1)[0]

    def select(self,category,desired):
        if desired in self.by_category[category]:
            return desired
        ident=self._pick(category,self.last_random.get(category))
        self.last_random[category]=ident
        return ident

    def _load_pcm(self,filename):
        with wave.open(str(self.folder/filename),'rb') as wav:
            if (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())!=(1,2,44100):
                raise ValueError('Expected mono 16-bit 44,100 Hz: '+filename)
            return np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2')

    def _sound(self,ident,kind):
        cat=self.samples[ident]['category']
        fx=self.effects[cat]
        key=(ident,kind,fx['speed'],fx['pitch'],fx['brightness'])
        if key not in self.cache:
            src=self.samples[ident]['preview_file' if kind=='preview' else 'file']
            pcm=self._load_pcm(src)
            pcm=_pitch_and_speed(pcm,fx['speed'],fx['pitch'],fx['brightness'])
            if len(self.cache)>64:self.cache.clear()
            self.cache[key]=self.pg.mixer.Sound(buffer=pcm.tobytes())
        return self.cache[key]

    def begin_stroke(self,category,desired):
        if self.muted or self.active_mode is not None or category not in self.MODES:
            return False
        self.active_mode=category
        self.active_desired=desired
        self.motion_gate=.20
        self.layers[category].start(self.select(category,desired))
        self.refresh_volume()
        return True

    def gesture_turn(self,axis='horizontal'):
        """Called only for a genuine new B/J/E hand pass, never by a timer."""
        if self.active_mode not in ('brush','eraser') or self.active_desired!='auto':
            return False
        category=self.active_mode
        direction=axis if category=='brush' and axis in ('horizontal','vertical') else None
        current=self.layers[category].current_id
        ident=self._pick(category,current,direction)
        result=self.layers[category].change(ident,fade_ms=90)
        if result:self.last_random[category]=ident
        self.refresh_volume()
        return result

    def tick(self):
        """Adjust gain only: never queue, restart or advance any recording."""
        if self.active_mode is not None:
            self.refresh_volume()

    def update_motion(self,px_per_sec):
        if self.active_mode is None:return
        moving=px_per_sec>5.
        self.motion_gate=.5*self.motion_gate+.5*(1. if moving else 0.)
        self.motion_estimate=.65*self.motion_estimate+.35*min(1.,max(.06,px_per_sec/950.))
        self.refresh_volume()

    def update_direction(self,dx,dy):
        """No sound is started merely because the pointing direction changes."""
        if self.active_mode=='brush':
            self.last_direction='horizontal' if abs(dx)>=abs(dy) else 'vertical'

    def set_pressure(self,pressure,real=True):
        self.pressure=max(0.,min(1.,float(pressure)))
        self.real_pressure=bool(real)
        self.pressure_time=self.clock()
        self.refresh_volume()

    def refresh_volume(self):
        base=0. if self.muted else self.volume
        if self.real_pressure and self.clock()-self.pressure_time>.6:
            self.real_pressure=False
        pressure=self.pressure if self.real_pressure else self.motion_estimate
        response=.15+.85*(pressure**.68)
        for mode in self.MODES:
            fx=self.effects[mode]
            sensitivity=fx['dynamics']/100.
            strength=(1.-sensitivity)+sensitivity*response
            amount=base*(fx['volume']/100.)*(self.motion_gate*strength if self.active_mode==mode else 0.)
            self.layers[mode].set_level(amount)
        if self.preview_mode:
            self.preview_channel.set_volume(base*(self.effects[self.preview_mode]['volume']/100.)*.85)
        else:
            self.preview_channel.set_volume(base*.85)

    def stop_stroke(self,fade_ms=120):
        if self.active_mode is None:return
        self.layers[self.active_mode].stop(fade_ms)
        self.active_mode=None
        self.motion_gate=0.

    def stop_all(self):
        self.stop_stroke(75)
        for layer in self.layers.values():layer.stop(75)
        self.preview_channel.fadeout(75)

    def set_volume(self,value):
        self.volume=max(0.,min(100,int(value)))/100.
        self.refresh_volume()

    def set_effect(self,mode,key,value):
        if mode not in self.MODES or key not in self.effects[mode]:
            raise ValueError('Unknown tool or audio setting')
        bounds={'volume':(0,100),'speed':(45,120),'pitch':(-8,8),
                'brightness':(-100,100),'dynamics':(0,100)}
        lo,hi=bounds[key]
        self.effects[mode][key]=max(lo,min(hi,int(value)))
        if key in ('speed','pitch','brightness'):
            self.cache={k:v for k,v in self.cache.items() if self.samples[k[0]]['category']!=mode}
            if self.active_mode==mode:self.stop_stroke()
            if self.preview_mode==mode:self.preview_channel.stop()
        self.refresh_volume()

    def set_tool_volume(self,mode,value):
        self.set_effect(mode,'volume',value)

    def preview(self,category,desired):
        ident=self.select(category,desired)
        self.preview_channel.stop()
        self.preview_mode=category
        self.preview_channel.play(self._sound(ident,'preview'),loops=0,fade_ms=18)
        self.refresh_volume()
        return self.samples[ident]['label']

    def close(self):
        self.stop_all()
        self.pg.mixer.quit()
