# QVMM — Quality Momentum, Volatility-Managed

Projet du cours *Applied Investment* (HEC Lausanne) : construction et évaluation d'une stratégie long/short sur actions américaines, présentée sous forme d'un mini-article scientifique et d'une présentation de 15 minutes devant un comité d'investissement.

- **Rendu de l'article** : vendredi 13 novembre 2026, 23h59 (20 pages maximum hors tableaux, graphiques et références)
- **Présentation orale** : 15 minutes, en classe (date communiquée plus tard)
- **Groupe 10** : Nadim MOUSSLIE, Léonard PERIGAULT, Matteo GIRAUD, Laura PINTO, Livio
- **Documents de référence** : `QVMM_Roadmap_finale.pdf` (stratégie ; en cas de doute, la roadmap fait foi) et `QVMM_Guide_donnees_CDIF.pdf` (téléchargement des données WRDS au CDIF)
- **Manuel d'exécution détaillé, module par module** : [`EXECUTION_GUIDE.md`](EXECUTION_GUIDE.md)

---

## 1. Présentation générale

### Objectif et problématique
Déterminer si une stratégie long/short sur actions américaines est « worthwhile » du point de vue d'un gérant.

**Question de recherche** : à exposition fixe 100 % long / 100 % short, un gérant peut-il obtenir un alpha positif et un meilleur rendement ajusté du risque en sélectionnant les actions sur le **Momentum** et la **Quality**, puis en utilisant la **volatilité** pour gérer le risque ? Et vaut-il mieux utiliser la volatilité pour *filtrer* les titres, pour les *pondérer*, ou les deux ?

