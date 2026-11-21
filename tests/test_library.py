"""Curated library checks for P, B/J and E."""
import ast, json, unittest, wave, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOUNDS=ROOT/'assets'/'sounds'
class LibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples=json.loads((SOUNDS/'library.json').read_text(encoding='utf8'))['samples']
    def test_catalogue(self):
        self.assertEqual(len(self.samples),17)
        self.assertEqual({c:sum(s['category']==c for s in self.samples) for c in ('pencil','brush','eraser')},{'pencil':11,'brush':4,'eraser':2})
        self.assertEqual(len({s['id'] for s in self.samples}),17)
        self.assertTrue(all(s['source']=='ElevenLabs (usuario)' for s in self.samples))
        self.assertTrue(all(s['kind']=='curated_real_recording_no_stretch' for s in self.samples))
        self.assertTrue(all(s['preview_file']==s['file'] for s in self.samples))
    def test_wavs_duration_and_rate(self):
        for s in self.samples:
            with self.subTest(name=s['id']),wave.open(str(SOUNDS/s['file']),'rb') as f:
                self.assertEqual((f.getframerate(),f.getnchannels(),f.getsampwidth()),(44100,1,2))
                self.assertAlmostEqual(f.getnframes()/44100,s['duration_sec'],delta=.003)
                self.assertLessEqual(f.getnframes()/44100,8.1)
    def test_only_curated_sounds(self):
        wavs={str(x.relative_to(SOUNDS)).replace('\\','/') for x in SOUNDS.rglob('*.wav')}
        self.assertEqual(wavs,{s['file'] for s in self.samples})
    def test_auto_selection_prioritizes_long_p_and_excludes_rough_audio(self):
        auto=[s for s in self.samples if s['auto_eligible'] and s['category']=='pencil']
        self.assertEqual(len(auto),5)
        self.assertTrue(all(s['duration_sec']>=4.8 for s in auto))
        self.assertTrue(all(s['loop']==(s['category']=='brush') for s in self.samples))
    def test_only_brush_loops(self):
        src=(ROOT/'app/audio.py').read_text(encoding='utf8')
        self.assertIn("loops=(-1 if category=='brush' else 0)",src)
        self.assertNotIn('_continuous_friction',src)
    def test_source_parses(self):
        for p in (ROOT/'app').glob('*.py'):ast.parse(p.read_text(encoding='utf8'),filename=str(p))
    def test_logo_untouched(self):
        self.assertEqual(hashlib.sha256((ROOT/'assets/icon.png').read_bytes()).hexdigest(),'cc0b3472c8832cd2cbdfe043a68812f20cd02acf224c58c0870be78e9d862778')
if __name__=='__main__':unittest.main()
