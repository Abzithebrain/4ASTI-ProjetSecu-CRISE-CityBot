#!/usr/bin/env bash
# INJECT B2 - declenche la publication de la mise a jour de demo chez l'editeur.
# Lance le script cote TIERS-EDITEUR via SSH (l'animation passe par KALI).
set -euo pipefail
: "${IP_EDITEUR:?}"
echo "[B2] Publication de la mise a jour 1.4.3 (empreinte incoherente) sur l'editeur"
ssh -o StrictHostKeyChecking=no "localuser@$IP_EDITEUR" "sudo /srv/editeur/publier-maj-demo.sh"
echo "[B2] Les vehicules vont detecter la 1.4.3 au prochain cycle et l'installer."
