#!/usr/bin/env bash
set -euo pipefail
umask 077
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
case "$#:${1:-}" in
  0:) bash files/install-voraussetzungen.sh --ansible ;;
  1:--check) command -v ansible-playbook >/dev/null || { echo 'Install ansible-core before running a preview.' >&2; exit 1; } ;;
  1:--help) echo 'bash run.sh [--check]'; exit 0 ;;
  *) echo 'Usage: bash run.sh [--check]' >&2; exit 2 ;;
esac
become_args=()
if (( EUID != 0 )); then
  if command -v sudo >/dev/null 2>&1; then
    sudo -n true 2>/dev/null || become_args+=(--ask-become-pass)
  elif command -v su >/dev/null 2>&1; then
    become_args+=(--become-method=su --ask-become-pass)
  else
    echo 'Local setup requires administrator privileges.' >&2; exit 1
  fi
fi
exec ansible-playbook -i localhost, -c local --limit localhost setup.yml "${become_args[@]}" "$@"
