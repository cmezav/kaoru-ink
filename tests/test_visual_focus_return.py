"""Focus-return regression tests for CSP without requiring Windows or Qt."""
import ast
import time
import unittest
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / 'app' / 'ui.py').read_text(encoding='utf8')
TREE = ast.parse(SOURCE)
MAIN = next(x for x in TREE.body if isinstance(x, ast.ClassDef) and x.name == 'MainWindow')

def method(name):
    fn = next(x for x in MAIN.body if isinstance(x, ast.FunctionDef) and x.name == name)
    module = ast.Module(body=[fn], type_ignores=[])
    context = {'foreground_paint':lambda:True, 'time':time}
    exec(compile(module, '<test_ui_focus>', 'exec'),context)
    return context[name]

class FakeDetector:
    def __init__(self):
        self.reset_count=0
        self.reason='B -> brush'
    def reset(self):self.reset_count+=1
    def snapshot_mode(self,focus):
        assert focus
        return 'brush'
    def toolbar_click_mode(self,x,y,focus):
        assert focus
        return 'brush'

class FakeController:
    def __init__(self):
        self.active=False
        self.mode='pencil'
        self.down=[]
    def mouse_down(self,x,y): self.down.append((x,y))

class FakeLabel:
    def setText(self,msg):self.text=msg

class FakeWindow:
    def __init__(self):
        self.focused=False
        self.muted=False
        self.controller=FakeController()
        self.visual_detector=FakeDetector()
        self.visual_keyboard_until=time.monotonic()+1
        self.visual_status=FakeLabel()
        self.status_calls=0
    def _update_status(self):self.status_calls+=1
    def _set_mode(self,mode):self.controller.mode=mode

class FocusReturnTests(unittest.TestCase):
    def test_first_pen_down_after_focus_return_uses_b(self):
        w=FakeWindow()
        method('_on_down')(w,300,400)
        self.assertTrue(w.focused)
        self.assertEqual(w.controller.mode,'brush')
        self.assertEqual(w.controller.down,[(300,400)])
        self.assertEqual(w.visual_detector.reset_count,1)
    def test_toolbar_click_after_focus_return_selects_b(self):
        w=FakeWindow()
        method('_on_toolbar_click')(w,25,222)
        self.assertTrue(w.focused)
        self.assertEqual(w.controller.mode,'brush')
    def test_delayed_resync_after_return(self):
        w=FakeWindow();w.focused=True
        method('_resync_focus')(w)
        self.assertEqual(w.controller.mode,'brush')
    def test_does_not_change_during_active_stroke(self):
        w=FakeWindow();w.focused=True;w.controller.active=True
        method('_resync_focus')(w)
        self.assertEqual(w.controller.mode,'pencil')
    def test_timing_refresh_and_timer_are_present(self):
        text=ast.get_source_segment(SOURCE,next(x for x in MAIN.body if isinstance(x,ast.FunctionDef) and x.name=='_tick'))
        self.assertIn('QTimer.singleShot(180,self._resync_focus)',text)
        self.assertIn('self.visual_detector.reset()',text)

if __name__=='__main__':unittest.main()
