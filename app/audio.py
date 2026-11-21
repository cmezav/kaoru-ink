"""Kaoru Ink v0.13: movement-driven streaming audio using original recordings.

No fixed-length one-shot can sustain an arbitrarily long drag. Instead, a
PortAudio output stream composes overlapping, transient-avoiding interior
regions from the existing recordings. The generator stays alive during ONE
mouse gesture; pressure, speed, and motion direction shape its amplitude. It
never starts a new full sample merely because a playback timer expired.

This is a best-effort texture renderer, not new real-world source material.
"""
from __future__ import annotations

import json
import math
import random
import threading
import time
import wave
from pathlib import Path

import numpy as np

RATE = 44100
MODES = ('pencil', 'brush', 'eraser')
BRUSH_TWO_STROKE = ('brush_pair_A', 'brush_pair_B', 'brush_pair_C')


def _overlap_stretch(data, factor):
    """Optional user-requested speed change only. No automatic time stretch."""
    factor = float(np.clip(factor, .32, 4.))
    if abs(factor - 1.) < .015:
        return data
    size, hop = 1024, 256
    if len(data) < size:
        return np.interp(np.linspace(0, len(data) - 1,
                                     max(1, int(len(data) * factor))),
                         np.arange(len(data)), data).astype('float32')
    length = max(1, int(len(data) * factor))
    out = np.zeros(length + size, dtype='float32')
    norms = np.zeros(length + size, dtype='float32')
    window = np.sqrt(np.hanning(size).astype('float32'))
    frames = int(np.ceil(max(0, len(data) - size) * factor / hop)) + 1
    for i in range(frames):
        src = min(len(data) - size, int(i * hop / factor))
        dst = i * hop
        out[dst:dst + size] += data[src:src + size] * window
        norms[dst:dst + size] += window
    valid = norms[:length] > 1.e-4
    out[:length][valid] /= norms[:length][valid]
    return out[:length]


def _pitch_and_speed(data, speed, pitch, brightness):
    if speed == 100 and pitch == 0 and brightness == 0:
        return data
    x = data.astype('float32') / 32768.
    factor = 2. ** (float(pitch) / 12.)
    if abs(factor - 1.) > .003:
        length = max(8, int(len(x) / factor))
        x = np.interp(np.arange(length, dtype='float32') * factor,
                      np.arange(len(x)), x).astype('float32')
    x = _overlap_stretch(x, factor / (speed / 100.))
    if brightness:
        low = np.convolve(x, np.ones(11, dtype='float32') / 11., mode='same')
        x = low + (x - low) * (1. + brightness / 100. * .70)
    return (np.clip(x, -.999, .999) * 32767).astype('<i2')


