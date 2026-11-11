"""
12_vol_matched.py — QVMM : P5 comparé au momentum classique ramené à la même volatilité.

Question : la gestion de la volatilité AU NIVEAU DES TITRES (P5) fait-elle mieux que la solution la plus
simple, c'est-à-dire détenir moins de momentum classique ? On multiplie les rendements de P1 par
k = vol(P5) / vol(P1) (le reste du capital est en cash, rendement excédentaire nul), puis on compare.

    T12  rendement, volatilité, Sharpe, drawdown maximal et rendement cumulé pendant les crashs,
         pour P1, P1 à la volatilité de P5, P1-EW et P5

Remarques : k est calculé sur l'échantillon complet (référence descriptive, pas une stratégie investissable) ;
le changement d'échelle laisse le Sharpe et les alphas par unité de risque inchangés.
Entrées : output/portfolios/*_returns.parquet (étape 05).
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import CFG, LABELS, MONTH, in_sample, load_returns, month, perf_stats, save_table


def main():
    rets = load_returns(["P1_VW", "P1_EW", "P5_IV"])
    S = in_sample(pd.DataFrame({k: v["LS"] for k, v in rets.items()}))
    k = S["P5_IV"].std() / S["P1_VW"].std()                 # facteur d'échelle (part du capital investie dans P1)
    series = {
        LABELS["P1_VW"]: S["P1_VW"],
        f"P1 à la volatilité de P5 (× {k:.3f})": S["P1_VW"] * k,
        LABELS["P1_EW"]: S["P1_EW"],
        LABELS["P5_IV"]: S["P5_IV"],
    }
    rows = {}
    for name, r in series.items():
        st = perf_stats(r)
        row = {c: st[c] for c in ("Rend. annualisé (%)", "Volatilité (%)", "Sharpe", "Max drawdown (%)")}
        # rendement long/short cumulé sur les mois de chaque épisode de crash (mêmes fenêtres que T10)
        for ep, windows in CFG["crashes"].items():
            months = []
            for a, b in windows:
                months += list(pd.date_range(month(a), month(b), freq=MONTH))
            row[f"Crash {ep} (%)"] = ((1 + r.reindex(months)).prod() - 1) * 100
        rows[name] = row
    t12 = pd.DataFrame(rows).T
    t12.index.name = "Portefeuille"
    save_table(t12, "T12_volatilite_egale",
               "P5 contre le momentum classique ramené à la même volatilité (facteur d'échelle sur l'échantillon complet)")
    print(t12.round(2).to_string())


if __name__ == "__main__":
    main()
