"""Execute the actual AudioEngine against a fake mixer on Linux."""
import sys,types,unittest
from unittest.mock import patch
from pathlib import Path
from app.audio import AudioEngine

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
            self.assertEqual(ch.plays[0]['loops'],0)
            self.engine.stop_stroke()
            self.assertFalse(ch.get_busy())

    def test_preview_never_loops_even_brush_or_eraser(self):
        for mode in ('pencil','brush','eraser'):
            self.engine.preview(mode,'auto')
        self.assertTrue(all(p['loops']==0 for p in self.mixer.channels[3].plays))

    def test_speed_does_not_retrigger(self):
        self.assertTrue(self.engine.begin_stroke('pencil','pencil_pencil_draw'))
        self.engine.set_speed(75)
        self.assertEqual(len(self.mixer.channels[0].plays),1)
        self.assertFalse(self.mixer.channels[0].busy)

if __name__=='__main__':unittest.main()
