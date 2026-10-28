"""
08_costs.py — QVMM : coûts de transaction (roadmap, section 9).

    T8   turnover, rendement / Sharpe / alpha FF5+MOM nets pour c = 5, 10, 25, 50 bps, break-even
    T8b  (bonus) modèle du prof : demi-spread bid-ask par titre, manquants remplacés par la moyenne
         de la catégorie de taille (micro / small / large), sans impact de prix
    F6   Sharpe net en fonction du coût c

Turnover (cours) : Δw = w_t - w*_t, w* = poids de t-1 après dérive des prix ; Turn = Σ|Δw| par jambe,
somme des deux jambes (max 400 %). Rendement net = brut - c × Turn.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (CFG, LABELS, MODELS, MONTH, PORTS, color_of, in_sample, leg_trades, load_factors, load_panel,
                 load_returns, nw_reg, save_table, savefig, setup_mpl)

PORTS_COST = ["P1_VW", "P2_VW", "P3_VW", "P4_IV", "P5_IV", "P5B_IV"]


def main():
    fac = load_factors()
    F = fac[MODELS["FF5+MOM"]]
    rets = {k: v for k, v in load_returns().items() if k in PORTS_COST}
    t8, alpha_g, turn = {}, {}, {}
    for k, r in rets.items():
        r = in_sample(r)
        gross = r["LS"]
        T = r["turnover"].fillna(0)
        turn[k] = T.mean()
        a = nw_reg(gross, F)
        alpha_g[k] = a["alpha"]
        row = {"Turnover moyen (%)": T.mean() * 100}
        for c in [0] + CFG["cost_bps"]:
            net = gross - c / 1e4 * T
            an = nw_reg(net, F)
            tag = "brut" if c == 0 else f"{c} bps"
            row[f"Rend. ann. {tag} (%)"] = net.mean() * 1200
            row[f"Sharpe {tag}"] = net.mean() / net.std() * np.sqrt(12)
            row[f"α {tag} (%)"] = an["alpha"] * 100
            row[f"t(α) {tag}"] = an["t_alpha"]
        row["Break-even α (bps)"] = a["alpha"] / T.mean() * 1e4 if T.mean() > 0 else np.nan
        t8[LABELS.get(k, k)] = row
    t8 = pd.DataFrame(t8).T
    if "P5_IV" in alpha_g and "P1_VW" in alpha_g:
        dT = turn["P5_IV"] - turn["P1_VW"]
        da = alpha_g["P5_IV"] - alpha_g["P1_VW"]
        be = da / dT * 1e4 if dT > 0 else (np.inf if da > 0 else np.nan)
        t8.loc[LABELS["P5_IV"], "Break-even avantage P5 vs P1 (bps)"] = be
    t8.index.name = "Portefeuille"
    save_table(t8, "T8_couts", "Coûts de transaction : rendements, Sharpe et alphas FF5+MOM nets, coût de break-even")

    # ------------------------------------------------------------------ F6 Sharpe net vs c
    plt = setup_mpl()
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    cs = np.arange(0, 61, 2)
    for k in ["P1_VW", "P5_IV", "P5B_IV"]:
        if k not in rets:
            continue
        r = in_sample(rets[k])
        sh = [((r["LS"] - c / 1e4 * r["turnover"].fillna(0)).mean() /
               (r["LS"] - c / 1e4 * r["turnover"].fillna(0)).std() * np.sqrt(12)) for c in cs]
        ax.plot(cs, sh, color=color_of(k), label=LABELS.get(k, k), linestyle="--" if k == "P5B_IV" else "-")
    ax.axhline(0, color="#8a8984", linewidth=0.8)
    ax.set_xlabel("Coût par unité échangée (bps)")
    ax.set_ylabel("Sharpe annualisé net")
    ax.set_title("Sharpe net selon le coût de transaction")
    ax.legend()
    savefig(fig, "F6_sharpe_net_couts")

    # ------------------------------------------------------------------ T8b bonus : demi-spread du prof
    panel = load_panel()
    if not {"bid", "ask"} <= set(panel.columns) or panel[["bid", "ask"]].notna().sum().min() == 0:
        print("  (bid/ask absents : T8b ignoré)")
        return
    mid = (panel["bid"] + panel["ask"]) / 2
    panel["hs"] = ((panel["ask"] - panel["bid"]) / (2 * mid)).where((panel["ask"] > panel["bid"]) & (panel["bid"] > 0))
    panel.loc[panel["hs"] > 0.25, "hs"] = np.nan
    # catégorie de taille : micro < 20e pct NYSE <= small < 50e pct NYSE <= large
    bp = panel[panel["nyse"]].groupby("date")["me_permco"].quantile([0.2, 0.5]).unstack()
    bp.columns = ["p20", "p50"]
    panel = panel.merge(bp, on="date", how="left")
    panel["size_cat"] = np.where(panel["me_permco"] < panel["p20"], "micro",
                                 np.where(panel["me_permco"] < panel["p50"], "small", "large"))
    by_date = panel.groupby(["date", "size_cat"])["hs"].transform("mean")
    overall = panel.groupby("size_cat")["hs"].transform("mean")
    panel["hs"] = panel["hs"].fillna(by_date).fillna(overall)
    t8b = {}
    for k in PORTS_COST:
        f = PORTS / f"{k}_weights.parquet"
        if not f.exists():
            continue
        w = pd.read_parquet(f)
        tr = leg_trades(w, panel)
        tr = tr.merge(panel[["date", "permno", "hs"]], on=["date", "permno"], how="left")
        tr["hs"] = tr["hs"].fillna(panel["hs"].mean())     # titres sortis du panel éligible
        cost = (tr["dw"] * tr["hs"]).groupby(tr["date"]).sum()
        cost.index = cost.index + MONTH
        r = in_sample(rets[k])
        net = r["LS"] - cost.reindex(r.index).fillna(0)
        an = nw_reg(net, F)
        t8b[LABELS.get(k, k)] = {"Coût moyen (%/mois)": cost.reindex(r.index).mean() * 100,
                                 "Rend. ann. net (%)": net.mean() * 1200,
                                 "Sharpe net": net.mean() / net.std() * np.sqrt(12),
                                 "α net (%)": an["alpha"] * 100, "t(α) net": an["t_alpha"]}
    t8b = pd.DataFrame(t8b).T
    t8b.index.name = "Portefeuille"
    save_table(t8b, "T8b_couts_spread", "Bonus : coûts par demi-spread bid-ask (méthode du cours, sans impact de prix)")


if __name__ == "__main__":
    main()
