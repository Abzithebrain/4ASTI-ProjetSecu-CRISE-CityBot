#!/usr/bin/env bash
# Remise a zero de l'inject A6 : retire les .locked et la note.
set -euo pipefail
CIBLE="${1:-/srv/partages_test}"
find "$CIBLE" -name "*.locked" -delete
rm -f "$CIBLE/RANCON.txt"
echo "Marqueurs factices retires de $CIBLE."
