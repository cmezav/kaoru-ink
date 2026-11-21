"""Prove that the previous noisy brush library was removed."""
import ast
import json
import unittest
import wave
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'assets'/'sounds'

class LibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples=json.loads((FOLDER/'library.json').read_text(encoding='utf8'))['samples']

    def test_audio_files(self):
        self.assertGreaterEqual(len(self.samples),18)
        for s in self.samples:
            with self.subTest(s=s['id']):
                with wave.open(str(FOLDER/s['file']),'rb') as wav:
                    self.assertEqual((wav.getframerate(),wav.getnchannels(),wav.getsampwidth()),(44100,1,2))
                    self.assertGreater(wav.getnframes(),4000)

    def test_single_pencil_scrape_source(self):
        pencil=[s for s in self.samples if s['category']=='pencil']
        self.assertGreaterEqual(len(pencil),12)
        self.assertTrue(all(s['source']=='pencil' and not s['loop'] for s in pencil))
        # Only a single 0.10-0.14 second source event per sample; NO multi-stroke source.
        self.assertTrue(all(s['end_sec']-s['start_sec']<=0.14 for s in pencil))
        self.assertTrue(any(s['favorite'] and 7.6<s['start_sec']<8 for s in pencil))

    def test_no_noisy_paint_file(self):
        brush=[s for s in self.samples if s['category']=='brush']
        self.assertEqual(len(brush),4)
        self.assertTrue(all(s['source']=='drawing' and s['loop'] for s in brush))
        self.assertFalse(list(FOLDER.glob('paint_loop*')))
        self.assertEqual(len(list(FOLDER.glob('*.wav'))),len(self.samples))

    def test_sources_not_in_repo(self):
        self.assertFalse(list(ROOT.glob('*.mp3')))

    def test_source_parses(self):
        for p in (ROOT/'app').glob('*.py'):
            ast.parse(p.read_text(encoding='utf8'),filename=str(p))

if __name__=='__main__':unittest.main()
