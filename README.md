# QVMM — Quality Momentum, Volatility-Managed

Projet du cours *Applied Investment* (HEC Lausanne) : construction et évaluation d'une stratégie long/short sur actions américaines, présentée sous forme d'un mini-article scientifique et d'une présentation de 15 minutes devant un comité d'investissement.

- **Rendu de l'article** : vendredi 13 novembre 2026, 23h59 (20 pages maximum hors tableaux, graphiques et références)
- **Présentation orale** : 15 minutes, en classe (date communiquée plus tard)
- **Groupe** : _[10 - Nadim MOUSSLIE Léonard PERIGAULT Matteo GIRAUD Laura PINTO Livio ]_
- **Documents de référence** : `QVMM_Roadmap_finale.pdf` (stratégie, version du 28 octobre 2026 ; en cas de doute, la roadmap fait foi) et `QVMM_Guide_donnees_CDIF.pdf` (quelles données télécharger au CDIF et comment les brancher au code).

---

## 1. Objectif

Déterminer si une stratégie long/short sur actions américaines est « worthwhile » du point de vue d'un gérant.

**Question de recherche** : à exposition fixe 100 % long / 100 % short, un gérant peut-il obtenir un alpha positif et un meilleur rendement ajusté du risque en sélectionnant les actions sur le **Momentum** et la **Quality**, puis en utilisant la **volatilité** pour gérer le risque ? Et vaut-il mieux utiliser la volatilité pour *filtrer* les titres, pour les *pondérer*, ou les deux ?

**Critères de jugement** : Sharpe et ratio d'information après coûts, alpha FF5 + Momentum (Newey-West), test de spanning face au momentum classique, comportement dans les crashs, stabilité hors échantillon. Aucun objectif d'alpha n'est fixé à l'avance : les règles sont figées avant de regarder les résultats.

## 2. Résumé de la stratégie

