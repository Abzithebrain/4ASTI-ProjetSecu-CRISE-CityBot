#!/usr/bin/env bash
set -euo pipefail
R=/srv/editeur
cp "$R/paquets/navlib-1.4.3-saine.tar.gz" "$R/maps/navlib-1.4.3.tar.gz"
H=$(sha256sum "$R/maps/navlib-1.4.3.tar.gz" | cut -d' ' -f1)
cat > "$R/maps/manifest.json" <<JSON
{"editeur":"NaviCarto SAS (simule)","produit":"navlib","version":"1.4.3",
 "fichier":"navlib-1.4.3.tar.gz","sha256":"$H","notes":"Republication apres verification."}
JSON
echo "[B8] Version saine republiee. Empreinte coherente : $H"
