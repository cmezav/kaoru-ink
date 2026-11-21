"""Visual tool sync is conservative and must not touch audio functionality."""
import unittest
from app.visual_csp import TOOL_POINTS, VisualStabilizer, choose_tool, mode_for_key, is_selected_rgb

class VisualToolTests(unittest.TestCase):
    def test_two_pen_icons_share_one_pencil_mode(self):
        self.assertEqual(mode_for_key('P1'), 'pencil')
        self.assertEqual(mode_for_key('P2'), 'pencil')
        self.assertEqual(mode_for_key('B'), 'brush')
        self.assertEqual(mode_for_key('J'), 'brush')
        self.assertEqual(mode_for_key('E'), 'eraser')

    def test_low_confidence_E_is_rejected(self):
        # Actual user's v2 report had one E reading with only 3/9.
        self.assertIsNone(choose_tool({'E': 3}))
        self.assertEqual(choose_tool({'E': 5}), 'E')

    def test_ambiguous_two_selected_buttons_are_rejected(self):
        self.assertIsNone(choose_tool({'P1':6, 'P2':5}))
        self.assertIsNone(choose_tool({'P1':5, 'E':4}))
        self.assertEqual(choose_tool({'B':4, 'P1':1}), 'B')
        self.assertEqual(choose_tool({'B':7, 'P1':1}), 'B')

    def test_selected_highlight_detected(self):
        self.assertTrue(is_selected_rgb((96, 106, 128)))
        self.assertFalse(is_selected_rgb((63, 63, 63)))
        self.assertFalse(is_selected_rgb((225, 225, 225)))

    def test_requires_three_consecutive_reads(self):
        x = VisualStabilizer()
        self.assertIsNone(x.feed('P2'))
        self.assertIsNone(x.feed('P2'))
        self.assertEqual(x.feed('P2'), 'pencil')
        self.assertIsNone(x.feed(None))
        self.assertIsNone(x.feed('E'))
        self.assertIsNone(x.feed('E'))
        self.assertEqual(x.feed('E'), 'eraser')
        x.reset()
        self.assertIsNone(x.feed('E'))

    def test_no_audio_imported(self):
        import inspect,app.visual_csp
        s=inspect.getsource(app.visual_csp)
        self.assertNotIn('from .audio import',s)
        self.assertNotIn('from app.audio import',s)

if __name__=='__main__':unittest.main()
