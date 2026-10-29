# Étude de marché : synthèse des 3 pays analysés

Générée le 2026-10-29 à partir de `data/pays/BE.json`, `DE.json` et `CH.json`,
après un contrôle qualité et une passe de correction par pays. Matière brute
pour Lenny : chiffres et détails sont dans les fiches `fiche-be.md`,
`fiche-de.md` et `fiche-ch.md`.

Position SH de départ pour les trois pays : 3402, hypothèse à confirmer avec la
douane.

## Notes par critère (1 à 5)

| Critère | Belgique (BE) | Allemagne (DE) | Suisse (CH) |
|---|:-:|:-:|:-:|
| Demande | 4 | 5 | 4 |
| Concurrence | 2 | 2 | 2 |
| Réglementation | 4 | 3 | 3 |
| Logistique | 5 | 5 | 4 |
| Accès au marché | 3 | 3 | 3 |
| Proximité culturelle | 4 | 3 | 4 |

Le classement pondéré se calcule à l'étape 2, avec les poids de
`data/scoring.json` que Lenny peut ajuster dans l'appli.

Comparabilité limitée entre les fiches :
- devises différentes : Belgique en EUR (Eurostat), Allemagne en USD courants
  (UN Comtrade), Suisse sans donnée d'importation SH 3402 ;
- millésimes différents : population et PIB 2024 pour la Belgique, 2025 pour
  l'Allemagne et la Suisse.

## Points à vérifier

### Transverses

- Règlement (UE) 2026/405 sur les détergents (remplace le 648/2004) : texte,
  dates d'application et de transition non confirmées (BE, DE).
- Classement douanier : 3402 (dont 3402.50 en SH 2022, conditionnés pour la
  vente au détail) ; pistes 3401 pour les gels douche et 3307 (3307.41/49) pour
  les parfums d'intérieur. Tout est à confirmer avec la douane. La position
  3305 (préparations capillaires) est écartée.
- Concurrence : note 2 dans les trois pays, faute de source sur les parts de
  marché des marques et marques de distributeur.
- Coûts de transport : aucune source, cotations à demander à un transitaire.

### Belgique (BE)

- Chiffres Eurostat Comext (NC 3402, 2023-2024) à recontrôler dans la base.
- Population et PIB/hab. 2024 (Banque mondiale) à vérifier.
- Langues d'étiquetage FR/NL/DE (SPF Santé publique) ; arrêté royal du
  7 septembre 2012 non lu.
- Demande segmentée par région (côté flamand) : non sourcée.
- Canaux et centrales d'achat belges : aucune source.
- Fiche Business France « cosmétiques » utilisée faute de fiche détergents :
  indicative seulement.
- Comparatifs de prix Test-Achats : source non officielle, à examiner.

### Allemagne (DE)

- Valeurs UN Comtrade (aperçu de l'API, 2024, USD courants) à recouper avec
  Eurostat Comext ; un seul millésime consulté.
- « Premier importeur européen » : aucune source comparative, ne pas
  l'affirmer.
- Exigences allemandes : notification des détergents, loi sur les emballages
  (registre LUCID), langue d'étiquetage.
- Structure de la distribution (discount, drogeries, B2B) : aucune source.
- Indice LPI : 4,1 en 2022, existence d'une édition plus récente à vérifier.
- Restés après la passe de correction (relecture) :
  - proximité culturelle : la justification dit « aucune source trouvée »
    alors qu'elle cite un article LSA ; la note 3 repose au mieux sur cette
    source indirecte ;
  - accès au marché : le chiffre de 497,6 M USD désigne les importations
    allemandes en provenance de France (et non les importations de la France) ;
  - date de l'article LSA « Werner & Mertz tente l'hygiène » (notée 2024) à
    vérifier, il pourrait être nettement plus ancien ;
  - justification réglementation à reformuler (redite).

### Suisse (CH)

- Droit de douane exact pour SH 3402 dans le tarif Tares : exceptions
  éventuelles du chapitre 34 à confirmer.
- Importations suisses de SH 3402 : aucune source (voir Swiss-Impex ou Comext).
- Parts Coop 43 % / Migros 37,4 % (Nielsen via swissinfo, fin 2025) : non
  officielles.
- Chiffres non datés écartés : Migros et Coop environ 70 % du détail, 52 % de
  produits sans marque.
- Seuils EDTA/PDTA et interdiction des phosphates (OFEV 2023) à reconfirmer
  dans l'ORRChim.
- TVA à l'importation (8,1 % / 2,6 %) : taux applicable aux détergents à
  confirmer.
- Population (OFS 2025) et PIB/hab. (Banque mondiale 2025) à reconfirmer.
- Étiquetage (langues, mentions) et représentant ou notifiant en Suisse.
- Réglementation des gels douche et brumes d'intérieur : non analysée.
- Exportations françaises vers la Suisse 2025 : 17,9 ou 22,6 Md EUR
  (incohérence dans l'article du Trésor).
- Taux de change EUR/CHF : aucune source.
- Restés après la passe de correction (relecture) :
  - cas Briochin (Team France Export) écarté pour une date jugée douteuse
    (26/10/2026) ; une date si récente est plausible (mise à jour de la
    page) : la source mérite d'être réexaminée, elle était le seul appui sur
    le recours à des distributeurs ;
  - justification accès au marché à reformuler (« donc dont »).

## Questions ouvertes pour Bulléo

Voir `livrables/questions-bulleo.md` (prix B2B, marges, capacité, budget,
produits prioritaires, langues des étiquettes et FDS, classement douanier,
composition des formules, contacts en Suisse).
