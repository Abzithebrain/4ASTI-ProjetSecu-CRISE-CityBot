#!/usr/bin/env bash
# Construit les paquets navlib et le manifeste initial (version 1.4.2 courante).
set -euo pipefail
R=/srv/editeur
mkdir -p "$R/maps" "$R/paquets" "$R/src/navlib"

# 1.4.2 courante = la bibliotheque saine etiquetee 1.4.2
cp "$R/src/route_sain.py" "$R/src/navlib/route.py"
printf 'from .route import calculer_position, decalage_actuel\nVERSION="1.4.2"\n' > "$R/src/navlib/__init__.py"
tar -czf "$R/maps/navlib-1.4.2.tar.gz" -C "$R/src" navlib

# 1.4.3 saine (celle que l'editeur signe reellement)
printf 'from .route import calculer_position, decalage_actuel\nVERSION="1.4.3"\n' > "$R/src/navlib/__init__.py"
tar -czf "$R/paquets/navlib-1.4.3-saine.tar.gz" -C "$R/src" navlib

# 1.4.3 de demonstration (decalage + heartbeat)
cp "$R/src/route_demo.py" "$R/src/navlib/route.py"
tar -czf "$R/paquets/navlib-1.4.3-demo.tar.gz" -C "$R/src" navlib

H=$(sha256sum "$R/maps/navlib-1.4.2.tar.gz" | cut -d' ' -f1)
cat > "$R/maps/manifest.json" <<JSON
{"editeur":"NaviCarto SAS (simule)","produit":"navlib","version":"1.4.2",
 "fichier":"navlib-1.4.2.tar.gz","sha256":"$H","notes":"Version courante stable."}
JSON
echo "Paquets prets. Manifeste en 1.4.2."
sha256sum "$R"/maps/*.tar.gz "$R"/paquets/*.tar.gz
