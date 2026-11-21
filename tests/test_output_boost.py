"""Global volume boost must preserve the waveform at 0 dB and mode logic."""
import unittest, numpy as np
from pathlib import Path
from app.audio import AudioEngine

class FakeStream:
    def start(self): pass
    def stop(self): pass
    def close(self): pass

def engine():
    root=Path(__file__).resolve().parents[1]/'assets'/'sounds'
    return AudioEngine(root,stream_factory=lambda _:FakeStream())

class OutputBoostTests(unittest.TestCase):
    def test_audio_content_is_unchanged_except_output_amplitude(self):
        for tool in ('pencil','brush','eraser'):
            with self.subTest(tool=tool):
                a=engine(); b=engine()
                for e in (a,b):
                    e.rng.seed(1234)
                    self.assertTrue(e.begin_stroke(tool,'auto'))
                    e.update_motion(270.)
                b.set_output_boost(8)
                output_a=a._render(8192)
                output_b=b._render(8192)
                self.assertGreater(np.max(np.abs(output_a)),0)
                # Recordings are quiet, so the ceiling does not activate here.
                ratio=10. ** (8/20.)
                np.testing.assert_allclose(output_b,output_a*ratio,rtol=1e-5,atol=1e-6)
                self.assertEqual(a.active_mode,b.active_mode)
                self.assertEqual(a.rendered_frames,b.rendered_frames)
                a.close(); b.close()

    def test_limits_and_default(self):
        a=engine()
        self.assertEqual(a.output_boost_db,0)
        a.set_output_boost(100)
        self.assertEqual(a.output_boost_db,12)
        a.set_output_boost(-55)
        self.assertEqual(a.output_boost_db,0)
        a.close()

if __name__=='__main__':unittest.main()