### Méthodologie
1. **Mandat** : 100 % long / 100 % short, rebalancement mensuel, exposition nette nulle. Pas de dérivés, pas de signal macro.
2. **Univers** à chaque fin de mois *t* : actions ordinaires de sociétés US cotées sur NYSE, AMEX ou NASDAQ (format CRSP CIZ), hors financières (SIC 6000–6999), prix ≥ 5 $, capitalisation (au niveau de l'entreprise) ≥ 20e percentile NYSE, signaux disponibles. Les rendements de délisting sont inclus.
3. **Signaux de sélection**
   - **Momentum 12-1** (comme le facteur UMD de French) : rendement cumulé sur les 11 mois t−11 à t−1, *t* étant la date de formation ; le mois *t* est sauté et le portefeuille est détenu en *t+1* ;
   - **Quality** : Operating Profitability de Fama-French (2015), OP = (REVT − COGS − XSGA − XINT) / BE, avec la règle de juin (comptes de l'année civile *y* utilisés de fin juin *y+1* à fin mai *y+2*), winsorisée à 1 %/99 % chaque mois.
4. **Score** : 0,5 × rang(MOM) + 0,5 × rang(OP). Long = décile supérieur, short = décile inférieur ; déciles calculés sur les seuls titres NYSE.
5. **Gestion du risque par la volatilité** σ (écart-type des 126 derniers rendements journaliers, annualisé) :
   - **filtre** : retrait du quintile le plus volatil de tout l'univers éligible ;
   - **pondération** : poids proportionnels à 1/σ dans chaque jambe.
6. **Pondération** : VW (baseline), EW (contrôle), inverse-vol ; plafond de 5 % par titre (EW si une jambe compte moins de 20 titres).
7. **Horse race** (un ingrédient ajouté à la fois, même univers) :

| Portefeuille | Sélection | Filtre de vol | Pondération | Nom dans le code |
|---|---|---|---|---|
| P1 Traditional MOM | Momentum seul | Non | VW, EW | `P1_VW`, `P1_EW` |
| P2 Quality MOM | Momentum × Quality | Non | VW, EW | `P2_VW`, `P2_EW` |
| P3 Filtered Q-MOM | Momentum × Quality | Oui | VW, EW | `P3_VW`, `P3_EW` |
| P4 Weighted Q-MOM | Momentum × Quality | Non | Inverse-vol | `P4_IV` |
| **P5 QVMM** | Momentum × Quality | Oui | Inverse-vol | `P5_IV` |
| P5-B | Comme P5 + règle 10 %/20 % (réduction du turnover) | Oui | Inverse-vol | `P5B_IV` |

8. **Évaluation** : performance et risque ; alphas CAPM, FF3, FF5, FF5 + MOM et modèle q (t-stats Newey-West, 6 lags) ; ratio d'information ; spanning ; test GRS ; test de différence de Sharpe (Jobson-Korkie-Memmel) ; déciles, double tri 3×3 et Fama-MacBeth (méthodes du cours) ; coûts de transaction (turnover du cours et demi-spread bid-ask) ; sous-périodes et crashs (2001, 2009, 2020) avec bêtas de Dimson ex ante ; robustesse.

### Fonctionnalités principales
- import des données WRDS (CSV téléchargés sur le site, ou extraction Python directe) ;
- construction d'un panel mensuel titre × date sans look-ahead ;
- une seule fonction (`lib.build_portfolio`) construit n'importe quel portefeuille, ce qui rend les variantes de robustesse « gratuites » ;
- tous les paramètres sont centralisés dans `code/00_config.py` ;
- production automatique de 19 tableaux (CSV + LaTeX) et 6 figures (PNG + PDF) prêts pour l'article.

---

## 2. Architecture du projet

```
Applied_Investment_Project_Group_10/
├── README.md                     # ce fichier
├── EXECUTION_GUIDE.md            # manuel d'exécution module par module
├── QVMM_Roadmap_finale.pdf       # stratégie (document de référence)
├── QVMM_Guide_donnees_CDIF.pdf   # guide de téléchargement des données WRDS
├── .gitignore                    # exclut data/, *.parquet, *.csv (sauf output/tables/), .venv/
├── test.py                       # fichier vide de test, non utilisé par le code
├── code/
│   ├── requirements.txt          # dépendances (versions testées)
│   ├── 00_config.py              # TOUS les paramètres et chemins
│   ├── 01_extract_wrds.py        # extraction WRDS en Python + téléchargement des facteurs French
│   ├── 01b_import_csv.py         # import des CSV WRDS téléchargés à la main (voie utilisée)
│   ├── 02_crsp_clean.py          # univers CRSP, capitalisation, drapeaux NYSE / prix / taille / financières
│   ├── 03_compustat_op.py        # BE, OP, règle de juin, lien CRSP-Compustat
│   ├── 04_signals.py             # momentum, volatilité et bêta journaliers, univers éligible -> panel
│   ├── 05_portfolios.py          # horse race P1 à P5-B + contrôle bloquant P1 contre UMD
│   ├── 06_course_tests.py        # T1 description, déciles, double tri 3×3, Fama-MacBeth
│   ├── 07_performance.py         # performance, alphas, GRS, spanning
│   ├── 08_costs.py               # coûts de transaction, break-even, demi-spread
│   ├── 09_periods_crashes.py     # sous-périodes, crashs, bêtas des jambes
│   ├── 10_robustness.py          # variantes (large caps, momentum 6-1, options)
│   ├── 11_figures.py             # figures F1 à F4
│   ├── lib.py                    # fonctions communes aux scripts 05 à 11
│   └── main.py                   # lance la chaîne 02 -> 11 (vérifie d'abord les entrées)
├── data/                         # NON versionné (licence WRDS, volume)
│   ├── raw/
│   │   ├── csv/                  # entrée de 01b : CSV/ZIP téléchargés sur WRDS
│   │   │   └── crsp_daily/       # CSV/ZIP du CRSP journalier (plusieurs fichiers possibles)
│   │   ├── crsp_daily/           # journalier converti, un fichier YYYY.parquet par année
│   │   ├── *.parquet             # données brutes converties + facteurs French
│   │   └── q5_factors_monthly.csv
│   └── clean/                    # crsp_m.parquet, op.parquet, panel.parquet
└── output/
    ├── portfolios/               # rendements et poids de chaque portefeuille (non versionné)
    ├── tables/                   # T0 à T11 en .csv et .tex (versionnés)
    └── figures/                  # F1 à F6 en .png et .pdf (versionnés)
```

### Comment les modules communiquent
Les scripts ne s'appellent pas entre eux : **chaque étape lit les fichiers écrits par la précédente** (format parquet), ce qui permet de relancer une étape sans tout recalculer. Ils partagent deux modules :
- `00_config.py` : chemins et paramètres, importé par `importlib.import_module("00_config")` (son nom commence par un chiffre). Les dossiers `data/` et `output/` sont créés automatiquement à partir de l'emplacement du fichier, **les scripts peuvent donc être lancés depuis n'importe quel dossier** ;
- `lib.py` : chargement des données, `build_portfolio`, statistiques (Newey-West, GRS, Fama-MacBeth, Jobson-Korkie-Memmel), écriture des tableaux et figures. Utilisé par les scripts 05 à 11.

### Flux des données
```
CSV WRDS (data/raw/csv/) ──01b──> data/raw/crsp_monthly, compustat_funda, ccm_link, crsp_daily/YYYY, crsp_bidask_monthly (.parquet)
Kenneth French (internet) ──01 --only french──> data/raw/french_ff5, french_mom, french_ff3_daily (.parquet)
global-q.org (à la main) ───────────────────────> data/raw/q5_factors_monthly.csv

crsp_monthly (+ bid/ask) ──02──> clean/crsp_m ─┐
compustat + ccm ──────────03──> clean/op ──────┼──04 (+ crsp_daily, french_ff3_daily)──> clean/panel
                                               ┘
panel + French ──05──> output/portfolios/*_returns, *_weights  + T0
panel ──────────06──> T1, T1b, T2a, T2b, T3, T4
portfolios + French + q ──07──> T5, T6, T6b, T6c, T7
portfolios + panel + French ──08──> T8, T8b, F6
portfolios + panel + French ──09──> T9, T10, F5
panel + P1/P5 + French ──10──> T11
portfolios + panel + French ──11──> F1, F2, F3, F4
```

---

## 3. Installation et configuration

### Prérequis
- **Python 3.13** (version testée : 3.13.0). La chaîne a aussi été reproduite à l'identique avec Python 3.10.12.
- **Mémoire vive : 8 Go recommandés.** L'import du CRSP mensuel complet (fichier « all » de 2,4 Go décompressé) dépasse 4 Go de mémoire.
- **Espace disque** : environ 1,4 Go pour les fichiers WRDS téléchargés, plus quelques Go pour les fichiers convertis.
- **Accès internet** pour télécharger les facteurs de Kenneth French. **Accès WRDS** uniquement si l'on utilise `01_extract_wrds.py` pour CRSP et Compustat.

### Installation (macOS / Linux)
```bash
git clone https://github.com/Nadimmousslie/Applied_Investment_Project_Group_10.git
cd Applied_Investment_Project_Group_10
python3 -m venv .venv
source .venv/bin/activate
pip install -r code/requirements.txt
python -c "import pandas, numpy, scipy, matplotlib, pyarrow; print('ok')"
```
Sous Windows, l'activation se fait avec `.venv\Scripts\activate`.

Une fois l'environnement activé, la commande `python` désigne le Python du projet ; toutes les commandes de ce README sont lancées **depuis la racine du projet**.

### Configuration
- **Paramètres** : tous dans `code/00_config.py` (période, filtres, seuils, portefeuilles, coûts, sous-périodes, crashs). Ils ont été fixés avant de regarder les résultats ; les tests de robustesse passent d'autres valeurs en argument sans modifier ce fichier.
- **Chemins** : aucun chemin à configurer, tout est relatif à la racine du projet.
- **Variable d'environnement** (uniquement pour `01_extract_wrds.py`) : `WRDS_USERNAME`. Le mot de passe est demandé à la première connexion. Ne jamais écrire ses identifiants dans le code.

---

## 4. Données utilisées

| Source | Contenu | Fréquence | Période du fichier utilisé | Format attendu | Emplacement | Obtention |
|---|---|---|---|---|---|---|
| CRSP CIZ, `crsp.msf_v2` (WRDS) | rendement mensuel (délisting inclus), prix, actions en circulation, capitalisation, volume, SIC, drapeaux du titre | mensuelle | 1970-01 → 2025-12 | CSV, ZIP ou CSV.GZ | `data/raw/csv/crsp_monthly.zip` | **à la main** (licence) |
| CRSP CIZ, `crsp.dsf_v2` (WRDS) | rendement journalier, bid et ask | journalière | 1970-01-02 → 2025-12-31 | un ou plusieurs CSV/ZIP | `data/raw/csv/crsp_daily/` | **à la main** |
| Compustat `comp.funda` (WRDS) | comptes annuels (REVT, COGS, XSGA, XINT, SEQ, CEQ, AT, TXDITC, PSTKRV, PSTKL, PSTK) | annuelle | exercices clos de 1970 à 2026 | CSV ou CSV.GZ | `data/raw/csv/compustat.csv.gz` | **à la main** |
| Lien CRSP-Compustat `crsp.ccmxpf_linktable` | correspondance gvkey ↔ permno | — | tout l'historique | CSV | `data/raw/csv/ccm_link.csv` | **à la main** |
| Kenneth French Data Library | FF5 et Momentum (mensuels), FF3 (journaliers), en décimal | mensuelle / journalière | jusqu'à la dernière mise à jour | parquet (créé par le script) | `data/raw/french_*.parquet` | **automatique** : `python code/01_extract_wrds.py --only french` |
| Hou-Xue-Zhang (global-q.org) | q-factors (MKT, ME, IA, ROE, EG), en % | mensuelle | 1967-01 → 2025-12 | CSV | `data/raw/q5_factors_monthly.csv` | **à la main** |

Les fichiers WRDS doivent être téléchargés au CDIF ou avec un compte WRDS ; la procédure (menus, variables, filtres) est détaillée dans `QVMM_Guide_donnees_CDIF.pdf`. Ils **ne sont pas redistribuables** : le dossier `data/` est exclu du dépôt Git.

Pour les q-factors : sur https://global-q.org/factors.html, section *The q-factors and Expected Growth Factor*, cliquer sur **Monthly**, puis renommer le fichier téléchargé (`q5_factors_monthly_AAAA.csv`) en `q5_factors_monthly.csv`. Sans ce fichier, le modèle q est simplement omis des tableaux.

### Noms de fichiers reconnus par `01b_import_csv.py`
Dans `data/raw/csv/` : `crsp_monthly`, `compustat`, `ccm_link` avec l'extension `.csv`, `.csv.gz`, `.zip` ou `.txt` (les majuscules des colonnes n'importent pas). Le CRSP journalier peut être découpé en plusieurs fichiers dans `data/raw/csv/crsp_daily/` (par exemple `crsp_daily_1970_1983.zip`, …). Le format CIZ et l'ancien format CRSP (avec `crsp_delist.csv`) sont détectés automatiquement.

### Transformations appliquées
| Module | Transformation |
|---|---|
| `01b` | filtres CIZ (équivalent shrcd 10/11 et exchcd 1/2/3), filtres Compustat standard (INDL, STD, D, C), liens LU/LC et P/C, conversion du journalier par année, bid/ask du dernier jour coté de chaque mois |
| `02` | doublons supprimés, capitalisation (ME) au niveau du titre et de l'entreprise (permco), drapeaux NYSE, financières, prix ≥ 5 $, taille ≥ p20 NYSE |
| `03` | BE et OP (définitions Fama-French), au moins 2 ans de présence dans Compustat, règle de juin, lien CCM valide en juin |
| `04` | momentum 12-1 et 6-1, rendement t+1, volatilité et bêta de Dimson sur 126 jours, log ME, log BE/ME, univers éligible, winsorisation de l'OP |

Règles de qualité : une valeur manquante n'est jamais remplacée par zéro (seule exception : les postes de coûts de l'OP, règle Fama-French) ; aucune information postérieure à la date de formation n'est utilisée pour former un portefeuille.

