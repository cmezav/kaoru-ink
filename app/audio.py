"""Kaoru Ink: natural sample playback with movement-gated, evolving sustain.

All modes play *real, original-pitch recordings*, without extending individual
files using synthetic friction or repeating a single file with mixer loops.
A small number of real recordings are softly crossfaded as the stylus moves.
This sustains sound throughout a drag. It cannot create truly novel foley from
finite clips, but avoids identical, sharply restarting loops.
"""
import json
import math
import random
import time
import wave
from pathlib import Path

import numpy as np


def _overlap_stretch(data, factor):
    """Optional user-controlled change of speed; neutral bypass is bit exact."""
    factor = float(np.clip(factor, .32, 4.))
    if abs(factor - 1.) < .015:
        return data
    size, hop = 1024, 256
    if len(data) < size:
        return np.interp(np.linspace(0, len(data)-1, max(1, int(len(data)*factor))),
                         np.arange(len(data)), data).astype('float32')
    length = max(1, int(len(data) * factor))
    out = np.zeros(length + size, dtype='float32')
    norms = np.zeros(length + size, dtype='float32')
    window = np.sqrt(np.hanning(size).astype('float32'))
    frame_count = int(np.ceil(max(0, len(data)-size) * factor/hop)) + 1
    for i in range(frame_count):
        src = min(len(data)-size, int(i * hop/factor))
        dst = i * hop
        out[dst:dst+size] += data[src:src+size] * window
        norms[dst:dst+size] += window
    valid = norms[:length] > 1e-4
    out[:length][valid] /= norms[:length][valid]
    return out[:length]


def _pitch_and_speed(data, speed, pitch, brightness):
    """Original sample is unchanged by default; effects are opt-in per tool."""
    if speed == 100 and pitch == 0 and brightness == 0:
        return data
    x = data.astype('float32') / 32768.
    p = 2. ** (float(pitch)/12.)
    if abs(p-1.) > .003:
        target = max(8, int(len(x)/p))
        x = np.interp(np.arange(target, dtype='float32') * p,
                      np.arange(len(x)), x).astype('float32')
    x = _overlap_stretch(x, p/(speed/100.))
    if brightness:
        low = np.convolve(x, np.ones(11, dtype='float32')/11., mode='same')
        x = low + (x-low) * (1. + brightness/100. * .70)
    return (np.clip(x, -.999, .999)*32767).astype('<i2')


