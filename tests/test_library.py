"""Validate all CC0 sounds and ensure source clips cannot loop."""
import ast,json,unittest,wave,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOUNDS=ROOT/'assets'/'sounds'

class LibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.samples=json.loads((SOUNDS/'library.json').read_text(encoding='utf8'))['samples']
    def test_catalogue(self):
        self.assertEqual(len(self.samples),24)
        self.assertEqual({c:sum(s['category']==c for s in self.samples) for c in ('pencil','brush','eraser')},{'pencil':12,'brush':9,'eraser':3})
        self.assertTrue(all(s['loop'] is False for s in self.samples))
        self.assertEqual(len(set(s['id'] for s in self.samples)),24)
        self.assertTrue(all(s['source'] in ('SFX Kit','UI SFX') for s in self.samples))
    def test_all_audio_22050_mono(self):
        for sample in self.samples:
            for key in ('file','preview_file'):
                p=SOUNDS/sample[key]
                with self.subTest(name=str(p)):
                    with wave.open(str(p),'rb') as wav:
                        self.assertEqual((wav.getframerate(),wav.getnchannels(),wav.getsampwidth()),(22050,1,2))
                        self.assertGreater(wav.getnframes(),3000)
                        if key=='file':self.assertGreater(wav.getnframes()/22050,25)
                        else:self.assertLess(wav.getnframes()/22050,.6)
    def test_no_previous_audio(self):
        actual={str(p.relative_to(SOUNDS)).replace('\\','/') for p in SOUNDS.rglob('*.wav')}
        expected={s[key] for s in self.samples for key in ('file','preview_file')}
        self.assertEqual(actual,expected)
    def test_no_loop_commands(self):
        audio=(ROOT/'app/audio.py').read_text(encoding='utf8')
        self.assertNotIn('loops=-1',audio)
        self.assertNotIn('start_loop',audio)
        self.assertIn('loops=0',audio)
    def test_source_parses(self):
        for p in list((ROOT/'app').glob('*.py')) + [ROOT/'tools/import_public_sfx.py']:
            ast.parse(p.read_text(encoding='utf8'),filename=str(p))
    def test_logo_is_original_png(self):
        # Original uploaded blue note (unaltered, byte for byte).
        original='cc0b3472c8832cd2cbdfe043a68812f20cd02acf224c58c0870be78e9d862778'
        self.assertEqual(hashlib.sha256((ROOT/'assets/icon.png').read_bytes()).hexdigest(),original)

if __name__=='__main__':unittest.main()
