import ast
import json
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'assets' / 'sounds'

class LibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = json.loads((FOLDER / 'library.json').read_text(encoding='utf-8'))
        cls.samples = cls.library['samples']

    def test_all_sound_files_valid(self):
        self.assertGreaterEqual(len(self.samples), 40)
        self.assertEqual(len(self.samples),len({s['id'] for s in self.samples}))
        for s in self.samples:
            with self.subTest(sample=s['id']):
                path = FOLDER / s['file']
                self.assertTrue(path.is_file())
                with wave.open(str(path), 'rb') as wf:
                    self.assertEqual(wf.getframerate(),44100)
                    self.assertEqual(wf.getnchannels(),1)
                    self.assertEqual(wf.getsampwidth(),2)
                    self.assertGreater(wf.getnframes(),4410)

    def test_categories(self):
        by_cat = {c:sum(s['category']==c for s in self.samples) for c in ('short','medium','long','brush')}
        self.assertGreaterEqual(by_cat['short'],30)
        self.assertGreaterEqual(by_cat['medium'],10)
        self.assertGreaterEqual(by_cat['long'],10)
        self.assertGreaterEqual(by_cat['brush'],10)
        self.assertTrue(all(s['loop'] == (s['category']=='brush') for s in self.samples))

    def test_requested_seven_second_favorite(self):
        favorites = [s for s in self.samples if s.get('favorite')]
        self.assertGreaterEqual(len(favorites),6)
        self.assertTrue(any(s['source']=='pencil' and 7 <= s['start_sec'] <= 8 and s['category']=='long' for s in favorites))

    def test_sources_not_in_repo(self):
        # The distribution contains only trimmed/processed audio, not the originals.
        self.assertFalse(list(ROOT.glob('*.mp3')))

    def test_source_parses(self):
        for path in (ROOT/'app').glob('*.py'):
            ast.parse(path.read_text(encoding='utf-8'), filename=str(path))

if __name__=='__main__': unittest.main()
