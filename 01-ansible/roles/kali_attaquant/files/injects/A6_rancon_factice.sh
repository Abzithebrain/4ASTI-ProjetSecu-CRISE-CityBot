#!/usr/bin/env bash
# INJECT A6 - CHIFFREMENT FACTICE. AUCUN vrai chiffrement.
# Le script agit UNIQUEMENT dans un repertoire de test /srv/partages_test
# (cree par l'animateur), renomme les fichiers en .locked, remplace leur
# contenu par un marqueur, et depose une note. Entierement reversible via
# A6_restaurer.sh. Ne jamais pointer ailleurs que le repertoire de test.
set -euo pipefail
CIBLE="${1:-/srv/partages_test}"
case "$CIBLE" in
  /srv/partages_test|/srv/partages_test/*) : ;;
  *) echo "Refus : ce script n'agit que sous /srv/partages_test"; exit 1 ;;
esac
[ -d "$CIBLE" ] || { echo "Repertoire de test absent : $CIBLE"; exit 1; }

echo "[A6] Chiffrement FACTICE dans $CIBLE ($(date))"
find "$CIBLE" -type f ! -name "*.locked" ! -name "RANCON.txt" | while read -r f; do
  printf 'FICHIER NEUTRALISE PAR EXERCICE (factice) - original: %s\n' "$(basename "$f")" > "$f.locked"
  rm -f "$f"
done
cat > "$CIBLE/RANCON.txt" <<'TXT'
--- NOTE DE RANCON (EXERCICE FICTIF CITYBOT) ---
Vos fichiers de TEST ont ete renommes dans le cadre de l'exercice de securite.
Ceci est une simulation. Aucun fichier reel n'est affecte, aucune cryptomonnaie
n'est demandee. Reaction attendue : isoler le serveur, preserver les preuves,
restaurer depuis la sauvegarde.
TXT
echo "[A6] Termine. $(find "$CIBLE" -name '*.locked' | wc -l) fichiers marques. Note deposee."
