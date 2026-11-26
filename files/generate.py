#!/usr/bin/env python3
"""Generate personalized documents only below /root/rescue/SSS."""
import argparse
import datetime
import getpass
import html
import itertools
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import uuid

# Deployed scripts are in bin/ and offline/; source tests import from files/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'offline'))
from recover import combine, encode, harden, run_ssss, validate_password, validate_bundle, MAX_BUNDLE_BYTES

BASE = Path('/root/rescue/SSS')


def aliases(data, fields):
    result = dict(data)
    for old, new in fields.items():
        if old in result:
            if new in result and result[new] != result[old]:
                raise ValueError(f'Conflicting values for {old} and {new}.')
            result[new] = result.pop(old)
    return result


def settings_for(settings):
    options = aliases(settings, {'konfiguration_bestaetigt': 'confirmed', 'kontakt': 'contact',
                                'datenorte': 'locations', 'master_anlass': 'master_purpose',
                                'infra_anlass': 'infra_purpose'})
    # Configurations created before language selection produced German letters.
    options.setdefault('language', 'de' if 'konfiguration_bestaetigt' in settings else 'en')
    if options['language'] not in ('de', 'en'):
        raise ValueError('Choose en or de for language.')
    return options


def trustee_for(person):
    return aliases(person, {'vorname': 'first_name', 'nachname': 'last_name'})


def validate(config):
    settings, people = settings_for(config['settings']), config['people']
    if settings.get('confirmed') is not True:
        raise ValueError('Complete the private config and set confirmed to true.')
    for key in ('contact', 'locations', 'master_purpose', 'infra_purpose'):
        if not isinstance(settings.get(key), str) or not settings[key].strip() or 'BITTE EINTRAGEN' in settings[key] or settings[key].strip() == 'REPLACE':
            raise ValueError(f'Missing setting: {key}.')
    if not isinstance(people, list) or not people:
        raise ValueError('A trustee list is required.')
    names, ids = set(), set()
    for person in people:
        p = trustee_for(person)
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', p['id']) or p['id'] in ids:
            raise ValueError('Invalid or duplicate trustee ID.')
        ids.add(p['id'])
        if any(not isinstance(p[k], str) or not p[k].strip() or any(ord(ch) < 32 or ord(ch) == 127 for ch in p[k]) for k in ('first_name', 'last_name')):
            raise ValueError('Enter the first and last names.')
        name = (p['first_name'].strip().casefold(), p['last_name'].strip().casefold())
        if name in names or 'beispiel' in name[0] or name[1] == 'ersetzen' or name[0] == 'example':
            raise ValueError('Replace example identities and distinguish trustees with identical names.')
        names.add(name)
        if p['master_id'] is False and p['infra_id'] is False:
            raise ValueError('Each trustee must receive at least one share.')
    for kind in ('master', 'infra'):
        t, n = settings[kind]['threshold'], settings[kind]['shares']
        if type(t) is not int or type(n) is not int or not 2 <= t <= n <= 20:
            raise ValueError('Required: 2 <= threshold <= shares <= 20.')
        if sum(1 for _ in itertools.combinations(range(n), t)) > 1000:
            raise ValueError('At most 1000 verification combinations are supported per category.')
        assigned = []
        for p in people:
            value = p[kind + '_id']
            if value is False:
                continue
            if type(value) is not int or not 1 <= value <= n:
                raise ValueError(f'{kind}: IDs must be integers between 1 and {n}, or false.')
            assigned.append(value)
        if sorted(assigned) != list(range(1, n + 1)):
            raise ValueError(f'{kind}: Assign each ID from 1 to {n} exactly once.')


