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
        with patch.object(hyper, 'external_bindings', return_value=[{'key': 'A', 'modmask': 32}]):
            with self.assertRaisesRegex(ValueError, 'already assigned'):
                hyper.mutate('assign', ['a', 'app', 'App'])

    def test_setup_keeps_unrelated_options(self):
        with patch.object(hyper, 'options', return_value='compose:caps,grp:alts_toggle'), patch.object(hyper, 'apply') as apply, patch.object(hyper, 'status'):
            hyper.mutate('enable', [])
            self.assertEqual(apply.call_args.args[0]['options'], 'grp:alts_toggle,caps:hyper')


if __name__ == '__main__':
    unittest.main()