---

## 5. Exécution

Le détail de chaque module (entrées, sorties, contrôles, erreurs fréquentes) est dans [`EXECUTION_GUIDE.md`](EXECUTION_GUIDE.md). Parcours complet :

```bash
# 0. environnement (section 3), à la racine du projet
source .venv/bin/activate

# 1. placer les fichiers WRDS téléchargés
mkdir -p data/raw/csv/crsp_daily
#    -> data/raw/csv/crsp_monthly.zip, compustat.csv.gz, ccm_link.csv
#    -> data/raw/csv/crsp_daily/crsp_daily_1970_1983.zip, ... (tous les fichiers du journalier)
#    -> data/raw/q5_factors_monthly.csv

# 2. convertir les données WRDS (une seule fois)
python code/01b_import_csv.py

# 3. télécharger les facteurs de Kenneth French (une seule fois, internet requis)
python code/01_extract_wrds.py --only french

# 4. toute l'analyse : étapes 02 à 11, tableaux et figures
python code/main.py
```

Options de `main.py` :

| Commande | Effet |
|---|---|
| `python code/main.py` | étapes 02 → 11 |
| `python code/main.py --from 5` | reprend à partir de l'étape 05 |
| `python code/main.py --to 4` | s'arrête après l'étape 04 |
| `python code/main.py --only 7` | une seule étape |
| `python code/main.py --optional` | ajoute les variantes de robustesse optionnelles (étape 10) |
| `python code/main.py --force` | continue malgré un contrôle P1/UMD raté (déconseillé) |
| `python code/main.py --with-extract` | lance aussi `01_extract_wrds.py` (accès WRDS requis) |

