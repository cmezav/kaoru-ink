"""Execute the actual AudioEngine against a fake mixer on Linux."""
import sys,types,unittest
from unittest.mock import patch
from pathlib import Path
from app.audio import AudioEngine, _pitch_and_speed, _brush_loop
import numpy as np

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

    def test_only_one_play_per_held_stroke_all_modes(self):
        for mode,ident in [('pencil','pencil_pencil_draw'),('brush','brush_marker_draw'),('eraser','eraser_eraser')]:
            self.assertTrue(self.engine.begin_stroke(mode,ident))
            for _ in range(100):
                self.engine.update_motion(900)
                self.assertFalse(self.engine.begin_stroke(mode,ident))
            ch=self.engine.channels[mode]
            self.assertEqual(len(ch.plays),1)
            self.assertEqual(ch.plays[0]['loops'], -1 if mode=='brush' else 0)
            self.engine.stop_stroke()
            self.assertFalse(ch.get_busy())

    def test_preview_never_loops_even_brush_or_eraser(self):
        for mode in ('pencil','brush','eraser'):
            self.engine.preview(mode,'auto')
        self.assertTrue(all(p['loops']==0 for p in self.mixer.channels[3].plays))

    def test_brush_loop_follows_motion_and_mutes_on_pause(self):
        self.engine.begin_stroke('brush','brush_marker_draw')
        ch=self.engine.channels['brush']
        for _ in range(5):self.engine.update_motion(750)
        active=ch.level
        for _ in range(8):self.engine.update_motion(0)
        self.assertLess(ch.level,active*.002)
        for _ in range(5):self.engine.update_motion(750)
        self.assertGreater(ch.level,active*.5)
        self.assertEqual(len(ch.plays),1)
        self.engine.stop_stroke()
        self.assertFalse(ch.busy)

    def test_pressure_changes_volume_without_restart(self):
        self.engine.begin_stroke('pencil','pencil_pencil_draw')
        self.engine.update_motion(150)
        ch=self.engine.channels['pencil']
        self.engine.set_pressure(.07,True)
        quiet=ch.level
        self.engine.set_pressure(1.,True)
        self.assertGreater(ch.level,quiet*1.7)
        self.assertEqual(len(ch.plays),1)

    def test_tone_independent_of_speed_duration(self):
        source=(np.sin(np.linspace(0,120*np.pi,22050,dtype='float32'))*.1*32767).astype('<i2')
        neutral=_pitch_and_speed(source,65,0,0)
        sharp=_pitch_and_speed(source,65,5,0)
        slow=_pitch_and_speed(source,45,5,0)
        self.assertLess(abs(len(sharp)-len(neutral))/len(neutral),.02)
        self.assertGreater(len(slow),len(sharp)*1.35)

    def test_loop_seam_is_smooth(self):
        data=self.engine._load_pcm('held/brush_marker_draw.wav')
        loop=_brush_loop(data)
        self.assertGreater(len(loop),22050)
        self.assertLess(abs(int(loop[-1])-int(loop[0])),max(450,int(np.percentile(np.abs(np.diff(loop.astype('float32'))),95))*2))

    def test_speed_does_not_retrigger(self):
        self.assertTrue(self.engine.begin_stroke('pencil','pencil_pencil_draw'))
        self.engine.set_speed(75)
        self.assertEqual(len(self.mixer.channels[0].plays),1)
        self.assertFalse(self.mixer.channels[0].busy)

if __name__=='__main__':unittest.main()
