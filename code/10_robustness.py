"""
10_robustness.py — QVMM : tests de robustesse (roadmap, section 11).

La baseline n'est jamais remplacée : on ne fait que relancer build_portfolio avec d'autres paramètres.
    T11  indispensables : large caps uniquement, momentum 6-1
         optionnels (--optional) : seuil du filtre au tercile, P5 en EW

    python 10_robustness.py             # indispensables
    python 10_robustness.py --optional  # + variantes optionnelles
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import CFG, LABELS, MODELS, build_portfolio, in_sample, load_factors, load_panel, load_returns, nw_reg, save_table


def summarize(ls, F):
    s = in_sample(ls).dropna()
    a = nw_reg(s, F)
    return {"Rend. ann. (%)": s.mean() * 1200, "Sharpe": s.mean() / s.std() * np.sqrt(12),
            "α FF5+MOM (%)": a["alpha"] * 100, "t(α)": a["t_alpha"], "IR": a["ir"], "Mois": len(s)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--optional", action="store_true")
    a = ap.parse_args()

    fac = load_factors()
    F = fac[MODELS["FF5+MOM"]]
    panel = load_panel()
    specs = CFG["portfolios"]
    base = load_returns(["P1_VW", "P5_IV"])

    variants = []
    for k in ("P1_VW", "P5_IV"):
        if k in base:
            variants.append(("Baseline", k, None))
        variants.append(("Large caps (ME ≥ médiane NYSE)", k, dict(universe="large")))
        variants.append(("Momentum 6-1", k, dict(mom_col="mom6")))
    if a.optional:
        variants.append(("Filtre de vol au tercile", "P5_IV", dict(vol_pct=2 / 3)))
        variants.append(("Pondération EW", "P5_IV", dict(weighting="ew")))
        variants.append(("Sans plafond de 5 %", "P5_IV", dict(cap=1.0)))

    rows = {}
    for label, k, over in variants:
        if over is None:
            ls = base[k]["LS"]
        else:
            kw = {**specs[k], **over}
            ls = build_portfolio(panel, **kw)[0]["LS"]
        rows[f"{LABELS[k]} · {label}"] = summarize(ls, F)
        print(f"  {k} · {label} : ok")
    t11 = pd.DataFrame(rows).T
    t11.index.name = "Portefeuille · variante"
    save_table(t11, "T11_robustesse", "Tests de robustesse (la baseline reste la spécification de référence)")


if __name__ == "__main__":
    main()
