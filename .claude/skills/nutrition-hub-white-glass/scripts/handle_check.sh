#!/usr/bin/env bash
# Where is a Nutrition Hub username taken, and are there look-alike accounts? (owner, 2026-11-26: "Add sherlock")
# Sherlock (MIT, github.com/sherlock-project/sherlock, pinned 0.16.2) checks the brand's platforms only.
#
#   bash handle_check.sh                          # nutritionhubkhanna + nutritionhub_khanna / -khanna / .khanna
#   bash handle_check.sh nutritionhubkhanna_official
#   bash handle_check.sh somename --all-sites     # every site Sherlock knows (400+), on the owner's computer
#
# Rule: only for Nutrition Hub's own handles and look-alikes of them (spotting impersonation, choosing a free handle);
# never to look up a private person. Results are "an account with this name exists", not who runs it: check by eye.
# This cloud environment only reaches allowed hosts, so most sites show "Proxy Error" here; run it on the owner's
# computer, or allow the platform hosts in the environment first.
set -euo pipefail
VENV="${SHERLOCK_VENV:-$HOME/.local/sherlock}"
if [ ! -x "$VENV/bin/sherlock" ]; then
  # its own venv: the system pip can't build Sherlock's "stem" dependency on Debian Python
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q --upgrade pip setuptools wheel
  "$VENV/bin/pip" install -q "sherlock-project==0.16.2"
fi
SITES=(Instagram YouTube TikTok threads Twitter Pinterest Snapchat LinkedIn Reddit Telegram GitHub)
names=()
all=0
for a in "$@"; do
  if [ "$a" = "--all-sites" ]; then all=1; else names+=("$a"); fi
done
[ ${#names[@]} -eq 0 ] && names=("nutritionhubkhanna" "nutritionhub{?}khanna")
args=(--print-all --no-color --timeout 15 --local)
if [ $all -eq 0 ]; then for s in "${SITES[@]}"; do args+=(--site "$s"); done; fi
out="${HANDLE_CHECK_DIR:-.}"
mkdir -p "$out"
"$VENV/bin/sherlock" "${names[@]}" "${args[@]}" --csv --folderoutput "$out"
echo "CSV per name in $out (one row per site: found, not found, or error)"
