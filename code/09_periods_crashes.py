"""
09_periods_crashes.py — QVMM : sous-périodes et crashs (roadmap, section 10).

    T9   sous-périodes 1975-2025, 1975-1999, 2000-2025 (hors échantillon), 2015-2025 (post-publication)
    T10  crashs 2001, 2009, 2020 : rendement cumulé L, S, L/S ; bêta ex ante de chaque jambe
         (moyenne pondérée des bêtas Dimson des titres détenus à la formation) ; vol de la jambe short ;
         dispersion cross-sectionnelle ; mois pour retrouver le niveau d'avant l'épisode
    F5   décomposition long / short des crashs, P1 contre P5
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (CFG, LABELS, MODELS, MONTH, PORTS, color_of, in_sample, load_factors, load_panel, load_returns,
                 month, nw_reg, save_table, savefig, setup_mpl)

SEL = ["P1_VW", "P2_VW", "P3_VW", "P4_IV", "P5_IV", "P5B_IV"]
PERIOD_NAMES = {"full": "1975–2025", "dev": "1975–1999", "oos": "2000–2025 (hors éch.)", "post_pub": "2015–2025 (post-pub.)"}


def recovery_months(ls, start):
    """Mois nécessaires après le début de l'épisode pour retrouver la richesse d'avant l'épisode."""
    w = (1 + ls.fillna(0)).cumprod()
    before = w[w.index < start]
    level = before.iloc[-1] if len(before) else 1.0
    after = w[w.index >= start]
    back = after[after >= level]
    return np.nan if back.empty else len(after.loc[:back.index[0]])


def main():
    fac = load_factors()
    F = fac[MODELS["FF5+MOM"]]
    rets = load_returns()
    names = [k for k in SEL if k in rets]
    series = {k: rets[k]["LS"] for k in names}
    series["UMD"] = fac["MOM"]

    # ------------------------------------------------------------------ T9
    rows = []
    for per, lab in PERIOD_NAMES.items():
        for k, s in series.items():
            s = in_sample(s, per).dropna()
            if len(s) < 24:
                continue
            a = nw_reg(s, F)
            rows.append({"Période": lab, "Portefeuille": LABELS.get(k, k), "Mois": len(s),
                         "Rend. ann. (%)": s.mean() * 1200, "Sharpe": s.mean() / s.std() * np.sqrt(12),
                         "α FF5+MOM (%)": a["alpha"] * 100, "t(α)": a["t_alpha"], "IR": a["ir"]})
    t9 = pd.DataFrame(rows).set_index(["Période", "Portefeuille"])
    t9.index = [f"{a} · {b}" for a, b in t9.index]
    t9.index.name = "Période · portefeuille"
    save_table(t9, "T9_sous_periodes", "Performance par sous-période (alpha FF5 + Momentum, Newey-West)")

    # ------------------------------------------------------------------ T10 crashs
    panel = load_panel()
    disp = panel.groupby("date")["ret_next"].std()
    disp.index = disp.index + MONTH
    rows, fig_data = [], {}
    for ep, windows in CFG["crashes"].items():
        months = []
        for a, b in windows:
            months += list(pd.date_range(month(a), month(b), freq=MONTH))
        months = pd.DatetimeIndex(months)
        form = months - MONTH                                     # dates de formation correspondantes
        for k in names:
            r = rets[k].reindex(months)
            w = pd.read_parquet(PORTS / f"{k}_weights.parquet")
            w = w[w["date"].isin(form)].merge(panel[["date", "permno", "beta", "vol"]], on=["date", "permno"], how="left")
            beta = {s: (w[w["side"] == s].assign(bw=lambda x: x["w"] * x["beta"]).groupby("date")["bw"].sum()
                        / w[(w["side"] == s) & w["beta"].notna()].groupby("date")["w"].sum()).mean() for s in (1, -1)}
            vol_s = (w[w["side"] == -1].assign(vw=lambda x: x["w"] * x["vol"]).groupby("date")["vw"].sum()).mean()
            row = {"Épisode": ep, "Portefeuille": LABELS.get(k, k),
                   "L cumulé (%)": ((1 + r["L"]).prod() - 1) * 100,
                   "S cumulé (%)": ((1 + r["S"]).prod() - 1) * 100,
                   "L/S cumulé (%)": ((1 + r["LS"]).prod() - 1) * 100,
                   "Bêta L": beta[1], "Bêta S": beta[-1], "Bêta L/S": beta[1] - beta[-1],
                   "Vol jambe S (%)": vol_s * 100,
                   "Dispersion (%)": disp.reindex(months).mean() * 100,
                   "Mois de récupération": recovery_months(rets[k]["LS"], months[0])}
            rows.append(row)
            fig_data[(ep, k)] = row
    t10 = pd.DataFrame(rows)
    t10.index = t10["Épisode"] + " · " + t10["Portefeuille"]
    t10 = t10.drop(columns=["Épisode", "Portefeuille"])
    t10.index.name = "Épisode · portefeuille"
    save_table(t10, "T10_crashs", "Crashs du momentum : décomposition long/short et bêtas ex ante des jambes")

    # ------------------------------------------------------------------ F5
    plt = setup_mpl()
    eps = list(CFG["crashes"])
    comp = [k for k in ("P1_VW", "P5_IV") if k in names]
    fig, axes = plt.subplots(1, len(eps), figsize=(7.2, 2.9), sharey=True)
    axes = np.atleast_1d(axes)
    x = np.arange(3)
    width = 0.38
    for ax, ep in zip(axes, eps):
        for i, k in enumerate(comp):
            d = fig_data[(ep, k)]
            vals = [d["L cumulé (%)"], -d["S cumulé (%)"], d["L/S cumulé (%)"]]
            ax.bar(x + (i - 0.5) * width, vals, width * 0.92, color=color_of(k), label=LABELS[k])
        ax.axhline(0, color="#8a8984", linewidth=0.8)
        ax.set_xticks(x, ["Long", "−Short", "L/S"])
        ax.set_title(ep)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Rendement cumulé sur l'épisode (%)")
    axes[0].legend(loc="lower left")
    fig.suptitle("Crashs du momentum : contribution des jambes, P1 contre P5", fontsize=10)
    fig.tight_layout()
    savefig(fig, "F5_crashs")


if __name__ == "__main__":
    main()
