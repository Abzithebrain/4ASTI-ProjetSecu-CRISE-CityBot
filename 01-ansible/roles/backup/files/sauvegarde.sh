#!/usr/bin/env bash
# Sauvegarde de la base clients et des partages vers BACKUP.
# Lance par timer systemd. Journalise dans auditd via logger.
set -euo pipefail
HORO=$(date +%F_%H%M)
DEST=/srv/backup/$HORO
mkdir -p "$DEST"

logger -t citybot-backup "Debut de sauvegarde $HORO"

# Dump PostgreSQL via le compte de sauvegarde (lecture seule)
PGPASSWORD="$DB_BACKUP_PASS" pg_dump -h "$IP_DB" -U "$DB_BACKUP_USER" "$DB_NAME" \
    > "$DEST/citybot.sql" 2>>"$DEST/erreurs.log" || logger -t citybot-backup "Echec dump SQL"

# Copie des partages exposes (si DC-FS accessible plus tard). Place-tenant.
# rsync -a dc-fs:/partages/ "$DEST/partages/" 2>/dev/null || true

gzip "$DEST/citybot.sql" 2>/dev/null || true
TAILLE=$(du -sh "$DEST" | cut -f1)
logger -t citybot-backup "Fin de sauvegarde $HORO, taille $TAILLE"

# Retention : garder 7 sauvegardes
ls -1dt /srv/backup/*/ | tail -n +8 | xargs -r rm -rf
