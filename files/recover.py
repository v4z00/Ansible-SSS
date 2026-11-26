#!/usr/bin/env python3
"""Offline recovery for SSS1 and SSS2 envelopes with Python and ssss."""
import getpass
import argparse
import base64
import binascii
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import resource
import secrets
import shutil
import subprocess
import sys
import threading
import warnings
import webbrowser


def harden():
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    warnings.simplefilter('error', getpass.GetPassWarning)


MAX_BUNDLE_BYTES = 1024
MAX_BLOCKS = 9


def validate_password(value):
    if (not isinstance(value, str) or not 1 <= len(value.encode('utf-8')) <= 127
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError('Passwords must contain 1–127 UTF-8 bytes without control characters.')


def validate_bundle(bundle):
    if not isinstance(bundle, dict) or set(bundle) != {'password', 'second_factor_type', 'second_factor'}:
        raise ValueError('Invalid credential bundle.')
    validate_password(bundle['password'])
    kind, value = bundle['second_factor_type'], bundle['second_factor']
    if kind not in ('totp', 'recovery_code') or not isinstance(value, str):
        raise ValueError('Use a TOTP setup secret or 2FA recovery code.')
    if not value.strip() or len(value.encode('utf-8')) > 128 or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError('Second factors must contain 1–128 UTF-8 bytes without control characters.')
    if kind == 'totp':
        if not re.fullmatch(r'[A-Z2-7]+', value):
            raise ValueError('Use the Base32 TOTP setup secret.')
        try:
            decoded = base64.b32decode(value + '=' * (-len(value) % 8))
        except (binascii.Error, ValueError):
            raise ValueError('Invalid Base32 TOTP secret.') from None
        if len(decoded) < 10:
            raise ValueError('The TOTP secret is too short.')


def encode(run, kind, threshold, count, raw, version='SSS1'):
    body = f'{version}|{run}|{kind}|{threshold}|{count}|{raw}'
    return body + '|' + hashlib.sha256(body.encode('ascii')).hexdigest()[:16]


def parse(value):
    value = ''.join(value.split())
    parts = value.split('|')
    if len(parts) != 7 or parts[0] not in ('SSS1', 'SSS2'):
        raise ValueError('Enter a complete SSS1 or SSS2 share.')
    version, run, kind, threshold, count, raw, checksum = parts
    if not re.fullmatch(r'[0-9a-f]{32}', run) or kind not in ('master', 'infra'):
        raise ValueError('Invalid set ID or category.')
    if not threshold.isdecimal() or not count.isdecimal():
        raise ValueError('Invalid threshold.')
    t, n = int(threshold), int(count)
    blocks = raw.split('~')
    if not 2 <= t <= n <= 20 or not 1 <= len(blocks) <= MAX_BLOCKS:
        raise ValueError('Invalid share format.')
    if (version == 'SSS1' and len(blocks) != 1) or (version == 'SSS2' and kind != 'master'):
        raise ValueError('Invalid format for this category.')
    indices = []
    for block in blocks:
        match = re.fullmatch(r'([0-9]{1,3})-([0-9a-fA-F]{16,256})', block)
        if not match or len(match[2]) % 2 or not 1 <= int(match[1]) <= n:
            raise ValueError('Invalid block or share number.')
        indices.append(int(match[1]))
    if len(set(indices)) != 1:
        raise ValueError('All blocks must have the same share number.')
    expected = hashlib.sha256('|'.join(parts[:-1]).encode('ascii')).hexdigest()[:16]
    if not hmac.compare_digest(checksum, expected):
        raise ValueError('Checksum mismatch. Copy the share again from the original.')
    return (run, kind, t, n, version, len(blocks)), indices[0], raw


def run_ssss(program, args, value):
    executable = shutil.which(program)
    if not executable:
        raise ValueError(f'Install the ssss package on the recovery computer to provide {program}.')
    result = subprocess.run([executable, *args], input=value, text=True,
                            encoding='ascii', capture_output=True, timeout=60, check=False)
    if result.returncode:
        # stderr may contain secrets; never propagate it into errors or logs.
        raise ValueError(f'{program} failed. Check the shares and installation.')
    return result


def combine(values, kind=None):
    parsed = [parse(value) for value in values]
    if not parsed:
        raise ValueError('No shares supplied.')
    metadata = parsed[0][0]
    if kind is not None and (kind not in ('master', 'infra') or metadata[1] != kind):
        raise ValueError('Shares do not match the selected access category.')
    if any(p[0] != metadata for p in parsed):
        raise ValueError('Use shares from one set, format and category.')
    if len(parsed) != metadata[2]:
        raise ValueError(f'Supply exactly {metadata[2]} distinct shares.')
    if len({p[1] for p in parsed}) != len(parsed):
        raise ValueError('Duplicate share.')
    blocks = [p[2].split('~') for p in parsed]
    payload = b''.join(combine_block([row[i] for row in blocks], metadata[2]) for i in range(metadata[5]))
    if metadata[4] == 'SSS2':
        if len(payload) > MAX_BUNDLE_BYTES:
            raise ValueError('Credential bundle exceeds the size limit.')
        try:
            bundle = json.loads(payload.decode('utf-8'))
        except (UnicodeError, ValueError):
            raise ValueError('Could not decode credential bundle.') from None
        validate_bundle(bundle)
        return bundle
    try:
        secret = payload.decode('utf-8')
    except UnicodeError:
        raise ValueError('The recovered password is not valid UTF-8.') from None
    validate_password(secret)
    return secret


def combine_block(raw_parts, threshold):
    if len({len(part.split('-')[1]) for part in raw_parts}) != 1:
        raise ValueError('Inconsistent share lengths.')
    result = run_ssss('ssss-combine', ['-t', str(threshold), '-x', '-Q'], '\n'.join(raw_parts) + '\n')
    # ssss writes the recovered value to stderr, even in quiet mode.
    lines = [line for line in result.stderr.splitlines()
             if re.fullmatch(r'[0-9a-fA-F]{16,256}', line)]
    if len(lines) != 1:
        raise ValueError('Unexpected ssss-combine output.')
    payload = bytes.fromhex(lines[0]).lstrip(b'\x00')
    if not payload.startswith(b'\x01'):
        raise ValueError('Invalid reconstruction. Check the original shares.')
    return payload[1:]


def main():
    harden()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--web', action='store_true', help='Open the offline recovery interface')
    parser.add_argument('--open-browser', action='store_true', help='With --web, open a local browser')
    parser.add_argument('--stop-on-stdin-close', action='store_true', help='With --web, stop when the launcher closes stdin')
    parser.add_argument('--lang', choices=('en', 'de'), help='Initial language for the offline browser')
    args = parser.parse_args()
    if args.open_browser and not args.web:
        parser.error('--open-browser requires --web')
    if args.stop_on_stdin_close and not args.web:
        parser.error('--stop-on-stdin-close requires --web')
    if not shutil.which('ssss-combine'):
        installer = Path(__file__).with_name('install-voraussetzungen.sh')
        if not installer.is_file():
            raise ValueError('Install ssss using the platform launcher.')
        subprocess.run(['bash', str(installer)], check=True)
        if not shutil.which('ssss-combine'):
            raise ValueError('ssss-combine is unavailable after installation.')
    if args.web:
        serve_web(open_browser=args.open_browser, stop_on_stdin_close=args.stop_on_stdin_close, language=args.lang)
        return
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError('Run in a local terminal without redirection.')
    print('Offline recovery. Turn off terminal recording.')
    first = getpass.getpass('First complete SSS1/SSS2 share: ')
    metadata, _, _ = parse(first)
    print(f'Category: {metadata[1]} | Set: {metadata[0]} | Required shares: {metadata[2]}')
    values = [first]
    for i in range(1, metadata[2]):
        values.append(getpass.getpass(f'Share {i + 1}/{metadata[2]}: '))
    recovered = combine(values)
    bundle = recovered if isinstance(recovered, dict) else None
    secret = bundle['password'] if bundle else recovered
    if input('Reveal credentials? Type REVEAL: ') != 'REVEAL':
        print('Closed without revealing credentials.')
        return
    print('\nPassword (including any spaces between the markers):')
    print('>>> ' + secret + ' <<<')
    if bundle:
        label = 'TOTP setup secret' if bundle['second_factor_type'] == 'totp' else '2FA recovery code'
        print('\n' + label + ':')
        print('>>> ' + bundle['second_factor'] + ' <<<')
        print('Import the TOTP secret into a trusted authenticator. Use a recovery code only for the documented recovery procedure.')
    if metadata[1] == 'master':
        print('\nMASTER: Use the documented Vaultwarden account, server and second factor.')
    else:
        print('\nINFRA: Use this password for the documented infrastructure account.')
    print('Verify offline KDBX credentials separately.')
    print('Verify access, then close the terminal.')


def create_server(language=None):
    if language is None:
        preference = Path(__file__).with_name('language.txt')
        language = preference.read_text(encoding='ascii').strip() if preference.is_file() else 'en'
    if language not in ('en', 'de'):
        raise ValueError('Choose en or de for the browser language.')
    page = Path(__file__).with_name('notfall_entschluesselung.html').read_bytes().replace(b'<html lang="en">', b'<html lang="' + language.encode('ascii') + b'">', 1)
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def respond(self, code, body, content_type='application/json; charset=utf-8'):
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.headers.get('Host') != self.server.expected_host or self.path != '/' + token + '/':
                self.respond(404, b'{}')
                return
            self.respond(200, page, 'text/html; charset=utf-8')

        def do_POST(self):
            if (self.headers.get('Host') != self.server.expected_host
                    or self.headers.get('Origin') != 'http://' + self.server.expected_host
                    or self.path != '/' + token + '/combine'):
                self.respond(403, b'{}')
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 120000 or self.headers.get('Content-Type') != 'application/json':
                    raise ValueError('Invalid request.')
                data = json.loads(self.rfile.read(length))
                values = data.get('shares')
                if not isinstance(values, list) or not 2 <= len(values) <= 20 or any(not isinstance(v, str) for v in values):
                    raise ValueError('Missing or invalid shares.')
                kind = data.get('kind')
                if not isinstance(kind, str) or kind not in ('infra', 'master'):
                    raise ValueError('Select infrastructure or master access.')
                recovered = combine(values, kind=kind)
                data = ({'secret': recovered['password'], 'second_factor_type': recovered['second_factor_type'],
                         'second_factor': recovered['second_factor']} if isinstance(recovered, dict)
                        else {'secret': recovered, 'second_factor_type': None, 'second_factor': None})
                self.respond(200, json.dumps(data).encode('utf-8'))
            except (ValueError, UnicodeError):
                self.respond(400, b'{"error":"Invalid shares, selection or request."}')
            except (OSError, subprocess.SubprocessError, TypeError, AttributeError):
                self.respond(400, b'{"error":"Local recovery failed."}')

    server = HTTPServer(('127.0.0.1', 0), Handler)
    server.expected_host = f'127.0.0.1:{server.server_port}'
    return server, f'http://{server.expected_host}/{token}/'


def open_local_browser(url):
    if sys.platform.startswith('linux') and not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        print('No graphical session found. Open the printed address on this computer.', flush=True)
        return
    try:
        opened = webbrowser.open(url, new=2)
    except Exception:
        opened = False
    if not opened:
        print('Open the printed address manually in a local browser.', flush=True)


def stop_when_input_closes(server, stream):
    try:
        while stream.read(1):
            pass
    finally:
        server.shutdown()


def serve_web(open_browser=False, stop_on_stdin_close=False, language=None):
    server, url = create_server(language)
    print('Open this address on the recovery computer:')
    print(url, flush=True)
    print('Press Ctrl+C to stop. Keep the service local.', flush=True)
    try:
        if stop_on_stdin_close:
            threading.Thread(target=stop_when_input_closes, args=(server, sys.stdin.buffer), daemon=True).start()
        if open_browser:
            # A browser launcher can block; the recovery server must remain responsive.
            threading.Thread(target=open_local_browser, args=(url,), daemon=True).start()
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError, getpass.GetPassWarning):
        print('Recovery failed. Check original shares, set, distinct IDs and the ssss installation.', file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print('\nCancelled.', file=sys.stderr)
        sys.exit(130)
