#!/usr/bin/env bash
# INJECT A2 - connexion de nuit avec le compte de l'ex-administrateur.
# Trace attendue : 4624 sur DC-FS (etape 2) + flux OPNsense.
# Ici (phase Linux), on materialise la connexion par un acces SSH/psql au SI
# avec le compte svc_admin, depuis KALI, hors horaires.
set -euo pipefail
: "${IP_DB:?}"; : "${DB_ADMIN_USER:?}"; : "${DB_ADMIN_PASS:?}"
echo "[A2] Connexion svc_admin depuis KALI vers le SI ($(date))"
PGPASSWORD="$DB_ADMIN_PASS" psql -h "$IP_DB" -U "$DB_ADMIN_USER" citybot \
  -c "SELECT current_user, inet_server_addr(), now();"