Avant de lancer quoi que ce soit, `main.py` vérifie la présence des fichiers d'entrée et indique la commande à exécuter s'il en manque un. La chaîne s'arrête au premier script en erreur et indique la commande pour reprendre.

**Durées observées** (MacBook, novembre 2026) : chaîne 02 → 11 complète en 3 à 7 minutes, dont environ 2,5 à 4,5 minutes pour l'étape 04 (volatilité journalière) ; l'import 01b prend quelques minutes.

**Contrôle bloquant** : P1-VW doit avoir une corrélation d'au moins 0,8 avec le facteur UMD de French. Sinon, l'étape 05 s'arrête et la suite n'est pas exécutée.

**Reproductibilité** : aucun élément aléatoire (pas de tirage, pas de graine à fixer) ; les mêmes données donnent exactement les mêmes résultats.

---

## 6. Résultats

### Fichiers produits
| Dossier | Contenu |
|---|---|
| `output/tables/` | 19 tableaux, chacun en `.csv` (Excel) et `.tex` (LaTeX) |
| `output/figures/` | 6 figures, chacune en `.png` et `.pdf` |
| `output/portfolios/` | `<NOM>_returns.parquet` (rendements L, S, L/S, nombre de titres, turnover) et `<NOM>_weights.parquet` (poids par titre) pour les 9 portefeuilles |

