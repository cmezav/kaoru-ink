"""Protect P/E audio and recognize actual CSP toolbar button clicks."""
import ast, unittest
from pathlib import Path
from unittest.mock import patch
from app.visual_csp import CspVisualDetector
ROOT=Path(__file__).resolve().parents[1]

class ClickTests(unittest.TestCase):
    def test_five_icons_and_two_p_modes(self):
        v=CspVisualDetector(enabled=True)
        for y,expected in [(166,'pencil'),(196,'pencil'),(222,'brush'),(272,'eraser'),(340,'brush')]:
            with patch.object(v,'_layout_supported',return_value=True):
                self.assertEqual(v.toolbar_click_mode(25,y,True),expected)
        self.assertIsNone(v.toolbar_click_mode(90,222,True))
        self.assertIsNone(v.toolbar_click_mode(25,248,True))
        self.assertIsNone(v.toolbar_click_mode(25,222,False))

    def test_click_ignored_when_layout_changed_or_detector_off(self):
        v=CspVisualDetector(enabled=True)
        with patch.object(v,'_layout_supported',return_value=False):
            self.assertIsNone(v.toolbar_click_mode(25,222,True))
        v.enabled=False
        with patch.object(v,'_layout_supported',return_value=True):
            self.assertIsNone(v.toolbar_click_mode(25,222,True))

    def test_snapshot_respects_recent_click_even_with_stale_pencil_pixels(self):
        ticks=[100.0]
        v=CspVisualDetector(enabled=True,clock=lambda:ticks[0])
        with patch.object(v,'_layout_supported',return_value=True),patch.object(v,'_read_scores',return_value={'P1':21,'P2':0,'B':0,'J':0,'E':0}):
            self.assertEqual(v.toolbar_click_mode(25,222,True),'brush')
            self.assertEqual(v.snapshot_mode(True),'brush')
            self.assertIsNone(v.poll(True))

    def test_only_detection_and_catalogue_are_patched(self):
        src=(ROOT/'app/ui.py').read_text(encoding='utf8')
        self.assertIn('self.bus.toolbar_click.connect(self._on_toolbar_click)',src)
        self.assertIn('def _on_toolbar_click',src)
        self.assertIn('self._set_mode(mode)',src)
        import wave
        wav=ROOT/'assets/sounds/curated/brush_eraser_medium_25.wav'
        import hashlib
        original=ROOT/'assets/sounds/curated/eraser_medium_25.wav'
        self.assertEqual(hashlib.sha256(wav.read_bytes()).digest(),hashlib.sha256(original.read_bytes()).digest())

if __name__=='__main__':unittest.main()
