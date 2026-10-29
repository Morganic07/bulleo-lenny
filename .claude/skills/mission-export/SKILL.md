---
name: mission-export
description: Workflow de la mission export de Lenny chez Bulléo, en 5 étapes (étude de marché, zone cible, prospection, devis, contrat). Reprend à la première étape non validée de data/mission.json, délègue le travail aux agents du projet, puis s'arrête pour validation. « /mission-export etape 2 » force une étape.
argument-hint: "[etape N]"
disable-model-invocation: true
---

# Mission export Bulléo

Tu pilotes la mission de Lenny. Le CLAUDE.md du projet s'applique en entier.

Argument reçu : `$ARGUMENTS`

## Règles du workflow

1. **Une seule étape par passage.** Tu exécutes une étape, puis tu t'arrêtes.
2. **Tu délègues.** Analyse pays, prospection, éléments douaniers, brouillons
   commerciaux et contrôle qualité sont faits par les agents du projet
   (outil Agent, `subagent_type` ci-dessous). Tu ne refais jamais leur
   travail toi-même, même partiellement. Si un agent échoue, dis-le à Lenny.
3. **Tu ne décides pas à la place de Lenny.** Choix des pays, de la zone, des
   secteurs, des prix : c'est lui. Données internes de Bulléo manquantes :
   question dans `livrables/questions-bulleo.md`, jamais d'hypothèse.
4. **Aucun envoi.** Tout ce qui part vers l'extérieur est un brouillon.

## Choisir l'étape

1. Lis `data/mission.json`.
2. Si `$ARGUMENTS` contient un numéro d'étape (`etape 2`, `2`), c'est cette
   étape. Si une étape antérieure n'est pas `validee`, préviens Lenny avant
   de commencer, sans bloquer.
3. Sinon, prends la première étape dont le statut n'est pas `validee`.
4. Si cette étape est `a_valider` : ne refais rien. Rappelle en 5 lignes ce
   qui a été produit et demande à Lenny s'il valide (AskUserQuestion :
   « Je valide » / « À reprendre »). « À reprendre » : demande ce qui ne va
   pas, puis reprends l'étape.
5. Si toutes les étapes sont `validee`, dis-le et arrête-toi.

## Cycle de vie d'une étape

- **Au démarrage** : `statut` → `en_cours`, `maj` → date du jour.
- **À la fin** : `statut` → `a_valider`, `livrable` → chemin du livrable
  principal, `maj` → date du jour. Puis résume en 5 lignes au plus ce qui a
  été produit (fichiers, résultats clés, points à vérifier) et **ARRÊTE-TOI** :
  demande à Lenny de valider.
