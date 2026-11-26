import copy
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import subprocess
import unittest
from unittest.mock import patch
import contextlib
import io

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'files'))
import generate
import recover


def config():
    return {'settings': {'konfiguration_bestaetigt': True,
                         'master': {'threshold': 3, 'shares': 10},
                         'infra': {'threshold': 2, 'shares': 6},
                         'kontakt': 'Testkontakt', 'datenorte': 'Offline-USB',
                         'master_anlass': 'Dauerhafter Ausfall', 'infra_anlass': 'IT-Notfall'},
            'people': [{'id': f'p{i}', 'vorname': f'Test{i}', 'nachname': 'Testperson',
                        'master_id': i, 'infra_id': i if i <= 6 else False} for i in range(1, 11)]}


class Configuration(unittest.TestCase):
    def test_second_factor_prompt_normalizes_totp_and_preserves_password(self):
        with patch('builtins.input', return_value='1'), \
                patch('getpass.getpass', side_effect=['jbsw y3dp ehpk3pxp', 'JBSWY3DPEHPK3PXP']), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            bundle = generate.prompt_second_factor(' slash / password ')
        self.assertEqual(bundle['password'], ' slash / password ')
        self.assertEqual(bundle['second_factor'], 'JBSWY3DPEHPK3PXP')
        self.assertNotIn(bundle['second_factor'], output.getvalue())
        with patch('builtins.input', return_value='2'), \
                patch('getpass.getpass', side_effect=['code-one', 'code-two']), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
            generate.prompt_second_factor('password')

    def test_bundle_rejects_unsupported_or_invalid_factor(self):
        for kind, value in [('api_secret', 'example'), ('totp', '123456'), ('totp', 'otpauth://example'),
                            ('recovery_code', ''), ('recovery_code', 'x' * 129)]:
            with self.subTest(kind=kind, value=value), self.assertRaises(ValueError):
                recover.validate_bundle({'password': 'pw', 'second_factor_type': kind, 'second_factor': value})

    def test_incomplete_and_mixed_bundle_envelopes_are_rejected(self):
        run = 'a' * 32
        first = recover.encode(run, 'master', 3, 10, '01-' + 'a' * 16 + '~01-' + 'b' * 16, 'SSS2')
        second = recover.encode(run, 'master', 3, 10, '02-' + 'a' * 16, 'SSS2')
        third = recover.encode(run, 'master', 3, 10, '03-' + 'a' * 16, 'SSS1')
        with self.assertRaises(ValueError):
            recover.combine([first, second, third])
        wrong_index = recover.encode(run, 'master', 3, 10, '01-' + 'a' * 16 + '~02-' + 'b' * 16, 'SSS2')
        with self.assertRaises(ValueError):
            recover.parse(wrong_index)

    def test_assignments(self):
        good = config()
        generate.validate(good)
        for value in (True, 0, 11, '1', None, 2):
            bad = copy.deepcopy(good)
            bad['people'][0]['master_id'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                generate.validate(bad)

    def test_placeholders_and_paths(self):
        for key, value in [('id', '../../secret'), ('vorname', 'Beispiel01')]:
            bad = config()
            bad['people'][0][key] = value
            with self.assertRaises(ValueError):
                generate.validate(bad)

    def test_personal_document_has_only_assigned_shares(self):
        cfg = config()
        shares = {'master': [f'MASTER_{i}' for i in range(10)],
                  'infra': [f'INFRA_{i}' for i in range(6)]}
        text = generate.document(cfg['people'][6], cfg['settings'], 'a' * 32, shares)
        self.assertIn('MASTER_6', text)
        self.assertNotIn('MASTER_5', text)
        self.assertNotIn('INFRA_', text)
        self.assertIn('&lt;script&gt;', generate.render_html('<script>'))

    def test_checksum_and_mixed_sets(self):
        first = recover.encode('a' * 32, 'infra', 2, 6, '1-' + 'a' * 16)
        second = recover.encode('b' * 32, 'infra', 2, 6, '2-' + 'b' * 16)
        with self.assertRaises(ValueError):
            recover.parse(first[:-1] + ('0' if first[-1] != '0' else '1'))
        with self.assertRaises(ValueError):
            recover.combine([first, second])
        with self.assertRaises(ValueError):
            recover.combine([first, first])


@unittest.skipUnless(shutil.which('ssss-split') and shutil.which('ssss-combine'), 'requires ssss-split and ssss-combine')
class RealSSSS(unittest.TestCase):
    def test_bundles_all_default_master_quorums(self):
        for factor_type, password, factor in [
                ('totp', '  ü / password " \\ 🔑 ' * 3, 'JBSWY3DPEHPK3PXP'),
                ('recovery_code', '"' * 127, '\\' * 128)]:
            bundle = {'password': password, 'second_factor_type': factor_type, 'second_factor': factor}
            shares = generate.split_bundle(bundle, 'd' * 32, {'threshold': 3, 'shares': 10})
            self.assertTrue(all(s.startswith('SSS2|') for s in shares))
            self.assertIn('~', shares[0])
            self.assertEqual(recover.combine(shares[-3:], kind='master'), bundle)
            with self.assertRaises(ValueError):
                recover.combine(shares[:2])
            with self.assertRaises(ValueError):
                recover.combine(shares[:3], kind='infra')

    def test_service_stops_when_launcher_disconnects(self):
        process = subprocess.Popen([sys.executable, str(Path(recover.__file__)), '--web', '--stop-on-stdin-close'],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            # Drain output with communicate; closing stdin models the Windows starter exiting.
            stdout, stderr = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, stderr)
            self.assertIn('http://127.0.0.1:', stdout)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def test_roundtrip_all_default_quorums(self):
        for kind, scheme in config()['settings'].items():
            if kind not in ('master', 'infra'):
                continue
            secret = "  Test-'\"-$()-Grüße-🔑  "
            shares = generate.split(secret, 'a' * 32, kind, scheme)
            self.assertEqual(recover.combine(shares[-scheme['threshold']:]), secret)
            self.assertEqual(recover.combine(shares[:scheme['threshold']], kind=kind), secret)
            with self.assertRaises(ValueError):
                recover.combine(shares[:scheme['threshold']], kind='master' if kind == 'infra' else 'infra')
            self.assertEqual(recover.combine(['\n'.join(s[i:i+40] for i in range(0, len(s), 40))
                                             for s in shares[:scheme['threshold']]]), secret)
            with self.assertRaises(ValueError):
                recover.combine(shares[:scheme['threshold'] - 1])

    def test_lengths(self):
        for secret in ('x', 'x' * 127):
            shares = generate.split(secret, 'b' * 32, 'infra', {'threshold': 2, 'shares': 3})
            self.assertEqual(recover.combine(shares[:2]), secret)
        for secret in ('', 'x' * 128, 'abc\n', '\0abc'):
            with self.assertRaises(ValueError):
                generate.split(secret, 'b' * 32, 'infra', {'threshold': 2, 'shares': 3})

    def test_web_loopback_and_origin(self):
        server, url = recover.create_server()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        from urllib.parse import urlsplit
        parsed = urlsplit(url)
        connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=10)
        try:
            connection.request('GET', parsed.path)
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.getheader('Cache-Control'), 'no-store')
            self.assertIn('Passwort wiederherstellen'.encode(), response.read())
            shares = generate.split('Web-Test-ä', 'c' * 32, 'infra', {'threshold': 2, 'shares': 3})
            body = json.dumps({'shares': shares[:2], 'kind': 'infra'})
            connection.request('POST', parsed.path + 'combine', body, {'Content-Type': 'application/json', 'Origin': 'https://example.org'})
            response = connection.getresponse()
            self.assertEqual(response.status, 403)
            response.read()
            connection.request('POST', parsed.path + 'combine', body, {'Content-Type': 'application/json', 'Origin': f'http://{parsed.netloc}'})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read())['secret'], 'Web-Test-ä')
            connection.request('POST', parsed.path + 'combine', json.dumps({'shares': shares[:2], 'kind': 'master'}),
                               {'Content-Type': 'application/json', 'Origin': f'http://{parsed.netloc}'})
            response = connection.getresponse()
            self.assertEqual(response.status, 400)
            self.assertIn('selection', json.loads(response.read())['error'])
            bundle = {'password': 'master / "ü"', 'second_factor_type': 'totp', 'second_factor': 'JBSWY3DPEHPK3PXP'}
            master = generate.split_bundle(bundle, 'e' * 32, {'threshold': 3, 'shares': 4})
            connection.request('POST', parsed.path + 'combine', json.dumps({'shares': master[:3], 'kind': 'master'}),
                               {'Content-Type': 'application/json', 'Origin': f'http://{parsed.netloc}'})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read()), {'secret': bundle['password'],
                                                         'second_factor_type': 'totp', 'second_factor': bundle['second_factor']})
        finally:
            connection.close()
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
