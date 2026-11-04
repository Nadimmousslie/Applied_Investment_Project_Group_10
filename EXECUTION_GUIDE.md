# Guide d'exécution — QVMM

Ce manuel permet à une personne qui découvre le projet de l'exécuter du chargement des données jusqu'à la validation des résultats. Il complète le [`README.md`](README.md), qui présente la stratégie et l'architecture.

**Conventions**
- Toutes les commandes sont lancées **depuis la racine du projet** (`Applied_Investment_Project_Group_10/`), avec l'environnement virtuel activé (`source .venv/bin/activate`). Les scripts calculent leurs chemins à partir de leur propre emplacement : ils fonctionnent aussi depuis un autre dossier.
- « Valeur de référence » = ce qu'affiche une exécution correcte avec les données WRDS du projet (téléchargement du 28 octobre et du 3 novembre 2026). Avec d'autres extractions, les ordres de grandeur doivent rester proches.
- Dates : *t* = date de **formation** du portefeuille (fin de mois) ; le rendement correspondant est daté *t+1*.

---

## Partie A — Feuille de route chronologique

L'ordre ci-dessous découle des dépendances réelles du code (chaque script lit les fichiers écrits par les précédents).

### Étape 1 — Préparation de l'environnement
- **Commandes**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate              # Windows : .venv\Scripts\activate
  pip install -r code/requirements.txt
  python -c "import pandas, numpy, scipy, matplotlib, pyarrow; print('ok')"
  ```
- **Fichiers nécessaires** : `code/requirements.txt`.
- **Résultat attendu** : `ok`.
- **Pour passer à l'étape suivante** : l'import fonctionne sans erreur.

### Étape 2 — Mise en place et import des données
- **Modules** : `01b_import_csv.py` (données WRDS), `01_extract_wrds.py --only french` (facteurs French).
- **Commandes**
  ```bash
  mkdir -p data/raw/csv/crsp_daily
  # copier les fichiers WRDS (voir module 01b) et q5_factors_monthly.csv (voir README, section 4)
  python code/01b_import_csv.py
  python code/01_extract_wrds.py --only french
  ```
- **Fichiers nécessaires** : `data/raw/csv/crsp_monthly.*`, `compustat.*`, `ccm_link.*`, `data/raw/csv/crsp_daily/*`, `data/raw/q5_factors_monthly.csv`, accès internet.
- **Résultats attendus** : `data/raw/*.parquet`, `data/raw/crsp_daily/1970.parquet … 2025.parquet` (56 fichiers), `data/raw/french_ff5.parquet`, `french_mom.parquet`, `french_ff3_daily.parquet`.
- **Pour passer à l'étape suivante** : 01b affiche `format détecté : CIZ` et `crsp_daily/ : 56 années (1970 -> 2025)`, sans ligne `[ATTENTION]` ; les trois fichiers `french_*.parquet` existent.

### Étape 3 — Nettoyage et construction du panel
- **Modules** : `02_crsp_clean.py`, `03_compustat_op.py`, `04_signals.py`.
- **Commande** : `python code/main.py --to 4`
- **Résultats attendus** : `data/clean/crsp_m.parquet`, `op.parquet`, `panel.parquet`.
- **Pour passer à l'étape suivante** : 04 affiche `Volatilité : 126 jours de rendements journaliers` et environ 1 200 à 1 950 titres éligibles par mois, sans ligne `[ATTENTION]`.

### Étape 4 — Construction des portefeuilles et contrôle bloquant
- **Module** : `05_portfolios.py`.
- **Commande** : `python code/main.py --only 5`
- **Résultats attendus** : `output/portfolios/*_returns.parquet` et `*_weights.parquet` (9 portefeuilles), `output/tables/T0_controle_P1.csv`.
- **Pour passer à l'étape suivante** : `Contrôle P1 OK : corrélation avec UMD = 0.92` (au moins 0,8 exigé).

### Étape 5 — Analyses
- **Modules** : `06_course_tests.py`, `07_performance.py`, `08_costs.py`, `09_periods_crashes.py`, `10_robustness.py`.
- **Commande** : `python code/main.py --from 6 --to 10`
- **Résultats attendus** : tableaux T1 à T11, figures F5 et F6.
- **Pour passer à l'étape suivante** : chaque étape se termine par `[NN] terminé en … s`.

### Étape 6 — Figures
- **Module** : `11_figures.py`.
- **Commande** : `python code/main.py --only 11`
- **Résultats attendus** : F1 à F4 dans `output/figures/`.

### Étape 7 — Validation des résultats
- Comparer les messages aux valeurs de référence de la partie D.
- Ouvrir `output/tables/T0_controle_P1.csv`, `T5_performance.csv` et les figures F1 à F3.
- `git status` : seuls `output/tables/` et `output/figures/` doivent apparaître parmi les fichiers modifiés (les données et les parquet sont exclus par `.gitignore`).

> Les étapes 3 à 6 peuvent être lancées en une seule commande : `python code/main.py`.

---

## Partie B — Tableau récapitulatif des modules

| Ordre | Module | Objectif | Inputs | Outputs | Dépendances |
|---|---|---|---|---|---|
| — | `00_config.py` | paramètres et chemins | — | dossiers `data/`, `output/` | aucune |
| — | `lib.py` | fonctions communes | `00_config` | — | `00_config` |
| 1a | `01b_import_csv.py` | importer les CSV WRDS | `data/raw/csv/*` | `data/raw/crsp_monthly`, `compustat_funda`, `ccm_link`, `crsp_bidask_monthly` (.parquet), `data/raw/crsp_daily/YYYY.parquet` | fichiers WRDS |
| 1a′ | `01_extract_wrds.py` | variante : extraire depuis WRDS en Python | accès WRDS | mêmes fichiers que 01b (sans bid/ask journalier) | compte WRDS |
| 1b | `01_extract_wrds.py --only french` | facteurs Fama-French | internet | `data/raw/french_ff5`, `french_mom`, `french_ff3_daily` (.parquet) | aucune |
| 2 | `02_crsp_clean.py` | univers CRSP et drapeaux | `crsp_monthly`, `crsp_bidask_monthly` | `data/clean/crsp_m.parquet` | 1a |
| 3 | `03_compustat_op.py` | BE, OP, règle de juin, lien CCM | `compustat_funda`, `ccm_link` | `data/clean/op.parquet` | 1a |
| 4 | `04_signals.py` | signaux, vol, bêta, univers éligible | `crsp_m`, `op`, `crsp_daily/`, `french_ff3_daily` | `data/clean/panel.parquet` | 2, 3, 1b |
| 5 | `05_portfolios.py` | P1 à P5-B, contrôle P1/UMD | `panel`, French | `output/portfolios/*`, T0 | 4, 1b |
| 6 | `06_course_tests.py` | tests du cours | `panel` | T1, T1b, T2a, T2b, T3 (EW, VW), T4 (tous, large caps) | 4 |
| 7 | `07_performance.py` | performance, alphas, GRS, spanning | portefeuilles, French, q | T5, T6, T6b, T6c, T7 | 5 |
| 8 | `08_costs.py` | coûts de transaction | portefeuilles, `panel`, French | T8, T8b, F6 | 5 |
| 9 | `09_periods_crashes.py` | sous-périodes et crashs | portefeuilles, `panel`, French | T9, T10, F5 | 5 |
| 10 | `10_robustness.py` | robustesse | `panel`, P1/P5, French | T11 | 5 |
| 11 | `11_figures.py` | figures de l'article | portefeuilles, `panel`, French | F1, F2, F3, F4 | 5 |
| — | `main.py` | orchestration 02 → 11 | tous les précédents | tous les précédents | — |

Les étapes 6 à 11 ne dépendent pas les unes des autres : après l'étape 5, elles peuvent être lancées dans n'importe quel ordre.

---

## Partie C — Fiches détaillées par module

### Module 00 — `00_config.py` (configuration)
1. **Objectif** : rassembler en un seul endroit tous les choix du projet, fixés avant de regarder les résultats.
2. **Fonctionnement** : définit les chemins (`ROOT`, `DATA_RAW`, `DATA_CLEAN`, `OUT_TABLES`, `OUT_FIGS`), crée les dossiers manquants, et expose le dictionnaire `CFG` : période (`sample_start` 1975-01, `sample_end` 2025-12), univers (`min_price` 5 $, `size_nyse_pct` 0,20, financières exclues, 2 ans de Compustat, filtres CIZ), signaux (`mom_window` (11, 1), au moins 8 rendements, OP winsorisée 1 %/99 %, vol sur 126 jours avec au moins 100 observations, repli sur 36 mois), construction (score 50/50, déciles 10 %/90 % NYSE, filtre de vol au 80e percentile, plafond 5 %, règle 10 %/20 %), définition des 9 portefeuilles, évaluation (6 lags Newey-West, coûts 5/10/25/50 bps, sous-périodes, fenêtres de crash), fichiers de facteurs.
3. **Inputs** : aucun.
4. **Outputs** : dossiers `data/raw/`, `data/raw/crsp_daily/`, `data/clean/`, `output/tables/`, `output/figures/`.
5. **Dépendances** : aucune. Importé par tous les autres scripts.
6. **Commande** : n'est pas lancé seul. Contrôle : `python -c "import importlib, sys; sys.path.insert(0, 'code'); print(importlib.import_module('00_config').CFG['sample_start'])"` affiche `1975-01`.
7. **Résultats attendus** : aucun affichage quand il est importé.
8. **Vérifications** : toute modification d'un paramètre change les résultats ; elle doit être discutée et justifiée dans le commit.
9. **Erreurs potentielles** : `ModuleNotFoundError: 00_config` si l'on déplace un script hors de `code/` ; les scripts doivent rester dans le même dossier.

### Module 01b — `01b_import_csv.py` (import des CSV WRDS) — voie utilisée par le groupe
1. **Objectif** : convertir les fichiers téléchargés sur le site WRDS en fichiers parquet standardisés, identiques à ceux de `01_extract_wrds.py`.
2. **Fonctionnement**
   - `import_monthly` : ne lit que les colonnes utiles du fichier « all » ; détecte le format (CIZ ou ancien CRSP) ; applique les filtres d'univers CIZ de `CFG["ciz_filters"]` (actions ordinaires, sociétés US, NYSE/AMEX/NASDAQ, titre actif) ; en CIZ, `MthRet` inclut déjà le rendement de délisting ; en ancien format, recombine `(1 + RET)(1 + DLRET) − 1`.
   - `import_compustat` : filtres INDL / STD / D / C ; vérifie les 15 variables ; `LT` et `FYEAR` absents sont mis à vide avec un message.
   - `import_ccm` : liens LU/LC, principal P/C, date de fin manquante = lien toujours actif.
   - `import_daily` : lit par blocs de 2 millions de lignes tous les fichiers du dossier `crsp_daily/` ; écrit un parquet par année ; extrait le bid/ask du dernier jour coté de chaque mois ; signale les années manquantes.
3. **Inputs** (dans `data/raw/csv/`, extensions `.csv`, `.csv.gz`, `.zip` ou `.txt`)
   - `crsp_monthly.*` : CRSP CIZ mensuel (`crsp.msf_v2`) ;
   - `compustat.*` : Compustat Fundamentals Annual ;
   - `ccm_link.*` : table de liens ;
   - `crsp_daily/*` : CRSP CIZ journalier, un ou plusieurs fichiers (colonnes utilisées : `PERMNO`, `DlyCalDt`, `DlyRet`, et `DlyBid`, `DlyAsk` si présentes) ;
   - ancien format CRSP uniquement : `crsp_delist.*`.
4. **Outputs** : `data/raw/crsp_monthly.parquet`, `compustat_funda.parquet`, `ccm_link.parquet`, `crsp_bidask_monthly.parquet`, `data/raw/crsp_daily/YYYY.parquet`.
5. **Dépendances** : aucune (première étape).
6. **Commande** : `python code/01b_import_csv.py` (tout) ou `python code/01b_import_csv.py --only monthly|compustat|ccm|daily`.
7. **Résultats attendus** (valeurs de référence)
   ```
   CRSP mensuel : crsp_monthly.zip, 4,712,731 lignes ...
     format détecté : CIZ
     -> crsp_monthly.parquet : 3,305,725 lignes, 25,650 titres, 1970-01 -> 2025-12
     [info] LT absent : mis à vide (impact négligeable)
   Compustat -> compustat_funda.parquet : 333,439 lignes, 27,854 firmes
   CCM -> ccm_link.parquet : 32,306 liens
     -> crsp_daily/ : 56 années (1970 -> 2025)
     -> crsp_bidask_monthly.parquet : bid/ask de fin de mois, 4,075,895 titres-mois
   ```
8. **Vérifications** : `format détecté : CIZ` ; aucune ligne `[ATTENTION] années de journalier manquantes` ; 56 fichiers dans `data/raw/crsp_daily/`.
9. **Erreurs potentielles**
   - `Fichier introuvable` : nom ou dossier incorrect (respecter `crsp_monthly`, `compustat`, `ccm_link`, et le sous-dossier `crsp_daily/`).
   - `Compustat : variables manquantes [...]` : retélécharger Compustat avec les variables listées.
   - `SHRCD et EXCHCD sont indispensables` : ancien format sans ces colonnes, retélécharger.
   - Processus interrompu (`Killed`, `MemoryError`) pendant le mensuel : mémoire insuffisante (8 Go recommandés).
   - `[ATTENTION] années de journalier manquantes` : un fichier du journalier manque ; sans lui, les titres de ces années n'ont pas de volatilité et sortent de l'univers.

### Module 01 — `01_extract_wrds.py` (extraction WRDS en Python et facteurs French)
1. **Objectif** : extraire directement CRSP, Compustat et le lien CCM depuis WRDS en Python (alternative à 01b), et télécharger les facteurs de Kenneth French.
2. **Fonctionnement** : se connecte à WRDS (`WRDS_USERNAME`), vérifie que les colonnes demandées existent dans les tables CIZ (`resolve`), extrait le mensuel, Compustat, le lien et le journalier année par année (reprend là où il s'est arrêté). `--only french` télécharge les fichiers zip de French (FF5 mensuel, Momentum mensuel, FF3 journalier), lit le premier tableau de chaque fichier, convertit les pourcentages en décimal et date les mois en fin de mois, **sans connexion WRDS**.
3. **Inputs** : compte WRDS (sauf `--only french`) ; accès internet.
4. **Outputs** : mêmes fichiers que 01b (le journalier ne contient que les rendements, pas le bid/ask) ; `data/raw/french_ff5.parquet`, `french_mom.parquet`, `french_ff3_daily.parquet`.
5. **Dépendances** : aucune.
6. **Commandes**
   - facteurs French (indispensable dans tous les cas) : `python code/01_extract_wrds.py --only french`
   - extraction WRDS complète : `python code/01_extract_wrds.py` ; sans le journalier : `--skip-daily` ; une table : `--only monthly|compustat|ccm|daily`.
7. **Résultats attendus** : pour chaque facteur, une ligne `ff5 : 1963-07 -> …, colonnes [...]`, puis `q-factors : trouvé` si `q5_factors_monthly.csv` est présent.
8. **Vérifications** : les trois fichiers `french_*.parquet` existent ; la dernière date couvre décembre 2025.
9. **Erreurs potentielles**
   - `ProxyError`, `ConnectionError` : pas d'accès internet vers `mba.tuck.dartmouth.edu`.
   - Erreur d'authentification WRDS : vérifier `WRDS_USERNAME` et le mot de passe.
   - Colonne absente d'une table CIZ : corriger seulement le dictionnaire `MSF_COLS` en tête du script.

### Module 02 — `02_crsp_clean.py` (univers CRSP)
1. **Objectif** : préparer le fichier CRSP mensuel nettoyé et les drapeaux qui définissent l'univers à chaque date.
2. **Fonctionnement** : met les dates en fin de mois ; supprime les doublons titre × mois ; reprend le bid/ask du journalier si le mensuel n'en a pas ; calcule la capitalisation ME (|prix| × actions, ou `MthCap`) et sa somme au niveau de l'entreprise (`me_permco`) ; crée les drapeaux `nyse`, `is_fin` (SIC 6000–6999), `price_ok` (prix ≥ 5 $) et `size_ok` (ME de l'entreprise ≥ 20e percentile NYSE du mois).
3. **Inputs** : `data/raw/crsp_monthly.parquet`, `data/raw/crsp_bidask_monthly.parquet` (facultatif).
4. **Outputs** : `data/clean/crsp_m.parquet`.
5. **Dépendances** : 01b (ou 01).
6. **Commande** : `python code/main.py --only 2` (ou `python code/02_crsp_clean.py`).
7. **Résultats attendus** : `Bid/ask repris du journalier : 86.0% des lignes couvertes`, un tableau du nombre de titres par année (par exemple 1 664 titres hors financières passant les filtres en 1975), `Rendements manquants : 0.44%`, `Écrit : …crsp_m.parquet (3,291,476 lignes)`.
8. **Vérifications** : rendements manquants inférieurs à 1 % ; le nombre de titres NYSE par an reste entre environ 1 300 et 1 800.
9. **Erreurs potentielles** : `SIC (siccd) absent ou vide` : le CRSP mensuel a été téléchargé sans `SICCD`, le retélécharger.

### Module 03 — `03_compustat_op.py` (Operating Profitability)
1. **Objectif** : calculer la Quality (OP) et la valeur comptable BE de chaque entreprise, et dater leur disponibilité sans look-ahead.
2. **Fonctionnement** : BE = SH + TXDITC − PS (SH = SEQ, sinon CEQ + PSTK, sinon AT − LT ; PS = PSTKRV, sinon PSTKL, sinon PSTK) ; OP = (REVT − COGS − XSGA − XINT) / BE si REVT et au moins un poste de coût sont disponibles et BE > 0 ; supprime la première année de chaque firme (biais de backfill) ; règle de juin : l'exercice clos pendant l'année civile *y* est utilisé de fin juin *y+1* à fin mai *y+2* ; rattache chaque gvkey à son permno par le lien CCM valide en juin.
3. **Inputs** : `data/raw/compustat_funda.parquet`, `data/raw/ccm_link.parquet`.
4. **Outputs** : `data/clean/op.parquet` (une ligne par permno et par juin).
5. **Dépendances** : 01b (ou 01).
6. **Commande** : `python code/main.py --only 3`.
7. **Résultats attendus** : `Compustat : 327,838 firmes-années, 27,854 firmes`, `Lag datadate -> premier usage : min 5.9 mois, médiane 6.0, max 17.0`, `OP : percentiles 1/50/99 = [-3.076 0.186 1.44 ]`, `Écrit : …op.parquet (284,100 lignes)`.
8. **Vérifications** : le délai minimal doit être d'au moins 5,9 mois (le script s'arrête sinon) ; OP médiane autour de 0,19.
9. **Erreurs potentielles** : `AssertionError: Look-ahead` si un exercice était utilisé moins de 6 mois après sa clôture (problème de dates dans les données).

### Module 04 — `04_signals.py` (signaux et panel)
1. **Objectif** : construire le panel mensuel titre × date contenant tous les signaux connus en *t* et le rendement réalisé en *t+1*.
2. **Fonctionnement**
   - **Momentum** : somme glissante des log-rendements de *t−11* à *t−1* (au moins 8 sur 11), puis exponentielle ; momentum 6-1 de *t−5* à *t−1* pour la robustesse.
   - **Rendement futur** : `ret_next` = rendement du mois *t+1* (résultat, jamais signal).
   - **OP et BE** : rattachées par la règle de juin ; log BE/ME avec la ME de décembre (ME convertie de milliers en millions de dollars pour être dans l'unité de Compustat).
   - **Volatilité et bêta** (`daily_vol_beta`, année par année) : écart-type des 126 derniers rendements journaliers jusqu'à *t* inclus, annualisé par √252 (au moins 100 observations) ; bêta de Dimson = b0 + b1 de la régression multiple du rendement du titre sur le marché du jour et de la veille (marché = MKT-RF + RF de French), sur la même fenêtre. Sans fichier journalier : volatilité sur 36 mois de rendements mensuels et bêta vide.
   - **Univers éligible** : `price_ok`, `size_ok`, momentum, OP et BE > 0 disponibles, hors financières, volatilité disponible ; puis OP winsorisée à 1 %/99 % chaque mois sur cet univers.
3. **Inputs** : `data/clean/crsp_m.parquet`, `data/clean/op.parquet`, `data/raw/crsp_daily/*.parquet`, `data/raw/french_ff3_daily.parquet`.
4. **Outputs** : `data/clean/panel.parquet`.
5. **Dépendances** : 02, 03, facteurs French.
6. **Commande** : `python code/main.py --only 4`.
7. **Résultats attendus** : `vol/bêta 1970 ok` … `vol/bêta 2025 ok`, `Volatilité : 126 jours de rendements journaliers`, `Panel : 1974-12 -> 2025-11`, `Titres éligibles par mois : min 1182, médiane 1337, max 1948`, `Part NYSE dans l'éligible : 62.8%`, `Corrélations de rang moyennes : MOM-OP 0.01 | MOM-vol 0.01 | OP-vol -0.16`, `Écrit : …panel.parquet (3,081,498 lignes)`.
8. **Vérifications** : pas de message de repli sur 36 mois ; aucune ligne `[ATTENTION]` ; 612 dates de formation (décembre 1974 à novembre 2025).
9. **Erreurs potentielles**
   - `[ATTENTION] journalier manquant pour [...]` ou `plus de 10 % des titres sont exclus faute de volatilité` : fichier journalier incomplet, relancer 01b avec tous les fichiers.
   - Étape la plus longue (2,5 à 4,5 minutes) et la plus gourmande en mémoire : c'est normal.

### Module 05 — `05_portfolios.py` (horse race)
1. **Objectif** : construire les 9 portefeuilles long/short et valider le momentum contre le facteur UMD de French.
2. **Fonctionnement** : appelle `lib.build_portfolio` pour chaque portefeuille défini dans `CFG["portfolios"]` ; enregistre rendements et poids ; commence par P1_VW et calcule sa corrélation avec UMD (T0) ; s'arrête (code 1) si elle est inférieure à 0,8.
3. **Inputs** : `data/clean/panel.parquet` (titres éligibles), `data/raw/french_ff5.parquet`, `french_mom.parquet`.
4. **Outputs** : `output/portfolios/<NOM>_returns.parquet`, `<NOM>_weights.parquet` ; `output/tables/T0_controle_P1.csv/.tex`.
5. **Dépendances** : 04.
6. **Commandes** : `python code/main.py --only 5` ; un seul groupe : `python code/05_portfolios.py --only P1` ; forcer malgré un contrôle raté (déconseillé) : `python code/05_portfolios.py --force`.
7. **Résultats attendus**
   ```
   Panel éligible : 845,587 lignes, 612 dates de formation
   P1_VW   | 612 mois | moy  0.71 %/mois | Sharpe  0.38 | titres L/S 193/158 | turnover  137 % | repli EW 0 mois
   Contrôle P1 OK : corrélation avec UMD = 0.92
   P5_IV   | 612 mois | moy  0.55 %/mois | Sharpe  0.54 | titres L/S 120/119 | turnover  119 % | repli EW 0 mois
   P5B_IV  | 612 mois | moy  0.49 %/mois | Sharpe  0.55 | titres L/S 156/153 | turnover   71 % | repli EW 0 mois
   ```
8. **Vérifications** : corrélation avec UMD d'au moins 0,8 ; 612 mois pour chaque portefeuille ; aucune ligne `[alerte] moins de 30 titres` ; `repli EW 0 mois`.
9. **Erreurs potentielles** : `*** CONTRÔLE RATÉ ***` : chercher l'erreur dans le timing des rendements, les délistings, les filtres ou les points de coupure avant d'aller plus loin.

### Module 06 — `06_course_tests.py` (tests du cours)
1. **Objectif** : décrire les données et tester l'hypothèse H1 (la Quality améliore le momentum) avec les méthodes du cours.
2. **Fonctionnement** : T1 et T1b (description par décennie, couverture de la capitalisation, corrélations de rang de Spearman) ; T2a/T2b (déciles NYSE de MOM puis d'OP, rendements EW et VW en *t+1*, écart 10−1 avec t de Newey-West) ; T3 (double tri indépendant 3×3 en terciles NYSE, spread momentum par tercile d'OP, interaction, case « gagnants rentables − perdants non rentables ») ; T4 (Fama-MacBeth du rendement *t+1* en % sur les rangs de MOM et d'OP, leur produit, log ME, log BE/ME et le rendement *t*, sur tous les titres et sur les large caps).
3. **Inputs** : `data/clean/panel.parquet` uniquement.
4. **Outputs** : `T1_description`, `T1b_correlations`, `T2a_deciles_mom`, `T2b_deciles_op`, `T3_double_tri_EW`, `T3_double_tri_VW`, `T4_fama_macbeth_tous`, `T4_fama_macbeth_large_caps` (.csv et .tex).
5. **Dépendances** : 04 (pas besoin de 05).
6. **Commande** : `python code/main.py --only 6`.
7. **Résultats attendus** : `titres moyens par case : {11: 179.0, 12: 140.0, …, 33: 164.0}` et 8 lignes `tableau -> …`.
8. **Vérifications** : T2a : écart 10−1 positif et significatif (environ 0,8 %/mois, t ≈ 3) ; log BE/ME moyen autour de −0,8 ; T4 : rang OP positif (t ≈ 2,6).
9. **Erreurs potentielles** : aucune connue en dehors d'un panel absent.

### Module 07 — `07_performance.py` (performance, alphas, spanning)
1. **Objectif** : mesurer performance, risque et alphas des portefeuilles.
2. **Fonctionnement** : T5 (rendement, Sharpe, Sortino, drawdown, VaR et ES historiques à 5 %, turnover) ; T6 (alphas CAPM, FF3, FF5, FF5+MOM et q par MCO avec t-stats de Newey-West à 6 lags, ratio d'information annualisé) ; T6b (expositions FF5+MOM) ; T6c (test GRS conjoint sur P1 à P5) ; T7 (spanning : régression d'un portefeuille sur FF5+MOM plus un autre portefeuille, différences de portefeuilles, test de différence de Sharpe de Jobson-Korkie avec correction de Memmel).
3. **Inputs** : `output/portfolios/*_returns.parquet`, facteurs French, `data/raw/q5_factors_monthly.csv` (facultatif).
4. **Outputs** : `T5_performance`, `T6_alphas`, `T6b_expositions_FF5MOM`, `T6c_GRS`, `T7_spanning`.
5. **Dépendances** : 05.
6. **Commande** : `python code/main.py --only 7`.
7. **Résultats attendus** : un résumé FF5+MOM (P1 : 0.07 %/mois, t = 0.64 ; P5 : 0.04, t = 0.53) ; UMD sans alpha FF5+MOM (régression sans objet).
8. **Vérifications** : T6c FF5+MOM : p-value ≈ 0,31 ; colonnes `q α (%)` présentes dans T6 si le fichier q est en place.
9. **Erreurs potentielles** : `(facteurs q absents : modèle q ignoré …)` : ajouter `data/raw/q5_factors_monthly.csv`.

### Module 08 — `08_costs.py` (coûts de transaction)
1. **Objectif** : évaluer la stratégie après coûts.
2. **Fonctionnement** : T8 : turnover du cours (Σ|Δw| par jambe, w* = poids de la veille après dérive des prix), rendement, Sharpe et alpha nets pour 5, 10, 25 et 50 bps par unité échangée, coût de break-even de l'alpha et de l'avantage de P5 sur P1. T8b : coût par titre = |Δw| × demi-spread bid-ask (spread manquant remplacé par la moyenne de la catégorie de taille), sur l'échantillon complet puis avant et après la décimalisation (2001). F6 : Sharpe net selon le coût.
3. **Inputs** : portefeuilles (rendements et poids), `data/clean/panel.parquet` (bid/ask), facteurs French.
4. **Outputs** : `T8_couts`, `T8b_couts_spread`, figure `F6_sharpe_net_couts`.
5. **Dépendances** : 05.
6. **Commande** : `python code/main.py --only 8`.
7. **Résultats attendus** : `P5 vs P1 : Δα = -2.6 bps/mois, Δturnover = -18 %, c* = 14.9 bps (P5 meilleur en net si c > c*)`.
8. **Vérifications** : T8b, coût moyen de P5 ≈ 1,1 %/mois sur 1975–2000 et ≈ 0,13 %/mois sur 2001–2025 ; part d'échanges à spread coté ≈ 70 % (les spreads NYSE sont rarement cotés avant 1993 et sont alors imputés).
9. **Erreurs potentielles** : `(bid/ask absents : T8b ignoré)` : le CRSP journalier a été importé sans `DlyBid`/`DlyAsk` et le mensuel sans bid/ask.

### Module 09 — `09_periods_crashes.py` (sous-périodes et crashs)
1. **Objectif** : tester la stabilité dans le temps et le comportement lors des crashs du momentum.
2. **Fonctionnement** : T9 : performance et alpha FF5+MOM sur 1975–2025, 1975–1999, 2000–2025 et 2015–2025 (pour UMD, l'alpha FF5+MOM est sans objet et laissé vide). T10 : pour 2001 (janvier et avril), 2009 (mars à mai) et 2020 (novembre), rendements cumulés des jambes, bêtas ex ante de chaque jambe (moyenne pondérée des bêtas de Dimson des titres détenus à la formation), volatilité de la jambe short, dispersion des rendements et mois de récupération. F5 : décomposition long/short, P1 contre P5.
3. **Inputs** : portefeuilles (rendements et poids), `data/clean/panel.parquet` (bêta, vol), facteurs French.
4. **Outputs** : `T9_sous_periodes`, `T10_crashs`, figure `F5_crashs`.
5. **Dépendances** : 05 (et 04 avec le journalier pour les bêtas).
6. **Commande** : `python code/main.py --only 9`.
7. **Résultats attendus** : deux tableaux et une figure.
8. **Vérifications** : T10, colonnes de bêta remplies ; en 2009, bêta L/S de P1 ≈ −1,1 et de P5 ≈ −0,4 ; L/S cumulé de P1 ≈ −53 % contre ≈ −24 % pour P5. « Mois de récupération » vide = richesse antérieure jamais retrouvée.
9. **Erreurs potentielles** : bêtas vides : pas de CRSP journalier (solution de repli de l'étape 04).

### Module 10 — `10_robustness.py` (robustesse)
1. **Objectif** : vérifier que les conclusions tiennent avec d'autres paramètres, sans modifier la baseline.
2. **Fonctionnement** : reconstruit P1_VW et P5_IV avec `build_portfolio` sur les large caps (ME ≥ médiane NYSE) et avec le momentum 6-1 ; avec `--optional`, ajoute pour P5 un filtre de vol au tercile, une pondération EW et l'absence de plafond.
3. **Inputs** : `data/clean/panel.parquet`, `P1_VW` et `P5_IV` (05), facteurs French.
4. **Outputs** : `T11_robustesse`.
5. **Dépendances** : 05.
6. **Commandes** : `python code/main.py --only 10` ; avec les variantes optionnelles : `python code/main.py --only 10 --optional`.
7. **Résultats attendus** : une ligne `… : ok` par variante (6, ou 9 avec `--optional`).
8. **Vérifications** : les lignes « Baseline » reproduisent T5 (P1 Sharpe 0,38 ; P5 Sharpe 0,54) ; la variante « Pondération EW » de P5 est identique à P3-EW.
9. **Erreurs potentielles** : aucune connue.

### Module 11 — `11_figures.py` (figures)
1. **Objectif** : produire les figures de l'article.
2. **Fonctionnement** : F1 (taille de l'univers et des portefeuilles), F2 (richesse cumulée de 1 $ en échelle log, P1 à P5 et UMD), F3 (drawdowns P1, P5, UMD), F4 (volatilité glissante sur 36 mois, P1 contre P5).
3. **Inputs** : portefeuilles, `data/clean/panel.parquet`, facteurs French.
4. **Outputs** : `output/figures/F1_nombre_titres`, `F2_richesse_cumulee`, `F3_drawdowns`, `F4_volatilite_glissante` (.png et .pdf).
5. **Dépendances** : 05.
6. **Commande** : `python code/main.py --only 11`.
7. **Résultats attendus** : quatre lignes `figure -> …`.
8. **Vérifications** : F3 cohérente avec T5 (drawdown maximal de P1 ≈ −65 %, de P5 ≈ −40 %) ; F1 : univers entre 1 200 et 1 950 titres avec un pic vers 2000.
9. **Erreurs potentielles** : aucune connue (matplotlib fonctionne sans écran, mode `Agg`).

### Module lib — `lib.py` (fonctions communes)
1. **Objectif** : éviter de dupliquer le code entre les scripts 05 à 11.
2. **Fonctionnement**
   - chargement : `load_panel`, `load_factors` (French en décimal, q-factors convertis de % en décimal, alignés en fin de mois), `load_returns`, `in_sample` ;
   - construction : `build_portfolio` (univers, filtre de vol, score, sélection NYSE, pondération, plafond `_cap_weights`, rendement *t+1*, turnover du cours, règle 10 %/20 %), `leg_trades` (|Δw| par titre) ;
   - statistiques : `perf_stats`, `nw_reg` (MCO avec erreurs de Newey-West, noyau de Bartlett), `grs_test`, `jkm_sharpe_test`, `fama_macbeth` ;
   - sorties : `save_table` (CSV + LaTeX), `setup_mpl`, `savefig`.
3. **Inputs** : `data/clean/panel.parquet`, facteurs, `output/portfolios/`.
4. **Outputs** : aucun par lui-même.
5. **Dépendances** : `00_config.py`.
6. **Commande** : n'est pas lancé seul.
7. **Résultats attendus** : —
8. **Vérifications** : les rendements de P1_VW, P2_EW et P5_IV ont été recalculés avec un code indépendant (écart nul sur 612 mois), ainsi que les t-stats, alphas, GRS et Fama-MacBeth.
9. **Erreurs potentielles** : `ModuleNotFoundError: scipy` dans 07 : installer les dépendances (`pip install -r code/requirements.txt`).

### Module main — `main.py` (orchestration)
1. **Objectif** : enchaîner les étapes 02 à 11 en une commande.
2. **Fonctionnement** : vérifie d'abord la présence des fichiers d'entrée nécessaires aux étapes demandées et indique la commande à lancer s'il en manque (message `Fichiers d'entrée manquants`) ; signale si le journalier ou les q-factors manquent ; lance chaque script dans un processus séparé ; s'arrête au premier script en erreur avec la commande de reprise.
3. **Inputs** : ceux des étapes lancées.
4. **Outputs** : ceux des étapes lancées.
5. **Dépendances** : 01b (ou 01) et `01_extract_wrds.py --only french` exécutés au préalable.
6. **Commandes** : `python code/main.py`, et les options `--from N`, `--to N`, `--only N`, `--optional`, `--force`, `--with-extract`.
7. **Résultats attendus** : `[NN] terminé en … s` pour chaque étape puis `Tout est à jour en … s : output/tables/ et output/figures/`.
8. **Vérifications** : comparer aux valeurs de la partie D.
9. **Erreurs potentielles** : `Fichiers d'entrée manquants` (suivre la commande indiquée) ; `*** Arrêt : NN_….py a échoué` (lire le message au-dessus, corriger puis `--from NN`).

---

## Partie D — Valeurs de référence pour valider une exécution

| Étape | Message ou fichier | Valeur de référence |
|---|---|---|
| 01b | CRSP mensuel après filtres | 3 305 725 lignes, 25 650 titres, 1970-01 → 2025-12 |
| 01b | Compustat / CCM | 333 439 lignes, 27 854 firmes / 32 306 liens |
| 01b | journalier | 56 années (1970 → 2025) ; bid/ask : 4 075 895 titres-mois |
| 02 | `crsp_m.parquet` | 3 291 476 lignes ; rendements manquants 0,44 % |
| 03 | `op.parquet` | 284 100 lignes ; délai minimal 5,9 mois |
| 04 | univers éligible | min 1 182, médiane 1 337, max 1 948 titres ; NYSE 62,8 % ; panel 3 081 498 lignes |
| 05 | T0 | corrélation P1_VW / UMD = 0,915 |
| 07 | T5 | Sharpe P1 0,383 ; P5 0,538 ; UMD 0,422 |
| 07 | T6c | GRS FF5+MOM = 1,19 (p = 0,311) |
| 08 | T8 | break-even P5 contre P1 : 14,9 bps |
| 09 | T10 | 2009 : L/S cumulé P1 −53,2 %, P5 −24,0 % |

Ces valeurs ont été obtenues sur deux environnements différents (macOS avec Python 3.13 et Linux avec Python 3.10) avec des résultats identiques à la 4e décimale.

## Partie E — Étapes manuelles et points d'attention
- **Téléchargement des données WRDS** : manuel (licence), voir `QVMM_Guide_donnees_CDIF.pdf`.
- **q-factors** : téléchargement manuel sur global-q.org.
- **Facteurs French** : un script, mais un accès internet est nécessaire.
- **Mise à jour du dépôt** : après `git pull`, relancer `python code/main.py --from N` à partir de la première étape dont le code a changé (toute la chaîne si `04_signals.py` ou une étape antérieure a changé).
- **Fichiers non utilisés par le code** : `test.py` (racine), les éventuels `data/raw/french_*.csv` et `output/portfolios/*_returns.csv` (copies d'export) peuvent être supprimés sans effet.
