#!/usr/bin/env bash
# Install missing prerequisites from the system package repositories.
set -euo pipefail
umask 077
# Terminals opened from Finder may lack Homebrew in PATH.
if [[ "$(uname -s)" == Darwin ]]; then
  export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
fi
case "${1:-}" in
  '') ;;
  --ansible) ;;
  -h|--help)
    printf 'bash install-voraussetzungen.sh [--ansible]\nRequired packages: python3, ssss. Use --ansible to include ansible-core.\n'
    exit 0 ;;
  *) printf 'Unknown option. See --help.\n' >&2; exit 2 ;;
esac
(( $# <= 1 )) || { printf 'Too many arguments.\n' >&2; exit 2; }

packages=()
command -v python3 >/dev/null 2>&1 || packages+=(python3)
if ! command -v ssss-combine >/dev/null 2>&1 || ! command -v ssss-split >/dev/null 2>&1; then
  packages+=(ssss)
fi
if [[ "${1:-}" == '--ansible' ]] && ! command -v ansible-playbook >/dev/null 2>&1; then
  packages+=(ansible-core)
fi
if (( ${#packages[@]} == 0 )); then
  printf 'All prerequisites are installed.\n'
  exit 0
fi
if [[ "$(uname -s)" == Darwin ]]; then
  if (( EUID == 0 )); then
    printf 'On macOS, run the launcher as a regular user. Homebrew will request permissions.\n' >&2
    exit 1
  fi
  if ! command -v brew >/dev/null 2>&1; then
    printf 'Downloading the Homebrew installer. It will request administrator access.\n'
    brew_installer="$(mktemp -t sss-homebrew)"
    trap 'rm -f -- "$brew_installer"' EXIT
    curl --fail --silent --show-error --location https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh -o "$brew_installer"
    /bin/bash "$brew_installer"
  fi
  command -v brew >/dev/null 2>&1 || { printf 'Homebrew installation is incomplete.\n' >&2; exit 1; }
  brew_packages=()
  for package in "${packages[@]}"; do
    case "$package" in
      python3) brew_packages+=(python) ;;
      ansible-core) brew_packages+=(ansible) ;;
      *) brew_packages+=("$package") ;;
    esac
  done
  brew install "${brew_packages[@]}"
  printf 'macOS prerequisites installed.\n'
  exit 0
fi
if [[ ! -r /etc/os-release ]]; then
  printf 'This installer requires Debian, Ubuntu or macOS.\n' >&2
  exit 1
fi
. /etc/os-release
case " ${ID:-} ${ID_LIKE:-} " in
  *' debian '*|*' ubuntu '*) ;;
  *) printf 'Install prerequisites manually on this system. Automatic Linux setup supports Debian and Ubuntu.\n' >&2; exit 1 ;;
esac
command -v apt-get >/dev/null 2>&1 || { printf 'apt-get is unavailable.\n' >&2; exit 1; }
printf 'Installing missing packages: %s\n' "${packages[*]}"
printf 'This step requires package repositories and administrator access.\n'
script_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/$(basename -- "${BASH_SOURCE[0]}")"
if (( EUID != 0 )); then
  if command -v sudo >/dev/null 2>&1; then
    exec sudo -- /bin/bash "$script_path" "$@"
  elif command -v su >/dev/null 2>&1; then
    printf 'sudo is unavailable. Enter the root password when prompted.\n'
    printf -v root_command '%q ' /bin/bash "$script_path" "$@"
    exec su -s /bin/bash -c "$root_command" root
  else
    printf 'Ask an administrator to install the prerequisites.\n' >&2
    exit 1
  fi
fi
apt-get update
apt-get install -y -- "${packages[@]}"
printf 'Prerequisites installed.\n'