def _sustain_body(pcm, rate=44100):
    """Remove the original start/pen-lift from continuation clips, not pitch.

    A real recording is used for *every* continuation. A short cosine edge
    smooths its splice. The first contact of each drag uses the whole original.
    """
    if len(pcm) < int(.26*rate):
        return pcm
    start = min(int(.105*rate), len(pcm)//9)
    end = min(int(.08*rate), len(pcm)//12)
    body = pcm[start:len(pcm)-end].copy()
    if len(body) < int(.18*rate):
        return pcm
    edge = min(int(.022*rate), len(body)//10)
    if edge:
        t = np.linspace(0., math.pi/2, edge, dtype='float32')
        a = body.astype('float32')
        a[:edge] *= np.sin(t)
        a[-edge:] *= np.cos(t)
        body = np.clip(a, -32768, 32767).astype('<i2')
    return body


class ContinuousLayer:
    """One continuous gesture with two real recordings crossfaded in alternation.

    The mixer uses one-shot sources only. A timer starts each next recording early
    enough that neither category becomes silent as a source runs out.
    """
    def __init__(self, channels, chooser, sound_for, clock):
        self.channels = tuple(channels)
        self.chooser = chooser
        self.sound_for = sound_for
        self.clock = clock
        self.active = False
        self.current_slot = 0
        self.current_id = None
        self.previous_id = None
        self.current_end = 0.
        self.in_transition = False
        self.transition_start = 0.
        self.transition_sec = 0.
        self.next_id = None
        self.next_end = 0.
        self.levels = (1., 0.)

    def start(self, ident):
        for channel in self.channels:
            channel.stop()
            channel.set_volume(0.)
        self.active = True
        self.current_slot = 0
        self.current_id = ident
        self.previous_id = None
        self.in_transition = False
        self.next_id = None
        self.levels = (1., 0.)
        snd = self.sound_for(ident, 'held')
        now = self.clock()
        self.channels[0].play(snd, loops=0, fade_ms=35)
        self._duration = snd.get_length()
        self.current_end = now + self._duration

    def _fade_duration(self, remaining, new_duration):
        return min(.58, max(.08, remaining*.85), new_duration*.36)

    def tick(self, now=None):
        if not self.active:
            return
        if now is None:
            now = self.clock()
        if not self.in_transition:
            remaining = self.current_end-now
            # Start before a recording ends so the handoff has no silence.
            # Begin around 400 ms before end; for very short recordings
            # begin earlier, but still keep the original initial contact.
            overlap = min(.48, max(.13, self.current_duration()*.34))
            if remaining <= overlap:
                self.next_id = self.chooser(self.current_id, self.previous_id)
                snd = self.sound_for(self.next_id, 'sustain')
                second = 1-self.current_slot
                self.channels[second].play(snd, loops=0, fade_ms=0)
                self.transition_start = now
                self.transition_sec = min(overlap, self._fade_duration(max(.05, remaining), snd.get_length()))
                self.next_end = now + snd.get_length()
                self.next_duration = snd.get_length()
                self.in_transition = True
        if self.in_transition:
            fraction = min(1., max(0., (now-self.transition_start)/max(.03, self.transition_sec)))
            # Raised-cosine crossfade removes hard edges and avoids a new attack.
            fade = fraction*fraction*(3.-2.*fraction)
            levels = [0., 0.]
            levels[self.current_slot] = 1.-fade
            levels[1-self.current_slot] = fade
            self.levels = tuple(levels)
            if fraction >= 1.:
                self.channels[self.current_slot].stop()
                self.previous_id = self.current_id
                self.current_id = self.next_id
                self.current_slot = 1-self.current_slot
                self.current_end = self.next_end
                self._duration = self.next_duration
                self.in_transition = False
                self.levels = (1.,0.) if self.current_slot == 0 else (0.,1.)
        else:
            self.levels = (1.,0.) if self.current_slot == 0 else (0.,1.)

    def current_duration(self):
        # The duration of a prepared sample is returned by pygame.Sound.
        # Do not rely on Channel.get_sound, unavailable in simple adapters.
        return max(.2, float(getattr(self, '_duration', 0.) or .3))

    def set_level(self, amount):
        for channel, factor in zip(self.channels, self.levels):
            channel.set_volume(max(0., min(1., amount*factor)))

    def stop(self, fade_ms=100):
        self.active = False
        for channel in self.channels:
            if channel.get_busy():
                channel.fadeout(fade_ms)
        self.in_transition = False
        self.levels = (0.,0.)


class AudioEngine:
    MODES = ('pencil','brush','eraser')

    def __init__(self, sounds_folder: Path):
        import pygame
        self.pg = pygame
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=1, buffer=512)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(9)
        self.folder = Path(sounds_folder)
        library = json.loads((self.folder/'library.json').read_text(encoding='utf8'))
        self.samples = {s['id']:s for s in library['samples']}
        self.by_category = {cat:[s['id'] for s in library['samples'] if s['category']==cat] for cat in self.MODES}
        if any(not self.by_category[c] for c in self.MODES):
            raise ValueError('Missing P/B/E samples')
        self.mixer_channels = [pygame.mixer.Channel(i) for i in range(9)]
        self.preview_channel = self.mixer_channels[8]
        self.last_random = {}
        self.cache = {}
        self.active_mode = None
        self.preview_mode = None
        self.volume = .76
        self.effects = {m:{'volume':100,'speed':100,'pitch':0,'brightness':0,'dynamics':70} for m in self.MODES}
        self.muted = False
        self.motion_gate = 0.
        self.pressure = .5
        self.motion_estimate = .5
        self.real_pressure = False
        self.pressure_time = 0.
        self.clock = time.monotonic
        self.brush_horizontal_ids = [s['id'] for s in library['samples'] if s['category']=='brush' and s.get('direction')=='horizontal']
        self.brush_vertical_ids = [s['id'] for s in library['samples'] if s['category']=='brush' and s.get('direction')=='vertical']
        self.brush_mix_h = .5
        self.brush_directions_active = False
        self.last_brush_pair = (None,None)
        self.active_desired = 'auto'
        self.layers = {
            'pencil':ContinuousLayer(self.mixer_channels[0:2],lambda current,prev:self._next('pencil',current,prev),self._sound,self.clock),
            'eraser':ContinuousLayer(self.mixer_channels[2:4],lambda current,prev:self._next('eraser',current,prev),self._sound,self.clock),
            'horizontal':ContinuousLayer(self.mixer_channels[4:6],lambda current,prev:self._next('brush',current,prev,'horizontal'),self._sound,self.clock),
            'vertical':ContinuousLayer(self.mixer_channels[6:8],lambda current,prev:self._next('brush',current,prev,'vertical'),self._sound,self.clock),
        }

    def _pool(self,category,direction=None):
        ids = self.by_category[category]
        eligible=[x for x in ids if self.samples[x].get('auto_eligible', True)]
        if direction:
            eligible = [x for x in eligible if self.samples[x].get('direction') == direction]
        if category == 'eraser' and not direction:
            # Longer genuine eraser recordings reduce the need for seams.
            chosen=[x for x in eligible if self.samples[x]['duration_sec'] >= .95]
            if chosen:eligible=chosen
        return eligible or ids

    def select(self,category,desired):
        if desired in self.by_category[category]:
            return desired
        options=self._pool(category)
        previous=self.last_random.get(category)
        choices=[x for x in options if x!=previous] or options
        ident=random.choice(choices)
        self.last_random[category]=ident
        return ident

    def _next(self,category,current,previous,direction=None):
        if self.active_desired!='auto':
            # Manual selection remains a single fixed texture, with soft seams.
            return self.active_desired
        options=self._pool(category,direction)
        choices=[x for x in options if x!=current and x!=previous] or [x for x in options if x!=current] or options
        weights=[4 if self.samples[x].get('favorite') else 1 for x in choices]
        return random.choices(choices,weights=weights,k=1)[0]

    def _load_pcm(self,filename):
        with wave.open(str(self.folder/filename),'rb') as wav:
            if (wav.getnchannels(),wav.getsampwidth(),wav.getframerate()) != (1,2,44100):
                raise ValueError('Expected mono 16-bit 44,100 Hz: '+filename)
            return np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2')

    def _sound(self,ident,kind):
        cat=self.samples[ident]['category']
        fx=self.effects[cat]
        key=(ident,kind,fx['speed'],fx['pitch'],fx['brightness'])
        if key not in self.cache:
            sample=self.samples[ident]
            pcm=self._load_pcm(sample['preview_file' if kind=='preview' else 'file'])
            pcm=_pitch_and_speed(pcm,fx['speed'],fx['pitch'],fx['brightness'])
            if kind=='sustain':
                pcm=_sustain_body(pcm)
            if len(self.cache)>64:
                self.cache.clear()
            self.cache[key]=self.pg.mixer.Sound(buffer=pcm.tobytes())
        return self.cache[key]

    def begin_stroke(self,category,desired):
        if self.muted or self.active_mode is not None or category not in self.MODES:
            return False
        self.active_mode=category
        self.active_desired=desired
        self.motion_gate=.2
        self.brush_directions_active=False
        if category=='brush':
            if desired=='auto' and self.brush_horizontal_ids and self.brush_vertical_ids:
                h=self._pick_direction('horizontal',self.last_brush_pair[0])
                v=self._pick_direction('vertical',self.last_brush_pair[1])
                self.last_brush_pair=(h,v)
                self.layers['horizontal'].start(h)
                self.layers['vertical'].start(v)
                self.brush_directions_active=True
                self.brush_mix_h=.5
            else:
                self.layers['horizontal'].start(self.select(category,desired))
        else:
            self.layers[category].start(self.select(category,desired))
        self.refresh_volume()
        return True

    def _pick_direction(self,direction,old):
        choices=self._pool('brush',direction)
        options=[x for x in choices if x!=old] or choices
        return random.choices(options,weights=[4 if self.samples[x].get('favorite') else 1 for x in options],k=1)[0]

    def tick(self):
        """Run from the UI's 60-80 ms timer; keep recordings continuous."""
        if self.active_mode is None:return
        now=self.clock()
        layer_keys=(('horizontal','vertical') if self.brush_directions_active else
                    ('horizontal',) if self.active_mode=='brush' else (self.active_mode,))
        for name in layer_keys:
            self.layers[name].tick(now)
        self.refresh_volume()

    def update_motion(self,px_per_sec):
        if self.active_mode is None:return
        moving=px_per_sec>5
        self.motion_gate=.5*self.motion_gate+.5*(1. if moving else 0.)
        self.motion_estimate=.65*self.motion_estimate+.35*min(1.,max(.06,px_per_sec/950.))
        self.refresh_volume()

    def update_direction(self,dx,dy):
        if self.active_mode!='brush' or not self.brush_directions_active:return
        mag2=float(dx)*dx+float(dy)*dy
        if mag2<2.:return
        target=float(dx)*dx/mag2
        self.brush_mix_h=.75*self.brush_mix_h+.25*target
        self.refresh_volume()

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
            sensitivity=self.effects[mode]['dynamics']/100.
            strength=(1.-sensitivity)+sensitivity*response
            multiplier=self.effects[mode]['volume']/100.
            amount=base*multiplier*(self.motion_gate*strength if mode==self.active_mode else 0.)
            if mode=='brush':
                if self.brush_directions_active:
                    h=max(0.,min(1.,self.brush_mix_h))
                    self.layers['horizontal'].set_level(amount*math.sqrt(h))
                    self.layers['vertical'].set_level(amount*math.sqrt(1.-h))
                else:
                    self.layers['horizontal'].set_level(amount)
                    self.layers['vertical'].set_level(0.)
            else:
                self.layers[mode].set_level(amount)
        if self.preview_mode:
            self.preview_channel.set_volume(base*(self.effects[self.preview_mode]['volume']/100.)*.85)
        else:
            self.preview_channel.set_volume(base*.85)

    def stop_stroke(self,fade_ms=120):
        if self.active_mode is None:return
        if self.active_mode=='brush':
            self.layers['horizontal'].stop(fade_ms)
            self.layers['vertical'].stop(fade_ms)
        else:
            self.layers[self.active_mode].stop(fade_ms)
        self.active_mode=None
        self.brush_directions_active=False
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
            raise ValueError('Unknown audio tool or setting')
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
