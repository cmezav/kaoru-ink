"""Regression tests for faster and more robust visual tool recognition."""
import unittest
from unittest.mock import patch
from app.visual_csp import (
    CspVisualDetector, VisualStabilizer, TOOL_POINTS, X_POINTS,
    Y_OFFSETS, choose_tool, mode_for_key, is_selected_rgb,
)


class VisualToolTests(unittest.TestCase):
    def test_both_pen_icons_same_mode(self):
        self.assertEqual(mode_for_key('P1'), 'pencil')
        self.assertEqual(mode_for_key('P2'), 'pencil')
        self.assertEqual(mode_for_key('B'), 'brush')
        self.assertEqual(mode_for_key('J'), 'brush')
        self.assertEqual(mode_for_key('E'), 'eraser')

    def test_reads_more_than_nine_pixels_per_icon(self):
        self.assertEqual(len(X_POINTS)*len(Y_OFFSETS), 24)
        self.assertEqual(len(TOOL_POINTS), 5)

    def test_recognizes_true_selection_even_when_old_nine_pixel_sample_weak(self):
        for key, confidence in [('P1',20),('P2',19),('B',21),('J',14),('E',14)]:
            scores = {name:0 for name,_,_ in TOOL_POINTS}
            scores[key] = confidence
            self.assertEqual(choose_tool(scores), key)
        self.assertIsNone(choose_tool({'E':3}))
        self.assertIsNone(choose_tool({'P1':17, 'B':16}))

    def test_selected_rgb(self):
        self.assertTrue(is_selected_rgb((96,106,128)))
        self.assertFalse(is_selected_rgb((63,63,63)))
        self.assertFalse(is_selected_rgb((225,225,225)))

    def test_debounce(self):
        s=VisualStabilizer()
        self.assertIsNone(s.feed('P2'))
        self.assertEqual(s.feed('P2'), 'pencil')
        self.assertIsNone(s.feed(None))
        self.assertIsNone(s.feed('B'))
        self.assertEqual(s.feed('B'), 'brush')

    def test_confident_snapshot_works_before_background_debounce(self):
        v = CspVisualDetector(enabled=True)
        scores = {'P1':0,'P2':0,'B':21,'J':0,'E':0}
        with patch.object(v, '_layout_supported', return_value=True), patch.object(v, '_read_scores',return_value=scores):
            self.assertEqual(v.snapshot_mode(True),'brush')
            self.assertEqual(v.last_key, 'B')
            self.assertIsNone(v.snapshot_mode(False))
            v.enabled=False
            self.assertIsNone(v.snapshot_mode(True))

    def test_uncertain_snapshot_does_not_force_pencil(self):
        v=CspVisualDetector(enabled=True)
        with patch.object(v,'_layout_supported',return_value=True),patch.object(v,'_read_scores',return_value={'B':8,'P1':6}):
            self.assertIsNone(v.snapshot_mode(True))

class UiIntegrationRegression(unittest.TestCase):
    def test_canvas_down_checks_visual_before_starting_audio(self):
        import ast
        src=(__import__('pathlib').Path(__file__).resolve().parents[1]/'app/ui.py').read_text(encoding='utf8')
        tree=ast.parse(src)
        main=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='MainWindow')
        fn=next(n for n in main.body if isinstance(n,ast.FunctionDef) and n.name=='_on_down')
        text=ast.get_source_segment(src,fn)
        self.assertLess(text.index('snapshot_mode('),text.index('self.controller.mouse_down(x,y)'))
        self.assertIn('self._set_mode(mode)',text)

if __name__=='__main__':unittest.main()
