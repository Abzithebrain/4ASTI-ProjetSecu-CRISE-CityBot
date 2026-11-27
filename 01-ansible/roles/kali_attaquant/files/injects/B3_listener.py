#!/usr/bin/env python3
"""Collecteur de balises cote KALI (ecoute sur 8443). Inoffensif : repond 200
et journalise l'IP et l'heure de chaque balise recue."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        print(f"{datetime.now().isoformat()} balise de {self.client_address[0]} {self.path}")
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
    def log_message(self, *a): pass

if __name__ == "__main__":
    print("Listener de balises sur 0.0.0.0:8443")
    HTTPServer(("0.0.0.0", 8443), H).serve_forever()
