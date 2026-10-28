"""
05_portfolios.py — QVMM : construction du horse race P1 à P5-B (roadmap, section 6).

Entrée  : data/clean/panel.parquet, facteurs French
Sorties : output/portfolios/<NOM>_returns.parquet   (L, S, LS, n_L, n_S, turnover, ...)
          output/portfolios/<NOM>_weights.parquet   (poids par titre à chaque formation)
          output/tables/T0_controle_P1.csv/.tex      (contrôle P1 contre UMD)

CONTRÔLE BLOQUANT : P1_VW doit avoir une corrélation >= 0,8 avec UMD (French).
Sinon le script s'arrête (code 1) et main.py ne va pas plus loin.
    python 05_portfolios.py           # tous les portefeuilles
    python 05_portfolios.py --only P1 # seulement P1_VW et P1_EW (pour valider le contrôle d'abord)
    python 05_portfolios.py --force   # continuer malgré un contrôle raté (déconseillé)
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import CFG, PORTS, build_portfolio, in_sample, load_factors, load_panel, save_table


def check_p1(ret, fac):
    d = pd.concat([ret["LS"], fac["MOM"]], axis=1, join="inner").dropna()
    d = in_sample(d)
    corr = d.corr().iloc[0, 1]
    tab = pd.DataFrame({
        "Moyenne mensuelle (%)": d.mean() * 100,
        "Volatilité annuelle (%)": d.std() * np.sqrt(12) * 100,
        "Sharpe": d.mean() / d.std() * np.sqrt(12),
    })
    tab.index = ["P1_VW (nous)", "UMD (French)"]
    tab["Corrélation avec UMD"] = [corr, 1.0]
    return corr, tab


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="préfixe des portefeuilles à construire (ex. P1)")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    panel = load_panel()
    fac = load_factors()
    print(f"Panel éligible : {len(panel):,} lignes, {panel['date'].nunique()} dates de formation")

    specs = CFG["portfolios"]
    if a.only:
        specs = {k: v for k, v in specs.items() if k.startswith(a.only)}
    # P1_VW en premier : le contrôle bloque tout le reste
    order = ["P1_VW"] + [k for k in specs if k != "P1_VW"] if "P1_VW" in specs else list(specs)

    for name in order:
        t0 = time.time()
        ret, wts = build_portfolio(panel, **specs[name])
        ret.reset_index().to_parquet(PORTS / f"{name}_returns.parquet", index=False)
        wts.to_parquet(PORTS / f"{name}_weights.parquet", index=False)
        r = in_sample(ret["LS"])
        print(f"{name:7s} | {len(r)} mois | moy {r.mean()*100:5.2f} %/mois | Sharpe {r.mean()/r.std()*np.sqrt(12):5.2f} | "
              f"titres L/S {ret['n_L'].mean():.0f}/{ret['n_S'].mean():.0f} | turnover {ret['turnover'].mean()*100:4.0f} % "
              f"| repli EW {int(ret['ew_fallback'].sum())} mois | {time.time()-t0:.0f}s")
        if ret[["n_L", "n_S"]].min().min() < CFG["min_names_alert"]:
            print(f"  [alerte] moins de {CFG['min_names_alert']} titres dans une jambe certains mois")

        if name == "P1_VW":
            corr, tab = check_p1(ret, fac)
            save_table(tab, "T0_controle_P1", "Contrôle : P1 (momentum VW) contre le facteur UMD de French")
            print(tab.round(3).to_string())
            if corr < CFG["umd_min_corr"]:
                msg = (f"\n*** CONTRÔLE RATÉ : corrélation P1_VW / UMD = {corr:.2f} < {CFG['umd_min_corr']} ***\n"
                       "Vérifier : timing (ret_next), délisting, filtres d'univers, points de coupure NYSE.")
                if not a.force:
                    print(msg + "\nArrêt. (--force pour continuer quand même)")
                    sys.exit(1)
                print(msg + "\n--force : on continue.")
            else:
                print(f"Contrôle P1 OK : corrélation avec UMD = {corr:.2f}\n")


if __name__ == "__main__":
    main()