| Section de l'article | Tableaux et figures |
|---|---|
| Contrôle (annexe) | T0 : P1 contre UMD |
| 3. Données | T1 description par décennie, T1b corrélations des signaux, F1 nombre de titres |
| 5.1 Tests du cours (H1) | T2a/T2b déciles MOM et OP, T3 double tri 3×3 (EW, VW), T4 Fama-MacBeth (tous, large caps) |
| 5.2 Horse race | T5 performance, F2 richesse cumulée, F3 drawdowns, F4 volatilité glissante |
| 5.3 Alphas et spanning | T6 alphas (CAPM, FF3, FF5, FF5+MOM, q), T6b expositions, T6c GRS, T7 spanning et différences de Sharpe |
| 5.4 Coûts | T8 coûts et break-even, T8b demi-spread (avant / après 2001), F6 Sharpe net selon le coût |
| 6. Robustesse | T9 sous-périodes, T10 et F5 crashs, T11 robustesse |

### Principaux résultats (version du 4 novembre 2026, janvier 1975 – décembre 2025, 612 mois)
| | P1 momentum VW | P5 QVMM | UMD (French) |
|---|---|---|---|
| Rendement annualisé | 8,5 % | 6,6 % | 6,3 % |
| Volatilité | 22,3 % | 12,2 % | 14,9 % |
| Sharpe | 0,38 | 0,54 | 0,42 |
| Max drawdown | −65 % | −40 % | −58 % |
| Alpha FF5+MOM (t) | 0,07 %/mois (0,6) | 0,04 %/mois (0,5) | — |
| Crash 2009 (L/S cumulé) | −53 % | −24 % | — |

