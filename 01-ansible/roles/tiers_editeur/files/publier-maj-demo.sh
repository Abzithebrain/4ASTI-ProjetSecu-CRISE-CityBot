#!/usr/bin/env bash
set -euo pipefail
R=/srv/editeur
H_ANNONCE=$(sha256sum "$R/paquets/navlib-1.4.3-saine.tar.gz" | cut -d' ' -f1)
cp "$R/paquets/navlib-1.4.3-demo.tar.gz" "$R/maps/navlib-1.4.3.tar.gz"
H_SERVI=$(sha256sum "$R/maps/navlib-1.4.3.tar.gz" | cut -d' ' -f1)
cat > "$R/maps/manifest.json" <<JSON
{"editeur":"NaviCarto SAS (simule)","produit":"navlib","version":"1.4.3",
 "fichier":"navlib-1.4.3.tar.gz","sha256":"$H_ANNONCE",
 "notes":"Mise a jour cartes secteur nord + bibliotheque navigation."}
JSON
echo "[B2] Manifeste 1.4.3 publie."
echo "     empreinte annoncee : $H_ANNONCE"
echo "     empreinte servie   : $H_SERVI   <- ecart volontaire a detecter"
