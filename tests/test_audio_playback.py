"""Validate actual audio routing against a fake pygame mixer."""
import sys,types,unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np
from app.audio import AudioEngine, _pitch_and_speed, _brush_loop
ROOT=Path(__file__).resolve().parents[1]

class FakeChannel:
    def __init__(self):self.plays=[];self.busy=False;self.level=1
    def play(self,sound,**kwargs):self.plays.append(kwargs);self.busy=True
    def stop(self):self.busy=False
    def get_busy(self):return self.busy
    def fadeout(self,ms):self.busy=False
    def set_volume(self,v):self.level=v

class FakeMixer:
    def __init__(self):self.channels=[FakeChannel() for i in range(5)]
    def pre_init(self,**kwargs):pass
    def init(self):pass
    def set_num_channels(self,n):pass
    def Channel(self,i):return self.channels[i]
    def Sound(self,buffer):return len(buffer)
    def quit(self):pass

class AudioPlaybackTests(unittest.TestCase):
    def setUp(self):
        self.mixer=FakeMixer()
        with patch.dict(sys.modules,{'pygame':types.SimpleNamespace(mixer=self.mixer)}):
            self.engine=AudioEngine(ROOT/'assets/sounds')

    def test_natural_defaults(self):
        self.assertEqual((self.engine.speed,self.engine.pitch,self.engine.brightness),(100,0,0))

    def test_neutral_processing_preserves_pcm_exactly(self):
        for ident in ('pencil_pencil_draw','brush_marker_draw','eraser_eraser'):
            src=self.engine._load_pcm(f'original/{ident}.wav')
            processed=_pitch_and_speed(src,100,0,0)
            self.assertTrue(np.array_equal(src,processed))
            self.assertEqual(self.engine._sound(ident,'held'),len(src)*2)

    def test_only_brush_loops(self):
        for mode,ident in [('pencil','pencil_pencil_draw'),('brush','brush_marker_draw'),('eraser','eraser_eraser')]:
            self.assertTrue(self.engine.begin_stroke(mode,ident))
            for _ in range(100):
                self.engine.update_motion(900)
                self.assertFalse(self.engine.begin_stroke(mode,ident))
            ch=self.engine.channels[mode]
            self.assertEqual(len(ch.plays),1)
            self.assertEqual(ch.plays[0]['loops'],-1 if mode=='brush' else 0)
            self.engine.stop_stroke()

    def test_preview_never_loops(self):
        for mode in ('pencil','brush','eraser'):
            self.engine.preview(mode,'auto')
        self.assertTrue(all(p['loops']==0 for p in self.mixer.channels[3].plays))

    def test_brush_motion_gate_and_pressure(self):
        self.engine.begin_stroke('brush','brush_marker_draw')
        ch=self.engine.channels['brush']
        for _ in range(5):self.engine.update_motion(750)
        active=ch.level
        for _ in range(8):self.engine.update_motion(0)
        self.assertLess(ch.level,active*.002)
        for _ in range(5):self.engine.update_motion(750)
        self.assertGreater(ch.level,active*.5)
        self.assertEqual(len(ch.plays),1)

    def test_pressure_dynamic_without_restart(self):
        self.engine.begin_stroke('pencil','pencil_pencil_draw')
        self.engine.update_motion(150)
        ch=self.engine.channels['pencil']
        self.engine.set_pressure(.07,True)
        quiet=ch.level
        self.engine.set_pressure(1.,True)
        self.assertGreater(ch.level,quiet*1.7)
        self.assertEqual(len(ch.plays),1)

    def test_brush_loop_joins_cleanly(self):
        src=self.engine._load_pcm('original/brush_marker_draw.wav')
        loop=_brush_loop(src)
        self.assertGreater(len(loop),2000)
        self.assertLess(abs(int(loop[-1])-int(loop[0])),1500)

    def test_manual_adjustments_are_optional(self):
        data=np.linspace(-1500,1500,44100,dtype='float32').astype('<i2')
        self.assertTrue(np.array_equal(data,_pitch_and_speed(data,100,0,0)))
        modified=_pitch_and_speed(data,100,2,0)
        self.assertIsInstance(modified,np.ndarray)

if __name__=='__main__':unittest.main()
