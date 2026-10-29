"""Lecture et écriture des fichiers produits par les agents (JSON et Markdown).

L'appli lit data/ et livrables/ ; elle n'écrit que data/scoring.json
(les pondérations modifiées par Lenny).
"""
import json
import os
import tempfile
from pathlib import Path

import markdown
import nh3

STATUTS_ETAPE = {
    "a_faire": "À faire",
    "en_cours": "En cours",
    "a_valider": "À valider",
    "validee": "Validée",
}


class DonneesInvalides(Exception):
    """Un fichier de données existe mais ne peut pas être lu (JSON cassé, format inattendu)."""


def lire_json(chemin, defaut=None):
    """Lit un fichier JSON. Fichier absent : renvoie `defaut`. JSON cassé : lève DonneesInvalides."""
    chemin = Path(chemin)
    try:
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return defaut
    except json.JSONDecodeError as e:
        raise DonneesInvalides(f"{chemin.name} n'est pas un JSON valide (ligne {e.lineno}).") from e


def ecrire_json(chemin, contenu):
    """Écrit dans un fichier temporaire puis le met à la place de l'ancien :
    en cas de plantage, on ne se retrouve jamais avec un fichier à moitié écrit."""
    chemin = Path(chemin)
    fd, temporaire = tempfile.mkstemp(dir=chemin.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(contenu, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(temporaire, chemin)
    except BaseException:
        Path(temporaire).unlink(missing_ok=True)
        raise


# --- Mission -----------------------------------------------------------------

def lire_mission(racine):
    contenu = lire_json(Path(racine) / "data" / "mission.json", {"etapes": []})
    if not isinstance(contenu, dict) or not isinstance(contenu.get("etapes"), list):
        raise DonneesInvalides("mission.json doit contenir une liste « etapes ».")
    return sorted(contenu["etapes"], key=lambda e: e.get("numero", 0))


def chemin_livrable(racine, relatif):
    """Renvoie le chemin du livrable s'il est affichable, sinon None.

    Seuls les fichiers .md situés dans livrables/ sont affichés : un chemin
    comme « ../../.ssh/id_rsa » écrit dans mission.json est refusé.
    """
    if not relatif:
        return None
    dossier = (Path(racine) / "livrables").resolve()
    cible = (Path(racine) / relatif).resolve()
    if not cible.is_relative_to(dossier) or cible.suffix.lower() != ".md" or not cible.is_file():
        return None
    return cible


def rendre_markdown(texte):
    """Convertit du Markdown en HTML, puis le nettoie avec nh3.

    Les livrables reprennent du contenu trouvé sur le web : sans nettoyage, une
    balise <script> glissée dans un fichier serait exécutée par le navigateur.
    """
    html = markdown.markdown(texte, extensions=["tables", "fenced_code", "sane_lists"])
    return nh3.clean(html)


def lire_questions(racine):
    """HTML de livrables/questions-bulleo.md, ou None si le fichier n'existe pas."""
    chemin = Path(racine) / "livrables" / "questions-bulleo.md"
    if not chemin.is_file():
        return None
    return rendre_markdown(chemin.read_text(encoding="utf-8"))


# --- Pays et scoring ---------------------------------------------------------

def lire_scoring(racine):
    contenu = lire_json(Path(racine) / "data" / "scoring.json", {"criteres": [], "pays": []})
    if not isinstance(contenu, dict) or not isinstance(contenu.get("criteres"), list):
        raise DonneesInvalides("scoring.json doit contenir une liste « criteres ».")
    return contenu


def lire_fiches_pays(racine):
    """Lit toutes les fiches data/pays/*.json.

    Renvoie (fiches, erreurs) : une fiche illisible n'empêche pas d'afficher
    les autres, elle est signalée dans `erreurs`.
    """
    fiches, erreurs = {}, []
    for chemin in sorted((Path(racine) / "data" / "pays").glob("*.json")):
        try:
            fiche = lire_json(chemin)
        except DonneesInvalides as e:
            erreurs.append(str(e))
            continue
        if not isinstance(fiche, dict) or not isinstance(fiche.get("criteres"), dict):
            erreurs.append(f"{chemin.name} : format inattendu (pas de « criteres »).")
            continue
        code = str(fiche.get("code") or chemin.stem).upper()
        fiches[code] = fiche
    return fiches, erreurs


def note_critere(fiche, id_critere):
    """La note (1 à 5) d'un critère, ou None si elle manque ou est invalide."""
    critere = fiche.get("criteres", {}).get(id_critere)
    note = critere.get("note") if isinstance(critere, dict) else None
    if isinstance(note, int) and not isinstance(note, bool) and 1 <= note <= 5:
        return note
    return None


def calculer_score(fiche, criteres):
    """Score pondéré = somme (note × poids) / 100.

    Si un critère n'a pas de note, renvoie None plutôt que de compter zéro :
    un score faussement bas serait pire qu'un score absent.
    """
    total = 0
    for critere in criteres:
        note = note_critere(fiche, critere["id"])
        if note is None:
            return None
        total += note * critere["poids"]
    return round(total / 100, 2)


def classement(fiches, criteres):
    """Une ligne par pays, triée par score décroissant ; les scores incomplets à la fin."""
    lignes = []
    for code, fiche in fiches.items():
        lignes.append({
            "code": code,
            "nom": fiche.get("nom", code),
            "notes": {c["id"]: note_critere(fiche, c["id"]) for c in criteres},
            "score": calculer_score(fiche, criteres),
        })
    lignes.sort(key=lambda l: (l["score"] is None, -(l["score"] or 0), l["nom"]))
    # Rang : deux pays au même score partagent le même rang (ex æquo) ; pas de rang si score incomplet.
    for position, ligne in enumerate(lignes, start=1):
        precedente = lignes[position - 2] if position > 1 else None
        if ligne["score"] is None:
            ligne["rang"] = None
        elif precedente is not None and precedente["score"] == ligne["score"]:
            ligne["rang"] = precedente["rang"]
        else:
            ligne["rang"] = position
    return lignes


def valider_ponderations(criteres, formulaire):
    """Lit les poids saisis. Renvoie (poids, None) si tout va bien, ou (None, message d'erreur)."""
    poids = {}
    for critere in criteres:
        brut = str(formulaire.get(f"poids_{critere['id']}", "")).strip()
        try:
            valeur = int(brut)
        except ValueError:
            return None, f"Poids de « {critere['libelle']} » : nombre entier attendu."
        if not 0 <= valeur <= 100:
            return None, f"Poids de « {critere['libelle']} » : entre 0 et 100."
        poids[critere["id"]] = valeur
    total = sum(poids.values())
    if total != 100:
        return None, f"Le total des poids doit faire 100 (actuellement {total})."
    return poids, None


def ecrire_ponderations(racine, poids):
    """Enregistre les nouveaux poids dans scoring.json, sans toucher au reste du fichier."""
    scoring = lire_scoring(racine)
    for critere in scoring["criteres"]:
        critere["poids"] = poids[critere["id"]]
    ecrire_json(Path(racine) / "data" / "scoring.json", scoring)


# --- Import de prospects -----------------------------------------------------

def fichiers_import(racine):
    """Noms des fichiers JSON présents dans data/import/."""
    dossier = Path(racine) / "data" / "import"
    if not dossier.is_dir():
        return []
    return sorted(p.name for p in dossier.glob("*.json"))


def url_sure(url):
    """Vrai si l'adresse peut devenir un lien cliquable (http ou https uniquement).

    Une adresse « javascript:… » trouvée sur une page web exécuterait du code au clic.
    """
    return isinstance(url, str) and url.strip().lower().startswith(("http://", "https://"))
