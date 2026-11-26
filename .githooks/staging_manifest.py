#!/usr/bin/env python3
"""Generate and verify the public package against immutable Git blobs or the index."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

MANIFEST = 'SHA256SUMS.json'
PUBLIC = set('''
.githooks/pre-commit .githooks/pre-push .githooks/staging_manifest.py
.gitignore LICENSE README.de.md README.md VERSION.txt controller-addon.json
examples/config.yml.example examples/trustees.yml.example
files/generate.py files/recover.py files/notfall_entschluesselung.html
files/install-voraussetzungen.ps1 files/install-voraussetzungen.sh files/start-html.bat
files/start-html.command files/start-html.ps1 files/start-html.sh
guides/BEDIENUNGSANLEITUNG.md guides/GUIDE.md guides/START-HERE.md guides/START-HIER.md
integration/sss.json integration/sss.sh integration/sss.md
run.sh setup.yml start-generator.sh tests/test_launcher.py tests/test_sss.py
tests/test_addon.py tests/browser.cjs
'''.split())


def git(*args):
    return subprocess.check_output(['git', *args])


def entries(ref):
    if ref == ':index':
        records = git('ls-files', '--stage', '-z')
    else:
        commit = git('rev-parse', '--verify', '--end-of-options', ref + '^{commit}').decode().strip()
        records = git('ls-tree', '-rz', commit)
    result = {}
    for record in records.split(b'\0'):
        if not record:
            continue
        attrs, path = record.split(b'\t', 1)
        path = path.decode()
        mode, field, last = attrs.decode('ascii').split()
        if ((path not in PUBLIC and path != MANIFEST) or path in result or
                mode not in ('100644', '100755') or (ref == ':index' and last != '0') or
                (ref != ':index' and field != 'blob')):
            raise ValueError('Unexpected or unsafe package entry.')
        result[path] = (mode, field if ref == ':index' else last)
    if PUBLIC - result.keys():
        raise ValueError('Missing required public package files.')
    return result


def manifest(tree):
    hashes = {}
    for path in sorted(PUBLIC):
        mode, oid = tree[path]
        hashes[path] = {'sha256': hashlib.sha256(git('cat-file', 'blob', oid)).hexdigest(),
                        'mode': '0755' if mode == '100755' else '0644'}
    return {'schema': 1, 'profile': 'SSS', 'files': hashes}


def write_index(data):
    path = Path(MANIFEST)
    if path.is_symlink():
        raise ValueError('Unexpected manifest symlink.')
    fd, name = tempfile.mkstemp(prefix='.sss-manifest-', dir='.')
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fchmod(handle.fileno(), 0o644)
            os.fsync(handle.fileno())
        os.replace(name, path)
        git('add', '--', MANIFEST)
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('write', 'verify'))
    parser.add_argument('ref', nargs='?')
    args = parser.parse_args()
    if args.action == 'write' and args.ref not in (None, ':index'):
        parser.error('write only accepts the index')
    os.chdir(os.fsdecode(git('rev-parse', '--show-toplevel').rstrip(b'\n')))
    ref = args.ref or (':index' if args.action == 'write' else 'HEAD')
    tree = entries(ref)
    actual = manifest(tree)
    if args.action == 'write':
        write_index((json.dumps(actual, indent=2, sort_keys=True) + '\n').encode())
    elif MANIFEST not in tree or tree[MANIFEST][0] != '100644' or json.loads(git('cat-file', 'blob', tree[MANIFEST][1])) != actual:
        raise ValueError('Package manifest mismatch.')
    print(f'SSS integrity OK ({ref}, {len(PUBLIC)} files).')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, UnicodeError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(f'Integrity check failed: {error}')
