#!/usr/bin/env bash
# Keep this launcher alongside the recovery tools.
set -euo pipefail
umask 077
if [[ "$(uname -s)" == Darwin ]]; then
  export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
fi

case "${1:-}" in
  -h|--help)
    printf 'Start: bash start-html.sh [--no-browser]\nPress Ctrl+C in the terminal to stop.\n'
    exit 0
    ;;
  ''|--no-browser) ;;
  *) printf 'Unknown option. Usage: bash start-html.sh --help\n' >&2; exit 2 ;;
esac
if (( $# > 1 )); then
  printf 'Too many arguments. Usage: bash start-html.sh --help\n' >&2
  exit 2
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
for filename in recover.py notfall_entschluesselung.html install-voraussetzungen.sh; do
  if [[ ! -r "$script_dir/$filename" ]]; then
    printf 'Missing file or read permission: %s\n' "$script_dir/$filename" >&2
    printf 'Keep all four tool files in the same directory.\n' >&2
    exit 1
  fi
done
bash "$script_dir/install-voraussetzungen.sh"

printf 'Offline recovery. The first share identifies the required quorum.\n'
printf 'Keep this terminal open. Press Ctrl+C to stop.\n\n'
if [[ "${1:-}" == '--no-browser' ]]; then
  exec python3 "$script_dir/recover.py" --web
fi
exec python3 "$script_dir/recover.py" --web --open-browser
