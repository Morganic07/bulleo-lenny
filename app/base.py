"""Base SQLite des prospects (mini-CRM)."""
import csv
import io
import sqlite3
from datetime import date, datetime

STATUTS = {
    "a_contacter": "À contacter",
    "contacte": "Contacté",
    "relance": "Relancé",
    "rdv": "RDV",
    "devis_envoye": "Devis envoyé",
    "gagne": "Gagné",
    "perdu": "Perdu",
}

# Champs modifiables dans le formulaire, dans l'ordre d'affichage.
CHAMPS = [
    "entreprise", "pays", "secteur", "site_web", "contact_fonction",
    "contact_email_pro", "source", "pertinence", "statut", "date_relance", "notes",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS prospects (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  entreprise        TEXT NOT NULL,
  pays              TEXT NOT NULL,
  secteur           TEXT,
  site_web          TEXT,
  contact_fonction  TEXT,
  contact_email_pro TEXT,
  source            TEXT,
  pertinence        INTEGER CHECK (pertinence BETWEEN 1 AND 5),
  statut            TEXT NOT NULL DEFAULT 'a_contacter'
                    CHECK (statut IN ('a_contacter','contacte','relance','rdv',
                                      'devis_envoye','gagne','perdu')),
  date_relance      TEXT,
  notes             TEXT,
  cree_le           TEXT NOT NULL,
  modifie_le        TEXT NOT NULL,
  cle_doublon       TEXT NOT NULL UNIQUE
);
"""


def connecter(chemin_db):
    conn = sqlite3.connect(chemin_db)
    conn.row_factory = sqlite3.Row  # accès aux colonnes par leur nom : ligne["entreprise"]
    return conn


def initialiser(chemin_db):
    """Crée la table si elle n'existe pas encore."""
    conn = connecter(chemin_db)
    try:
        conn.executescript(SCHEMA)
    finally:
        conn.close()


def cle_doublon(entreprise, pays):
    """« Hôtel  X » et « hôtel x » en Belgique donnent la même clé : un seul prospect."""
    return " ".join(entreprise.split()).casefold() + "|" + pays.strip().upper()


def _texte(valeur):
    return "" if valeur is None else str(valeur).strip()


def valider(saisie):
    """Contrôle une saisie (formulaire ou ligne d'import).

    Renvoie (prospect_propre, erreurs). Si `erreurs` est vide, le prospect peut
    être enregistré.
    """
    p = {champ: _texte(saisie.get(champ)) for champ in CHAMPS}
    erreurs = []

    if not p["entreprise"]:
        erreurs.append("L'entreprise est obligatoire.")

    p["pays"] = p["pays"].upper()
    if len(p["pays"]) != 2 or not p["pays"].isalpha():
        erreurs.append("Le pays doit être un code à 2 lettres (BE, DE, CH…).")

    if p["pertinence"]:
        try:
            p["pertinence"] = int(p["pertinence"])
        except ValueError:
            p["pertinence"] = None
            erreurs.append("La pertinence doit être un nombre de 1 à 5.")
        else:
            if not 1 <= p["pertinence"] <= 5:
                erreurs.append("La pertinence doit être un nombre de 1 à 5.")
    else:
        p["pertinence"] = None

    p["statut"] = p["statut"] or "a_contacter"
    if p["statut"] not in STATUTS:
        erreurs.append("Statut inconnu.")

    if p["date_relance"]:
        try:
            date.fromisoformat(p["date_relance"])
        except ValueError:
            erreurs.append("La date de relance doit être au format AAAA-MM-JJ.")

    if p["contact_email_pro"] and "@" not in p["contact_email_pro"]:
        erreurs.append("L'email pro n'a pas l'air d'une adresse email.")

    # Champs facultatifs vides : on stocke NULL plutôt qu'une chaîne vide.
    for champ in CHAMPS:
        if p[champ] == "":
            p[champ] = None
    return p, erreurs


def _maintenant():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def ajouter(conn, p):
    """Ajoute un prospect validé. Lève sqlite3.IntegrityError si c'est un doublon."""
    maintenant = _maintenant()
    colonnes = CHAMPS + ["cree_le", "modifie_le", "cle_doublon"]
    valeurs = [p[c] for c in CHAMPS] + [maintenant, maintenant, cle_doublon(p["entreprise"], p["pays"])]
    conn.execute(
        f"INSERT INTO prospects ({', '.join(colonnes)}) VALUES ({', '.join('?' * len(colonnes))})",
        valeurs,
    )
    conn.commit()


def modifier(conn, id_prospect, p):
    """Met à jour un prospect validé. Lève sqlite3.IntegrityError si le nouveau nom crée un doublon."""
    affectations = ", ".join(f"{c} = ?" for c in CHAMPS)
    valeurs = [p[c] for c in CHAMPS] + [_maintenant(), cle_doublon(p["entreprise"], p["pays"]), id_prospect]
    conn.execute(
        f"UPDATE prospects SET {affectations}, modifie_le = ?, cle_doublon = ? WHERE id = ?",
        valeurs,
    )
    conn.commit()


def est_doublon(erreur):
    """Vrai si l'IntegrityError vient de la contrainte d'unicité (et pas d'une autre règle)."""
    return "UNIQUE" in str(erreur) and "cle_doublon" in str(erreur)


def obtenir(conn, id_prospect):
    ligne = conn.execute("SELECT * FROM prospects WHERE id = ?", (id_prospect,)).fetchone()
    return dict(ligne) if ligne else None


def lister(conn, q="", pays="", statut=""):
    """Prospects filtrés par texte libre, pays et statut, triés par nom d'entreprise."""
    sql = "SELECT * FROM prospects WHERE 1 = 1"
    parametres = []
    if q:
        sql += (" AND (entreprise LIKE ? OR secteur LIKE ? OR contact_fonction LIKE ?"
                " OR site_web LIKE ? OR notes LIKE ?)")
        parametres += [f"%{q}%"] * 5
    if pays:
        sql += " AND pays = ?"
        parametres.append(pays.upper())
    if statut:
        sql += " AND statut = ?"
        parametres.append(statut)
    sql += " ORDER BY entreprise COLLATE NOCASE"
    return [dict(l) for l in conn.execute(sql, parametres)]


def pays_presents(conn):
    return [l["pays"] for l in conn.execute("SELECT DISTINCT pays FROM prospects ORDER BY pays")]


def a_relancer(prospect, aujourd_hui=None):
    """Vrai si la date de relance est aujourd'hui ou dépassée, sauf pour un prospect gagné ou perdu."""
    aujourd_hui = aujourd_hui or date.today().isoformat()
    return (
        bool(prospect.get("date_relance"))
        and prospect.get("statut") not in ("gagne", "perdu")
        and prospect["date_relance"] <= aujourd_hui  # les dates AAAA-MM-JJ se comparent comme du texte
    )


def importer(conn, lignes):
    """Ajoute les prospects d'un fichier data/import/ sans créer de doublon.

    Renvoie un bilan : nombre d'ajouts, de doublons ignorés, de lignes invalides
    (avec la raison des premières).
    """
    if not isinstance(lignes, list):
        raise ValueError("Le fichier doit contenir une liste de prospects.")
    bilan = {"ajoutes": 0, "doublons": 0, "invalides": 0, "details": []}
    for numero, ligne in enumerate(lignes, start=1):
        if not isinstance(ligne, dict):
            bilan["invalides"] += 1
            bilan["details"].append(f"ligne {numero} : format inattendu")
            continue
        saisie = {c: ligne.get(c) for c in CHAMPS if c not in ("statut", "date_relance", "notes")}
        if ligne.get("justification"):
            saisie["notes"] = f"Justification (import) : {ligne['justification']}"
        prospect, erreurs = valider(saisie)
        if erreurs:
            bilan["invalides"] += 1
            bilan["details"].append(f"ligne {numero} : {erreurs[0]}")
            continue
        try:
            ajouter(conn, prospect)
            bilan["ajoutes"] += 1
        except sqlite3.IntegrityError as e:
            if not est_doublon(e):
                raise
            bilan["doublons"] += 1
    return bilan


COLONNES_CSV = [
    ("entreprise", "Entreprise"), ("pays", "Pays"), ("secteur", "Secteur"),
    ("site_web", "Site web"), ("contact_fonction", "Fonction du contact"),
    ("contact_email_pro", "Email pro"), ("source", "Source"), ("pertinence", "Pertinence"),
    ("statut", "Statut"), ("date_relance", "Prochaine relance"), ("notes", "Notes"),
    ("cree_le", "Créé le"), ("modifie_le", "Modifié le"),
]


def _cellule_csv(valeur):
    """Neutralise une cellule qui commence par = + - @ : sinon Excel l'exécuterait comme une formule."""
    if valeur is None:
        return ""
    texte = str(valeur)
    if texte and texte[0] in "=+-@\t\r":
        return "'" + texte
    return texte


def exporter_csv(prospects):
    """CSV séparé par des points-virgules, lisible directement par Excel en français."""
    tampon = io.StringIO()
    ecrivain = csv.writer(tampon, delimiter=";")
    ecrivain.writerow([titre for _, titre in COLONNES_CSV])
    for p in prospects:
        ligne = dict(p, statut=STATUTS.get(p["statut"], p["statut"]))
        ecrivain.writerow([_cellule_csv(ligne.get(champ)) for champ, _ in COLONNES_CSV])
    return "﻿" + tampon.getvalue()  # le ﻿ (BOM) indique l'UTF-8 à Excel : les accents s'affichent bien
