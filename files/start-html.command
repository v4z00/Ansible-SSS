#!/bin/bash
# macOS: Double-click in Finder or run bash start-html.command
set -uo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)" || exit 1
bash "$script_dir/start-html.sh" "$@"
result=$?
if (( result != 0 && result != 130 )); then
  printf '\nStartup failed. Read the message above. Press Enter to close this window.\n'
  read -r _
fi
exit "$result"
