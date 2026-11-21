"""Safety checks for the scroll-wheel bug and mixer controls."""
from pathlib import Path
import unittest,ast
ROOT=Path(__file__).resolve().parents[1]
class UIChecks(unittest.TestCase):
    def test_wheel_never_selects_another_sample(self):
        src=(ROOT/'app/ui.py').read_text(encoding='utf8')
        self.assertIn('class SafeComboBox(QComboBox)',src)
        self.assertIn('def wheelEvent(self,event):',src)
        self.assertIn('event.ignore()',src)
        self.assertIn('combo=SafeComboBox()',src)
    def test_original_png_bundled_for_application(self):
        workflow=(ROOT/'.github/workflows/build-windows.yml').read_text(encoding='utf8')
        source=(ROOT/'app/main.py').read_text(encoding='utf8')
        self.assertIn('assets/icon.png;assets',workflow)
        self.assertIn("original_png=resource('assets/icon.png')",source)
        self.assertIn("icon=resource('assets/icon.png')",source)
    def test_separate_panels_and_tone_reset_for_p_b_e(self):
        src=(ROOT/'app/ui.py').read_text(encoding='utf8')
        self.assertIn("self.mix_sliders[setting]=slider",src)
        self.assertIn("self.audio.set_effect(mode,param,value)",src)
        self.assertIn("def _restore_original_tone(self,mode)",src)
        self.assertIn("self.original_tone_buttons[mode]=restore",src)

    def test_settings_persist_independently(self):
        src=(ROOT/'app/config.py').read_text(encoding='utf8')
        self.assertIn("DEFAULTS[f'{mode}_{param}']=initial",src)
        self.assertIn("'per_tool_controls_v1':True",src)
        self.assertIn("settings[key]=max(lo,min(hi,settings[key]))",src)
if __name__=='__main__':unittest.main()
