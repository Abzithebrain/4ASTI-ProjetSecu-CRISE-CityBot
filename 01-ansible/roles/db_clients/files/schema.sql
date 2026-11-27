-- Schema de la base clients CityBot Mobility. Donnees entierement fictives.
CREATE TABLE IF NOT EXISTS clients (
    id            SERIAL PRIMARY KEY,
    nom           TEXT NOT NULL,
    prenom        TEXT NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    telephone     TEXT,
    mot_de_passe  TEXT NOT NULL,          -- hash SHA-256 (laboratoire)
    iban_rembours TEXT,                   -- coordonnees de remboursement (cible F2)
    cree_le       TIMESTAMP DEFAULT now(),
    modifie_le    TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS courses (
    id          SERIAL PRIMARY KEY,
    client_id   INTEGER REFERENCES clients(id),
    depart      TEXT,
    arrivee     TEXT,
    vehicule    TEXT,
    montant     NUMERIC(8,2),
    statut      TEXT DEFAULT 'terminee',  -- terminee / annulee / en_cours
    reservee_le TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS transactions (
    id           SERIAL PRIMARY KEY,
    course_id    INTEGER REFERENCES courses(id),
    client_id    INTEGER REFERENCES clients(id),
    type         TEXT,                    -- paiement / remboursement
    montant      NUMERIC(8,2),
    beneficiaire TEXT,
    reference    TEXT,
    cree_le      TIMESTAMP DEFAULT now()
);

-- Journal applicatif des modifications de profil : preuve attendue pour F2.
CREATE TABLE IF NOT EXISTS journal_profil (
    id         SERIAL PRIMARY KEY,
    client_id  INTEGER REFERENCES clients(id),
    champ      TEXT,
    avant      TEXT,
    apres      TEXT,
    ip_source  TEXT,
    cree_le    TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_courses_client ON courses(client_id);
CREATE INDEX IF NOT EXISTS idx_tx_client ON transactions(client_id);
