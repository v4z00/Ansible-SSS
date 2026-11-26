import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'files'))
import generate
import recover


def options():
    return {'confirmed': True, 'language': 'en', 'master': {'threshold': 2, 'shares': 3},
            'infra': {'threshold': 4, 'shares': 5}, 'contact': 'Synthetic contact',
            'locations': 'Test storage', 'master_purpose': 'First test', 'infra_purpose': 'Second test'}


def trustees():
    return [{'id': f'p{i}', 'first_name': f'Test{i}', 'last_name': 'Fixture',
             'master_id': i if i <= 3 else False, 'infra_id': i} for i in range(1, 6)]


class Addon(unittest.TestCase):
    def test_settings_letters_and_localized_guides(self):
        cfg = {'settings': options(), 'people': trustees()}
        generate.validate(cfg)
        with self.assertRaises(ValueError):
            generate.settings_for({**cfg['settings'], 'kontakt': 'Different'})
        shares = {'master': ['m1', 'm2', 'm3'], 'infra': ['i1', 'i2', 'i3', 'i4', 'i5']}
        for language, text, guide in [('en', 'Gather 4 distinct shares', 'START-HERE.md'),
                                      ('de', 'Sammelt 4 verschiedene Teile', 'START-HIER.md')]:
            cfg['settings']['language'] = language
            output = generate.document(cfg['people'][4], cfg['settings'], 'a' * 32, shares)
            self.assertIn(text, output)
            self.assertIn('i5', output)
            self.assertNotIn('m1', output)
            self.assertIn(guide, output)
            self.assertTrue((ROOT / 'guides' / guide).is_file())
            html = generate.render_html(output, language)
            self.assertIn(f'lang="{language}"', html)
        with self.assertRaises(ValueError):
            generate.document(cfg['people'][0], cfg['settings'], 'a' * 32, shares, 'xx')
        cfg['settings']['language'] = 'xx'
        with self.assertRaises(ValueError):
            generate.validate(cfg)

    def test_private_config_and_atomic_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            private = Path(temporary) / 'synthetic.json'
            generate.write_private(private, json.dumps({'settings': options(), 'people': trustees()}))
            self.assertEqual(private.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                generate.write_private(private, 'duplicate')
            def validate(path):
                return subprocess.run([sys.executable, str(ROOT / 'files/generate.py'), '--validate-file', str(path)],
                                      capture_output=True, text=True).returncode
            self.assertEqual(validate(private), 0)
            alias = private.with_name('symlink')
            alias.symlink_to(private)
            self.assertNotEqual(validate(alias), 0)
            private.chmod(0o644)
            self.assertNotEqual(validate(private), 0)
            private.chmod(0o600)
            os.link(private, private.with_name('hardlink'))
            self.assertNotEqual(validate(private), 0)

    def test_addon_description_hashes_and_payload(self):
        desc = json.loads((ROOT / 'controller-addon.json').read_text())
        self.assertEqual(desc['replaces'], [])
        self.assertTrue(all((ROOT / path).exists() for path in desc['payload']))
        mounted = {target: ROOT / source for source, target in desc['exports'].items()}
        md = (ROOT / 'integration/sss.md').read_text()
        contract = json.loads(re.search(r'```json\n(.*?)\n```', md, re.S)[1])
        self.assertEqual(set(contract['sources']), set(contract['source_hashes']))
        for name, digest in contract['source_hashes'].items():
            path = mounted.get(name) or ROOT / Path(name).relative_to(desc['mount_prefix'])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
        examples = list((ROOT / 'examples').iterdir())
        self.assertTrue(examples and all(path.suffix == '.example' for path in examples))

    @unittest.skipUnless(shutil.which('node'), 'requires Node.js to run the browser script')
    def test_browser_dynamic_quorums_both_languages_and_file_mode(self):
        subprocess.run(['node', str(ROOT / 'tests/browser.cjs'),
                        str(ROOT / 'files/notfall_entschluesselung.html')], check=True)

    @unittest.skipUnless(shutil.which('ssss-combine') and shutil.which('ssss-split'), 'requires ssss')
    def test_http_language_and_nonstandard_quorums(self):
        for language, kind, t, n in [('en', 'master', 2, 3), ('de', 'infra', 4, 5)]:
            with self.subTest(language=language):
                server, url = recover.create_server(language)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                target = urlsplit(url)
                conn = http.client.HTTPConnection(target.hostname, target.port, timeout=10)
                try:
                    conn.request('GET', target.path)
                    page = conn.getresponse()
                    self.assertEqual(page.status, 200)
                    self.assertIn(f'<html lang="{language}">'.encode(), page.read())
                    shares = generate.split('synthetic password', 'a' * 32, kind, {'threshold': t, 'shares': n})
                    for values, expected in [(shares[:t-1], 400), (shares[:t], 200)]:
                        body = json.dumps({'shares': values, 'kind': kind})
                        conn.request('POST', target.path + 'combine', body,
                                     {'Content-Type': 'application/json', 'Origin': 'http://' + target.netloc})
                        response = conn.getresponse()
                        self.assertEqual(response.status, expected)
                        result = json.loads(response.read())
                        if expected == 200:
                            self.assertEqual(result['secret'], 'synthetic password')
                finally:
                    conn.close()
                    server.shutdown()
                    server.server_close()
                    thread.join()
