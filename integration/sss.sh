#!/usr/bin/env bash
set -euo pipefail
umask 077
root=${CONTROL_PROJECT_ROOT:?}/playbooks/security/sss
case "${1:-}" in
  ''|--help|-h) printf '%s\n' 'control sss --check    Preview local setup' 'control sss --setup    Install the recovery kit on this controller' ;;
  --check) [[ $# == 1 ]] || exit 2; exec bash "$root/run.sh" --check ;;
  --setup) [[ $# == 1 ]] || exit 2; exec bash "$root/run.sh" ;;
  *) echo 'Use control sss --help.' >&2; exit 2 ;;
esac
