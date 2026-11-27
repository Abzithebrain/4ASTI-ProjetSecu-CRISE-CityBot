#!/usr/bin/env bash
# Restauration de la derniere sauvegarde saine (test de reprise, inject A8/reset).
set -euo pipefail
DERNIER=$(ls -1dt /srv/backup/*/ | head -1)
echo "Restauration depuis : $DERNIER"
gunzip -c "$DERNIER/citybot.sql.gz" | \
  PGPASSWORD="$DB_ADMIN_PASS" psql -h "$IP_DB" -U "$DB_ADMIN_USER" "$DB_NAME"
logger -t citybot-backup "Restauration effectuee depuis $DERNIER"
echo "Restauration terminee."