Lecture : la gestion de la volatilité réduit fortement le risque et les crashs, mais aucun portefeuille n'a d'alpha significatif face à FF5 + Momentum (test GRS : p = 0,31). Filtrer la volatilité bat la pondération inverse-vol (P3-EW contre P4 : alpha 0,13 %/mois, t = 2,8). Les coûts réels (demi-spread) sont élevés avant la décimalisation de 2001 (environ 1 %/mois pour P5) et faibles ensuite (environ 0,13 %/mois).

### Vérifier que le programme fonctionne
Avec les données WRDS du projet, une exécution correcte affiche notamment : `format détecté : CIZ`, `3,305,725 lignes, 25,650 titres` (01b), `Volatilité : 126 jours de rendements journaliers` et `Titres éligibles par mois : min 1182, médiane 1337, max 1948` (04), `Contrôle P1 OK : corrélation avec UMD = 0.92` (05), puis `Tout est à jour`. La liste complète des valeurs de contrôle se trouve dans `EXECUTION_GUIDE.md`.

---

## 7. Échéances restantes

| Dates | Étape |
|---|---|
| jusqu'au 12 nov. | Rédaction des résultats, robustesse, conclusion, relecture (chiffres du texte = tableaux), comptage des pages |
| **13 nov., 23h59** | **Remise de l'article** |
| après le 13 nov. | Diapositives (9) et répétition chronométrée |

## 8. Bonnes pratiques de collaboration
- récupérer le travail des autres avant de commencer : `git pull` (avec `git stash` / `git stash pop` si l'on a des modifications locales) ;
- après une modification du code, relancer la chaîne à partir de l'étape modifiée (`python code/main.py --from N`) avant de pousser, pour que `output/` corresponde au code ;
- commits courts et explicites ; ne pas travailler à plusieurs sur le même fichier en parallèle ;
- versions des paquets fixées dans `code/requirements.txt` ;
- toute modification d'un paramètre de `00_config.py` est discutée en groupe et justifiée dans le commit.

## 9. Références principales
- Jegadeesh, N., et Titman, S. (1993). *Returns to Buying Winners and Selling Losers*. Journal of Finance.
- Novy-Marx, R. (2013). *The Other Side of Value: The Gross Profitability Premium*. Journal of Financial Economics.
- Fama, E. F., et French, K. R. (2015). *A Five-Factor Asset Pricing Model*. Journal of Financial Economics.
- Barroso, P., et Santa-Clara, P. (2015). *Momentum Has Its Moments*. Journal of Financial Economics.
- Daniel, K., et Moskowitz, T. (2016). *Momentum Crashes*. Journal of Financial Economics.
- Stambaugh, R., et Yuan, Y. (2017). *Mispricing Factors*. Review of Financial Studies.
- Supports du cours : Strategies, Factor models, Trading costs, Aggregate predictability.

La bibliographie complète est dans la roadmap (section 16).

## 10. Licence et avertissement
Projet académique réalisé dans le cadre d'un cours. Les données WRDS sont soumises à licence et ne sont pas distribuées. Les résultats ne constituent pas un conseil en investissement.
