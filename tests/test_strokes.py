"""Test stroke semantics without requiring PySide6 on a Linux build host."""
import ast
import math
import time
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / 'app' / 'input_monitor.py'
parsed = ast.parse(SRC.read_text(encoding='utf8'), filename=str(SRC))
controller_ast = next(node for node in parsed.body
                      if isinstance(node, ast.ClassDef) and node.name == 'StrokeController')
namespace = {'time': time, 'hypot': math.hypot}
exec(compile(ast.Module(body=[controller_ast], type_ignores=[]), str(SRC), 'exec'), namespace)
Controller = namespace['StrokeController']


class FakeAudio:
    def __init__(self):
        self.pencil_starts = 0
        self.loops = []
        self.stops = 0
        self.brush_stops = 0

    def start_pencil(self, *args):
        self.pencil_starts += 1

    def start_loop(self, category, desired):
        self.loops.append(category)

    def stop_stroke(self):
        self.stops += 1

    def stop_brush(self):
        self.brush_stops += 1

    def stop_all(self):
        self.stops += 1


class StrokeTests(unittest.TestCase):
    def setUp(self):
        self.audio = FakeAudio()
        self.settings = {'short_id':'auto', 'medium_id':'auto',
                         'long_id':'auto', 'brush_id':'auto'}
        self.controller = Controller(self.audio, self.settings)

    def test_pencil_only_one_play_even_for_very_long_stroke(self):
        c = self.controller
        c.mouse_down(100, 100)
        for x in range(110, 3000, 10):
            c.mouse_move(x, 100)
        self.assertEqual(self.audio.pencil_starts, 1)
        self.assertEqual(self.audio.loops, [])
        c.mouse_up()
        c.mouse_down(100, 100)
        c.mouse_move(125, 100)
        self.assertEqual(self.audio.pencil_starts, 2)

    def test_pencil_paused_does_not_play_second_sound(self):
        c = self.controller
        c.mouse_down(0, 0)
        c.mouse_move(100, 0)
        c.last_motion = time.monotonic() - .5
        c.tick(True)
        c.mouse_move(200, 0)
        self.assertEqual(self.audio.pencil_starts, 1)
        self.assertEqual(self.audio.loops, [])

    def test_brush_is_the_only_mode_that_loops(self):
        c = self.controller
        c.change_mode('brush')
        c.mouse_down(0, 0)
        for x in range(10, 100, 10):
            c.mouse_move(x, 0)
        self.assertEqual(self.audio.loops, ['brush'])
        c.last_motion = time.monotonic() - .5
        c.tick(True)
        self.assertEqual(self.audio.brush_stops, 1)
        c.mouse_move(150, 0)
        self.assertEqual(self.audio.loops, ['brush', 'brush'])

    def test_sound_resets_on_focus_loss(self):
        c = self.controller
        c.mouse_down(0, 0)
        c.mouse_move(30, 0)
        c.tick(False)
        c.mouse_move(40, 0)
        self.assertEqual(self.audio.pencil_starts, 1)
        self.assertFalse(c.active)


if __name__ == '__main__':
    unittest.main()
