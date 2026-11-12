"""
12_vol_matched.py — QVMM : P5 comparé au momentum classique ramené à la même volatilité.

Question : la gestion de la volatilité AU NIVEAU DES TITRES (P5) fait-elle mieux que la solution la plus
simple, c'est-à-dire détenir moins de momentum classique ? On multiplie les rendements de P1 par
k = vol(P5) / vol(P1) (le reste du capital est en cash, rendement excédentaire nul), puis on compare.

    T12  rendement, volatilité, Sharpe, drawdown maximal et rendement cumulé pendant les crashs, pour P1,
         P1 à la volatilité de P5, P1-EW, P5 et P1 géré par la volatilité au niveau du portefeuille

Remarques : k est calculé sur l'échantillon complet (référence descriptive, pas une stratégie investissable) ;
le changement d'échelle laisse le Sharpe et les alphas par unité de risque inchangés.

Second point de comparaison, celui de la littérature : le momentum géré par la volatilité AU NIVEAU DU
PORTEFEUILLE de Barroso et Santa-Clara (2015). Chaque fin de mois t, l'exposition à P1 pour t+1 vaut
cible / volatilité réalisée de P1 sur ses 126 derniers rendements journaliers (cible : 12 % par an, comme
dans l'article). L'exposition varie donc dans le temps : c'est un benchmark, hors du mandat 100/100 fixe.

Entrées : output/portfolios/*_returns.parquet et P1_VW_weights.parquet (étape 05), data/raw/crsp_daily/ (01b).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import CFG, LABELS, MONTH, PORTS, RAW, in_sample, load_returns, month, perf_stats, save_table

BSC_TARGET = 0.12      # volatilité cible annualisée (Barroso et Santa-Clara, 2015)
BSC_WINDOW = 126       # jours de bourse utilisés pour la volatilité réalisée (6 mois)


def daily_ls_returns(name="P1_VW"):
    """Rendements JOURNALIERS long/short d'un portefeuille, reconstruits à partir de ses poids mensuels.
    Chaque jambe vaut 1 en début de mois puis dérive avec les rendements des titres (buy-and-hold dans le mois) ;
    un rendement journalier manquant est traité comme nul. Renvoie None s'il n'y a pas de CRSP journalier."""
    files = {int(f.stem): f for f in (RAW / "crsp_daily").glob("*.parquet") if f.stem.isdigit()}
    if not files:
        return None
    w = pd.read_parquet(PORTS / f"{name}_weights.parquet")[["date", "permno", "side", "w"]]
    w["hold"] = pd.to_datetime(w["date"]) + MONTH              # mois de détention = mois suivant la formation
    out = []
    for year, g in w.groupby(w["hold"].dt.year):
        if year not in files:
            continue
        d = pd.read_parquet(files[year])
        d["date"] = pd.to_datetime(d["date"])
        d = d[d["permno"].isin(g["permno"].unique())]
        d["hold"] = d["date"] + pd.offsets.MonthEnd(0)
        days = d.groupby("hold")["date"].unique()               # calendrier de bourse de chaque mois
        m = g[["permno", "side", "w", "hold"]].merge(d[["permno", "date", "hold", "ret"]], on=["permno", "hold"], how="left")
        for (hold, side), x in m.groupby(["hold", "side"]):
            if hold not in days.index:
                continue
            r = (x.pivot_table(index="date", columns="permno", values="ret", aggfunc="last")
                  .reindex(index=np.sort(days[hold]), columns=x["permno"].unique()).fillna(0.0))
            wt = x.drop_duplicates("permno").set_index("permno")["w"].reindex(r.columns)
            v = ((1 + r).cumprod() * wt).sum(axis=1)             # valeur de la jambe (1 en début de mois)
            leg = v / v.shift(1).fillna(wt.sum()) - 1
            out.append(pd.DataFrame({"date": leg.index, "side": side, "r": leg.to_numpy()}))
    legs = pd.concat(out).pivot(index="date", columns="side", values="r").sort_index()
    return (legs[1] - legs[-1]).dropna()


def bsc_scaled(monthly, daily):
    """Momentum géré par la volatilité (Barroso et Santa-Clara) : exposition de t+1 = cible / vol réalisée en t."""
    rv = np.sqrt(252 * (daily ** 2).rolling(BSC_WINDOW, min_periods=BSC_WINDOW).mean())   # vol réalisée annualisée
    rv_m = rv.groupby(rv.index + pd.offsets.MonthEnd(0)).last()                           # valeur de fin de mois t
    expo = (BSC_TARGET / rv_m).shift(1).reindex(monthly.index)                            # appliquée au mois t+1
    return (monthly * expo).dropna(), expo.dropna()


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
    daily = daily_ls_returns("P1_VW")
    if daily is None:
        print("  (pas de CRSP journalier : benchmark Barroso-Santa-Clara ignoré)")
    else:
        # contrôle : les rendements journaliers composés doivent redonner le rendement mensuel de P1
        comp = (1 + daily).groupby(daily.index + pd.offsets.MonthEnd(0)).prod() - 1
        chk = pd.concat([comp, S["P1_VW"]], axis=1, join="inner").dropna()
        print(f"  contrôle journalier/mensuel de P1 : corrélation {chk.corr().iloc[0, 1]:.4f}, "
              f"écart absolu moyen {(chk.iloc[:, 0] - chk.iloc[:, 1]).abs().mean() * 100:.2f} %/mois")
        bsc, expo = bsc_scaled(S["P1_VW"], daily)
        print(f"  exposition Barroso-Santa-Clara : moyenne {expo.mean():.2f}, min {expo.min():.2f}, max {expo.max():.2f} "
              f"({len(bsc)} mois, à partir de {bsc.index[0]:%Y-%m})")
        series[f"P1 géré par la volatilité (Barroso-Santa-Clara, cible {BSC_TARGET:.0%})"] = bsc
    rows = {}
    for name, r in series.items():
        st = perf_stats(r)
        row = {c: st[c] for c in ("Rend. annualisé (%)", "Volatilité (%)", "Sharpe", "Max drawdown (%)", "Mois")}
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
               "P5 contre le momentum classique à volatilité égale et contre le momentum géré par la volatilité "
               "au niveau du portefeuille (Barroso et Santa-Clara, 2015)")
    print(t12.round(2).to_string())


if __name__ == "__main__":
    main()
