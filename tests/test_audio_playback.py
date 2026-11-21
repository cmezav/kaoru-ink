"""Regression tests for sustained, non-looping real-recording crossfades."""
import sys
import types
import unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np

from app.audio import AudioEngine, _pitch_and_speed, _sustain_body

ROOT=Path(__file__).resolve().parents[1]

class FakeSound:
    def __init__(self,buffer):
        self.nbytes=len(buffer)
    def get_length(self):
        return self.nbytes/2/44100.

class FakeChannel:
    def __init__(self):
        self.clock=lambda:0.
        self.end_time=0.
        self.plays=[]
        self.busy=False
        self.level=0.
        self.sound=None
    def play(self,sound,**kwargs):
        self.plays.append(kwargs)
        self.sound=sound
        self.busy=True
        self.end_time=self.clock()+sound.get_length()
    def stop(self):self.busy=False
    def get_busy(self):return self.busy and self.clock()<self.end_time
    def fadeout(self,ms):self.busy=False
    def set_volume(self,v):self.level=v

class FakeMixer:
    def __init__(self):self.channels=[FakeChannel() for _ in range(9)]
    def pre_init(self,**kwargs):pass
    def init(self):pass
    def set_num_channels(self,n):
        if n!=9:raise AssertionError('Wrong number of channels')
    def Channel(self,i):return self.channels[i]
    def Sound(self,buffer):return FakeSound(buffer)
    def quit(self):pass

