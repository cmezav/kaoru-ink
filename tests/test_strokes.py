"""Verify every mouse drag fires exactly one event for P/B/E."""
import ast,math,time,unittest
from unittest.mock import patch
from pathlib import Path
SRC=Path(__file__).resolve().parents[1]/'app'/'input_monitor.py'
parsed=ast.parse(SRC.read_text(encoding='utf8'),filename=str(SRC))
cls=next(n for n in parsed.body if isinstance(n,ast.ClassDef) and n.name=='StrokeController')
ns={'time':time,'hypot':math.hypot}
exec(compile(ast.Module(body=[cls],type_ignores=[]),str(SRC),'exec'),ns)
StrokeController=ns['StrokeController']

class FakeAudio:
    def __init__(self):self.begins=[];self.stops=0;self.motion=[]
    def begin_stroke(self,*args):self.begins.append(args);return True
    def stop_stroke(self,*args):self.stops+=1
    def update_motion(self,value):self.motion.append(value)
    def stop_all(self):self.stops+=1
    def gesture_turn(self,axis):self.turns.append(axis);return True

class StrokeTests(unittest.TestCase):
    def setUp(self):
        self.audio=FakeAudio()
        self.audio.turns=[]
        self.settings={'pencil_id':'pencil_pencil_draw','brush_id':'brush_marker_draw','eraser_id':'eraser_eraser'}
        self.c=StrokeController(self.audio,self.settings)

    def test_one_sound_per_stroke_in_every_mode_even_when_very_long(self):
        for mode in ('pencil','brush','eraser'):
            self.c.change_mode(mode)
            self.c.mouse_down(0,0)
            for x in range(1,4500,5):self.c.mouse_move(x,0)
            self.assertEqual(len([x for x in self.audio.begins if x[0]==mode]),1)
            self.c.mouse_up()
        self.assertEqual(len(self.audio.begins),3)

    def test_pause_does_not_start_again_even_after_resume(self):
        for mode in ('pencil','brush','eraser'):
            self.c.change_mode(mode)
            self.c.mouse_down(0,0)
            self.c.mouse_move(70,0)
            self.c.last_motion=time.monotonic()-.5
            self.c.tick(True)
            self.c.mouse_move(140,0)
            self.c.mouse_up()
        self.assertEqual(len(self.audio.begins),3)
        self.assertTrue(any(m==0 for m in self.audio.motion))

    def test_click_without_drag_silent(self):
        self.c.mouse_down(20,20)
        self.c.mouse_up()
        self.assertEqual(self.audio.begins,[])

    def test_focus_loss_stops_and_does_not_restart(self):
        self.c.mouse_down(0,0)
        self.c.mouse_move(15,0)
        self.c.tick(False)
        self.c.mouse_move(50,0)
        self.assertEqual(len(self.audio.begins),1)
        self.assertFalse(self.c.active)

    def test_new_drag_restarts_once(self):
        for i in range(2):
            self.c.mouse_down(0,0);self.c.mouse_move(40,0);self.c.mouse_up()
        self.assertEqual(len(self.audio.begins),2)

    def test_directional_controller_tracks_xy_without_retrigger(self):
        self.audio.direction=[]
        self.audio.update_direction=lambda dx,dy:self.audio.direction.append((dx,dy))
        self.c.change_mode('brush')
        self.c.mouse_down(20,20)
        self.c.mouse_move(35,20)
        self.c.mouse_move(35,50)
        self.assertEqual(len(self.audio.begins),1)
        self.assertEqual(self.audio.direction[:2],[(15,0),(0,30)])
        self.c.mouse_up()

    def test_direction_reversal_triggers_one_new_pass_not_timer(self):
        self.c.change_mode('brush')
        with patch.object(time,'monotonic',side_effect=[100.,100.1,100.2,100.45,100.54]):
            self.c.mouse_down(0,0)
            self.c.mouse_move(20,0)
            self.c.mouse_move(55,0)
            self.c.mouse_move(55,10)
            self.c.mouse_move(55,30)
        self.assertEqual(self.audio.turns,['vertical'])
        self.assertEqual(len(self.audio.begins),1)

    def test_steady_movement_and_jitter_never_restarts(self):
        self.c.change_mode('brush')
        self.c.mouse_down(0,0)
        for x in range(5,500,5):
            self.c.mouse_move(x,0)
        self.assertEqual(self.audio.turns,[])
        self.assertEqual(len(self.audio.begins),1)

    def test_no_automatic_new_pass_for_pencil(self):
        self.c.change_mode('pencil')
        self.c.mouse_down(0,0)
        for x in range(1,201,10):self.c.mouse_move(x,0)
        for y in range(1,201,10):self.c.mouse_move(201,y)
        self.assertEqual(self.audio.turns,[])
        self.assertEqual(len(self.audio.begins),1)

    def test_keyboard_shortcuts_include_e(self):
        tree=ast.parse(SRC.read_text(encoding='utf8'))
        self.assertIn("'e':'eraser'",SRC.read_text(encoding='utf8'))
        self.assertIn("'j':'brush'",SRC.read_text(encoding='utf8'))

if __name__=='__main__':unittest.main()
