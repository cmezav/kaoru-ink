"""Kaoru Ink audio: one continuous one-shot per pencil stroke, brush loops only."""
import json
import random
import wave
from pathlib import Path
import numpy as np


class AudioEngine:
    def __init__(self, sounds_folder: Path):
        import pygame
        self.pg = pygame
        self.pg.mixer.pre_init(frequency=44100, size=-16, channels=1, buffer=512)
        self.pg.mixer.init()
        self.pg.mixer.set_num_channels(6)
        self.channels = {
            'pencil': self.pg.mixer.Channel(0),
            'brush': self.pg.mixer.Channel(1),
            'preview': self.pg.mixer.Channel(2),
        }
        data = json.loads((sounds_folder / 'library.json').read_text(encoding='utf-8'))
        self.samples = {sample['id']: sample for sample in data['samples']}
        self.by_category = {
            c: [s['id'] for s in data['samples'] if s['category'] == c]
            for c in ('short', 'medium', 'long', 'brush')
        }
        self.pcm = {}
        for ident, sample in self.samples.items():
            with wave.open(str(sounds_folder / sample['file']), 'rb') as wav:
                assert wav.getframerate() == 44100
                assert wav.getnchannels() == 1 and wav.getsampwidth() == 2
                self.pcm[ident] = np.frombuffer(
                    wav.readframes(wav.getnframes()), dtype='<i2'
                ).copy()
        self.cache = {}
        self.pencil_cache = {}
        self.last_random = {}
        self.volume = .76
        self.speed = 65
        self.muted = False
        self.current_brush = None

    def select(self, category, desired):
        if desired in self.by_category[category]:
            return desired
        choices = self.by_category[category]
        previous = self.last_random.get(category)
        picked = random.choice([x for x in choices if x != previous] or choices)
        self.last_random[category] = picked
        return picked

    def _slow_pcm(self, sample_id):
        original = self.pcm[sample_id]
        if self.speed == 100:
            return original.astype(np.float32)
        ratio = self.speed / 100.
        count = max(16, int(len(original) / ratio))
        x = np.arange(count, dtype=np.float32) * ratio
        result = np.interp(x, np.arange(len(original)), original)
        return result.astype(np.float32)

    def sound(self, sample_id):
        key = (sample_id, self.speed)
        if key not in self.cache:
            pcm = np.clip(self._slow_pcm(sample_id), -32768, 32767).astype('<i2')
            if len(self.cache) >= 120:
                self.cache.clear()
            self.cache[key] = self.pg.mixer.Sound(buffer=pcm.tobytes())
        return self.cache[key]

    @staticmethod
    def _crossfade(a, b, ms=90):
        n = min(int(ms * 44.1), len(a) // 3, len(b) // 3)
        if n < 8:
            return np.concatenate((a, b))
        fade = np.linspace(0, 1, n, dtype=np.float32)
        bridge = a[-n:] * (1-fade) + b[:n] * fade
        return np.concatenate((a[:-n], bridge, b[n:]))

    def _pencil_one_shot(self, short_id, medium_id, long_id):
        """Build ONE long playable recording: intro -> middle -> sustained texture.

        Unlike brush playback, it is *never* played with loops=-1.
        Gentle grain crossfades in its body prolong the recording without
        retriggering attacks or restarting sounds while the mouse is held.
        Release (or stationary mouse) fades it out immediately.
        """
        key = (short_id, medium_id, long_id, self.speed)
        if key in self.pencil_cache:
            return self.pencil_cache[key]
        short = self._slow_pcm(short_id)
        medium = self._slow_pcm(medium_id)
        long = self._slow_pcm(long_id)
        intro = self._crossfade(short, medium, 90)
        total = 20 * 44100  # supports long continuous drags, at most 20 s
        output = np.zeros(total, dtype=np.float32)
        count = min(len(intro), total)
        output[:count] = intro[:count]
        # The center of a long sample is scratch texture without a fresh onset.
        start = int(len(long) * .18)
        end = max(start + 8000, int(len(long) * .89))
        body = long[start:min(len(long), end)]
        if len(body) < 9000:
            body = long
        # Stable randomness for a chosen triplet, avoiding repetitive rhythm.
        seed = sum(ord(c) for c in (short_id + medium_id + long_id)) + self.speed
        rng = random.Random(seed)
        while count < total:
            duration = min(len(body), rng.randint(16000, 38000))
            if len(body) > duration:
                offset = rng.randint(0, len(body) - duration)
                chunk = body[offset:offset+duration]
            else:
                chunk = body
            # Gentle differences between grains, no new sharp attacks.
            chunk = chunk * rng.uniform(.78, .94)
            cross = min(3500, count // 4, len(chunk) // 4)
            if cross > 16:
                fade = np.linspace(0, 1, cross, dtype=np.float32)
                output[count-cross:count] = (
                    output[count-cross:count]*(1-fade) + chunk[:cross]*fade
                )
            available = min(len(chunk)-cross, total-count)
            if available <= 0:
                break
            output[count:count+available] = chunk[cross:cross+available]
            count += available
        fade_len = 9000
        output[-fade_len:] *= np.linspace(1, 0, fade_len, dtype=np.float32)
        pcm = np.clip(output, -32768, 32767).astype('<i2')
        sound = self.pg.mixer.Sound(buffer=pcm.tobytes())
        if len(self.pencil_cache) >= 8:
            self.pencil_cache.clear()
        self.pencil_cache[key] = sound
        return sound

    def start_pencil(self, short_desired, medium_desired, long_desired):
        if self.muted:
            return
        # Exactly ONE play() per stroke. No pencil loops; never retriggered
        # by switching from a short to a medium or a long time threshold.
        short_id = self.select('short', short_desired)
        medium_id = self.select('medium', medium_desired)
        long_id = self.select('long', long_desired)
        self.channels['pencil'].play(
            self._pencil_one_shot(short_id, medium_id, long_id), loops=0, fade_ms=20
        )
        self.refresh_volume()

    def start_loop(self, category, desired):
        if category != 'brush':
            raise ValueError('Only B/brush can loop')
        if self.muted or self.current_brush is not None:
            return
        ident = self.select('brush', desired)
        channel = self.channels['brush']
        channel.stop()  # cancel any fade-out from a previous stroke
        self.current_brush = ident
        channel.play(self.sound(ident), loops=-1, fade_ms=90)
        self.refresh_volume()

    def stop_brush(self, fade_ms=160):
        channel = self.channels['brush']
        if channel.get_busy():
            channel.fadeout(fade_ms)
        self.current_brush = None

    def stop_stroke(self):
        self.channels['pencil'].fadeout(160)
        self.stop_brush()

    def stop_all(self):
        for channel in self.channels.values():
            channel.fadeout(130)
        self.current_brush = None

    def set_volume(self, percent):
        self.volume = percent / 100.
        self.refresh_volume()

    def refresh_volume(self):
        v = 0.0 if self.muted else self.volume
        for name, channel in self.channels.items():
            channel.set_volume(v * (.9 if name == 'preview' else 1.))

    def set_speed(self, value):
        self.stop_stroke()
        self.speed = int(value)
        self.cache.clear()
        self.pencil_cache.clear()

    def preview(self, category, desired):
        ident = self.select(category, desired)
        channel = self.channels['preview']
        channel.stop()
        channel.play(self.sound(ident), loops=1 if category == 'brush' else 0, fade_ms=40)
        self.refresh_volume()
        return self.samples[ident]['label']

    def refresh_live_loop(self, category, desired):
        if category == 'brush' and self.current_brush is not None:
            self.stop_brush(70)
            self.start_loop('brush', desired)

    def close(self):
        self.stop_all()
        self.pg.mixer.quit()
