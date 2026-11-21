"""Natural original recordings for each stroke. P/E never loop, synthesize,
or re-trigger in the same drag. B alone may loop while actually painting.
Every tool has independent settings. Neutral processing is bit-exact.
"""
import json
import random
import wave
import time
from pathlib import Path
import numpy as np


def _overlap_stretch(data, factor):
    """Short-time overlap/add stretch of broadband drawing textures.

    Optional time stretching for explicit manual adjustments only.
    The default 1.00x bypass avoids this transform entirely.
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
    """Natural 44.1 kHz playback is byte-identical at neutral settings.

    Deliberate manual effects are optional. Speed-only changes use lightweight
    overlap/add processing and can color the sound: use 100% for original.
    """
    if speed==100 and pitch==0 and brightness==0:
        return data  # absolutely no time-stretch, EQ, interpolation or retuning
    x=data.astype('float32')/32768.
    p=2.**(float(pitch)/12.)
    if abs(p-1.)>.003:
        target=max(8,int(len(x)/p))
        x=np.interp(np.arange(target,dtype='float32')*p,np.arange(len(x)),x).astype('float32')
    x=_overlap_stretch(x,p/(speed/100.))
    if brightness:
        low=np.convolve(x,np.ones(11,dtype='float32')/11.,mode='same')
        x=low+(x-low)*(1.+brightness/100.*.70)
    return (np.clip(x,-.999,.999)*32767).astype('<i2')


def _brush_loop(pcm, rate=44100):
    """Crossfade a real brush recording into a seamless loop; no fake noise."""
    # Skip the very first touch so it is not replayed with every loop.
    start=min(int(.045*rate),len(pcm)//6)
    body=pcm[start:].astype('float32').copy()
    if len(body)<800:return pcm
    overlap=min(int(.09*rate),len(body)//5)
    if overlap>0:
        t=np.linspace(0,1,overlap,dtype='float32')
        tail=body[-overlap:].copy()
        head=body[:overlap].copy()
        body=body[overlap:]
        body[-overlap:]=tail*(1-t)+head*t
    return np.clip(body,-32768,32767).astype('<i2')


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
        self.brush_vertical_channel=pygame.mixer.Channel(4)
        self.folder=Path(sounds_folder)
        library=json.loads((self.folder/'library.json').read_text(encoding='utf8'))
        self.samples={s['id']:s for s in library['samples']}
        self.by_category={cat:[s['id'] for s in library['samples'] if s['category']==cat] for cat in self.MODES}
        if any(not self.by_category[c] for c in self.MODES):raise ValueError('Missing samples for a P/B/E tool')
        self.last_random={};self.cache={};self.active_mode=None;self.preview_mode=None
        # User-approved related velvet clips are assigned H/V mixing roles.
        # Direction labels are playback roles, not physical recording claims.
        self.brush_directions_active=False
        self.brush_mix_h=.5
        self.last_brush_pair=(None,None)
        self.brush_horizontal_ids=[s['id'] for s in library['samples'] if s['category']=='brush' and s.get('direction')=='horizontal']
        self.brush_vertical_ids=[s['id'] for s in library['samples'] if s['category']=='brush' and s.get('direction')=='vertical']
        self.volume=.76
        self.effects={m:{"volume":100,"speed":100,"pitch":0,"brightness":0,"dynamics":70} for m in self.MODES}
        self.muted=False
        self.motion_gate=.0;self.pressure=0.5;self.motion_estimate=.5
        self.real_pressure=False;self.pressure_time=0.

    def select(self,category,desired):
        choices=self.by_category[category]
        if desired in choices:
            return desired
        # Automatic variation happens ONCE at the start of each drag.
        # Do not repeat the last sample on consecutive strokes.
        # For P, prefer genuine long recordings: choosing a 0.5 s sample
        # at the beginning of a long stroke would cut out almost immediately.
        pool=[ident for ident in choices if self.samples[ident].get('auto_eligible',True)]
        if not pool:
            pool=choices
        previous=self.last_random.get(category)
        ident=random.choice([x for x in pool if x!=previous] or pool)
        self.last_random[category]=ident
        return ident

    def _choose_brush_direction(self,options,previous):
        # Prefer the four user-selected velvet recordings without excluding
        # the other compatible recordings. No immediate repeats per axis.
        pool=[x for x in options if x!=previous] or list(options)
        weighted=[]
        for ident in pool:
            weighted.extend([ident]*(3 if self.samples[ident].get('favorite') else 1))
        return random.choice(weighted)

    def _load_pcm(self,filename):
        with wave.open(str(self.folder/filename),'rb') as wav:
            if (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())!=(1,2,44100):
                raise ValueError('Expected mono 16-bit 44,100 Hz WAV: '+filename)
            return np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2')

    def _sound(self,ident,kind):
        category=self.samples[ident]["category"]
        fx=self.effects[category]
        key=(ident,kind,fx["speed"],fx["pitch"],fx["brightness"])
        if key not in self.cache:
            sample=self.samples[ident]
            pcm=self._load_pcm(sample['preview_file' if kind=='preview' else 'file'])
            # Transform only the *short original recording*. Applying effects
            # to a two-minute continuation would stall the UI for many seconds.
            pcm=_pitch_and_speed(pcm,fx['speed'],fx['pitch'],fx['brightness'])
            if kind=='loop':
                pcm=_brush_loop(pcm)
            # P/E play the unmodified original once. There is deliberately
            # no granular sustain, fake friction, repeated attack or loop.
            # Short recordings naturally end before a very long stroke.
            if len(self.cache)>=6:self.cache.clear()
            self.cache[key]=self.pg.mixer.Sound(buffer=pcm.tobytes())
        return self.cache[key]

    def begin_stroke(self,category,desired):
        if self.muted or self.active_mode is not None or category not in self.MODES:return False
        ident=self.select(category,desired)
        ch=self.channels[category]
        # P/E: exactly one unmodified-pitch source per drag, never repeated.
        # B and J share brush mode: one smooth looping texture motion-gated
        # by the actual mouse movement, without new attacks on each motion.
        self.brush_directions_active=False
        if category=='brush' and desired=='auto' and self.brush_horizontal_ids and self.brush_vertical_ids:
            # Two original user-generated brush recordings run simultaneously. Their volumes
            # crossfade smoothly with cursor orientation; neither retriggers
            # when the stylus changes direction within the same drag.
            horizontal=self._choose_brush_direction(self.brush_horizontal_ids,self.last_brush_pair[0])
            vertical=self._choose_brush_direction(self.brush_vertical_ids,self.last_brush_pair[1])
            self.last_brush_pair=(horizontal,vertical)
            ch.play(self._sound(horizontal,'loop'),loops=-1,fade_ms=30)
            self.brush_vertical_channel.play(self._sound(vertical,'loop'),loops=-1,fade_ms=30)
            self.brush_directions_active=True
            self.brush_mix_h=.5
        else:
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

    def update_direction(self,dx,dy):
        """Blend paired brush textures assigned to horizontal and vertical mixes by drag direction.

        A horizontal movement approaches H=1; vertical approaches H=0;
        diagonal movements blend them. Direction sign is deliberately ignored:
        a left-to-right reversal should NOT trigger a new audio attack.
        """
        if self.active_mode!='brush' or not self.brush_directions_active:return
        mag2=float(dx)*dx+float(dy)*dy
        if mag2<2.0:return
        target=float(dx)*dx/mag2
        self.brush_mix_h=.75*self.brush_mix_h+.25*target
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
        for mode,ch in self.channels.items():
            sensitivity=self.effects[mode]['dynamics']/100.
            strength=(1.-sensitivity)+sensitivity*response
            multiplier=self.effects[mode]['volume']/100.
            if mode==self.active_mode:
                multiplier*=self.motion_gate*strength
            if mode=='brush' and self.brush_directions_active:
                # Equal-power crossfade, with motion gating applied to both.
                mix=max(0.,min(1.,self.brush_mix_h))
                ch.set_volume(min(1.,base*multiplier*(mix**.5)))
                self.brush_vertical_channel.set_volume(min(1.,base*multiplier*((1.-mix)**.5)))
            else:
                ch.set_volume(min(1.,base*multiplier))
        if not self.brush_directions_active:
            self.brush_vertical_channel.set_volume(0.)
        if self.preview_mode:
            self.preview_channel.set_volume(base*(self.effects[self.preview_mode]['volume']/100.)*.85)
        else:
            self.preview_channel.set_volume(base*.85)

    def stop_stroke(self,fade_ms=100):
        if self.active_mode is not None:
            ch=self.channels[self.active_mode]
            if ch.get_busy():ch.fadeout(fade_ms)
            if self.brush_directions_active and self.brush_vertical_channel.get_busy():
                self.brush_vertical_channel.fadeout(fade_ms)
        self.brush_directions_active=False
        self.active_mode=None;self.motion_gate=0.

    def stop_all(self):
        self.stop_stroke(75)
        for ch in self.channels.values():
            if ch.get_busy():ch.fadeout(75)
        self.preview_channel.fadeout(75)
        self.brush_vertical_channel.fadeout(75)

    def set_volume(self,value):
        self.volume=max(0,min(100,int(value)))/100.
        self.refresh_volume()

    def set_effect(self,mode,key,value):
        """Each tool owns all five sliders; no shared pitch or speed."""
        if mode not in self.MODES or key not in self.effects[mode]:
            raise ValueError('Unknown audio tool or setting')
        bounds={'volume':(0,100),'speed':(45,120),'pitch':(-8,8),
                'brightness':(-100,100),'dynamics':(0,100)}
        lo,hi=bounds[key]
        self.effects[mode][key]=max(lo,min(hi,int(value)))
        if key in ('speed','pitch','brightness'):
            # Changing one tool never invalidates or stops another tool.
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
