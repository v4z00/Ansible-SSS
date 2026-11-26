#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
bash "$script_dir/files/install-voraussetzungen.sh"
printf 'Starting the local generator. Administrator access to /root/rescue is required.\n'
if (( EUID == 0 )); then
  exec /usr/bin/python3 /root/rescue/SSS/bin/generate.py "$@"
elif command -v sudo >/dev/null 2>&1; then
  exec sudo -- /usr/bin/python3 /root/rescue/SSS/bin/generate.py "$@"
elif command -v su >/dev/null 2>&1; then
  printf 'Enter the root password.\n'
  printf -v root_command '%q ' /usr/bin/python3 /root/rescue/SSS/bin/generate.py "$@"
  exec su -s /bin/bash -c "$root_command" root
else
  printf 'Local setup requires sudo, su or a root shell.\n' >&2
  exit 1
fi
