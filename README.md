# Stratégie multi-signaux « turnover-aware » sur actions américaines

Projet du cours *Applied Investment* : construction et évaluation d'une stratégie d'investissement sur actions américaines, présentée sous forme d'un mini-article scientifique et d'une présentation de 15 minutes devant un comité d'investissement.

- **Rendu de l'article** : vendredi 13 novembre 2026, 23h59 (20 pages maximum hors tableaux, graphiques et références)
- **Présentation orale** : 15 minutes, en classe
- **Groupe** : _[noms des membres]_

---

## 1. Objectif

Déterminer si une stratégie long-short sur actions américaines est « worthwhile » du point de vue d'un gérant : génère-t-elle un alpha significatif contre les modèles à facteurs usuels, et cet alpha survit-il aux coûts de transaction ?

Objectif de performance : **alpha d'au moins 0,5 % par mois** (brut, pondération égale), avec une t-statistique supérieure à 3. L'alpha net de coûts et la capacité de la stratégie sont rapportés de façon transparente.

## 2. Résumé de la stratégie

1. **Univers** : actions ordinaires CRSP (NYSE, AMEX, Nasdaq), délistings inclus. Version « tradable » (prix > 5 $, capitalisation > 20e percentile NYSE) et version « tous titres » en robustesse.
2. **Signaux**, regroupés en quatre blocs :
   - émissions et investissement : croissance des actifs, émissions nettes d'actions, accruals ;
   - qualité : gross profits / actifs, ROA ;
   - information et prix : surprise de résultats (SUE), momentum 12-2 ;
   - risque : volatilité idiosyncratique, bêta.
3. **Score composite** : winsorisation, rangs en pourcentile, neutralisation par industrie (FF48), moyenne par bloc puis entre blocs.
4. **Portefeuilles** : déciles avec points de rupture NYSE, long décile 10 / short décile 1, pondération égale et par capitalisation plafonnée, neutralité de bêta.
5. **Contrôle du turnover** : bandes de non-transaction et lissage du score.
6. **Gestion du risque** : volatility targeting et overlay de régime optionnel, testé uniquement hors échantillon.
7. **Coûts** : demi-spread et impact de marché, alpha net et capacité.
8. **Évaluation** : alphas contre CAPM, FF3, FF5 et FF5 + momentum (erreurs standard Newey-West), Sharpe, drawdown, test GRS, Fama-MacBeth, sous-périodes et avant/après publication.

## 3. Structure du dépôt

```
projet-strategie/
├── README.md
├── requirements.txt
├── .gitignore
├── config.py                 # paramètres centraux (dates, filtres, seuils, chemins)
├── data/
│   ├── raw/                  # extractions WRDS (non versionnées)
│   └── processed/            # bases nettoyées (non versionnées)
├── src/
│   ├── 01_load.py            # chargement CRSP, Compustat, liens, facteurs FF
│   ├── 02_clean.py           # filtres, délistings, alignement des dates (lags)
│   ├── 03_signals.py         # construction des signaux et du score composite
│   ├── 04_portfolios.py      # déciles NYSE, pondérations, bandes de turnover
│   ├── 05_evaluate.py        # alphas, Sharpe, GRS, Fama-MacBeth
│   ├── 06_costs.py           # spreads, impact, alpha net, capacité
│   ├── 07_robustness.py      # sous-périodes, hors échantillon, variantes
│   └── 08_export.py          # tableaux et graphiques pour l'article
├── outputs/
│   ├── tables/
│   └── figures/
├── text/
│   ├── paper/                # article
│   └── presentation/         # diapositives
└── tests/                    # contrôles de cohérence (vs Ken French)
```

## 4. Données

| Source | Contenu | Tables |
|---|---|---|
| CRSP (WRDS) | rendements, prix, capitalisation, délistings, données quotidiennes | `msf`, `msenames`, `msedelist`, `dsf` |
| Compustat (WRDS) | comptabilité annuelle et trimestrielle | `funda`, `fundq` |
| Lien CRSP-Compustat | correspondance des identifiants | `ccmxpf_linktable` |
| Ken French Data Library | facteurs FF3, FF5, momentum, industries FF48 | fichiers en ligne |

**Période** : 1963-2025 (minimum acceptable : environ 2000-2025).

**Règles de qualité appliquées**
- les valeurs manquantes ne sont jamais remplacées par zéro ;
- décalage de 6 mois pour les variables comptables annuelles et de 3 à 4 mois pour les trimestrielles (pas de look-ahead) ;
- rendements de délisting intégrés pour éviter le biais de survie ;
- actions ordinaires uniquement (`shrcd` 10 et 11).

> **Important** : les données WRDS ne sont pas redistribuables. Le dossier `data/` est exclu du dépôt (voir `.gitignore`).

## 5. Installation

```bash
git clone <url-du-depot>
cd projet-strategie
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

**Connexion WRDS** : ne jamais écrire ses identifiants dans le code. Utiliser les variables d'environnement `WRDS_USERNAME` et `WRDS_PASSWORD`, ou le fichier `~/.pgpass`.

## 6. Exécution

Les scripts s'enchaînent dans l'ordre numérique. Chacun lit les sorties de l'étape précédente.

```bash
python src/01_load.py
python src/02_clean.py
python src/03_signals.py
python src/04_portfolios.py
python src/05_evaluate.py
python src/06_costs.py
python src/07_robustness.py
python src/08_export.py
```

Tous les paramètres de conception (dates, filtres, nombre de portefeuilles, seuils des bandes, graine aléatoire) sont définis dans `config.py`, ce qui documente les choix faits avant les tests.

## 7. Résultats

_À compléter une fois les analyses terminées : alphas bruts et nets, Sharpe, drawdown, capacité._

## 8. Bonnes pratiques de collaboration

- une branche par fonctionnalité (`signals`, `costs`, etc.), fusionnée par pull request relue par un coéquipier ;
- commits courts et explicites ;
- ne pas travailler à plusieurs sur le même fichier en parallèle ;
- versions des paquets fixées dans `requirements.txt` et graine aléatoire fixée dans `config.py`.

## 9. Références

- Cooper, M. J., Gulen, H., et Schill, M. J. (2008). *Asset Growth and the Cross-Section of Stock Returns*. Journal of Finance.
- Fama, E. F., et French, K. R. (1993, 2015). Modèles à trois et cinq facteurs.
- Supports du cours : Strategies, Factor models, Trading costs, Aggregate predictability.

## 10. Licence et avertissement

Projet académique réalisé dans le cadre d'un cours. Les résultats ne constituent pas un conseil en investissement.