class AudioPlaybackTests(unittest.TestCase):
    def setUp(self):
        self.mixer=FakeMixer()
        self.now=20.
        with patch.dict(sys.modules,{'pygame':types.SimpleNamespace(mixer=self.mixer)}):
            self.engine=AudioEngine(ROOT/'assets/sounds')
        self.engine.clock=lambda:self.now
        for ch in self.mixer.channels:ch.clock=self.engine.clock
        for layer in self.engine.layers.values():layer.clock=self.engine.clock

    def advance(self,seconds,step=.05):
        for _ in range(round(seconds/step)):
            self.now+=step
            self.engine.tick()

    def test_original_tone_remains_identical_by_default(self):
        for mode,ident in [('pencil','pencil_long_08a'),('brush','brush_velvet_fav_15_01'),('eraser','eraser_medium_25')]:
            original=self.engine._load_pcm('curated/'+ident+'.wav')
            self.assertTrue(np.array_equal(original,_pitch_and_speed(original,100,0,0)))
            self.assertEqual(self.engine._sound(ident,'preview').nbytes,len(original)*2)
            self.assertTrue(np.array_equal(original,_pitch_and_speed(original,100,0,0)))

    def test_sustain_preserves_real_waveform_middle_no_generated_noise(self):
        raw=self.engine._load_pcm('curated/brush_velvet_fav_15_01.wav')
        body=_sustain_body(raw)
        self.assertGreater(len(body),44100)
        self.assertLess(len(body),len(raw))
        self.assertFalse(np.array_equal(body,np.zeros(len(body),dtype=body.dtype)))

    def test_pencil_continues_past_its_original_8_second_recording(self):
        self.assertTrue(self.engine.begin_stroke('pencil','auto'))
        self.engine.update_motion(380)
        self.advance(25)
        p=self.engine.layers['pencil']
        self.assertTrue(p.active)
        self.assertTrue(self.engine.active_mode=='pencil')
        plays=sum(len(ch.plays) for ch in p.channels)
        self.assertGreaterEqual(plays,4)
        self.assertTrue(all(x.get('loops')==0 for ch in p.channels for x in ch.plays))
        self.assertTrue(any(ch.get_busy() and ch.level>0 for ch in p.channels))
        self.engine.stop_stroke()
        self.assertFalse(p.active)
        self.assertTrue(all(not ch.get_busy() for ch in p.channels))

    def test_eraser_never_goes_silent_on_a_ten_second_drag(self):
        self.assertTrue(self.engine.begin_stroke('eraser','auto'))
        e=self.engine.layers['eraser']
        for _ in range(200):
            self.engine.update_motion(200)
            self.advance(.05)
            self.assertTrue(any(ch.get_busy() and ch.level > .0001 for ch in e.channels), 'unexpected silent eraser handoff')
        self.assertGreater(sum(len(ch.plays) for ch in e.channels),4)
        self.assertTrue(all(a['loops']==0 for c in e.channels for a in c.plays))

    def test_brush_direction_mixes_favorites_without_static_mixer_loops(self):
        self.assertTrue(self.engine.begin_stroke('brush','auto'))
        self.assertTrue(self.engine.brush_directions_active)
        self.engine.update_motion(350)
        for _ in range(160):
            self.engine.update_direction(35,2)
            self.advance(.05)
        h=self.engine.layers['horizontal']
        v=self.engine.layers['vertical']
        self.assertGreater(sum(len(c.plays) for c in h.channels),2)
        self.assertGreater(sum(len(c.plays) for c in v.channels),2)
        self.assertTrue(all(call['loops']==0 for l in (h,v) for ch in l.channels for call in ch.plays))
        hlevel=sum(ch.level for ch in h.channels)
        vlevel=sum(ch.level for ch in v.channels)
        self.assertGreater(hlevel,vlevel*3)
        for _ in range(25):
            self.engine.update_direction(2,35)
            self.advance(.05)
        self.assertGreater(sum(ch.level for ch in v.channels),sum(ch.level for ch in h.channels)*3)
        self.engine.stop_stroke()
        self.assertFalse(h.active)
        self.assertFalse(v.active)

    def test_no_restart_on_pause_then_resume_and_zero_gain_while_idle(self):
        self.engine.begin_stroke('brush','auto')
        self.engine.update_motion(450)
        self.advance(1.5)
        for _ in range(12):self.engine.update_motion(0)
        self.assertLess(sum(ch.level for l in (self.engine.layers['horizontal'],self.engine.layers['vertical']) for ch in l.channels),.004)
        self.engine.update_motion(600)
        self.advance(2)
        self.assertGreater(sum(ch.level for l in (self.engine.layers['horizontal'],self.engine.layers['vertical']) for ch in l.channels),.04)

    def test_all_modes_remain_continuous_through_90_seconds(self):
        # Finite source WAVs (0.7-8 s) must never produce a silent gap during
        # continuous painting/drawing. The tests use real WAV durations.
        for mode in ('pencil','brush','eraser'):
            self.engine.begin_stroke(mode,'auto')
            self.engine.update_motion(320)
            for _ in range(900):
                self.now += .1
                self.engine.tick()
                keys=('horizontal','vertical') if mode=='brush' else (mode,)
                self.assertTrue(any(ch.get_busy() and ch.level>.00001
                    for key in keys for ch in self.engine.layers[key].channels),
                    f'{mode} fell silent after {self.now:.1f}s')
            self.engine.stop_stroke()

    def test_preview_is_one_shot(self):
        self.engine.preview('brush','brush_velvet_fav_15_01')
        self.assertEqual(self.mixer.channels[8].plays[-1]['loops'],0)

    def test_controls_independent_for_all_modes(self):
        old_b=self.engine.effects['brush'].copy()
        old_e=self.engine.effects['eraser'].copy()
        self.engine.set_effect('pencil','pitch',2)
        self.engine.set_effect('pencil','speed',90)
        self.engine.set_effect('pencil','volume',55)
        self.assertEqual(self.engine.effects['brush'],old_b)
        self.assertEqual(self.engine.effects['eraser'],old_e)

    def test_manual_mode_stays_with_selected_file_during_crossfades(self):
        self.engine.begin_stroke('brush','brush_velvet_fav_15_01')
        self.engine.update_motion(400)
        self.advance(5)
        l=self.engine.layers['horizontal']
        self.assertTrue(l.active)
        self.assertEqual(l.current_id,'brush_velvet_fav_15_01')
        self.assertGreater(sum(len(ch.plays) for ch in l.channels),2)

    def test_no_auto_second_start_in_same_drag(self):
        self.engine.begin_stroke('pencil','auto')
        self.engine.update_motion(550)
        self.advance(12)
        self.assertFalse(self.engine.begin_stroke('pencil','auto'))
        self.engine.stop_stroke()
        self.assertTrue(self.engine.begin_stroke('pencil','auto'))

if __name__=='__main__':unittest.main()
