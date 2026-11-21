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
        self.assertEqual(len(self.samples),44)
        self.assertEqual({c:sum(s['category']==c for s in self.samples) for c in ('pencil','brush','eraser')},{'pencil':16,'brush':22,'eraser':6})
        self.assertEqual(len({s['id'] for s in self.samples}),44)
        self.assertTrue(all(s['source']=='ElevenLabs (usuario)' for s in self.samples))
        self.assertTrue(all(s['kind']=='curated_real_recording_no_stretch' for s in self.samples))
        self.assertTrue(all(s['preview_file']==s['file'] for s in self.samples))
    def test_wavs_duration_and_rate(self):
        for s in self.samples:
            with self.subTest(name=s['id']),wave.open(str(SOUNDS/s['file']),'rb') as f:
                self.assertEqual((f.getframerate(),f.getnchannels(),f.getsampwidth()),(44100,1,2))
                self.assertAlmostEqual(f.getnframes()/44100,s['duration_sec'],delta=.003)
                self.assertLessEqual(f.getnframes()/44100,9.6 if s['id']=='brush_fast_velvet_10' else 8.1)
    def test_only_curated_sounds(self):
        wavs={str(x.relative_to(SOUNDS)).replace('\\','/') for x in SOUNDS.rglob('*.wav')}
        self.assertEqual(wavs,{s['file'] for s in self.samples})
    def test_auto_selection_prioritizes_long_p_and_excludes_rough_audio(self):
        auto=[s for s in self.samples if s['auto_eligible'] and s['category']=='pencil']
        self.assertEqual(len(auto),5)
        self.assertTrue(all(s['duration_sec']>=4.8 for s in auto))
        self.assertTrue(all(s['loop'] is False for s in self.samples if s['category'] != 'brush'))
        self.assertEqual([s['id'] for s in self.samples if s.get('loop')], ['brush_fast_velvet_10'])
    def test_four_favorites_are_retained_and_in_automatic_directional_mode(self):
        expected={f'brush_velvet_fav_15_{i:02d}' for i in range(1,5)}
        samples={s['id']:s for s in self.samples}
        self.assertTrue(expected.issubset(samples))
        self.assertTrue(all(samples[s]['auto_eligible'] for s in expected))
        self.assertEqual({samples[s]['direction'] for s in expected},{'horizontal','vertical'})
        self.assertTrue(all(samples[s].get('favorite') for s in expected))
        self.assertTrue(all(s.get('direction_role')=='mezcla_sonica_asignada_no_direccion_documentada' for s in self.samples if s.get('direction')))

    def test_continuous_texture_uses_original_recordings_without_fixed_wav_loops(self):
        src=(ROOT/'app/audio.py').read_text(encoding='utf8')
        self.assertIn('class GrainBank:',src)
        self.assertIn('class SeamlessBrushLoop:',src)
        self.assertIn('class AudioEngine:',src)
        self.assertIn('sounddevice',src)
        self.assertNotIn('play(snd, loops=-1',src)
        self.assertNotIn('_continuous_friction',src)
        self.assertNotIn('_sustain_body',src)
        self.assertNotIn('self.next_end',src)
    def test_source_parses(self):
        for p in (ROOT/'app').glob('*.py'):ast.parse(p.read_text(encoding='utf8'),filename=str(p))
    def test_logo_untouched(self):
        self.assertEqual(hashlib.sha256((ROOT/'assets/icon.png').read_bytes()).hexdigest(),'042ce253a146d9b75e77fa68ef5044ba1f4b02d50c53e129c88a4dca4819d34b')
if __name__=='__main__':unittest.main()
