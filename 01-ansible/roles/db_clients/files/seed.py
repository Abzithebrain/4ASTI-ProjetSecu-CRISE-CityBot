#!/usr/bin/env python3
"""Remplit la base CityBot avec des donnees fictives reproductibles.
Aucune donnee reelle : noms, emails et IBAN sont generes."""
import hashlib
import os
import random
import sys
from datetime import datetime, timedelta

import psycopg2

random.seed(42)  # jeu de donnees identique a chaque remise a zero

NB_CLIENTS = int(os.environ.get("NB_CLIENTS", 500))
NB_COURSES = int(os.environ.get("NB_COURSES", 3000))

PRENOMS = ["Awa", "Moussa", "Fatou", "Ibrahima", "Camille", "Lucas", "Marie", "Yacine",
           "Sophie", "Omar", "Julie", "Karim", "Nina", "Paul", "Aminata", "Theo",
           "Chloe", "Samba", "Elise", "Hugo"]
NOMS = ["Diallo", "Martin", "Ndiaye", "Bernard", "Fall", "Dubois", "Sow", "Robert",
        "Cisse", "Richard", "Ba", "Petit", "Gueye", "Durand", "Sarr", "Leroy"]
QUARTIERS = ["Centre-ville", "Gare", "Technopole", "Port", "Universite", "Parc des Expos",
             "Hopital", "Aeroport", "Zone Nord", "Quartier des Lacs"]


def hash_mdp(mdp: str) -> str:
    return hashlib.sha256(mdp.encode()).hexdigest()


def iban_fictif(i: int) -> str:
    return f"FR76{3000 + i % 900:04d}{1000 + i % 9000:04d}{i:012d}"


def main():
    conn = psycopg2.connect(
        host="127.0.0.1",
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASS"],
    )
    cur = conn.cursor()

    cur.execute("SELECT count(*) FROM clients")
    if cur.fetchone()[0] > 0:
        print("Base deja peuplee, rien a faire.")
        return

    # Les mots de passe sont volontairement faibles et devinables : c'est l'export
    # de la table (inject A4) qui doit permettre de rejouer les comptes en F1.
    clients = []
    for i in range(1, NB_CLIENTS + 1):
        prenom = random.choice(PRENOMS)
        nom = random.choice(NOMS)
        email = f"{prenom.lower()}.{nom.lower()}{i}@client.citybot.lab"
        mdp = f"{prenom}{1000 + i}!"
        clients.append((nom, prenom, email, f"+2217{random.randint(0,9)}{random.randint(1000000,9999999)}",
                        hash_mdp(mdp), iban_fictif(i)))
    cur.executemany(
        "INSERT INTO clients (nom, prenom, email, telephone, mot_de_passe, iban_rembours)"
        " VALUES (%s,%s,%s,%s,%s,%s)", clients)

    # Fichier de correspondance email/mot de passe : sert a l'animateur et a
    # l'inject F1 (l'attaquant est cense l'avoir obtenu par l'export A4).
    with open("/opt/citybot/comptes_clients.csv", "w") as f:
        f.write("email,mot_de_passe\n")
        for i in range(1, NB_CLIENTS + 1):
            c = clients[i - 1]
            prenom = c[1]
            f.write(f"{c[2]},{prenom}{1000 + i}!\n")

    debut = datetime.now() - timedelta(days=90)
    courses = []
    for _ in range(NB_COURSES):
        cid = random.randint(1, NB_CLIENTS)
        courses.append((cid, random.choice(QUARTIERS), random.choice(QUARTIERS),
                        f"VEH-{random.randint(1,3):03d}", round(random.uniform(3.5, 42.0), 2),
                        random.choices(["terminee", "annulee"], weights=[92, 8])[0],
                        debut + timedelta(minutes=random.randint(0, 90 * 24 * 60))))
    cur.executemany(
        "INSERT INTO courses (client_id, depart, arrivee, vehicule, montant, statut, reservee_le)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s)", courses)

    cur.execute("""
        INSERT INTO transactions (course_id, client_id, type, montant, beneficiaire, reference, cree_le)
        SELECT c.id, c.client_id,
               CASE WHEN c.statut = 'annulee' THEN 'remboursement' ELSE 'paiement' END,
               c.montant, cl.iban_rembours,
               'TX-' || lpad(c.id::text, 8, '0'), c.reservee_le
        FROM courses c JOIN clients cl ON cl.id = c.client_id
    """)

    conn.commit()
    cur.execute("SELECT count(*) FROM clients")
    n_cli = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM courses")
    n_cou = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM transactions")
    n_tx = cur.fetchone()[0]
    print(f"Base peuplee : {n_cli} clients, {n_cou} courses, {n_tx} transactions.")
    print("Correspondance comptes : /opt/citybot/comptes_clients.csv")


if __name__ == "__main__":
    sys.exit(main())
