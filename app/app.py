"""Bulléo Export Hub : appli web locale de suivi de la mission export.

Lancement : ./lancer.sh à la racine du projet, puis http://127.0.0.1:5000
"""
import os
import sqlite3
from datetime import date
from pathlib import Path

from flask import Flask, Response, abort, flash, g, redirect, render_template, request, url_for

import base
import donnees

DOSSIER_APP = Path(__file__).resolve().parent


def date_fr(valeur):
    """« 2026-10-29 » devient « 29/10/2026 » ; une valeur qui n'est pas une date est affichée telle quelle."""
    try:
        return date.fromisoformat(str(valeur)).strftime("%d/%m/%Y")
    except ValueError:
        return valeur


def version_css():
    """Date de dernière modification du CSS, ajoutée à son adresse (style.css?v=…) :
    dès que le fichier change, le navigateur le recharge au lieu de garder l'ancien en cache."""
    return int((DOSSIER_APP / "static" / "style.css").stat().st_mtime)


def create_app(racine=None, chemin_db=None):
    """Fabrique l'appli. Les tests passent un autre dossier pour ne pas toucher aux vraies données."""
    racine = Path(racine or DOSSIER_APP.parent)
    chemin_db = chemin_db or DOSSIER_APP / "prospects.db"

    app = Flask(__name__)
    app.secret_key = os.urandom(24)  # nécessaire aux messages flash ; change à chaque lancement
    # Sans debug, Flask garde les templates en mémoire : une page modifiée resterait à l'ancienne
    # version tant que l'appli tourne, alors que le CSS, lu sur le disque, serait déjà le nouveau.
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    base.initialiser(chemin_db)
    app.jinja_env.globals.update(url_sure=donnees.url_sure, version_css=version_css)
    app.jinja_env.filters["date_fr"] = date_fr

    def bd():
        """Une connexion SQLite par requête, fermée automatiquement à la fin."""
        if "bd" not in g:
            g.bd = base.connecter(chemin_db)
        return g.bd

    @app.teardown_appcontext
    def fermer_bd(_erreur):
        conn = g.pop("bd", None)
        if conn is not None:
            conn.close()

    @app.errorhandler(donnees.DonneesInvalides)
    def donnees_invalides(erreur):
        return render_template("erreur.html", message=str(erreur)), 500

    # --- Module 1 : suivi de mission ------------------------------------------

    @app.route("/")
    def mission():
        return render_template(
            "mission.html",
            etapes=donnees.lire_mission(racine),
            statuts=donnees.STATUTS_ETAPE,
            questions=donnees.lire_questions(racine),
        )

    @app.route("/etape/<int:numero>")
    def etape(numero):
        etape = next((e for e in donnees.lire_mission(racine) if e.get("numero") == numero), None)
        if etape is None:
            abort(404)
        chemin = donnees.chemin_livrable(racine, etape.get("livrable"))
        contenu = donnees.rendre_markdown(chemin.read_text(encoding="utf-8")) if chemin else None
        return render_template("livrable.html", etape=etape, contenu=contenu, statuts=donnees.STATUTS_ETAPE)

    # --- Module 2 : pays ------------------------------------------------------

    def page_pays(saisie=None, erreur=None):
        scoring = donnees.lire_scoring(racine)
        fiches, erreurs_fiches = donnees.lire_fiches_pays(racine)
        return render_template(
            "pays.html",
            criteres=scoring["criteres"],
            lignes=donnees.classement(fiches, scoring["criteres"]),
            erreurs_fiches=erreurs_fiches,
            total=sum(c["poids"] for c in scoring["criteres"]),
            saisie=saisie or {},
            erreur=erreur,
        )

    @app.route("/pays")
    def pays():
        return page_pays()

    @app.post("/pays/ponderations")
    def ponderations():
        scoring = donnees.lire_scoring(racine)
        poids, erreur = donnees.valider_ponderations(scoring["criteres"], request.form)
        if erreur:
            # On réaffiche la page avec ce que Lenny a tapé, pour qu'il n'ait pas à tout ressaisir.
            return page_pays(saisie=request.form, erreur=erreur), 400
        donnees.ecrire_ponderations(racine, poids)
        flash("Pondérations enregistrées dans data/scoring.json.", "ok")
        return redirect(url_for("pays"))

    @app.route("/pays/<code>")
    def pays_detail(code):
        fiches, _ = donnees.lire_fiches_pays(racine)
        fiche = fiches.get(code.upper())
        if fiche is None:
            abort(404)
        criteres = donnees.lire_scoring(racine)["criteres"]
        return render_template(
            "pays_detail.html",
            code=code.upper(),
            fiche=fiche,
            criteres=criteres,
            score=donnees.calculer_score(fiche, criteres),
        )

    # --- Module 3 : prospects -------------------------------------------------

    def filtres():
        return {cle: request.args.get(cle, "").strip() for cle in ("q", "pays", "statut")}

    @app.route("/prospects")
    def prospects():
        f = filtres()
        lignes = base.lister(bd(), f["q"], f["pays"], f["statut"])
        aujourd_hui = date.today().isoformat()
        return render_template(
            "prospects.html",
            lignes=lignes,
            a_relancer={p["id"] for p in lignes if base.a_relancer(p, aujourd_hui)},
            pays_liste=base.pays_presents(bd()),
            statuts=base.STATUTS,
            filtres=f,
        )

    def formulaire(prospect, erreurs, titre, code_http=200):
        return render_template(
            "prospect_form.html", prospect=prospect, erreurs=erreurs, titre=titre, statuts=base.STATUTS
        ), code_http

    @app.route("/prospects/nouveau", methods=["GET", "POST"])
    def prospect_nouveau():
        titre = "Nouveau prospect"
        if request.method == "GET":
            return formulaire({}, [], titre)
        prospect, erreurs = base.valider(request.form)
        if not erreurs:
            try:
                base.ajouter(bd(), prospect)
                flash(f"Prospect « {prospect['entreprise']} » ajouté.", "ok")
                return redirect(url_for("prospects"))
            except sqlite3.IntegrityError as e:
                if not base.est_doublon(e):
                    raise
                erreurs.append("Ce prospect existe déjà (même entreprise, même pays).")
        return formulaire(request.form, erreurs, titre, 400)

    @app.route("/prospects/<int:id_prospect>/modifier", methods=["GET", "POST"])
    def prospect_modifier(id_prospect):
        existant = base.obtenir(bd(), id_prospect)
        if existant is None:
            abort(404)
        titre = f"Modifier « {existant['entreprise']} »"
        if request.method == "GET":
            return formulaire(existant, [], titre)
        prospect, erreurs = base.valider(request.form)
        if not erreurs:
            try:
                base.modifier(bd(), id_prospect, prospect)
                flash(f"Prospect « {prospect['entreprise']} » modifié.", "ok")
                return redirect(url_for("prospects"))
            except sqlite3.IntegrityError as e:
                if not base.est_doublon(e):
                    raise
                erreurs.append("Un autre prospect porte déjà ce nom dans ce pays.")
        return formulaire(request.form, erreurs, titre, 400)

    @app.route("/prospects/importer", methods=["GET", "POST"])
    def prospects_importer():
        fichiers = donnees.fichiers_import(racine)
        if request.method == "GET":
            return render_template("importer.html", fichiers=fichiers)

        nom = request.form.get("fichier", "")
        # Seul un nom présent dans data/import/ est accepté : impossible de viser un autre fichier.
        if nom not in fichiers:
            flash("Choisis un fichier de la liste.", "erreur")
            return redirect(url_for("prospects_importer"))
        try:
            bilan = base.importer(bd(), donnees.lire_json(Path(racine) / "data" / "import" / nom))
        except (ValueError, donnees.DonneesInvalides) as e:
            flash(f"{nom} : {e}", "erreur")
            return redirect(url_for("prospects_importer"))

        message = (f"{nom} : {bilan['ajoutes']} ajouté(s), {bilan['doublons']} doublon(s) ignoré(s), "
                   f"{bilan['invalides']} ligne(s) invalide(s).")
        if bilan["details"]:
            message += " " + " ; ".join(bilan["details"][:5])
        flash(message, "erreur" if bilan["invalides"] else "ok")
        return redirect(url_for("prospects"))

    @app.route("/prospects/export.csv")
    def prospects_export():
        f = filtres()
        lignes = base.lister(bd(), f["q"], f["pays"], f["statut"])
        nom = f"prospects-{date.today().isoformat()}.csv"
        return Response(
            base.exporter_csv(lignes),
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={nom}"},
        )

    return app


if __name__ == "__main__":
    # 127.0.0.1 : l'appli n'est visible que depuis cet ordinateur.
    # debug=False : la console de débogage de Flask permet d'exécuter du code, on la laisse fermée.
    create_app().run(host="127.0.0.1", port=5000, debug=False)
