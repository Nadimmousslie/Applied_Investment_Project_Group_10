"""
06_course_tests.py — QVMM : analyses de portefeuilles du cours (roadmap, sections 3.4 et 7).

    T1  description des données par décennie (+ corrélations de rang)
    T2a déciles de MOM, T2b déciles d'OP : rendements EW/VW, 10-1, caractéristiques
    T3  double tri indépendant 3x3 Momentum x OP (EW et VW)
    T4  régressions Fama-MacBeth (H1)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import MONTH, fama_macbeth, load_panel, nw_reg, save_table


def nyse_bins(df, col, qs):
    """Affecte chaque titre à un groupe selon des points de coupure NYSE (par date)."""
    out = pd.Series(np.nan, index=df.index)
    for t, d in df.groupby("date"):
        ref = d.loc[d["nyse"], col] if d["nyse"].sum() >= 20 else d[col]
        bp = ref.quantile(qs).to_numpy()
        out.loc[d.index] = np.searchsorted(bp, d[col].to_numpy(), side="left") + 1
    return out.astype(int)


def port_returns(df, group_col):
    """Rendements EW et VW (t+1) par groupe et par date ; index = mois de rendement."""
    d = df.dropna(subset=["ret_next"])
    ew = d.groupby(["date", group_col])["ret_next"].mean().unstack()
    d = d.assign(wr=d["ret_next"] * d["me"])
    vw = (d.groupby(["date", group_col])["wr"].sum() / d.groupby(["date", group_col])["me"].sum()).unstack()
    ew.index, vw.index = ew.index + MONTH, vw.index + MONTH
    return ew, vw


def decile_table(p, col, label):
    p = p.copy()
    p["g"] = nyse_bins(p, col, np.arange(0.1, 1.0, 0.1))
    ew, vw = port_returns(p, "g")
    rows = {}
    for g in range(1, 11):
        d = p[p["g"] == g]
        rows[str(g)] = {
            "EW (%)": ew[g].mean() * 100, "VW (%)": vw[g].mean() * 100,
            "Titres": d.groupby("date").size().mean(),
            "ME médiane (M$)": d.groupby("date")["me"].median().mean() / 1000,
            "log BE/ME": d["log_bm"].mean(), "MOM (%)": d["mom"].mean() * 100,
            "OP": d["op"].mean(), "Vol (%)": d["vol"].mean() * 100,
        }
    t = pd.DataFrame(rows).T
    for w, ser in (("EW", ew), ("VW", vw)):
        r = nw_reg(ser[10] - ser[1], None)
        t.loc["10-1", f"{w} (%)"] = r["alpha"] * 100
        t.loc["t(10-1)", f"{w} (%)"] = r["t_alpha"]
    t.index.name = f"Décile {label}"
    return t


def main():
    p = load_panel()
    full = load_panel(eligible_only=False)

    # ------------------------------------------------------------------ T1
    p["decade"] = (p["date"].dt.year // 10) * 10
    full["decade"] = (full["date"].dt.year // 10) * 10
    mkt = full.groupby("date")["me"].sum()
    cov = (p.groupby("date")["me"].sum() / mkt).groupby(lambda d: (d.year // 10) * 10).mean()
    g = p.groupby("decade")
    t1 = pd.DataFrame({
        "Titres/mois": p.groupby(["decade", "date"]).size().groupby("decade").mean(),
        "Part NYSE (%)": g["nyse"].mean() * 100,
        "ME médiane (M$)": g["me"].median() / 1000,
        "ME moyenne (M$)": g["me"].mean() / 1000,
        "Couverture cap. (%)": cov * 100,
        "MOM moy. (%)": g["mom"].mean() * 100, "MOM σ (%)": g["mom"].std() * 100,
        "OP moy.": g["op"].mean(), "OP σ": g["op"].std(),
        "Vol moy. (%)": g["vol"].mean() * 100,
    })
    t1.index.name = "Décennie"
    save_table(t1, "T1_description", "Description de l'univers éligible par décennie")
    rc = p.groupby("date").apply(lambda d: d[["mom", "op", "vol"]].rank().corr().to_numpy()[np.triu_indices(3, 1)])
    rc = np.nanmean(np.vstack(rc.to_numpy()), axis=0)
    t1b = pd.DataFrame({"Corrélation de rang moyenne": rc}, index=["MOM-OP", "MOM-Vol", "OP-Vol"])
    save_table(t1b, "T1b_correlations", "Corrélations de rang (Spearman) moyennes entre les signaux")

    # ------------------------------------------------------------------ T2
    save_table(decile_table(p, "mom", "MOM"), "T2a_deciles_mom", "Portefeuilles déciles triés sur le momentum 12-1")
    save_table(decile_table(p, "op", "OP"), "T2b_deciles_op", "Portefeuilles déciles triés sur l'Operating Profitability")

    # ------------------------------------------------------------------ T3 double tri 3x3
    p["gm"] = nyse_bins(p, "mom", [1 / 3, 2 / 3])
    p["go"] = nyse_bins(p, "op", [1 / 3, 2 / 3])
    p["cell"] = p["gm"] * 10 + p["go"]
    ew, vw = port_returns(p, "cell")
    names = {1: "Faible", 2: "Moyen", 3: "Élevé"}
    for w, ser in (("EW", ew), ("VW", vw)):
        rows_ = [f"MOM {names[m]}" for m in (1, 2, 3)] + ["WML", "t(WML)", "HH − LL", "t(HH − LL)"]
        tab = pd.DataFrame(index=rows_, columns=[f"OP {names[o]}" for o in (1, 2, 3)] + ["Élevé − Faible", "t"],
                           dtype=float)
        for m in (1, 2, 3):
            for o in (1, 2, 3):
                tab.loc[f"MOM {names[m]}", f"OP {names[o]}"] = ser[m * 10 + o].mean() * 100
        for o in (1, 2, 3):
            r = nw_reg(ser[30 + o] - ser[10 + o], None)
            tab.loc["WML", f"OP {names[o]}"] = r["alpha"] * 100
            tab.loc["t(WML)", f"OP {names[o]}"] = r["t_alpha"]
        # interaction : le spread momentum est-il plus fort chez les entreprises rentables ?
        r = nw_reg((ser[33] - ser[13]) - (ser[31] - ser[11]), None)
        tab.loc["WML", "Élevé − Faible"], tab.loc["WML", "t"] = r["alpha"] * 100, r["t_alpha"]
        # version 3x3 de P2 : gagnants rentables moins perdants non rentables
        r = nw_reg(ser[33] - ser[11], None)
        tab.loc["HH − LL", "OP Élevé"], tab.loc["t(HH − LL)", "OP Élevé"] = r["alpha"] * 100, r["t_alpha"]
        tab.index.name = w
        save_table(tab, f"T3_double_tri_{w}", f"Double tri indépendant 3×3 Momentum × OP, rendements {w} (% par mois)")
    n = p.groupby(["date", "cell"]).size().groupby(level="cell").mean()
    print("  titres moyens par case :", n.round(0).to_dict())

    # ------------------------------------------------------------------ T4 Fama-MacBeth
    p["r_mom"] = p.groupby("date")["mom"].rank(pct=True)
    p["r_op"] = p.groupby("date")["op"].rank(pct=True)
    p["r_mom_op"] = p["r_mom"] * p["r_op"]
    specs = {"(1) MOM": ["r_mom", "log_me", "log_bm", "ret"],
             "(2) MOM + OP": ["r_mom", "r_op", "log_me", "log_bm", "ret"],
             "(3) + interaction": ["r_mom", "r_op", "r_mom_op", "log_me", "log_bm", "ret"]}
    nice = {"const": "Constante", "r_mom": "Rang MOM", "r_op": "Rang OP", "r_mom_op": "MOM × OP",
            "log_me": "log ME", "log_bm": "log BE/ME", "ret": "Rendement t (reversal)"}
    d = p.assign(y=p["ret_next"] * 100)
    med = d[d["nyse"]].groupby("date")["me_permco"].median().rename("nyse_med")
    d = d.merge(med, on="date", how="left")
    large = d[d["me_permco"] >= d["nyse_med"]]
    for uni, dd in (("tous", d), ("large_caps", large)):
        cols = {}
        for k, xs in specs.items():
            res, r2, nobs, T = fama_macbeth(dd, "y", xs)
            col = {}
            for v in ["const"] + list(nice)[1:]:
                if v in res:
                    col[nice[v]] = f"{res[v][0]:.2f} ({res[v][1]:.2f})"
            col["R² moyen (%)"] = f"{r2*100:.1f}"
            col["Titres/mois"] = f"{nobs:.0f}"
            cols[k] = col
        t4 = pd.DataFrame(cols).reindex([nice[v] for v in nice] + ["R² moyen (%)", "Titres/mois"])
        t4.index.name = "Variable"
        save_table(t4.fillna(""), f"T4_fama_macbeth_{uni}",
                   f"Régressions Fama-MacBeth, rendement t+1 en % (t-stats Newey-West entre parenthèses), {uni.replace('_', ' ')}")


if __name__ == "__main__":
    main()
