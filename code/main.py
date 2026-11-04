"""
main.py — QVMM : lance toute la chaîne et régénère tous les tableaux et figures du rapport.

    python code/main.py                  # 02 -> 11 (l'extraction WRDS 01 est lancée à part, une fois)
    python code/main.py --from 5         # reprendre à partir de 05_portfolios.py
    python code/main.py --only 7         # un seul script
    python code/main.py --with-extract   # inclure 01_extract_wrds.py (accès WRDS requis)
    python code/main.py --optional       # inclure les robustesses optionnelles (10)
    python code/main.py --force          # continuer malgré un contrôle P1/UMD raté (déconseillé)

La chaîne s'arrête au premier script en erreur.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STEPS = {
    1: "01_extract_wrds.py",
    2: "02_crsp_clean.py",
    3: "03_compustat_op.py",
    4: "04_signals.py",
    5: "05_portfolios.py",
    6: "06_course_tests.py",
    7: "07_performance.py",
    8: "08_costs.py",
    9: "09_periods_crashes.py",
    10: "10_robustness.py",
    11: "11_figures.py",
}


# Fichiers lus par chaque étape (chemins relatifs à la racine du projet) et fichiers qu'elle produit.
# Sert uniquement à vérifier AVANT de lancer la chaîne qu'aucune entrée ne manque (message clair au lieu d'une trace Python).
IMPORT = "python code/01b_import_csv.py (CSV WRDS dans data/raw/csv/) ou python code/01_extract_wrds.py (accès WRDS)"
FRENCH = "python code/01_extract_wrds.py --only french (accès internet, pas besoin de WRDS)"
NEEDS = {
    2: {"data/raw/crsp_monthly.parquet": IMPORT},
    3: {"data/raw/compustat_funda.parquet": IMPORT, "data/raw/ccm_link.parquet": IMPORT},
    4: {"data/clean/crsp_m.parquet": "étape 2", "data/clean/op.parquet": "étape 3"},
    5: {"data/clean/panel.parquet": "étape 4", "data/raw/french_ff5.parquet": FRENCH,
        "data/raw/french_mom.parquet": FRENCH},
}
NEEDS[6] = {"data/clean/panel.parquet": "étape 4"}                 # tests du cours : le panel suffit
for _s in range(7, 12):
    NEEDS[_s] = {"data/clean/panel.parquet": "étape 4", "data/raw/french_ff5.parquet": FRENCH,
                 "data/raw/french_mom.parquet": FRENCH, "output/portfolios/P1_VW_returns.parquet": "étape 5"}
MAKES = {2: ["data/clean/crsp_m.parquet"], 3: ["data/clean/op.parquet"], 4: ["data/clean/panel.parquet"],
         5: ["output/portfolios/P1_VW_returns.parquet"]}


def preflight(steps):
    """Vérifie les entrées de la chaîne ; renvoie la liste des fichiers manquants (avec la commande pour les créer)."""
    made, missing = set(), []
    daily = any((ROOT / "data/raw/crsp_daily").glob("*.parquet"))
    if daily:                                   # la volatilité journalière a besoin du marché journalier (bêtas)
        NEEDS[4]["data/raw/french_ff3_daily.parquet"] = FRENCH
    for i in steps:
        for f, how in NEEDS.get(i, {}).items():
            if f not in made and not (ROOT / f).exists() and (f, how) not in missing:
                missing.append((f, how))
        made.update(MAKES.get(i, []))
    if any(i >= 4 for i in steps) and not daily:
        print("[info] aucun CRSP journalier dans data/raw/crsp_daily/ : volatilité sur 36 mois (solution de repli), bêtas vides")
    if any(i >= 7 for i in steps) and not (ROOT / "data/raw/q5_factors_monthly.csv").exists():
        print("[info] data/raw/q5_factors_monthly.csv absent : le modèle q sera ignoré (voir README, section Données)")
    return missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", type=int, default=2)
    ap.add_argument("--to", dest="end", type=int, default=11)
    ap.add_argument("--only", type=int)
    ap.add_argument("--with-extract", action="store_true")
    ap.add_argument("--optional", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    start = 1 if a.with_extract else a.start
    steps = [a.only] if a.only else [i for i in STEPS if start <= i <= a.end]
    missing = preflight([i for i in steps if i >= 2])
    if missing:
        print("Fichiers d'entrée manquants :")
        for f, how in missing:
            print(f"  - {f}\n      -> à créer avec : {how}")
        sys.exit(1)

    t_all = time.time()
    for i in steps:
        args = [sys.executable, str(HERE / STEPS[i])]
        if i == 5 and a.force:
            args.append("--force")
        if i == 10 and a.optional:
            args.append("--optional")
        print(f"\n{'=' * 70}\n[{i:02d}] {STEPS[i]}\n{'=' * 70}", flush=True)
        t0 = time.time()
        res = subprocess.run(args)
        if res.returncode != 0:
            print(f"\n*** Arrêt : {STEPS[i]} a échoué (code {res.returncode}). Corriger puis relancer avec --from {i}.")
            sys.exit(res.returncode)
        print(f"[{i:02d}] terminé en {time.time() - t0:.0f} s")
    print(f"\nTout est à jour en {time.time() - t_all:.0f} s : output/tables/ et output/figures/")


if __name__ == "__main__":
    main()
