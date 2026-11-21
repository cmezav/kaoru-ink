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
    def test_effect_settings_persist(self):
        src=(ROOT/'app/config.py').read_text(encoding='utf8')
        tree=ast.parse(src)
        assign=next(node for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DEFAULTS' for t in node.targets))
        keys=[k.value for k in assign.value.keys]
        for key in ('volume','speed','pitch','brightness','dynamics','pencil_volume','brush_volume','eraser_volume'):
            self.assertIn(key,keys)
if __name__=='__main__':unittest.main()