- **Validation** : uniquement sur un accord explicite de Lenny (« je
  valide », « ok pour l'étape N »…). Alors `statut` → `validee`, `maj` → date
  du jour. Annonce l'étape suivante et demande s'il veut la lancer maintenant.
  Sans réponse claire, ne passe pas à la suite.

Modifie `data/mission.json` champ par champ, sans toucher aux autres étapes.

## Étape 1 : étude de marché

1. Propose 5 pays candidats, une ligne de justification chacun, en mêlant UE,
   Europe hors UE et hors Europe. Justifications qualitatives : aucun chiffre
   sans source. Puis demande à Lenny d'en retenir 3 avec AskUserQuestion.
   Une question n'accepte que 4 options : pose deux questions à choix
   multiples (« Pays de l'UE » et « Pays hors UE »), et vérifie que le total
   retenu fait exactement 3. Sinon, redemande.
2. Lance **3 agents `analyste-marche` en parallèle** (trois appels Agent dans
   le même message), un par pays, en donnant à chacun le nom du pays et son
   code ISO2.
3. Quand les trois ont fini, lance **`controleur-qualite`** sur les 3 fichiers
   `data/pays/<CODE>.json` et les 3 fiches `livrables/1-etude-marche/fiche-<code>.md`.
   Pour chaque fichier « à corriger », renvoie les points du rapport à un
   `analyste-marche` pour ce pays. **Une seule fois** par pays : ce qui reste
   non corrigé ensuite va dans la liste « à vérifier » de la synthèse.
4. Écris `livrables/1-etude-marche/synthese.md` : tableau comparatif (pays en
   colonnes, les 6 critères en lignes, notes de 1 à 5), puis la liste
   consolidée des points à vérifier, pays par pays. Ne recopie que ce que
   disent les fiches.
5. Ajoute les 3 codes dans le tableau `pays` de `data/scoring.json`, sans
   doublon et sans toucher aux pondérations.

Livrable principal : `livrables/1-etude-marche/synthese.md`.

## Étape 2 : choix de la zone cible

1. Rappelle à Lenny qu'il peut ajuster les pondérations dans l'appli (module
   Pays) avant de décider, et propose-lui de le faire maintenant.
2. Lis `data/scoring.json` et les fiches `data/pays/<CODE>.json` des pays
   listés. Calcule pour chaque pays : somme (note × poids) / 100. Présente un
   classement avec le détail par critère. Si la somme des poids n'est pas 100,
   ou si une fiche n'a pas l'un des 6 critères, signale-le au lieu de
   compléter.
3. Pose à Lenny 2 ou 3 questions pour l'aider à trancher (capacité à servir
   un pays lointain, langue, appétit pour le risque, mode d'entrée…). Ne
   recommande pas un pays à sa place.
4. Une fois son choix fait, écris `livrables/2-zone-cible/choix-zone.md` :
   pays retenu, raisons (avec la note pondérée), risques, modes d'entrée
   possibles (export direct, importateur-distributeur, agent commercial…).
   Si un skill `plan-dev-export` est disponible, appuie-toi dessus.

Livrable principal : `livrables/2-zone-cible/choix-zone.md`.

## Étape 3 : prospection

1. Demande à Lenny les secteurs à cibler et le nombre de prospects voulus
   (15 au maximum ; au-delà, ramène à 15 et dis-le).
2. Lance l'agent **`prospecteur`** avec le pays retenu (lu dans
   `livrables/2-zone-cible/choix-zone.md`), les secteurs et le nombre.
3. Lance **`controleur-qualite`** sur le fichier
   `data/import/prospects-AAAA-MM-JJ.json` produit.
4. Indique à Lenny d'importer ce fichier dans l'appli (module Prospects).
5. Propose de lancer **`redacteur-commercial`** pour un premier mail type de
   prospection. Ne le lance que si Lenny accepte.

Livrable principal : le fichier `data/import/prospects-AAAA-MM-JJ.json`.

## Étape 4 : devis

1. Demande à Lenny : le prospect, les produits, les quantités et le **prix
   départ usine**. Ce prix est une donnée Bulléo : ne le suppose jamais, ne
   le déduis jamais des prix de bulleo.eu. S'il ne l'a pas, ajoute la
   question à `livrables/questions-bulleo.md` et prépare le devis avec la
   case vide.
2. Lance **`expert-douane-logistique`** pour le pays du prospect et les
   produits concernés.
3. Écris `livrables/4-devis/devis-<prospect>.md` (nom du prospect en
   minuscules, sans espaces) à partir de `livrables/4-devis/elements-<code>.md` :
   - l'Incoterm retenu et ce qu'il inclut ;
   - un calcul ligne par ligne (prix départ usine × quantités, emballage,
     transport jusqu'au point convenu, dédouanement export, fret principal,
     assurance, etc., selon l'Incoterm) ;
   - toute valeur inconnue (fret, assurance, frais de transitaire) en case
     clairement signalée `[À COMPLÉTER : cotation transitaire]`, jamais
     estimée ;
   - pas de total chiffré tant qu'une case reste vide : écris le total
     partiel et liste ce qui manque.

Livrable principal : `livrables/4-devis/devis-<prospect>.md`.

## Étape 5 : contrat

1. Écris `livrables/5-contrat/checklist-contrat.md` : une case à cocher et
   une courte explication pour chaque point. Incoterm, mode de paiement,
   délais, langue du contrat, loi applicable, règlement des litiges,
   conditions de livraison. Reprends ce qui a été décidé aux étapes
   précédentes, et marque « à décider » ce qui ne l'a pas été.
2. Rappelle clairement que le contrat doit être validé par Bulléo, et par un
   juriste si besoin. Rédiger ou valider un contrat n'est pas le rôle de
   cet assistant.

Livrable principal : `livrables/5-contrat/checklist-contrat.md`.