1. **Mandat** : 100 % long / 100 % short, rebalancement mensuel, exposition nette nulle (le produit des ventes à découvert reste en collatéral). Pas de dérivés, pas de signal macro.
2. **Univers** : actions ordinaires de sociétés US cotées sur NYSE, AMEX ou NASDAQ (format CRSP CIZ), hors financières (SIC 6000–6999), prix ≥ 5 $, capitalisation ≥ 20e percentile NYSE, délistings inclus.
3. **Signaux de sélection** :
   - **Momentum 12-1** : rendement cumulé de t−12 à t−2 ;
   - **Quality** : Operating Profitability de Fama-French (2015), avec la règle de juin (comptes de l'année y utilisés de fin juin y+1 à fin mai y+2).
4. **Score** : 0,5 × rang(MOM) + 0,5 × rang(OP). Long = décile supérieur, short = décile inférieur, points de coupure NYSE.
5. **Gestion du risque par la volatilité** (126 jours de rendements journaliers) :
   - **filtre** : on retire le quintile le plus volatil de tout l'univers éligible ;
   - **pondération** : poids proportionnels à 1/σ dans chaque jambe.
6. **Pondération** : VW (baseline), EW (contrôle), inverse-vol ; plafond de 5 % par titre (EW si la jambe compte moins de 20 titres).
7. **Horse race** :

| Portefeuille | Sélection | Filtre de vol | Pondération |
|---|---|---|---|
| P1 Traditional MOM | Momentum seul | Non | VW, EW |
| P2 Quality MOM | Momentum × Quality | Non | VW, EW |
| P3 Filtered Q-MOM | Momentum × Quality | Oui | VW, EW |
| P4 Weighted Q-MOM | Momentum × Quality | Non | Inverse-vol |
| **P5 QVMM** | Momentum × Quality | Oui | Inverse-vol |
| P5-B | Comme P5 + règle 10 %/20 % | Oui | Inverse-vol |

8. **Évaluation** : performance et risque ; alphas CAPM, FF3, FF5, FF5 + MOM et modèle q (Newey-West, 6 lags) ; ratio d'information ; spanning de P5 sur FF5 + MOM + P1 ; test GRS ; déciles, double tri 3×3 et Fama-MacBeth (méthodes du cours) ; coûts de transaction ; sous-périodes (1975–1999, 2000–2025, 2015–2025) et crashs (2001, 2009, 2020) ; robustesse (large caps, momentum 6-1).

## 3. Structure du dépôt

```
qvmm/
├── README.md
├── QVMM_Roadmap_finale.pdf     # document de référence (stratégie)
├── QVMM_Guide_donnees_CDIF.pdf # guide de téléchargement des données WRDS
├── .gitignore
├── code/
│   ├── requirements.txt
│   ├── main.py                 # lance toute la chaîne (02 -> 11) en une commande
│   ├── lib.py                  # fonctions communes (build_portfolio, Newey-West, GRS, tableaux, figures)
│   ├── 00_config.py            # TOUS les paramètres (dates, filtres, seuils, portefeuilles, coûts)
│   ├── 01_extract_wrds.py      # CRSP CIZ mensuel + journalier, Compustat, CCM, facteurs French
│   ├── 01b_import_csv.py       # alternative : import des CSV téléchargés à la main sur WRDS
│   ├── 02_crsp_clean.py        # univers, ME, flag NYSE, SIC -> data/clean/crsp_m.parquet
│   ├── 03_compustat_op.py      # BE, OP, règle de juin, lien CCM -> data/clean/op.parquet
│   ├── 04_signals.py           # MOM 12-1, sigma 126 j, merge OP, rendement t+1 -> panel.parquet
│   ├── 05_portfolios.py        # build_portfolio(...) : P1 à P5-B, poids, rendements, turnover
│   ├── 06_course_tests.py      # Tableau 1, déciles, double tri 3x3, Fama-MacBeth
│   ├── 07_performance.py       # métriques, alphas NW, IR, spanning, GRS
│   ├── 08_costs.py             # turnover du cours, coûts nets, break-even, règle 10 %/20 %
│   ├── 09_periods_crashes.py   # sous-périodes, épisodes de crash, bêtas Dimson par jambe
│   ├── 10_robustness.py        # variantes via build_portfolio avec d'autres paramètres
│   └── 11_figures.py           # figures de l'article
├── data/                       # non versionné
│   ├── raw/                    # extractions WRDS + facteurs (parquet)
│   │   ├── csv/                # CSV téléchargés sur le site WRDS (entrée de 01b_import_csv.py)
│   │   └── crsp_daily/         # un fichier par année
│   └── clean/                  # bases nettoyées
├── output/
│   ├── portfolios/             # rendements et poids de chaque portefeuille (non versionné)
│   ├── tables/                 # T0 à T11, en .csv et .tex
│   └── figures/                # F1 à F6, en .png et .pdf
└── text/
    ├── paper/                  # article
    └── presentation/           # diapositives
```

État d'avancement : tous les scripts (00 à 11, `01b`, `lib.py`, `main.py`) sont écrits et testés sur données synthétiques ; reste à les lancer sur les données WRDS (téléchargement au CDIF le 28 octobre).

## 4. Données

| Source | Contenu | Tables / fichiers |
|---|---|---|
| CRSP CIZ (WRDS) | rendements mensuels (délisting inclus), prix, shrout, capitalisation, bid, ask, volume, flags des titres, SIC | `crsp.msf_v2` |
| CRSP CIZ (WRDS) | rendements journaliers (volatilité, bêtas) | `crsp.dsf_v2` |
| Compustat (WRDS) | comptes annuels (OP, BE) | `comp.funda` |
| Lien CRSP–Compustat | correspondance gvkey / permno | `crsp.ccmxpf_linktable` |
| Kenneth French Data Library | FF5, Momentum (mensuels), FF3 (journaliers) | téléchargés automatiquement (`01_extract_wrds.py --only french`) ; déjà dans `data/raw/` |
| Hou-Xue-Zhang | q-factors mensuels | fichier *q5 factors, monthly* sur global-q.org, renommé `q5_factors_monthly.csv`, dans `data/raw/` |

**Deux façons d'obtenir les données WRDS** (détail dans `QVMM_Guide_donnees_CDIF.pdf`) :
- **extraction Python** avec `01_extract_wrds.py`, si l'accès WRDS en Python est possible ;
- **téléchargement sur le site WRDS** en CSV (clé USB), copié dans `data/raw/csv/` sous les noms `crsp_monthly.csv`, `compustat.csv`, `ccm_link.csv`, `crsp_daily/*.csv` (et `crsp_delist.csv` pour l'ancien format CRSP), puis converti avec `01b_import_csv.py`. Le format CIZ et l'ancien format CRSP sont reconnus automatiquement.

**Période** : rendements de janvier 1975 à décembre 2025 (51 ans) ; données à partir de 1972 (CRSP) et 1970 (Compustat) pour initialiser les signaux.

**Règles de qualité appliquées**
- format CRSP **CIZ** de préférence (l'ancien format msf / msedelist n'est plus mis à jour après 2024, mais reste accepté par `01b_import_csv.py`) ; noms de colonnes à aligner sur le code du prof ;
- les valeurs manquantes ne sont jamais remplacées par zéro (seule exception : postes de coûts de l'OP, règle Fama-French) ;
- règle de juin pour les comptes annuels ; momentum qui saute t−1 ; volatilité calculée jusqu'à t ; rendement en t+1 (pas de look-ahead) ;
- rendements de délisting intégrés pour éviter le biais de survie ;
- firmes présentes depuis au moins 2 ans dans Compustat (biais de backfill).

> **Important** : les données WRDS ne sont pas redistribuables. Le dossier `data/` est exclu du dépôt (voir `.gitignore`).

## 5. Installation

```bash
git clone <url-du-depot>
cd qvmm
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r code/requirements.txt
```

**Connexion WRDS** : ne jamais écrire ses identifiants dans le code. Utiliser la variable d'environnement `WRDS_USERNAME` (le mot de passe est demandé à la première connexion et peut être enregistré dans `~/.pgpass`).

## 6. Exécution

Les scripts s'enchaînent dans l'ordre numérique. Chacun lit les fichiers parquet de l'étape précédente, ce qui évite de tout relancer.

```bash
# une seule fois : SOIT extraction Python (accès WRDS requis)...
python code/01_extract_wrds.py --skip-daily   # mensuel, Compustat, CCM, facteurs French
python code/01_extract_wrds.py --only daily   # journalier (long ; reprend là où il s'est arrêté)
# ...SOIT import des CSV téléchargés sur le site WRDS (mis dans data/raw/csv/, voir l'en-tête du script)
python code/01b_import_csv.py

# toute l'analyse, tableaux et figures
python code/main.py                 # 02 -> 11
python code/main.py --from 5        # reprendre à une étape
python code/main.py --only 7        # un seul script
python code/main.py --optional      # + robustesses optionnelles
```

Tous les choix de conception (dates, filtres, points de coupure, seuil du filtre de vol, plafond, portefeuilles, grille de coûts, sous-périodes, crashs) sont définis dans `00_config.py`. Ils sont fixés avant les tests ; les variantes de robustesse passent d'autres valeurs en argument sans modifier ce fichier.

**Contrôle bloquant** : P1-VW doit avoir une corrélation d'au moins 0,8 avec le facteur UMD de French. Tant que ce contrôle ne passe pas, on ne construit pas P2 à P5.

## 7. Calendrier

| Dates | Étape |
|---|---|
| 28 oct. | Code complet ; téléchargement des données au CDIF ; mail au prof |
| 29 oct. | Import des données, `main.py`, **contrôle P1 contre UMD** (jalon) ; corrections éventuelles |
| 30 oct. – 2 nov. | Rédaction : introduction, littérature, données (T1, F1), méthodologie |
| 3 – 6 nov. | Rédaction des résultats : tests du cours, horse race, alphas, spanning |
| 7 – 8 nov. | Coûts, sous-périodes, crashs, robustesse ; robustesses optionnelles si le temps le permet |
| 9 – 12 nov. | Conclusion, figures finales, relecture, comptage des pages |
| **13 nov., 23h59** | **Remise de l'article** |

La rédaction (introduction, littérature, données, méthodologie) avance en parallèle du code dès la première semaine.

## 8. Résultats

`main.py` produit les tableaux et figures du rapport dans `output/` :

| Section du rapport | Tableaux et figures |
|---|---|
| Contrôle (annexe) | T0 : P1 contre UMD |
| 3. Données | T1 description, T1b corrélations, F1 nombre de titres |
| 5.1 Tests du cours (H1) | T2a/T2b déciles, T3 double tri 3×3, T4 Fama-MacBeth |
| 5.2 Horse race | T5 performance, F2 richesse cumulée, F3 drawdowns, F4 volatilité glissante |
| 5.3 Alphas et spanning | T6 alphas (CAPM → q), T6b expositions, T6c GRS, T7 spanning |
| 5.4 Coûts | T8 coûts et break-even, T8b demi-spread, F6 Sharpe net |
| 6. Robustesse | T9 sous-périodes, T10 et F5 crashs, T11 robustesse |

_Principaux chiffres à compléter une fois les analyses lancées sur les données WRDS._

## 9. Bonnes pratiques de collaboration

- une branche par étape (`extract`, `signals`, `portfolios`, `costs`, etc.), fusionnée par pull request relue par un coéquipier ;
- commits courts et explicites ;
- ne pas travailler à plusieurs sur le même fichier en parallèle ;
- versions des paquets fixées dans `code/requirements.txt` ;
- toute modification d'un paramètre de `00_config.py` est discutée en groupe et justifiée dans le commit.

## 10. Références principales

- Jegadeesh, N., et Titman, S. (1993). *Returns to Buying Winners and Selling Losers*. Journal of Finance.
- Novy-Marx, R. (2013). *The Other Side of Value: The Gross Profitability Premium*. Journal of Financial Economics.
- Fama, E. F., et French, K. R. (2015). *A Five-Factor Asset Pricing Model*. Journal of Financial Economics.
- Barroso, P., et Santa-Clara, P. (2015). *Momentum Has Its Moments*. Journal of Financial Economics.
- Daniel, K., et Moskowitz, T. (2016). *Momentum Crashes*. Journal of Financial Economics.
- Stambaugh, R., et Yuan, Y. (2017). *Mispricing Factors*. Review of Financial Studies.
- Supports du cours : Strategies, Factor models, Trading costs, Aggregate predictability.

La bibliographie complète est dans la roadmap (section 16).

## 11. Licence et avertissement

Projet académique réalisé dans le cadre d'un cours. Les résultats ne constituent pas un conseil en investissement.
