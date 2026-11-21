"""Audio regression tests: natural previews, held P/E and per-tool controls."""
import sys, types, unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np
from app.audio import AudioEngine, _pitch_and_speed, _brush_loop
ROOT=Path(__file__).resolve().parents[1]

class FakeChannel:
    def __init__(self):self.plays=[];self.busy=False;self.level=1.;self.sound=None
    def play(self,sound,**kwargs):self.plays.append(kwargs);self.sound=sound;self.busy=True
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

    def test_all_three_tools_default_to_unmodified_tones(self):
        for mode in ('pencil','brush','eraser'):
            self.assertEqual(tuple(self.engine.effects[mode][p] for p in ('speed','pitch','brightness')),(100,0,0))

    def test_preview_uses_raw_original_pcm_at_neutral_settings(self):
        for mode,ident in [('pencil','pencil_long_08a'),('brush','brush_soft_05b'),('eraser','eraser_medium_25')]:
            pcm=self.engine._load_pcm('curated/'+ident+'.wav')
            self.assertTrue(np.array_equal(pcm,_pitch_and_speed(pcm,100,0,0)))
            self.assertEqual(self.engine._sound(ident,'preview'),len(pcm)*2)
            self.engine.preview(mode,ident)
        self.assertTrue(all(p['loops']==0 for p in self.mixer.channels[3].plays))

    def test_pencil_and_eraser_play_one_unmodified_original_without_loop(self):
        for mode,ident in [('pencil','pencil_long_08a'),('eraser','eraser_medium_25')]:
            pcm=self.engine._load_pcm('curated/'+ident+'.wav')
            self.assertTrue(self.engine.begin_stroke(mode,ident))
            ch=self.engine.channels[mode]
            self.assertEqual(ch.plays[-1]['loops'],0)
            self.assertEqual(ch.sound,len(pcm)*2)
            for _ in range(100):
                self.engine.update_motion(800)
                self.assertFalse(self.engine.begin_stroke(mode,ident))
            self.assertEqual(len(ch.plays),1)
            self.engine.stop_stroke()

    def test_no_artificial_120_second_extension(self):
        pcm=self.engine._load_pcm('curated/pencil_long_08a.wav')
        self.assertEqual(self.engine._sound('pencil_long_08a','held'),len(pcm)*2)
        self.assertLess(self.engine._sound('pencil_long_08a','held'),44100*2*9)
        self.assertNotIn('_continuous_friction',Path(__file__).resolve().parents[1].joinpath('app','audio.py').read_text())

    def test_paint_mode_is_only_looping_mode(self):
        self.engine.begin_stroke('brush','brush_soft_05b')
        ch=self.engine.channels['brush']
        self.assertEqual(ch.plays[-1]['loops'],-1)
        for _ in range(10):self.engine.update_motion(100)
        loud=ch.level
        for _ in range(8):self.engine.update_motion(0)
        self.assertLess(ch.level,loud*.002)
        self.engine.stop_stroke()

    def test_controls_are_independent(self):
        before=self.engine.effects['brush'].copy()
        before_e=self.engine.effects['eraser'].copy()
        self.engine.set_effect('pencil','pitch',4)
        self.engine.set_effect('pencil','speed',90)
        self.engine.set_effect('pencil','brightness',20)
        self.engine.set_effect('pencil','volume',39)
        self.engine.set_effect('pencil','dynamics',95)
        self.assertEqual(self.engine.effects['brush'],before)
        self.assertEqual(self.engine.effects['eraser'],before_e)
        self.assertEqual(self.engine.effects['pencil'],{'volume':39,'speed':90,'pitch':4,'brightness':20,'dynamics':95})

    def test_dynamic_strength_changes_level_without_new_play(self):
        self.engine.begin_stroke('pencil','pencil_long_08a')
        self.engine.update_motion(130)
        ch=self.engine.channels['pencil']
        self.engine.set_pressure(.04,True);soft=ch.level
        self.engine.set_pressure(1.,True);strong=ch.level
        self.assertGreater(strong,soft*1.7)
        self.assertEqual(len(ch.plays),1)

    def test_auto_variation_uses_curated_long_P_and_avoids_repeat(self):
        last=None
        for i in range(25):
            ident=self.engine.select('pencil','auto')
            self.assertTrue(self.engine.samples[ident]['auto_eligible'])
            self.assertGreaterEqual(self.engine.samples[ident]['duration_sec'],4.8)
            if last is not None:self.assertNotEqual(ident,last)
            last=ident
        for mode in ('brush','eraser'):
            x=self.engine.select(mode,'auto')
            y=self.engine.select(mode,'auto')
            self.assertNotEqual(x,y)

    def test_no_pitch_processing_when_neutral_and_b_loop_seam(self):
        a=self.engine._load_pcm('curated/brush_soft_05b.wav')
        self.assertTrue(np.array_equal(a,_pitch_and_speed(a,100,0,0)))
        loop=_brush_loop(a)
        self.assertLess(abs(int(loop[-1])-int(loop[0])),1500)

if __name__=='__main__':unittest.main()
