"""Tests de l'appli, sur un dossier de données temporaire (les vraies données ne sont jamais touchées)."""
import json
from datetime import date, timedelta

import pytest

import base
import donnees
from app import create_app

CRITERES = [
    {"id": "demande", "libelle": "Demande", "poids": 25},
    {"id": "concurrence", "libelle": "Concurrence", "poids": 20},
    {"id": "reglementation", "libelle": "Réglementation", "poids": 15},
    {"id": "logistique", "libelle": "Logistique", "poids": 15},
    {"id": "acces_marche", "libelle": "Accès au marché", "poids": 15},
    {"id": "proximite_culturelle", "libelle": "Proximité culturelle", "poids": 10},
]


def fiche(code, nom, notes):
    return {
        "code": code, "nom": nom, "genere_le": "2026-10-29",
        "criteres": {
            cid: {"note": n, "justification": f"Justification {cid}.",
                  "sources": [{"intitule": "Source", "url": "https://exemple.org", "annee": 2024}]}
            for cid, n in notes.items()
        },
        "points_forts": ["Point fort A"], "risques": ["Risque B"], "a_verifier": ["Vérif C"],
    }


def ecrire(chemin, contenu):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(contenu, str):
        chemin.write_text(contenu, encoding="utf-8")
    else:
        chemin.write_text(json.dumps(contenu, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def racine(tmp_path):
    ecrire(tmp_path / "data" / "mission.json", {"etapes": [
        {"numero": 1, "nom": "Étude de marché", "statut": "validee",
         "livrable": "livrables/1-etude-marche/synthese.md", "maj": "2026-10-29"},
        {"numero": 2, "nom": "Choix d'une zone cible", "statut": "a_faire", "livrable": "../secret.md", "maj": "2026-10-29"},
        {"numero": 3, "nom": "Prospection", "statut": "a_faire", "livrable": "", "maj": "2026-10-29"},
    ]})
    ecrire(tmp_path / "data" / "scoring.json", {"criteres": CRITERES, "pays": ["BE", "DE"]})
    ecrire(tmp_path / "data" / "pays" / "BE.json",
           fiche("BE", "Belgique", dict(zip([c["id"] for c in CRITERES], [4, 2, 4, 5, 3, 4]))))
    ecrire(tmp_path / "data" / "pays" / "DE.json",
           fiche("DE", "Allemagne", dict(zip([c["id"] for c in CRITERES], [5, 3, 3, 5, 3, 3]))))
    ecrire(tmp_path / "livrables" / "1-etude-marche" / "synthese.md",
           "# Synthèse\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n<script>alert('x')</script>\n")
    ecrire(tmp_path / "livrables" / "questions-bulleo.md", "# Questions pour Bulléo\n\n- Prix B2B ?\n")
    ecrire(tmp_path / "secret.md", "SECRET")
    ecrire(tmp_path / "data" / "import" / "prospects-2026-10-29.json", [
        {"entreprise": "Hôtel Exemple", "pays": "BE", "secteur": "Hôtellerie",
         "site_web": "https://hotel.example", "contact_fonction": "Responsable achats",
         "contact_email_pro": "", "source": "https://hotel.example/contact",
         "pertinence": 4, "justification": "Gros consommateur."},
        {"entreprise": "  hôtel   exemple ", "pays": "be", "secteur": "Doublon",
         "source": "x", "pertinence": 3, "justification": "Même entreprise."},
        {"entreprise": "", "pays": "BE", "pertinence": 2},
        {"entreprise": "Nettoyage SA", "pays": "BE", "pertinence": 9},
        {"entreprise": "=Formule SA", "pays": "BE", "pertinence": 5, "justification": "Test CSV."},
    ])
    return tmp_path


@pytest.fixture
def client(racine):
    app = create_app(racine=racine, chemin_db=racine / "test.db")
    return app.test_client()


# --- Score et pondérations ---------------------------------------------------

def test_score_pondere():
    notes = dict(zip([c["id"] for c in CRITERES], [4, 2, 4, 5, 3, 4]))
    # (4×25 + 2×20 + 4×15 + 5×15 + 3×15 + 4×10) / 100 = 360 / 100
    assert donnees.calculer_score(fiche("BE", "Belgique", notes), CRITERES) == 3.6


def test_score_incomplet_si_une_note_manque():
    notes = dict(zip([c["id"] for c in CRITERES[:-1]], [4, 2, 4, 5, 3]))
    assert donnees.calculer_score(fiche("BE", "Belgique", notes), CRITERES) is None


def test_classement_par_score_decroissant(racine):
    fiches, erreurs = donnees.lire_fiches_pays(racine)
    lignes = donnees.classement(fiches, CRITERES)
    assert erreurs == []
    assert [l["code"] for l in lignes] == ["DE", "BE"]  # DE 3.80 > BE 3.60


def test_rang_partage_en_cas_d_egalite_et_absent_si_incomplet():
    ids = [c["id"] for c in CRITERES]
    fiches = {
        "BE": fiche("BE", "Belgique", dict(zip(ids, [4, 2, 4, 5, 3, 4]))),   # 3.60
        "DE": fiche("DE", "Allemagne", dict(zip(ids, [5, 2, 3, 5, 3, 3]))),  # 3.60
        "CH": fiche("CH", "Suisse", dict(zip(ids, [4, 2, 3, 4, 3, 4]))),     # 3.30
        "XX": fiche("XX", "Incomplet", dict(zip(ids[:-1], [5, 5, 5, 5, 5]))),
    }
    rangs = {l["code"]: l["rang"] for l in donnees.classement(fiches, CRITERES)}
    assert rangs == {"DE": 1, "BE": 1, "CH": 3, "XX": None}


def test_ponderations_refusees_si_total_different_de_100(client, racine):
    avant = (racine / "data" / "scoring.json").read_text(encoding="utf-8")
    formulaire = {f"poids_{c['id']}": "20" for c in CRITERES}  # total 120
    reponse = client.post("/pays/ponderations", data=formulaire)
    assert reponse.status_code == 400
    assert "120" in reponse.get_data(as_text=True)
    assert (racine / "data" / "scoring.json").read_text(encoding="utf-8") == avant


def test_ponderations_enregistrees_si_total_100(client, racine):
    poids = [30, 20, 10, 15, 15, 10]
    formulaire = {f"poids_{c['id']}": str(p) for c, p in zip(CRITERES, poids)}
    reponse = client.post("/pays/ponderations", data=formulaire)
    assert reponse.status_code == 302
    scoring = json.loads((racine / "data" / "scoring.json").read_text(encoding="utf-8"))
    assert [c["poids"] for c in scoring["criteres"]] == poids
    assert scoring["pays"] == ["BE", "DE"]  # le reste du fichier est conservé


# --- Livrables ---------------------------------------------------------------

def test_livrable_affiche_et_nettoye(client):
    page = client.get("/etape/1").get_data(as_text=True)
    assert "<table>" in page
    assert "<script>" not in page


def test_livrable_hors_du_dossier_livrables_refuse(client):
    page = client.get("/etape/2").get_data(as_text=True)
    assert "SECRET" not in page
    assert "Aucun livrable affichable" in page


# --- Pages -------------------------------------------------------------------

def test_les_trois_pages_s_affichent(client):
    accueil = client.get("/").get_data(as_text=True)
    assert "Étude de marché" in accueil and "Prix B2B" in accueil
    pays = client.get("/pays").get_data(as_text=True)
    assert "Belgique" in pays and "3.60" in pays and "3.80" in pays
    assert client.get("/prospects").status_code == 200


def test_css_versionne_et_templates_recharges(client):
    page = client.get("/").get_data(as_text=True)
    assert "/static/style.css?v=" in page  # le navigateur recharge le CSS quand il change
    assert client.application.config["TEMPLATES_AUTO_RELOAD"] is True


def test_detail_pays(client):
    page = client.get("/pays/be").get_data(as_text=True)
    assert "Justification demande." in page and "Point fort A" in page and "Vérif C" in page
    assert client.get("/pays/XX").status_code == 404


def test_lien_javascript_non_cliquable():
    assert donnees.url_sure("https://exemple.org")
    assert not donnees.url_sure("javascript:alert(1)")
    assert not donnees.url_sure(None)


# --- Prospects ---------------------------------------------------------------

def test_import_sans_doublon(client, racine):
    reponse = client.post("/prospects/importer", data={"fichier": "prospects-2026-10-29.json"},
                          follow_redirects=True)
    texte = reponse.get_data(as_text=True)
    assert "2 ajouté(s), 1 doublon(s) ignoré(s), 2 ligne(s) invalide(s)" in texte

    # Un deuxième import du même fichier n'ajoute rien : les 2 prospects déjà en base,
    # plus la ligne qui doublonnait déjà dans le fichier, soit 3 doublons.
    texte = client.post("/prospects/importer", data={"fichier": "prospects-2026-10-29.json"},
                        follow_redirects=True).get_data(as_text=True)
    assert "0 ajouté(s), 3 doublon(s) ignoré(s), 2 ligne(s) invalide(s)" in texte


def test_import_refuse_un_fichier_hors_liste(client):
    reponse = client.post("/prospects/importer", data={"fichier": "../mission.json"}, follow_redirects=True)
    assert "Choisis un fichier de la liste" in reponse.get_data(as_text=True)


def test_ajout_modification_et_doublon(client, racine):
    formulaire = {"entreprise": "Centrale Achat", "pays": "de", "statut": "a_contacter", "notes": "Premier contact."}
    assert client.post("/prospects/nouveau", data=formulaire).status_code == 302
    reponse = client.post("/prospects/nouveau", data=dict(formulaire, entreprise="centrale  achat"))
    assert reponse.status_code == 400
    assert "existe déjà" in reponse.get_data(as_text=True)

    conn = base.connecter(racine / "test.db")
    (prospect,) = base.lister(conn)
    assert prospect["pays"] == "DE"
    reponse = client.post(f"/prospects/{prospect['id']}/modifier",
                          data=dict(formulaire, statut="rdv", notes="RDV fixé."))
    assert reponse.status_code == 302
    modifie = base.obtenir(conn, prospect["id"])
    conn.close()
    assert modifie["statut"] == "rdv" and modifie["notes"] == "RDV fixé."


def test_saisie_invalide_refusee(client):
    reponse = client.post("/prospects/nouveau", data={"entreprise": "X", "pays": "Belgique", "pertinence": "7"})
    texte = reponse.get_data(as_text=True)
    assert reponse.status_code == 400
    assert "code à 2 lettres" in texte and "1 à 5" in texte


def test_relance_du_jour_et_en_retard_mises_en_evidence(client):
    aujourd_hui = date.today()
    for nom, jour, statut in [("Aujourd'hui", aujourd_hui, "contacte"),
                              ("En retard", aujourd_hui - timedelta(days=3), "relance"),
                              ("Plus tard", aujourd_hui + timedelta(days=3), "contacte"),
                              ("Gagné", aujourd_hui, "gagne")]:
        client.post("/prospects/nouveau", data={"entreprise": nom, "pays": "BE", "statut": statut,
                                                "date_relance": jour.isoformat()})
    page = client.get("/prospects").get_data(as_text=True)
    assert page.count('class="a-relancer"') == 2


def test_recherche_et_filtres(client):
    # follow_redirects : la page d'arrivée consomme le message « … ajouté », qui sinon
    # s'afficherait sur la page vérifiée ensuite et fausserait le test.
    client.post("/prospects/importer", data={"fichier": "prospects-2026-10-29.json"}, follow_redirects=True)
    client.post("/prospects/nouveau", data={"entreprise": "Firma GmbH", "pays": "DE", "statut": "rdv"},
                follow_redirects=True)
    assert "Firma GmbH" not in client.get("/prospects?pays=BE").get_data(as_text=True)
    assert "Hôtel Exemple" not in client.get("/prospects?statut=rdv").get_data(as_text=True)
    assert "Hôtel Exemple" in client.get("/prospects?q=consommateur").get_data(as_text=True)


def test_export_csv(client):
    client.post("/prospects/importer", data={"fichier": "prospects-2026-10-29.json"})
    reponse = client.get("/prospects/export.csv")
    texte = reponse.get_data(as_text=True)
    assert reponse.mimetype == "text/csv"
    assert texte.startswith("﻿Entreprise;Pays;")
    assert "Hôtel Exemple;BE;" in texte
    assert "'=Formule SA" in texte  # formule neutralisée pour Excel