def split_bytes(raw, scheme):
    if not 1 <= len(raw) <= 127:
        raise ValueError('Invalid block length.')
    payload = b'\x01' + raw
    bits = max(64, len(payload) * 8)
    t, n = scheme['threshold'], scheme['shares']
    result = run_ssss('ssss-split', ['-t', str(t), '-n', str(n), '-s', str(bits), '-x', '-Q'],
                      payload.hex().zfill(bits // 4) + '\n')
    shares = result.stdout.splitlines()
    if len(shares) != n:
        raise ValueError('Unexpected number of generated shares.')
    return shares


def split(secret, run, kind, scheme):
    validate_password(secret)
    t, n = scheme['threshold'], scheme['shares']
    shares = split_bytes(secret.encode('utf-8'), scheme)
    envelopes = [encode(run, kind, t, n, share) for share in shares]
    # Every quorum is verified before any private document is written.
    for quorum in itertools.combinations(envelopes, t):
        if combine(quorum) != secret:
            raise ValueError('Share verification failed before output.')
    return envelopes


def split_bundle(bundle, run, scheme):
    validate_bundle(bundle)
    raw = json.dumps(bundle, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if len(raw) > MAX_BUNDLE_BYTES:
        raise ValueError('Credential bundle exceeds the size limit.')
    t, n = scheme['threshold'], scheme['shares']
    blocks = [split_bytes(raw[i:i + 127], scheme) for i in range(0, len(raw), 127)]
    envelopes = [encode(run, 'master', t, n, '~'.join(block[j] for block in blocks), version='SSS2')
                 for j in range(n)]
    for quorum in itertools.combinations(envelopes, t):
        if combine(quorum) != bundle:
            raise ValueError('Credential bundle verification failed before output.')
    return envelopes


def prompt_second_factor(password):
    print('Select what to store with the Vaultwarden master password:')
    print('1 = TOTP setup secret, 2 = 2FA recovery code, 0 = password only')
    choice = input('Choice (0/1/2): ').strip()
    if choice == '0':
        return None
    if choice not in ('1', '2'):
        raise ValueError('Choose 0, 1 or 2. Generation cancelled.')
    kind = 'totp' if choice == '1' else 'recovery_code'
    label = 'TOTP setup secret (not a six-digit login code)' if choice == '1' else '2FA recovery code'
    first = getpass.getpass(label + ': ')
    second = getpass.getpass('Repeat the second factor: ')
    if kind == 'totp':
        first, second = (''.join(value.split()).upper().rstrip('=') for value in (first, second))
    if first != second:
        raise ValueError('The second factor entries differ.')
    bundle = {'password': password, 'second_factor_type': kind, 'second_factor': first}
    validate_bundle(bundle)
    return bundle


def document(person, settings, run, shares, language=None):
    settings = settings_for(settings)
    person = trustee_for(person)
    lang = language or settings['language']
    if lang not in ('en', 'de'):
        raise ValueError('Unsupported letter language.')
    def message(en, de):
        return de if lang == 'de' else en
    lines = [message('DIGITAL ESTATE & IT EMERGENCY', 'DIGITALER NACHLASS & IT-NOTFALL'),
             f"{person['first_name']} {person['last_name']}", f"ID: {run}", '',
             message('Keep this letter sealed and separate from the other shares. Report a damaged seal to the emergency contact.',
                     'Bewahre den Brief verschlossen und getrennt von weiteren Teilen auf. Melde ein beschädigtes Siegel dem Notfallkontakt.'),
             message('Emergency contact', 'Notfallkontakt'), settings['contact'],
             message('Vaults and offline copies', 'Tresore und Offline-Kopien'), settings['locations'], '']
    for kind in ('master', 'infra'):
        number = person[kind + '_id']
        if number is False:
            continue
        scheme = settings[kind]
        lines += [message('Vaultwarden master access', 'Vaultwarden-Masterzugang') if kind == 'master'
                  else message('Infrastructure access', 'Infrastrukturzugang'),
                  settings[kind + '_purpose'],
                  message(f"Your share: {number} of {scheme['shares']}. Gather {scheme['threshold']} distinct shares from this set and category.",
                          f"Dein Teil: {number} von {scheme['shares']}. Sammelt {scheme['threshold']} verschiedene Teile dieses Satzes und Bereichs."),
                  message('Copy the entire share including its checksum and all blocks:', 'Den ganzen Teil mit Prüfsumme und allen Blöcken übernehmen:'),
                  shares[kind][number - 1], '']
    lines += [message('RECOVERY', 'WIEDERHERSTELLUNG'),
              message('Open START-HERE.md and follow the steps on the prepared offline computer. Choose English in the browser.',
                      'Öffne START-HIER.md am vorbereiteten Offline-Rechner und wähle Deutsch im Browser.'),
              message('SSS2 master shares can recover a second factor. A TOTP setup secret belongs in your authenticator. Use a recovery code only in the documented account recovery process.',
                      'SSS2-Masterteile können einen zweiten Faktor enthalten. Ein TOTP-Einrichtungsschlüssel gehört in den Authenticator. Einen Wiederherstellungscode nur im vorgesehenen Notfallverfahren verwenden.'),
              message('Check access using the documented account and vault. Access to a separate KDBX depends on its own credentials.',
                      'Prüft den Zugang mit dem dokumentierten Konto und Tresor. Für eine separate KDBX gelten deren eigene Zugangsdaten.'),
              message('Keep shares, passwords and vault files out of chats, cloud tools and print queues.',
                      'Schlüsselteile, Passwörter und Tresordateien aus Chats, Cloud-Diensten und Druckwarteschlangen heraushalten.')]
    return '\n'.join(lines) + '\n'


def render_html(text, language='en'):
    if language not in ('en', 'de'):
        raise ValueError('Unsupported letter language.')
    title = 'Persönlicher Notfallbrief' if language == 'de' else 'Personal emergency letter'
    return (f'<!doctype html><html lang="{language}"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
            f'<title>{title}</title><style>@page {{size:A4;margin:16mm}} '
            'body{max-width:46rem;margin:auto;padding:1rem}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>'
            '<pre>' + html.escape(text) + '</pre></html>\n')


def secure_directory(path):
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError('Output directories must be real root-owned directories with mode 0700.')


def write_private(path, content):
    # Every destination is new. Link the flushed temporary file without replacing an original.
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def generate(config, language=None):
    validate(config)
    language = language or settings_for(config['settings'])['language']
    if os.geteuid() != 0:
        raise ValueError('Run the generator locally as root.')
    for path in (Path('/root/rescue'), BASE, BASE / 'ausgaben'):
        secure_directory(path)
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError('Run in an interactive terminal without redirection.')
    run = uuid.uuid4().hex
    print(f'Creating set {run} in a new output directory.')
    if input('Create new personal envelopes? Type GENERATE: ') != 'GENERATE':
        return
    secrets = {}
    for kind in ('master', 'infra'):
        prompt = ('MASTER – current Vaultwarden master password: ' if kind == 'master'
                  else 'INFRA – agreed infrastructure password: ')
        value = getpass.getpass(prompt)
        if value != getpass.getpass('Repeat password: '):
            raise ValueError('The passwords differ.')
        secrets[kind] = value
    if secrets['master'] == secrets['infra']:
        raise ValueError('Use different passwords for master and infrastructure access.')
    bundle = prompt_second_factor(secrets['master'])
    print('Generating shares and testing every quorum …')
    shares = {
        'master': split_bundle(bundle, run, config['settings']['master']) if bundle
                  else split(secrets['master'], run, 'master', config['settings']['master']),
        'infra': split(secrets['infra'], run, 'infra', config['settings']['infra'])}
    del secrets
    del bundle
    destination = BASE / 'ausgaben' / run
    destination.mkdir(mode=0o700)
    # A failed write remains visibly incomplete; nothing is silently removed or overwritten.
    write_private(destination / 'UNVOLLSTAENDIG', 'INCOMPLETE / UNVOLLSTAENDIG. Do not distribute.\n')
    for person in config['people']:
        text = document(person, config['settings'], run, shares, language)
        write_private(destination / (person['id'] + '.txt'), text)
        write_private(destination / (person['id'] + '.html'), render_html(text, language))
    manifest = {'satz_id': run, 'erstellt_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'format': 'SSS1 password or SSS2 master bundle / independent ssss hex blocks / diffusion enabled / 01 prefix',
                'settings': config['settings'], 'people': config['people'], 'alle_quoren_geprueft': True}
    write_private(destination / 'manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    (destination / 'UNVOLLSTAENDIG').unlink()
    print(f'Created: {destination}')
    print('Print the local HTML letter for each trustee. The text file contains the same letter.')
    print('Test master and infrastructure access before distribution. Verify KDBX access separately.')


def main():
    harden()
    parser = argparse.ArgumentParser()
    parser.add_argument('--validate', action='store_true', help='Validate installed settings')
    parser.add_argument('--validate-file', type=Path, help='Validate a candidate private configuration before installing it')
    parser.add_argument('--lang', choices=('en', 'de'), help='Override the language for the new letters')
    args = parser.parse_args()
    path = args.validate_file or BASE / 'config.json'
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, encoding='utf-8') as stream:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) & 0o077):
            raise ValueError('Expected a regular private configuration file.')
        config = json.load(stream)
    if args.validate or args.validate_file:
        validate(config)
        print('Configuration valid.')
    else:
        generate(config, args.lang)


if __name__ == '__main__':
    try:
        main()
    except ValueError as exc:
        print(f'Aborted: {exc}', file=sys.stderr)
        sys.exit(1)
    except (OSError, KeyError, TypeError, subprocess.SubprocessError, getpass.GetPassWarning):
        print('Check settings, permissions and installation. Do not distribute incomplete output.', file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print('\nCancelled. Do not distribute incomplete output.', file=sys.stderr)
        sys.exit(130)
