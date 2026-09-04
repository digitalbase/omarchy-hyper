import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('hyper', Path(__file__).parents[1] / 'hyper.py')
hyper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hyper)


class HyperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.paths = patch.multiple(hyper, MAIN=root / 'hyprland.lua', GENERATED=root / 'hyper.lua', STATE=root / 'state.json')
        self.paths.start()
        hyper.MAIN.write_text('-- personal settings\n')

    def tearDown(self):
        self.paths.stop()
        self.tmp.cleanup()

    def test_rejects_injection_in_key(self):
        with self.assertRaises(ValueError):
            hyper.key('A\nexec malicious')

    def test_shell_and_lua_quoting(self):
        import shlex
        data = {'options': None, 'shortcuts': {'A': {'id': "Bob's $(touch nope)", 'name': '"App"'}}}
        output = hyper.render(data)
        self.assertIn(shlex.quote("Bob's $(touch nope).desktop").replace('"', '\\"'), output)
        self.assertIn('MOD3 + A', output)

    @patch.object(hyper, 'run', return_value='')
    def test_hook_idempotent_and_removal_preserves_user_config(self, run):
        data = {'version': 1, 'options': None, 'shortcuts': {'A': {'id': 'test', 'name': 'Test'}}}
        hyper.apply(data)
        hyper.apply(data)
        self.assertEqual(hyper.MAIN.read_text().count(hyper.MARKER), 1)
        data['shortcuts'] = {}
        hyper.apply(data)
        self.assertNotIn(hyper.MARKER, hyper.MAIN.read_text())
        self.assertIn('-- personal settings', hyper.MAIN.read_text())

    def test_config_failure_rolls_back_all_files(self):
        with patch.object(hyper, 'run', side_effect=['', '', 'bad config', '']):
            with self.assertRaises(RuntimeError):
                hyper.apply({'options': None, 'shortcuts': {}})
        self.assertEqual(hyper.MAIN.read_text(), '-- personal settings\n')
        self.assertFalse(hyper.STATE.exists())
        self.assertFalse(hyper.GENERATED.exists())

    def test_external_shortcut_cannot_be_replaced(self):
        with patch.object(hyper, 'external_bindings', return_value=[{'key': 'A', 'modmask': 32, 'name': 'Original app'}]):
            with self.assertRaisesRegex(ValueError, 'already assigned'):
                hyper.mutate('assign', ['a', 'app', 'App'])

    def test_external_overwrite_requires_matching_confirmation(self):
        existing = [{'key': 'A', 'name': 'Original app'}]
        confirmation = [{'name': 'Original app', 'external': True, 'submap': ''}]
        with patch.object(hyper, 'external_bindings', return_value=existing), patch.object(hyper, 'apply') as apply, patch.object(hyper, 'status'):
            with self.assertRaises(hyper.Conflict) as error:
                hyper.mutate('assign', ['A', 'new', 'New app'])
            self.assertIn('Original app', str(error.exception))
            hyper.mutate('overwrite', ['A', 'new', 'New app', json.dumps(confirmation)])
            data = apply.call_args.args[0]
            rendered = hyper.render(data)
            self.assertLess(rendered.index('hl.unbind("MOD3 + A")'), rendered.index('o.bind('))
            self.assertEqual(data['shortcuts']['A']['id'], 'new')
            with self.assertRaises(hyper.Conflict):
                hyper.mutate('overwrite', ['A', 'new', 'New app', '[]'])

    def test_remove_external_physical_binding_persists_unbind(self):
        with patch.object(hyper, 'external_bindings', return_value=[{'key': 'CODE:49', 'name': '1Password'}]), patch.object(hyper, 'apply') as apply, patch.object(hyper, 'status'):
            hyper.mutate('remove', ['CODE:49'])
            self.assertIn('hl.unbind("MOD3 + code:49")', hyper.render(apply.call_args.args[0]))

    def test_owned_conflict_is_named_and_removal_keeps_external_suppressed(self):
        data = {'version': 1, 'options': None, 'suppressed': ['A'], 'shortcuts': {'A': {'id': 'old', 'name': 'Old app'}}}
        with patch.object(hyper, 'load', return_value=data), patch.object(hyper, 'external_bindings', return_value=[]), patch.object(hyper, 'apply') as apply, patch.object(hyper, 'status'):
            with self.assertRaisesRegex(hyper.Conflict, 'Old app'):
                hyper.mutate('assign', ['A', 'new', 'New app'])
            hyper.mutate('remove', ['A'])
            self.assertEqual(apply.call_args.args[0]['shortcuts'], {})
            self.assertEqual(apply.call_args.args[0]['suppressed'], ['A'])

    def test_recovers_multiline_physical_binding_without_guessing(self):
        root = Path(self.tmp.name)
        (root / 'hypr').mkdir()
        binding = root / 'hypr/physical.lua'
        binding.write_text('o.bind(\n "MOD3 + code:49",\n "1Password", "launch")')
        with patch.object(hyper, 'CONFIG', root):
            self.assertEqual(hyper.configured_physical_key('1Password'), 'CODE:49')
            binding.write_text(binding.read_text() + '\no.bind("MOD3 + code:50", "1Password", "other")')
            self.assertEqual(hyper.configured_physical_key('1Password'), '')

    def test_toggle_overrides_existing_hyper_and_keeps_shortcuts(self):
        saved = {'version': 1, 'options': None, 'shortcuts': {'A': {'id': 'app', 'name': 'App'}}}
        with patch.object(hyper, 'load', return_value=saved), patch.object(hyper, 'options', return_value='grp:alts_toggle,caps:hyper'), patch.object(hyper, 'apply') as apply, patch.object(hyper, 'status'):
            hyper.mutate('disable', [])
            self.assertEqual(apply.call_args.args[0]['options'], 'grp:alts_toggle,caps:capslock')
            self.assertEqual(apply.call_args.args[0]['shortcuts'], saved['shortcuts'])
        with patch.object(hyper, 'options', return_value='grp:alts_toggle,caps:capslock'), patch.object(hyper, 'apply') as apply, patch.object(hyper, 'status'):
            hyper.mutate('enable', [])
            self.assertEqual(apply.call_args.args[0]['options'], 'grp:alts_toggle,caps:hyper')

    def test_setup_keeps_unrelated_options(self):
        with patch.object(hyper, 'options', return_value='compose:caps,grp:alts_toggle'), patch.object(hyper, 'apply') as apply, patch.object(hyper, 'status'):
            hyper.mutate('enable', [])
            self.assertEqual(apply.call_args.args[0]['options'], 'grp:alts_toggle,caps:hyper')


if __name__ == '__main__':
    unittest.main()
