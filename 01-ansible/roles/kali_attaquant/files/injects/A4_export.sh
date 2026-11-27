#!/usr/bin/env bash
# INJECT A4 - export massif de la table clients.
# Trace attendue : journaux PostgreSQL (log_statement=all) + volume sortant.
set -euo pipefail
: "${IP_DB:?}"; : "${DB_ADMIN_USER:?}"; : "${DB_ADMIN_PASS:?}"
SORTIE=/tmp/export_clients_$(date +%s).csv
echo "[A4] Export de la base clients vers $SORTIE"
PGPASSWORD="$DB_ADMIN_PASS" psql -h "$IP_DB" -U "$DB_ADMIN_USER" citybot \
  -c "\copy (SELECT id,nom,prenom,email,telephone,iban_rembours FROM clients) TO '$SORTIE' CSV HEADER"
echo "[A4] $(wc -l < "$SORTIE") lignes exportees."
echo "     Ce fichier joue le role de la fuite : il alimente la branche fraude (F1)."
