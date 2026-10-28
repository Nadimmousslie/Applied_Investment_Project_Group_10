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
