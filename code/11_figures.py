"""
11_figures.py — QVMM : figures principales du rapport.

    F1  nombre de titres éligibles par mois et taille des jambes de P1 et P5
    F2  richesse cumulée (échelle log) de P1 à P5 et UMD
    F3  drawdowns de P1, P5 et UMD
    F4  volatilité glissante sur 36 mois, P1 contre P5
(F5 est produite par 09_periods_crashes.py, F6 par 08_costs.py.)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import LABELS, MONTH, color_of, in_sample, load_factors, load_panel, load_returns, savefig, setup_mpl

MAIN = ["P1_VW", "P2_VW", "P3_VW", "P4_IV", "P5_IV"]


def main():
    plt = setup_mpl()
    fac = load_factors()
    rets = load_returns()
    S = pd.DataFrame({k: rets[k]["LS"] for k in MAIN if k in rets})
    S["UMD"] = fac["MOM"]
    S = in_sample(S)

    # ------------------------------------------------------------------ F1
    p = load_panel()
    n = p.groupby("date").size()
    n.index = n.index + MONTH
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    ax.plot(n.index, n.to_numpy(), color="#52514e", label="Univers éligible")
    for k in ("P1_VW", "P5_IV"):
        if k in rets:
            ax.plot(rets[k].index, rets[k]["n_L"] + rets[k]["n_S"], color=color_of(k), label=f"{LABELS[k]} (long + short)")
    ax.set_ylabel("Nombre de titres")
    ax.set_title("Taille de l'univers et des portefeuilles")
    ax.legend()
    savefig(fig, "F1_nombre_titres")

    # ------------------------------------------------------------------ F2
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    W = (1 + S.fillna(0)).cumprod()
    for k in S.columns:
        ax.plot(W.index, W[k], color=color_of(k), label=LABELS.get(k, k),
                linestyle=":" if k == "UMD" else "-", linewidth=2.0 if k == "P5_IV" else 1.4)
    ax.set_yscale("log")
    ax.set_ylabel("Valeur de 1 $ investi (échelle log)")
    ax.set_title("Richesse cumulée des portefeuilles long/short, 1975–2025")
    ax.legend(ncol=2)
    savefig(fig, "F2_richesse_cumulee")

    # ------------------------------------------------------------------ F3
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    for k in [c for c in ("P1_VW", "P5_IV", "UMD") if c in S]:
        w = (1 + S[k].fillna(0)).cumprod()
        dd = (w / w.cummax() - 1) * 100
        ax.plot(dd.index, dd, color=color_of(k), label=LABELS.get(k, k), linestyle=":" if k == "UMD" else "-")
    ax.set_ylabel("Drawdown (%)")
    ax.set_title("Drawdowns : momentum classique contre QVMM")
    ax.legend(loc="best")
    savefig(fig, "F3_drawdowns")

    # ------------------------------------------------------------------ F4
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    for k in [c for c in ("P1_VW", "P5_IV") if c in S]:
        v = S[k].rolling(36, min_periods=24).std() * np.sqrt(12) * 100
        ax.plot(v.index, v, color=color_of(k), label=LABELS[k])
    ax.set_ylabel("Volatilité annualisée sur 36 mois (%)")
    ax.set_title("Risque glissant : P1 contre P5")
    ax.legend()
    savefig(fig, "F4_volatilite_glissante")


if __name__ == "__main__":
    main()
