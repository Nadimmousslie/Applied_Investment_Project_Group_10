"""
00_config.py — QVMM : TOUS les choix du projet au même endroit.

Règle : ces paramètres sont fixés AVANT de regarder les résultats (roadmap, section 5).
Les tests de robustesse ne modifient pas ce fichier : ils passent d'autres valeurs
en argument à build_portfolio().

Usage dans les autres scripts :
    from config import CFG          (copier ce fichier sous le nom config.py, voir plus bas)
ou
    import importlib; CFG = importlib.import_module("00_config").CFG
"""
from pathlib import Path

# ------------------------------------------------------------------ chemins
ROOT = Path(__file__).resolve().parent.parent          # dossier qvmm/
DATA_RAW = ROOT / "data" / "raw"
DATA_CLEAN = ROOT / "data" / "clean"
OUT_TABLES = ROOT / "output" / "tables"
OUT_FIGS = ROOT / "output" / "figures"
for _p in (DATA_RAW, DATA_RAW / "crsp_daily", DATA_CLEAN, OUT_TABLES, OUT_FIGS):
    _p.mkdir(parents=True, exist_ok=True)

CFG = {
    # -------------------------------------------------------------- WRDS
    # Identifiant WRDS : variable d'environnement WRDS_USERNAME, sinon demandé à la connexion.
    "wrds_username_env": "WRDS_USERNAME",

    # -------------------------------------------------------------- échantillon
    "crsp_start": "1972-01-01",       # momentum (12 mois) + volatilité initialisés avant 1975
    "crsp_end": "2025-12-31",
    "comp_start": "1970-01-01",       # OP disponible dès 1975 avec la règle de juin
    "sample_start": "1975-01",        # premier mois de RENDEMENT des portefeuilles
    "sample_end": "2025-12",

    # -------------------------------------------------------------- univers (section 3.2)
    "min_price": 5.0,                 # prix >= 5 $ à t
    "size_nyse_pct": 0.20,            # ME >= 20e percentile NYSE à t
    "exclude_financials": True,       # SIC 6000-6999 exclus
    "sic_fin": (6000, 6999),
    "min_years_compustat": 2,         # biais de backfill

    # Filtres CIZ (équivalent shrcd 10/11, exchcd 1/2/3) — à aligner sur le code du prof
    "ciz_filters": {
        "sharetype": ["NS"],
        "securitytype": ["EQTY"],
        "securitysubtype": ["COM"],
        "usincflg": ["Y"],
        "issuertype": ["ACOR", "CORP"],
        "primaryexch": ["N", "A", "Q"],
        "conditionaltype": ["RW"],
        "tradingstatusflg": ["A"],
    },

    # -------------------------------------------------------------- signaux (section 4)
    "mom_window": (12, 2),            # rendement cumulé de t-12 à t-2
    "mom_min_obs": 8,                 # au moins 8 rendements valides sur 11
    "op_winsor": (0.01, 0.99),        # winsorisation mensuelle de l'OP
    "op_june_rule": True,             # comptes de l'année civile y utilisés de fin juin y+1 à fin mai y+2
    "vol_window_days": 126,           # écart-type des rendements journaliers
    "vol_min_obs_days": 100,
    "vol_window_months": 36,          # solution de repli sans journalier
    "vol_min_obs_months": 24,
    "beta_window_days": 126,          # bêtas Dimson (analyse des crashs)

    # -------------------------------------------------------------- construction (section 5)
    "score_weights": {"mom": 0.5, "op": 0.5},
    "long_pct": 0.90,                 # long : score > 90e percentile NYSE
    "short_pct": 0.10,                # short : score < 10e percentile NYSE
    "breakpoints": "nyse",            # points de coupure de SÉLECTION : NYSE
    "vol_filter_pct": 0.80,           # filtre : quintile de TOUT l'univers éligible (pas NYSE)
    "weight_cap": 0.05,               # 5 % max par titre
    "cap_min_names": 20,              # sous 20 titres : la jambe passe en EW
    "buffer_in": 0.90,                # règle 10 %/20 % (P5-B) : entrée dans le top 10 %
    "buffer_out": 0.80,               #                         sortie si on quitte le top 20 %

    # -------------------------------------------------------------- horse race (section 6)
    "portfolios": {
        "P1_VW": dict(selection="mom",   vol_filter=False, weighting="vw"),
        "P1_EW": dict(selection="mom",   vol_filter=False, weighting="ew"),
        "P2_VW": dict(selection="combo", vol_filter=False, weighting="vw"),
        "P2_EW": dict(selection="combo", vol_filter=False, weighting="ew"),
        "P3_VW": dict(selection="combo", vol_filter=True,  weighting="vw"),
        "P3_EW": dict(selection="combo", vol_filter=True,  weighting="ew"),
        "P4_IV": dict(selection="combo", vol_filter=False, weighting="iv"),
        "P5_IV": dict(selection="combo", vol_filter=True,  weighting="iv"),
        "P5B_IV": dict(selection="combo", vol_filter=True, weighting="iv", buffer=True),
    },

    # -------------------------------------------------------------- évaluation (sections 8-10)
    "nw_lags": 6,
    "cost_bps": [5, 10, 25, 50],
    "umd_min_corr": 0.80,             # contrôle qualité de P1_VW
    "min_names_alert": 30,
    "subperiods": {
        "full": ("1975-01", "2025-12"),
        "dev": ("1975-01", "1999-12"),
        "oos": ("2000-01", "2025-12"),
        "post_pub": ("2015-01", "2025-12"),
    },
    "crashes": {
        "2001": [("2001-01", "2001-01"), ("2001-04", "2001-04")],
        "2009": [("2009-03", "2009-05")],
        "2020": [("2020-11", "2020-11")],
    },

    # -------------------------------------------------------------- facteurs (libres)
    "french_files": {
        "ff5": "F-F_Research_Data_5_Factors_2x3_CSV.zip",
        "mom": "F-F_Momentum_Factor_CSV.zip",
        "ff3_daily": "F-F_Research_Data_Factors_daily_CSV.zip",
    },
    "french_url": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/",
    # q-factors : télécharger à la main sur https://global-q.org/factors.html
    # le fichier mensuel q5 et le placer dans data/raw/ sous le nom ci-dessous.
    "qfactor_file": "q5_factors_monthly.csv",
}

