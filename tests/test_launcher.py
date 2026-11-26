import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

FILES = Path(__file__).resolve().parents[1] / 'files'
sys.path.insert(0, str(FILES))
import recover


class Launcher(unittest.TestCase):
    @unittest.skipIf(os.geteuid() == 0, 'requires a non-root user')
    def test_ansible_requests_admin_password(self):
        with tempfile.TemporaryDirectory(prefix='sss admin ') as directory:
            folder = Path(directory)
            (folder / 'files').mkdir()
            shutil.copyfile(FILES.parent / 'run.sh', folder / 'run.sh')
            shutil.copyfile(FILES / 'install-voraussetzungen.sh', folder / 'files' / 'install-voraussetzungen.sh')
            programs = folder / 'programs'
            programs.mkdir()
            for program in ('python3', 'ssss-combine', 'ssss-split', 'ansible-playbook', 'sudo', 'uname'):
                executable = programs / program
                executable.write_text('#!/bin/sh\n' + ('exit 1\n' if program == 'sudo' else 'echo Linux\n' if program == 'uname' else 'printf "ARG:%s\\n" "$@"\n'))
                executable.chmod(0o700)
            result = subprocess.run(['bash', str(folder / 'run.sh')], cwd='/',
                                    env={**os.environ, 'PATH': str(programs) + os.pathsep + os.environ['PATH']},
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('ARG:--ask-become-pass', result.stdout)
            self.assertIn('All prerequisites are installed.', result.stdout)

    def test_start_from_other_directory_and_no_browser(self):
        with tempfile.TemporaryDirectory(prefix='sss launcher ') as directory:
            folder = Path(directory)
            for filename in ('start-html.sh', 'recover.py', 'notfall_entschluesselung.html', 'install-voraussetzungen.sh'):
                shutil.copyfile(FILES / filename, folder / filename)
            programs = folder / 'programs'
            programs.mkdir()
            for program, body in [('python3', '#!/bin/sh\nprintf "ARG:%s\\n" "$@"\n'),
                                  ('ssss-combine', '#!/bin/sh\nexit 0\n'),
                                  ('uname', '#!/bin/sh\necho Linux\n'),
                                  ('ssss-split', '#!/bin/sh\nexit 0\n')]:
                executable = programs / program
                executable.write_text(body)
                executable.chmod(0o700)
            environment = {**os.environ, 'PATH': str(programs) + os.pathsep + os.environ['PATH']}
            for option in ([], ['--no-browser']):
                result = subprocess.run(['bash', str(folder / 'start-html.sh'), *option], cwd='/',
                                        env=environment, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('ARG:' + str((folder / 'recover.py').resolve()), result.stdout)
                self.assertIn('ARG:--web', result.stdout)
                self.assertEqual('ARG:--open-browser' in result.stdout, not option)
            (folder / 'recover.py').unlink()
            result = subprocess.run(['bash', str(folder / 'start-html.sh')], env=environment,
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Missing file', result.stderr)
            self.assertNotIn('ARG:', result.stdout)

    def test_browser_failure_keeps_manual_fallback(self):
        with patch.dict(os.environ, {'DISPLAY': ':0'}), \
                patch.object(recover.webbrowser, 'open', side_effect=OSError), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            recover.open_local_browser('http://127.0.0.1:1234/test/')
            self.assertIn('manually', output.getvalue())

    def test_headless_does_not_launch_browser(self):
        with patch.object(recover.sys, 'platform', 'linux'), patch.dict(os.environ, {}, clear=True), \
                patch.object(recover.webbrowser, 'open') as browser, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            recover.open_local_browser('http://127.0.0.1:1234/test/')
            browser.assert_not_called()
            self.assertIn('No graphical session', output.getvalue())

    def test_parent_disconnect_stops_only_own_server(self):
        from unittest.mock import Mock
        server = Mock()
        recover.stop_when_input_closes(server, io.BytesIO(b''))
        server.shutdown.assert_called_once_with()
