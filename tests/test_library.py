"""Validate original, untuned sound recordings and byte-identical user logo."""
import ast, json, unittest, wave, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOUNDS=ROOT/'assets'/'sounds'

class LibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples=json.loads((SOUNDS/'library.json').read_text(encoding='utf8'))['samples']

    def test_catalogue(self):
        self.assertEqual(len(self.samples),24)
        self.assertEqual({c:sum(s['category']==c for s in self.samples) for c in ('pencil','brush','eraser')},
                         {'pencil':12,'brush':9,'eraser':3})
        self.assertEqual(len({s['id'] for s in self.samples}),24)
        self.assertTrue(all(s['source'] in ('SFX Kit','UI SFX') for s in self.samples))
        self.assertTrue(all(s['kind']=='natural_original_no_processing' for s in self.samples))
        self.assertTrue(all(s['preview_file']==s['file'] for s in self.samples))

    def test_all_recordings_original_duration_and_rate(self):
        for s in self.samples:
            path=SOUNDS/s['file']
            with self.subTest(name=path.name), wave.open(str(path),'rb') as f:
                self.assertEqual((f.getframerate(),f.getnchannels(),f.getsampwidth()),(44100,1,2))
                self.assertAlmostEqual(f.getnframes()/44100,s['duration_sec'],delta=.003)
                self.assertGreater(f.getnframes()/44100,.2)
                self.assertLess(f.getnframes()/44100,2)

    def test_no_generated_26_second_pads(self):
        wavs={str(x.relative_to(SOUNDS)).replace('\\','/') for x in SOUNDS.rglob('*.wav')}
        self.assertEqual(wavs,{s['file'] for s in self.samples})
        self.assertFalse((SOUNDS/'held').exists() and any((SOUNDS/'held').glob('*.wav')))

    def test_only_brush_loops(self):
        audio=(ROOT/'app/audio.py').read_text(encoding='utf8')
        self.assertIn("loops=(-1 if category=='brush' else 0)",audio)
        self.assertIn('if kind==\'loop\':pcm=_brush_loop(pcm)',audio)

    def test_source_parses(self):
        for p in list((ROOT/'app').glob('*.py')) + [ROOT/'tools/import_public_sfx.py']:
            ast.parse(p.read_text(encoding='utf8'),filename=str(p))

    def test_logo_untouched(self):
        original='cc0b3472c8832cd2cbdfe043a68812f20cd02acf224c58c0870be78e9d862778'
        self.assertEqual(hashlib.sha256((ROOT/'assets/icon.png').read_bytes()).hexdigest(),original)

if __name__=='__main__':unittest.main()
