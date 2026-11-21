"""Real-time texture tests: sustained movement, tone, pressure and direction."""
import unittest
from pathlib import Path
import numpy as np
from app.audio import AudioEngine, _pitch_and_speed, GrainBank, RATE

ROOT=Path(__file__).resolve().parents[1]

class FakeStream:
    def __init__(self,callback):self.callback=callback;self.started=False
    def start(self):self.started=True
    def stop(self):self.started=False
    def close(self):self.closed=True

class PlaybackTests(unittest.TestCase):
    def setUp(self):
        self.engine=AudioEngine(ROOT/'assets/sounds',stream_factory=FakeStream)
        self.now=100.
        self.engine.clock=lambda:self.now

    def tearDown(self):self.engine.close()

    def render(self,frames=1024):
        output=np.zeros((frames,1),dtype='float32')
        self.engine._callback(output,frames,None,None)
        self.now+=frames/RATE
        return output[:,0].copy()

    def test_neutral_original_samples_not_resampled(self):
        for ident in ('pencil_long_08a','brush_velvet_fav_15_01','eraser_medium_25'):
            pcm=self.engine._load_pcm('curated/'+ident+'.wav')
            self.assertTrue(np.array_equal(pcm,_pitch_and_speed(pcm,100,0,0)))

    def test_uninterrupted_25_second_drag_each_mode(self):
        for mode in ('pencil','brush','eraser'):
            with self.subTest(mode=mode):
                self.assertTrue(self.engine.begin_stroke(mode,'auto'))
                self.engine.update_motion(480)
                chunks=[]
                for _ in range(round(25*RATE/4096)):
                    chunks.append(self.render(4096))
                # The audio remains present near the end of long strokes.
                last=np.concatenate(chunks[-6:])
                self.assertGreater(np.sqrt(np.mean(last*last)),.001)
                self.assertGreater(self.engine.rendered_frames,24*RATE)
                self.engine.stop_stroke()
                for _ in range(10):self.render(4096)
                self.assertIsNone(self.engine.active_mode)

    def test_sustained_90_seconds_without_source_expiration(self):
        for mode in ('pencil','brush','eraser'):
            self.engine.begin_stroke(mode,'auto')
            self.engine.update_motion(460)
            tail=[]
            for n in range(round(90*RATE/8192)):
                out=self.render(8192)
                if n>round(85*RATE/8192):tail.append(out)
            self.assertGreater(np.sqrt(np.mean(np.concatenate(tail)**2)),.001)
            self.engine.stop_stroke()
            for _ in range(4):self.render(8192)
            self.assertIsNone(self.engine.active_mode)

    def test_new_gesture_after_release(self):
        self.engine.begin_stroke('pencil','auto')
        self.engine.update_motion(300)
        self.render(4096)
        self.engine.stop_stroke()
        for _ in range(8):self.render(4096)
        self.assertTrue(self.engine.begin_stroke('pencil','auto'))

    def test_pressure_drives_volume_and_source_is_honest(self):
        self.engine.begin_stroke('eraser','auto')
        self.engine.update_motion(380)
        self.engine.set_pressure(.15,True)
        self.assertEqual(self.engine.real_packet_count,1)
        self.assertAlmostEqual(self.engine.last_real_pressure,.15)
        self.assertEqual(self.engine.pressure_source,'movimiento')
        low=self.engine._strength()
        self.assertEqual(self.engine.pressure_source,'wintab')
        self.engine.set_pressure(.95,True)
        high=self.engine._strength()
        self.assertGreater(high,low*1.7)
        self.now+=1.
        self.engine.tick()
        self.assertFalse(self.engine.real_pressure)
        self.engine._strength()
        self.assertEqual(self.engine.pressure_source,'movimiento')

    def test_direction_changes_gain_without_a_retrigger(self):
        self.engine.begin_stroke('brush','auto')
        self.engine.update_motion(450)
        for _ in range(4):self.render(4096)
        before=self.engine.banks['horizontal']
        self.engine.update_direction(0,35)
        for _ in range(4):self.render(4096)
        self.assertIs(self.engine.banks['horizontal'],before)
        self.assertGreater(self.engine.axis_mix,.5)
        self.engine.gesture_turn('horizontal')
        for _ in range(4):self.render(4096)
        self.assertLess(self.engine.axis_mix,.8)

    def test_motion_pause_fades_and_resume_same_live_gesture(self):
        self.engine.begin_stroke('pencil','auto')
        self.engine.update_motion(300)
        for _ in range(5):self.render(4096)
        self.engine.update_motion(0)
        for _ in range(9):quiet=self.render(4096)
        self.assertLess(np.max(np.abs(quiet)),.004)
        original=self.engine.banks['main']
        self.engine.update_motion(300)
        for _ in range(8):loud=self.render(4096)
        self.assertGreater(np.sqrt(np.mean(loud*loud)),.001)
        self.assertIs(self.engine.banks['main'],original)

    def test_preview_still_plays_single_original_sample(self):
        self.engine.preview('brush','brush_velvet_fav_15_01')
        self.assertEqual(self.engine.preview_mode,'brush')
        self.assertEqual(len(self.engine.preview_pcm),self.engine._load_pcm('curated/brush_velvet_fav_15_01.wav').size)

    def test_separate_settings(self):
        before_b=self.engine.effects['brush'].copy()
        before_e=self.engine.effects['eraser'].copy()
        self.engine.set_effect('pencil','volume',45)
        self.engine.set_effect('pencil','dynamics',95)
        self.assertEqual(before_b,self.engine.effects['brush'])
        self.assertEqual(before_e,self.engine.effects['eraser'])

    def test_auto_uses_multiple_recordings_in_one_drag(self):
        self.engine.begin_stroke('brush','auto')
        self.engine.update_motion(500)
        for _ in range(170):self.render(4096)
        used=self.engine.banks['horizontal'].used_ids | self.engine.banks['vertical'].used_ids
        self.assertGreaterEqual(len(used),4)
        self.assertTrue(set(['brush_velvet_fav_15_01','brush_velvet_fav_15_02','brush_velvet_fav_15_03','brush_velvet_fav_15_04']) & used)

    def test_manual_one_clip_is_manual(self):
        ident='pencil_warm_10_02'
        self.engine.begin_stroke('pencil',ident)
        self.engine.update_motion(420)
        for _ in range(200):self.render(1024)
        self.assertEqual(self.engine.banks['main'].used_ids,{ident})

if __name__=='__main__':unittest.main()
