"""Regression: v0.11 timed clip handoffs MUST NOT return."""
import sys
import types
import unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np

from app.audio import AudioEngine, _pitch_and_speed

ROOT=Path(__file__).resolve().parents[1]

class FakeSound:
    def __init__(self,buffer):self.nbytes=len(buffer)
    def get_length(self):return self.nbytes/2/44100.

class FakeChannel:
    def __init__(self):
        self.clock=lambda:0.
        self.end_time=0.
        self.plays=[]
        self.busy=False
        self.level=0.
    def play(self,sound,**kwargs):
        self.plays.append(kwargs)
        self.busy=True
        self.end_time=self.clock()+sound.get_length()
    def stop(self):self.busy=False
    def get_busy(self):return self.busy and self.clock()<self.end_time
    def fadeout(self,ms):self.busy=False
    def set_volume(self,value):self.level=value

class FakeMixer:
    def __init__(self):self.channels=[FakeChannel() for _ in range(9)]
    def pre_init(self,**kwargs):pass
    def init(self):pass
    def set_num_channels(self,n):self.num_channels=n
    def Channel(self,i):return self.channels[i]
    def Sound(self,buffer):return FakeSound(buffer)
    def quit(self):pass

class AudioPlaybackTests(unittest.TestCase):
    def setUp(self):
        self.mixer=FakeMixer()
        self.now=10.
        with patch.dict(sys.modules,{'pygame':types.SimpleNamespace(mixer=self.mixer)}):
            self.engine=AudioEngine(ROOT/'assets/sounds')
        self.engine.clock=lambda:self.now
        for ch in self.mixer.channels:ch.clock=self.engine.clock

    def advance(self,seconds):
        for _ in range(round(seconds/.05)):
            self.now+=.05
            self.engine.tick()

    def count(self,mode):
        return sum(len(ch.plays) for ch in self.engine.layers[mode].channels)

    def test_original_audio_bit_exact_neutral(self):
        for ident in ('pencil_long_08a','brush_velvet_fav_15_01','eraser_medium_25'):
            pcm=self.engine._load_pcm('curated/'+ident+'.wav')
            self.assertTrue(np.array_equal(pcm,_pitch_and_speed(pcm,100,0,0)))
            self.assertEqual(self.engine._sound(ident,'held').nbytes,len(pcm)*2)

    def test_no_timed_restart_on_90_second_straight_drag_in_any_mode(self):
        for mode in self.engine.MODES:
            with self.subTest(mode=mode):
                self.engine.begin_stroke(mode,'auto')
                self.engine.update_motion(350)
                self.advance(90)
                self.assertEqual(self.count(mode),1)
                self.assertTrue(all(k.get('loops')==0 for ch in self.engine.layers[mode].channels for k in ch.plays))
                self.engine.stop_stroke()

    def test_no_audio_relaunch_on_direction_update(self):
        self.engine.begin_stroke('brush','auto')
        for i in range(100):
            self.engine.update_direction(35,2 if i%2 else 35)
            self.advance(.05)
        self.assertEqual(self.count('brush'),1)

    def test_actual_brush_pass_can_trigger_one_new_oneshot(self):
        self.engine.begin_stroke('brush','auto')
        before=self.engine.layers['brush'].current_id
        self.engine.gesture_turn('vertical')
        self.assertEqual(self.count('brush'),2)
        self.assertNotEqual(self.engine.layers['brush'].current_id,before)
        self.advance(10)
        self.assertEqual(self.count('brush'),2)

    def test_eraser_new_pass_can_trigger_one_new_oneshot(self):
        self.engine.begin_stroke('eraser','auto')
        self.engine.gesture_turn('horizontal')
        self.assertEqual(self.count('eraser'),2)
        self.advance(15)
        self.assertEqual(self.count('eraser'),2)

    def test_manual_selected_sound_never_restarts_on_turns(self):
        self.engine.begin_stroke('brush','brush_velvet_fav_15_01')
        self.assertFalse(self.engine.gesture_turn('vertical'))
        self.advance(10)
        self.assertEqual(self.count('brush'),1)

    def test_pencil_never_turns_or_restarts(self):
        self.engine.begin_stroke('pencil','auto')
        self.assertFalse(self.engine.gesture_turn('horizontal'))
        self.advance(16)
        self.assertEqual(self.count('pencil'),1)

    def test_no_overlapping_loop_pipelines(self):
        self.engine.begin_stroke('brush','auto')
        self.assertEqual(self.count('brush'),1)
        self.assertFalse(any(ch.plays for ch in self.mixer.channels[4:8]))
        self.engine.stop_stroke()

    def test_new_mouse_stroke_can_start_again(self):
        self.engine.begin_stroke('pencil','auto')
        self.assertFalse(self.engine.begin_stroke('pencil','auto'))
        self.engine.stop_stroke()
        self.assertTrue(self.engine.begin_stroke('pencil','auto'))
        self.assertEqual(self.count('pencil'),2)

    def test_volume_and_tone_independent(self):
        oldb=self.engine.effects['brush'].copy();olde=self.engine.effects['eraser'].copy()
        self.engine.set_effect('pencil','volume',40)
        self.engine.set_effect('pencil','pitch',2)
        self.assertEqual(self.engine.effects['brush'],oldb)
        self.assertEqual(self.engine.effects['eraser'],olde)

    def test_preview_play_once(self):
        self.engine.preview('brush','brush_velvet_fav_15_01')
        self.assertEqual(self.mixer.channels[8].plays[-1]['loops'],0)

if __name__=='__main__':unittest.main()