class GrainBank:
    """Aperiodic, 50%-overlap microtexture from real waveform interiors.

    Use low-onset-variance interior sections; avoid whole recorded attacks.
    Different start positions, clip selections and grain lengths prevent a
    short fixed WAV from coming back at a recognizable periodic interval.
    """

    def __init__(self, sources: dict[str, np.ndarray], weights=None, *, seed=0):
        if not sources:
            raise ValueError('GrainBank requires at least one recorded source')
        self.sources = sources
        self.ids = list(sources)
        self.weights = [float((weights or {}).get(s, 1.)) for s in self.ids]
        self.rng = random.Random(seed)
        self.position = 0
        self.next_start = 0
        self.grains = []
        self.last_id = None
        self.rms_by_id = {}
        self.regions = {}
        self.used_ids = set()
        for ident, x in sources.items():
            x = np.asarray(x, dtype='float32')
            self.sources[ident] = x
            # Exclude the obvious first/last contact, where possible.
            margin = min(int(.12 * RATE), max(0, (len(x) - 8192) // 3))
            a = margin
            b = len(x) - margin
            self.regions[ident] = (a, b)
            section = x[a:b] if b > a else x
            self.rms_by_id[ident] = float(np.sqrt(np.mean(section**2) + 1e-12))
        median = float(np.median(list(self.rms_by_id.values())))
        self.gain_by_id = {
            s: float(np.clip(median / max(1e-5, rms), .60, 2.4))
            for s, rms in self.rms_by_id.items()
        }

    def _pick_id(self):
        if len(self.ids) == 1:
            chosen = self.ids[0]
        else:
            opts = [(s, w) for s, w in zip(self.ids, self.weights)
                    if s != self.last_id]
            chosen = self.rng.choices([s for s, _ in opts],
                                      weights=[w for _, w in opts], k=1)[0]
        self.last_id = chosen
        self.used_ids.add(chosen)
        return chosen

    def _new_grain(self):
        ident = self._pick_id()
        x = self.sources[ident]
        lo, hi = self.regions[ident]
        available = hi - lo
        # Vary both grain length and onset. 260-510 ms gives smooth overlap
        # while avoiding the whole recorded multi-stroke sequence.
        wanted = int(self.rng.uniform(.26, .51) * RATE)
        size = min(max(512, available), wanted)
        size += size % 2
        if size > len(x):
            size = len(x) - len(x) % 2
        if size < 32:
            raise ValueError('Recorded sound is too short for texture')
        high_start = max(lo, hi - size)
        if high_start <= lo:
            start = max(0, min(lo, len(x)-size))
        else:
            # Sample several candidate windows and prefer stable, audible
            # internal friction over sudden attacks or silence.
            target = self.rms_by_id[ident]
            candidates = [self.rng.randint(lo, high_start) for _ in range(7)]
            def score(i):
                part = x[i:i+size]
                thirds = np.array_split(part, 4)
                env = np.array([np.sqrt(np.mean(t*t)+1e-12) for t in thirds])
                # Penalize abrupt level changes and nearly silent regions.
                return np.std(env)/(target+1e-5) + .16*abs(np.mean(env)-target)/(target+1e-5)
            start = min(candidates, key=score)
        data = np.ascontiguousarray(x[start:start+size]) * self.gain_by_id[ident]
        # Standard Hann overlap-add at 50%, plus power-aware normalization.
        window = np.hanning(size).astype('float32')
        return data, window

    def render(self, length: int):
        if length <= 0:
            return np.empty(0, dtype='float32')
        begin = self.position
        end = begin + length
        while self.next_start < end:
            data, window = self._new_grain()
            self.grains.append((self.next_start, data, window))
            self.next_start += max(1, len(data) // 2)
        out = np.zeros(length, dtype='float32')
        power = np.zeros(length, dtype='float32')
        remaining = []
        for start, data, window in self.grains:
            stop = start + len(data)
            if stop <= begin:
                continue
            left = max(begin, start)
            right = min(end, stop)
            if right > left:
                a = left - start
                b = right - start
                dest = slice(left - begin, right - begin)
                w = window[a:b]
                out[dest] += data[a:b] * w
                power[dest] += w*w
            if stop > end:
                remaining.append((start, data, window))
        # Normalize incoherent energy, avoiding a rhythmic 50%-overlap swell.
        np.divide(out, np.sqrt(np.maximum(power, .5)), out=out)
        self.grains = remaining
        self.position = end
        return out


class PencilFlowBank(GrainBank):
    """P-only: use longer quiet interior sections instead of rapid micro-grains.

    B/J and E keep the exact original GrainBank. The longer, irregular
    segments reduce the repeated short 'scratch-scratch' attacks the user
    heard in P while retaining the real-time movement and pressure response.
    This is continuous reconstruction from the existing pencil recordings,
    not a claim that the recorded material lasts forever by itself.
    """

    def _new_grain(self):
        ident = self._pick_id()
        recording = self.sources[ident]
        lo, hi = self.regions[ident]
        available = hi - lo
        # P ONLY: 0.95-1.8s instead of the previous 0.26-0.51s. This
        # reduces repeated attacks without changing speed or pitch.
        target_size = int(self.rng.uniform(.95, 1.8) * RATE)
        size = min(target_size, available)
        size = max(32, size - size % 2)
        size = min(size, len(recording) - len(recording) % 2)
        if size < 32:
            raise ValueError('Pencil sample too short')
        maximum = max(lo, hi-size)
        if maximum <= lo:
            offset = max(0, min(lo, len(recording)-size))
        else:
            # Prefer a sustained stroke interior instead of pen contact,
            # a separate attack, or the silence after a lift.
            positions = [self.rng.randint(lo, maximum) for _ in range(11)]
            reference = self.rms_by_id[ident]
            def stability(start):
                sample = recording[start:start+size]
                chunks = np.array_split(sample, 12)
                levels = np.array([np.sqrt(np.mean(part*part) + 1.e-12)
                                   for part in chunks])
                # Gaps, marked 'restarts', and peaks are undesirable.
                return (2.5 * np.std(levels) / (reference+1.e-6)
                        + .9 * np.max(np.abs(np.diff(levels))) / (reference+1.e-6)
                        + .3 * abs(np.mean(levels)-reference)/(reference+1.e-6))
            offset = min(positions, key=stability)
        segment = np.ascontiguousarray(recording[offset:offset+size]) * self.gain_by_id[ident]
        return segment, np.hanning(size).astype('float32')


class SeamlessBrushLoop:
    """Read a long, already seam-crossfaded recording as one continuous loop.

    Unlike the real-time GrainBank, this keeps the chosen 10-second recording
    intact. This is used ONLY for rapid coloring in the brush mode.
    """

    def __init__(self, pcm):
        self.pcm = np.ascontiguousarray(pcm, dtype='float32')
        if len(self.pcm) < 128:
            raise ValueError('Brush loop audio is too short')
        self.cursor = 0
        self.wraps = 0

    def render(self, frames):
        if frames <= 0:
            return np.zeros(0, dtype='float32')
        n = len(self.pcm)
        positions = (np.arange(frames, dtype=np.int64) + self.cursor) % n
        self.cursor += frames
        if self.cursor >= n:
            self.wraps += self.cursor // n
            self.cursor %= n
        return self.pcm[positions]


class AudioEngine:
    """UI-facing streaming engine. The audio callback owns timeline progression."""
    MODES = MODES

    def __init__(self, sounds_folder: Path, *, stream_factory=None):
        self.folder = Path(sounds_folder)
        self.library = json.loads((self.folder/'library.json').read_text(encoding='utf8'))
        self.samples = {s['id']: s for s in self.library['samples']}
        self.by_category = {c: [s['id'] for s in self.library['samples'] if s['category']==c]
                            for c in MODES}
        if any(not self.by_category[m] for m in MODES):
            raise ValueError('Missing recordings for a drawing tool')
        self.lock = threading.RLock()
        self.clock = time.monotonic
        self.volume = .76
        self.output_boost_db = 0  # 0 dB = bit-identical legacy mix.
        self.muted = False
        self.effects = {m: {'volume':100,'speed':100,'pitch':0,'brightness':0,'dynamics':70}
                        for m in MODES}
        self.pcm_cache = {}
        self.active_mode = None
        self.active_desired = 'auto'
        self.banks = {}
        # B/J ONLY: long natural loop fades in when short quick coloring
        # gestures are detected. P and E do not use this playback path.
        self.brush_fast_loop = None
        self.brush_fast_mix = 0.
        self.brush_fast_target = 0.
        self.brush_release_at = -1e9
        self.motion_gate = 0.
        self.motion_target = 0.
        self.releasing = False
        self.motion_estimate = .5
        self.pressure = .5
        self.real_pressure = False
        self.pressure_time = 0.
        self.real_packet_count = 0
        self.last_real_pressure = None
        self.pressure_source = 'movimiento'
        self.axis_target = .5
        self.axis_mix = .5
        self.preview_pcm = None
        self.preview_pos = 0
        self.preview_mode = None
        self.rng = random.Random()
        self.last_random = {}
        self.rendered_frames = 0
        self.last_peak = 0.
        self.stream_error = None
        if stream_factory is None:
            import sounddevice as sd
            stream_factory = lambda callback: sd.OutputStream(
                samplerate=RATE, channels=1, dtype='float32',
                blocksize=1024, latency='low', callback=callback)
        self.stream = stream_factory(self._callback)
        self.stream.start()

    def _pool(self, category, direction=None):
        pool = [s for s in self.by_category[category]
                if self.samples[s].get('auto_eligible', True)]
        if not pool:
            pool = self.by_category[category]
        if category == 'brush' and direction:
            # Favor direction-marked velvet favorites but retain additional
            # qualified recordings as alternate material (no forced clicks).
            marked = [s for s in pool if self.samples[s].get('direction') == direction]
            neutral = [s for s in pool if not self.samples[s].get('direction')]
            pool = marked + neutral if marked else pool
        return pool

    def _load_pcm(self, filename):
        with wave.open(str(self.folder/filename), 'rb') as wav:
            if (wav.getnchannels(),wav.getsampwidth(),wav.getframerate()) != (1,2,RATE):
                raise ValueError('Expected mono 16-bit 44,100 Hz: '+filename)
            return np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2')

    def _processed(self, ident):
        fx = self.effects[self.samples[ident]['category']]
        key = (ident, fx['speed'], fx['pitch'], fx['brightness'])
        if key not in self.pcm_cache:
            pcm = self._load_pcm(self.samples[ident]['file'])
            pcm = _pitch_and_speed(pcm, fx['speed'], fx['pitch'], fx['brightness'])
            self.pcm_cache[key] = np.ascontiguousarray(pcm.astype('float32') / 32768.)
        return self.pcm_cache[key]

    def _new_bank(self, category, desired, direction=None, seed=0):
        ids = [desired] if desired in self.by_category[category] else self._pool(category,direction)
        pcm = {s: self._processed(s) for s in ids}
        weights = {s: (3.5 if self.samples[s].get('favorite') else 1.) for s in ids}
        # Only pencil gets the smoother long-fragment stream. Never route
        # brush or eraser through this bank.
        bank_type = PencilFlowBank if category == 'pencil' else GrainBank
        return bank_type(pcm, weights, seed=seed)

    def select(self, category, desired):
        if desired in self.by_category[category]:
            return desired
        ids = self._pool(category)
        choices = [x for x in ids if x != self.last_random.get(category)] or ids
        ident = self.rng.choice(choices)
        self.last_random[category] = ident
        return ident

    def begin_stroke(self, category, desired):
        if self.muted or category not in MODES:
            return False
        with self.lock:
            if self.active_mode is not None and not self.releasing:
                return False
            # If consecutive short brush passes are separated by less than
            # 180 ms, resume the existing texture instead of starting over.
            # This special case NEVER applies to the pencil or eraser.
            if (category == 'brush' and self.active_mode == 'brush'
                    and self.releasing and desired == self.active_desired
                    and self.clock() - self.brush_release_at <= .18):
                self.releasing = False
                self.motion_target = 0.
                return True
            self.active_desired = desired
            seed = self.rng.randrange(1,2**30)
            if category == 'brush':
                # Approved B/J-only two-stroke cycles play as full recordings.
                # Never turn them into grains or restart them at a direction change.
                fast_id = desired if desired in BRUSH_TWO_STROKE else 'brush_fast_velvet_10'
                if fast_id in self.samples and desired in ('auto', fast_id):
                    self.brush_fast_loop = SeamlessBrushLoop(self._processed(fast_id))
                else:
                    self.brush_fast_loop = None
                self.brush_fast_mix = 1. if desired == fast_id else 0.
                self.brush_fast_target = self.brush_fast_mix
                self.banks = {
                    'horizontal': self._new_bank(category,desired,'horizontal',seed),
                    'vertical': self._new_bank(category,desired,'vertical',seed+1),
                }
            else:
                self.brush_fast_loop = None
                self.banks = {'main':self._new_bank(category,desired,seed=seed)}
            self.active_mode = category
            self.motion_gate = 0.
            self.motion_target = 0.
            self.releasing = False
            self.axis_mix = self.axis_target
            self.rendered_frames = 0
        return True

    def update_motion(self, px_per_sec):
        with self.lock:
            v = max(0.,float(px_per_sec))
            self.motion_target = min(1., max(.20, v/300.)) if v>7 else 0.
            self.motion_estimate = .78*self.motion_estimate+.22*min(1.,v/900.)

    def update_direction(self, dx, dy):
        with self.lock:
            if self.active_mode == 'brush':
                ax,ay = abs(float(dx)),abs(float(dy))
                if ax+ay >= 1.:
                    self.axis_target = float(ay/(ax+ay))

    def gesture_turn(self, axis='horizontal'):
        """Direction changes now adjust the blend, never retrigger playback."""
        with self.lock:
            if self.active_mode != 'brush':
                return False
            self.axis_target = 1. if axis == 'vertical' else 0.
        return True

    def set_fast_coloring(self, value):
        """Only B/J: a gesture-based 0..1 target, not a timing loop trigger."""
        with self.lock:
            if self.active_mode == 'brush' and self.brush_fast_loop is not None:
                if self.active_desired == 'auto':
                    self.brush_fast_target = float(np.clip(value, 0., 1.))
                elif self.active_desired in (*BRUSH_TWO_STROKE, 'brush_fast_velvet_10'):
                    self.brush_fast_target = 1.

    def set_pressure(self, pressure, real=True):
        with self.lock:
            self.pressure = float(np.clip(pressure,0.,1.))
            self.real_pressure = bool(real)
            self.pressure_time = self.clock()
            if real:
                self.real_packet_count += 1
                self.last_real_pressure = self.pressure

    def _strength(self):
        real = self.real_pressure and (self.clock() - self.pressure_time < .35)
        self.pressure_source = 'wintab' if real else 'movimiento'
        x = self.pressure if real else self.motion_estimate
        dynamics = self.effects[self.active_mode]['dynamics']/100.
        # A touch of sound remains at low pressure, more body when pressing.
        response = .12+.88*float(np.clip(x,0.,1.))**.72
        return (1.-dynamics)+dynamics*response

    def _render(self, frames):
        result = np.zeros(frames, dtype='float32')
        if self.active_mode and self.banks:
            if self.active_mode == 'brush':
                h = self.banks['horizontal'].render(frames)
                v = self.banks['vertical'].render(frames)
                smoothing = 1.-math.exp(-frames/(RATE*.13))
                next_axis = self.axis_mix+(self.axis_target-self.axis_mix)*smoothing
                axis = np.linspace(self.axis_mix,next_axis,frames, dtype='float32')
                self.axis_mix = next_axis
                # Equal-power pans avoid dips when switching directions.
                result = np.sqrt(1.-axis)*h + np.sqrt(axis)*v
                if self.brush_fast_loop is not None:
                    # Long loop advances even when nearly silent, avoiding
                    # a new start sound on each quick reverse or pen lift.
                    fast = self.brush_fast_loop.render(frames)
                    tau_fast = .11 if self.brush_fast_target > self.brush_fast_mix else .23
                    a = 1. - math.exp(-frames / (RATE * tau_fast))
                    next_fast = self.brush_fast_mix + (self.brush_fast_target - self.brush_fast_mix)*a
                    blend = np.linspace(self.brush_fast_mix, next_fast, frames, dtype='float32')
                    self.brush_fast_mix = next_fast
                    result = np.sqrt(1.-blend)*result + np.sqrt(blend)*fast
            else:
                result = self.banks['main'].render(frames)
            tau = .045 if self.motion_target > self.motion_gate else .11
            smoothing = 1.-math.exp(-frames/(RATE*tau))
            next_gate = self.motion_gate+(self.motion_target-self.motion_gate)*smoothing
            gate = np.linspace(self.motion_gate,next_gate,frames,dtype='float32')
            self.motion_gate = next_gate
            fx = self.effects[self.active_mode]
            gain = self.volume * (fx['volume']/100.) * self._strength()
            # Gate is driven by movement; pressure changes amplitude in real time.
            result *= gate*gain
            self.rendered_frames += frames
            if self.releasing and self.motion_gate < .012:
                self.active_mode = None
                self.banks = {}
                self.brush_fast_loop = None
                self.releasing = False
        if self.preview_pcm is not None:
            left = len(self.preview_pcm)-self.preview_pos
            n = min(frames,max(0,left))
            if n:
                preview_gain = self.volume*(self.effects[self.preview_mode]['volume']/100.)*.7
                result[:n] += self.preview_pcm[self.preview_pos:self.preview_pos+n]*preview_gain
                self.preview_pos += n
            if self.preview_pos >= len(self.preview_pcm):
                self.preview_pcm = None
                self.preview_mode = None
        if self.muted:
            result[:] = 0
        # Final output-only gain. No changes to sample selection, grain timing,
        # pitch, pressure response or the P/B/J/E signal before this point.
        # A per-block peak ceiling prevents hard clipping at high boost values.
        if self.output_boost_db and not self.muted:
            result *= 10. ** (self.output_boost_db / 20.)
            peak = float(np.max(np.abs(result))) if frames else 0.
            if peak > .95:
                result *= .95 / peak
        np.clip(result,-.97,.97,out=result)
        self.last_peak = float(np.max(np.abs(result))) if frames else 0.
        return result

    def _callback(self, outdata, frames, time_info, status):
        try:
            with self.lock:
                outdata[:,0] = self._render(frames)
        except Exception as exc:
            self.stream_error = str(exc)
            outdata.fill(0)

    def tick(self):
        # Audio time advances in the audio thread, not a Qt timer.
        with self.lock:
            if self.real_pressure and self.clock()-self.pressure_time>.35:
                self.real_pressure = False
                self.pressure_source = 'movimiento'

    def refresh_volume(self):
        # The next audio block uses the updated controls.
        pass

    def stop_stroke(self, fade_ms=120):
        with self.lock:
            if self.active_mode is not None:
                self.motion_target = 0.
                self.releasing = True
                if self.active_mode == 'brush':
                    self.brush_release_at = self.clock()

    def stop_all(self):
        with self.lock:
            self.stop_stroke()
            self.preview_pcm = None
            self.preview_mode = None

    def set_volume(self, value):
        with self.lock:
            self.volume = float(np.clip(int(value),0,100))/100.

    def set_output_boost(self, db):
        """Extra final output volume only (0-12 dB). No changes to presets."""
        with self.lock:
            self.output_boost_db = int(np.clip(int(db), 0, 12))

    def set_effect(self, mode, key, value):
        if mode not in MODES or key not in self.effects[mode]:
            raise ValueError('Unknown tool or audio setting')
        bounds = {'volume':(0,100),'speed':(45,120),'pitch':(-8,8),
                  'brightness':(-100,100),'dynamics':(0,100)}
        lo, hi = bounds[key]
        with self.lock:
            value = int(np.clip(value,lo,hi))
            if self.effects[mode][key] == value:
                return
            self.effects[mode][key] = value
            if key in ('speed','pitch','brightness'):
                self.pcm_cache = {k:v for k,v in self.pcm_cache.items()
                                  if self.samples[k[0]]['category']!=mode}
                # Rebuild texture material from the changed files at the new
                # settings; no timer-driven restart or full-sample click.
                if self.active_mode == mode:
                    desired = self.active_desired
                    self.active_mode = None
                    self.releasing = False
                    self.banks = {}
                    self.begin_stroke(mode,desired)

    def set_tool_volume(self,mode,value):
        self.set_effect(mode,'volume',value)

    def preview(self,category,desired):
        with self.lock:
            ident = self.select(category,desired)
            src = self.samples[ident]['preview_file']
            pcm = self._load_pcm(src).astype('float32')/32768.
            self.preview_pcm = np.ascontiguousarray(pcm)
            self.preview_pos = 0
            self.preview_mode = category
            return self.samples[ident]['label']

    def close(self):
        self.stop_all()
        self.stream.stop()
        self.stream.close()
