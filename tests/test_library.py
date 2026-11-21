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
        self.assertEqual(len(self.samples),47)
        self.assertEqual({c:sum(s['category']==c for s in self.samples) for c in ('pencil','brush','eraser')},{'pencil':16,'brush':25,'eraser':6})
        self.assertEqual(len({s['id'] for s in self.samples}),47)
        self.assertTrue(all(s['source']=='ElevenLabs (usuario)' for s in self.samples))
        self.assertTrue(all(s['kind']=='curated_real_recording_no_stretch' for s in self.samples if not s['id'].startswith('brush_pair_')))
        self.assertEqual({s['id'] for s in self.samples if s['id'].startswith('brush_pair_')},{'brush_pair_A','brush_pair_B','brush_pair_C'})
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
        self.assertEqual(set(s['id'] for s in self.samples if s.get('loop')), {'brush_fast_velvet_10','brush_pair_A','brush_pair_B','brush_pair_C'})
    def test_four_favorites_are_retained_and_in_automatic_directional_mode(self):
        expected={f'brush_velvet_fav_15_{i:02d}' for i in range(1,5)}
        samples={s['id']:s for s in self.samples}
        self.assertTrue(expected.issubset(samples))
        self.assertTrue(all(samples[s]['auto_eligible'] for s in expected))
        self.assertEqual({samples[s]['direction'] for s in expected},{'horizontal','vertical'})
        self.assertTrue(all(samples[s].get('favorite') for s in expected))
        self.assertTrue(all(s.get('direction_role')=='mezcla_sonica_asignada_no_direccion_documentada' for s in self.samples if s.get('direction')))

    def test_two_stroke_pairs_are_brush_only_and_selected_default_is_fast_A(self):
        from app import config
        samples={s['id']:s for s in self.samples}
        self.assertEqual(config.DEFAULTS['brush_id'],'brush_pair_A')
        self.assertEqual(config.DEFAULTS['pencil_id'],'auto')
        self.assertEqual(config.DEFAULTS['eraser_id'],'auto')
        for pair in ('A','B','C'):
            item=samples['brush_pair_'+pair]
            self.assertEqual(item['category'],'brush')
            self.assertFalse(item['auto_eligible'])
        self.assertEqual(samples['brush_pair_A']['kind'],'curated_two_stroke_tempo_115_pitch_preserved')
        self.assertAlmostEqual(samples['brush_pair_A']['duration_sec'],2.75/1.15,delta=.04)

    def test_brush_upgrade_selects_A_without_changing_P_E_preferences(self):
        from unittest.mock import patch
        from tempfile import TemporaryDirectory
        from app import config
        with TemporaryDirectory() as td:
            f=Path(td)/'settings.json'
            old={'curated_auto_v08':True,'curated_auto_v10':True,
                 'natural_original_v07_1':True,'per_tool_controls_v1':True,
                 'brush_id':'auto','pencil_id':'pencil_long_07a',
                 'eraser_id':'eraser_soft_08','brush_volume':73,
                 'pencil_speed':105,'eraser_volume':35}
            f.write_text(json.dumps(old))
            with patch('app.config.config_path',return_value=f):
                new=config.load()
                self.assertEqual(new['brush_id'],'brush_pair_A')
                self.assertEqual(new['pencil_id'],old['pencil_id'])
                self.assertEqual(new['eraser_id'],old['eraser_id'])
                self.assertEqual(new['pencil_speed'],105)
                self.assertEqual(new['eraser_volume'],35)
                self.assertEqual(new['brush_volume'],73)
                # Once migrated, respect a later manual B/J selection.
                new['brush_id']='brush_pair_C'
                config.save(new)
                self.assertEqual(config.load()['brush_id'],'brush_pair_C')

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
