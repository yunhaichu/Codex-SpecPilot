#!/bin/zsh
set -e

SCRIPT_DIR="${0:A:h}"
python3 "$SCRIPT_DIR/install_specpilot.py"

echo
echo "Codex SpecPilot install finished. Enable Codex hooks in Codex settings if needed."
echo "Press any key to close this window."
read -k 1
