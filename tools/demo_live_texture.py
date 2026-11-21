"""Render demonstration of the live generator without a sound device.
The audio comes from the real, unchanged 37 recordings; directional/pressure
and speed controls are simulated. This is NOT a Windows/device validation.
"""
import os
import sys
import wave
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.audio import AudioEngine, RATE

class FakeStream:
    def __init__(self, callback):
        self.callback=callback
    def start(self):pass
    def stop(self):pass
    def close(self):pass


def render(mode, seconds=10):
    engine = AudioEngine(ROOT/'assets/sounds', stream_factory=FakeStream)
    engine.volume = .88
    engine.begin_stroke(mode, 'auto')
    frames = int(seconds * RATE)
    arr = np.zeros(frames, dtype='float32')
    idx = 0
    while idx < frames:
        t=idx/RATE
        # Active motion, two pauses in the demo, some pressure variation.
        velocity = 380 + 170 * np.sin(t*.85)
        if 3.8 <= t < 4.15 or 7.4 <= t < 7.68:
            velocity=0
        engine.update_motion(velocity)
        engine.set_pressure(.15+.75*(.5+.5*np.sin(t*.64)),real=True)
        if mode=='brush':
            engine.update_direction(70,10) if t%3<1.5 else engine.update_direction(10,70)
        n=min(1024,frames-idx)
        with engine.lock:
            arr[idx:idx+n]=engine._render(n)
        idx+=n
    engine.close()
    out=ROOT.parent/f'KaoruInk-v13-demo-{mode}-10s.wav'
    with wave.open(str(out),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(RATE)
        f.writeframes((np.clip(arr,-.99,.99)*32767).astype('<i2').tobytes())
    return out,arr

if __name__=='__main__':
    for m in ('pencil','brush','eraser'):
        output,arr=render(m)
        # Envelope fluctuation and output headroom.
        step=RATE//10
        chunks=np.array([np.sqrt(np.mean(x*x)) for x in np.array_split(arr,len(arr)//step)])
        print(m,output, 'peak=',float(np.max(abs(arr))), 'rms=',float(np.sqrt(np.mean(arr*arr))),
              'env std=',float(np.std(chunks)), 'env min/max=',float(chunks.min()),float(chunks.max()))
