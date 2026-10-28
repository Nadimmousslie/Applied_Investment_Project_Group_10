"""
lib.py — QVMM : fonctions communes aux scripts 05 à 11.

    load_panel, load_factors, load_returns   chargement des données
    build_portfolio                          construction de n'importe quel portefeuille (P1 à P5-B, variantes)
    leg_trades                               |Δw| par titre (définition du turnover du cours)
    perf_stats, nw_reg, grs_test, fama_macbeth, jkm_sharpe_test   statistiques
    save_table, savefig, COLORS              sorties pour le rapport

Convention de dates : un portefeuille FORMÉ à la fin du mois t a son rendement daté t+1
(mois où il est réalisé). Les facteurs sont datés du mois de leur rendement : on les aligne
donc directement sur la date de rendement.
"""
import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
_cfg = importlib.import_module("00_config")
CFG, RAW, CLEAN = _cfg.CFG, _cfg.DATA_RAW, _cfg.DATA_CLEAN
TABLES, FIGS = _cfg.OUT_TABLES, _cfg.OUT_FIGS
PORTS = TABLES.parent / "portfolios"
PORTS.mkdir(parents=True, exist_ok=True)
MONTH = pd.offsets.MonthEnd()

# Palette catégorielle (ordre fixe, validée daltonisme) ; gris pour les références externes
COLORS = {"P1": "#2a78d6", "P2": "#eb6834", "P3": "#1baf7a", "P4": "#eda100", "P5": "#e87ba4",
          "P5B": "#6250d6", "UMD": "#7a7974", "MKT": "#b5b4ae"}
LABELS = {"P1_VW": "P1 Traditional MOM", "P2_VW": "P2 Quality MOM", "P3_VW": "P3 Filtered Q-MOM",
          "P4_IV": "P4 Weighted Q-MOM", "P5_IV": "P5 QVMM", "P5B_IV": "P5-B QVMM (10/20)",
          "P1_EW": "P1 EW", "P2_EW": "P2 EW", "P3_EW": "P3 EW", "UMD": "UMD (French)", "MKT_RF": "Marché (MKT-RF)"}


def color_of(name):
    key = name.split("_")[0]
    return COLORS.get(key, "#52514e")


# =============================================================================== données
def month(s):
    return pd.Period(s, "M").to_timestamp(how="end").normalize()


def load_panel(eligible_only=True):
    p = pd.read_parquet(CLEAN / "panel.parquet")
    p["date"] = pd.to_datetime(p["date"])
    return p[p["eligible"]].copy() if eligible_only else p


def load_factors():
    """Facteurs mensuels en décimal, indexés par mois de rendement (fin de mois)."""
    ff5 = pd.read_parquet(RAW / "french_ff5.parquet").set_index("date")
    mom = pd.read_parquet(RAW / "french_mom.parquet").set_index("date")
    mom.columns = ["MOM" if c.upper().startswith("MOM") else c for c in mom.columns]
    f = ff5.join(mom[["MOM"]], how="inner")
    f.index = pd.to_datetime(f.index) + pd.offsets.MonthEnd(0)
    q = RAW / CFG["qfactor_file"]
    if q.exists():
        qf = pd.read_csv(q)
        qf.columns = [c.strip().upper() for c in qf.columns]
        qf.index = pd.to_datetime(dict(year=qf["YEAR"], month=qf["MONTH"], day=1)) + pd.offsets.MonthEnd(0)
        ren = {"R_MKT": "Q_MKT", "R_ME": "Q_ME", "R_IA": "Q_IA", "R_ROE": "Q_ROE", "R_EG": "Q_EG"}
        qf = qf[[c for c in ren if c in qf]].rename(columns=ren) / 100.0
        f = f.join(qf, how="left")
    return f


MODELS = {
    "CAPM": ["MKT_RF"],
    "FF3": ["MKT_RF", "SMB", "HML"],
    "FF5": ["MKT_RF", "SMB", "HML", "RMW", "CMA"],
    "FF5+MOM": ["MKT_RF", "SMB", "HML", "RMW", "CMA", "MOM"],
    "q": ["Q_MKT", "Q_ME", "Q_IA", "Q_ROE"],
}


def in_sample(s, period="full"):
    a, b = CFG["subperiods"][period]
    return s.loc[month(a):month(b)]


def load_returns(names=None):
    """Rendements long/short sauvegardés par 05_portfolios.py (colonne LS), plus UMD et MKT."""
    out = {}
    for f in sorted(PORTS.glob("*_returns.parquet")):
        n = f.name.replace("_returns.parquet", "")
        if names is None or n in names:
            out[n] = pd.read_parquet(f).set_index("date")
    return out


# =============================================================================== construction
def _cap_weights(w, cap, min_names):
    """Plafond par titre avec redistribution itérative ; EW si trop peu de titres."""
    n = len(w)
    if n == 0:
        return w, False
    if n < min_names:
        return pd.Series(1.0 / n, index=w.index), True
    w = w / w.sum()
    for _ in range(100):
        over = w > cap + 1e-12
        if not over.any():
            break
        excess = (w[over] - cap).sum()
        w[over] = cap
        free = ~over & (w < cap)
        w[free] += excess * w[free] / w[free].sum()
    return w, False


def _weights(df, weighting):
    if weighting == "vw":
        return df["me"].astype(float)
    if weighting == "ew":
        return pd.Series(1.0, index=df.index)
    if weighting == "iv":
        return 1.0 / df["vol"].astype(float)
    raise ValueError(weighting)


def build_portfolio(panel, selection="combo", vol_filter=False, weighting="vw", buffer=False,
                    universe="all", mom_col="mom", vol_pct=None, cap=None, start=None, end=None):
    """
    Portefeuille 100 % long / 100 % short reconstruit chaque fin de mois t, rendement en t+1.

    selection : "mom" (P1) ou "combo" (score 50/50 MOM + OP)
    vol_filter: retire les titres au-dessus du percentile vol_pct de TOUT l'univers éligible
    weighting : "vw", "ew" ou "iv" (1/sigma), puis plafond par titre
    buffer    : règle 10 %/20 % (entrée au top/bottom décile, sortie hors top/bottom 20 %)
    universe  : "all" ou "large" (ME >= médiane NYSE)
    Retourne (returns, weights) :
      returns : index = mois de rendement ; colonnes L, S, LS, n_L, n_S, turn_L, turn_S, turnover, ew_fallback
      weights : date (formation), permno, side (+1 long / -1 short), w (somme 1 par jambe), ret_next, retx_next
    """
    vol_pct = CFG["vol_filter_pct"] if vol_pct is None else vol_pct
    cap = CFG["weight_cap"] if cap is None else cap
    sw = CFG["score_weights"]
    rows, wrows = [], []
    prev = {1: set(), -1: set()}
    prev_w = {1: None, -1: None}
    p = panel
    if start is not None:
        p = p[p["date"] >= start]
    if end is not None:
        p = p[p["date"] <= end]

    for t, df in p.groupby("date", sort=True):
        df = df[df[mom_col].notna()]
        if universe == "large":
            nyse_me = df.loc[df["nyse"], "me_permco"]
            if len(nyse_me) == 0:
                continue
            df = df[df["me_permco"] >= nyse_me.median()]
        if vol_filter:
            df = df[df["vol"] <= df["vol"].quantile(vol_pct)]
        if len(df) < 20:
            continue
        if selection == "mom":
            score = df[mom_col].rank(pct=True)
        else:
            score = sw["mom"] * df[mom_col].rank(pct=True) + sw["op"] * df["op"].rank(pct=True)
        ref = score[df["nyse"]] if df["nyse"].sum() >= 20 else score
        q = ref.quantile([0.1, 0.2, 0.8, 0.9])
        perm = df["permno"]
        if buffer:
            long_m = (score >= q[0.9]) | (perm.isin(prev[1]) & (score >= q[0.8]))
            short_m = (score <= q[0.1]) | (perm.isin(prev[-1]) & (score <= q[0.2]))
        else:
            long_m, short_m = score >= q[0.9], score <= q[0.1]
        short_m &= ~long_m

        rec = {"date": t + MONTH}
        for side, mask, tag in ((1, long_m, "L"), (-1, short_m, "S")):
            leg = df[mask]
            w, fb = _cap_weights(_weights(leg, weighting), cap, CFG["cap_min_names"])
            w.index = leg["permno"].to_numpy()
            r = leg["ret_next"].to_numpy()
            ok = ~np.isnan(r)
            # titres sans rendement en t+1 (rare : délisté sans rendement) -> poids renormalisés
            rec[tag] = float(np.sum(w.to_numpy()[ok] * r[ok]) / w.to_numpy()[ok].sum()) if ok.any() else np.nan
            rec[f"n_{tag}"] = len(leg)
            rec[f"fb_{tag}"] = fb
            # turnover du cours : w* = w_{t-1}(1+Rx) / somme ; Δw = w_t - w*
            if prev_w[side] is not None:
                pw = prev_w[side]
                union = w.index.union(pw.index)
                rec[f"turn_{tag}"] = float((w.reindex(union, fill_value=0) - pw.reindex(union, fill_value=0)).abs().sum())
            else:
                rec[f"turn_{tag}"] = np.nan
            rx = leg["retx_next"].fillna(leg["ret_next"]).fillna(0).to_numpy()
            drift = w.to_numpy() * (1 + rx)
            prev_w[side] = pd.Series(drift / drift.sum(), index=w.index)
            prev[side] = set(w.index)
            wrows.append(pd.DataFrame({"date": t, "permno": w.index, "side": side, "w": w.to_numpy(),
                                       "ret_next": r}))
        rec["LS"] = rec["L"] - rec["S"]
        rec["turnover"] = rec["turn_L"] + rec["turn_S"]
        fb_l, fb_s = rec.pop("fb_L"), rec.pop("fb_S")
        rec["ew_fallback"] = bool(fb_l or fb_s)
        rows.append(rec)

    ret = pd.DataFrame(rows).set_index("date")
    wts = pd.concat(wrows, ignore_index=True) if wrows else pd.DataFrame()
    return ret, wts


def leg_trades(weights, panel):
    """|Δw| par titre et par date de rebalancement (pour le modèle de coûts du prof)."""
    w = weights.merge(panel[["date", "permno", "retx_next"]], on=["date", "permno"], how="left")
    w["rx"] = w["retx_next"].fillna(w["ret_next"]).fillna(0)
    out = []
    for side in (1, -1):
        s = w[w["side"] == side]
        prev = None
        for t, cur in s.groupby("date", sort=True):
            cur = cur.set_index("permno")
            if prev is not None:
                union = cur.index.union(prev.index)
                dw = (cur["w"].reindex(union, fill_value=0) - prev.reindex(union, fill_value=0)).abs()
                out.append(pd.DataFrame({"date": t, "permno": union, "side": side, "dw": dw.to_numpy()}))
            d = cur["w"] * (1 + cur["rx"])
            prev = d / d.sum()
    return pd.concat(out, ignore_index=True)


# =============================================================================== statistiques
def perf_stats(r):
    """Statistiques d'un rendement mensuel long/short (déjà un excess return)."""
    r = r.dropna()
    if len(r) < 12:
        return {}
    wealth = (1 + r).cumprod()
    dd = wealth / wealth.cummax() - 1
    down = np.sqrt(np.mean(np.minimum(r, 0) ** 2))
    q5 = r.quantile(0.05)
    mdd = dd.min()
    nw = nw_reg(r, None)
    return {
        "Rend. annualisé (%)": r.mean() * 1200,
        "t (NW)": nw["t_alpha"],
        "Volatilité (%)": r.std() * np.sqrt(12) * 100,
        "Sharpe": r.mean() / r.std() * np.sqrt(12),
        "Sortino": r.mean() * 12 / (down * np.sqrt(12)) if down > 0 else np.nan,
        "Max drawdown (%)": mdd * 100,
        "Calmar": (r.mean() * 12) / abs(mdd) if mdd < 0 else np.nan,
        "Skewness": r.skew(),
        "Kurtosis": r.kurt(),
        "Pire mois (%)": r.min() * 100,
        "VaR 5% (%)": -q5 * 100,
        "ES 5% (%)": -r[r <= q5].mean() * 100,
        "Mois": len(r),
    }


def nw_reg(y, X, lags=None):
    """OLS avec erreurs Newey-West (noyau de Bartlett), comme statsmodels HAC. X=None : moyenne seule."""
    lags = CFG["nw_lags"] if lags is None else lags
    y = y.dropna()
    if X is None:
        X = pd.DataFrame(index=y.index)
    else:
        X = X.reindex(y.index).dropna()
        y = y.loc[X.index]
    names = ["const"] + list(X.columns)
    Xm = np.column_stack([np.ones(len(y))] + [X[c].to_numpy(float) for c in X.columns])
    yv = y.to_numpy(float)
    XtX_inv = np.linalg.pinv(Xm.T @ Xm)
    b = XtX_inv @ Xm.T @ yv
    e = yv - Xm @ b
    u = Xm * e[:, None]
    S = u.T @ u
    for l in range(1, min(lags, len(yv) - 1) + 1):
        g = u[l:].T @ u[:-l]
        S += (1 - l / (lags + 1)) * (g + g.T)
    se = np.sqrt(np.diag(XtX_inv @ S @ XtX_inv))
    params = pd.Series(b, index=names)
    tvals = pd.Series(b / se, index=names)
    r2 = 1 - np.sum(e ** 2) / np.sum((yv - yv.mean()) ** 2) if len(names) > 1 else 0.0
    resid_sd = e.std(ddof=1)
    return {"alpha": params["const"], "t_alpha": tvals["const"],
            "betas": params.drop("const"), "t_betas": tvals.drop("const"),
            "r2": r2, "ir": params["const"] / resid_sd * np.sqrt(12) if resid_sd > 0 else np.nan,
            "resid": pd.Series(e, index=y.index), "n": len(yv)}


def grs_test(R, F):
    """Test de Gibbons-Ross-Shanken : alphas conjointement nuls. R : T x N, F : T x K."""
    from scipy import stats
    df = R.join(F, how="inner").dropna()
    R, F = df[R.columns].to_numpy(), df[F.columns].to_numpy()
    T, N = R.shape
    K = F.shape[1]
    X = np.column_stack([np.ones(T), F])
    B = np.linalg.lstsq(X, R, rcond=None)[0]
    E = R - X @ B
    a = B[0]
    S = E.T @ E / (T - K - 1)
    mu = F.mean(axis=0)
    Om = np.cov(F, rowvar=False, ddof=1).reshape(K, K)
    grs = (T / N) * ((T - N - K) / (T - K - 1)) * (a @ np.linalg.solve(S, a)) / (1 + mu @ np.linalg.solve(Om, mu))
    return float(grs), float(1 - stats.f.cdf(grs, N, T - N - K))


def jkm_sharpe_test(r1, r2):
    """Différence de Sharpe (Jobson-Korkie avec correction de Memmel). Retourne (diff mensuelle, z, p)."""
    from scipy import stats
    d = pd.concat([r1, r2], axis=1).dropna()
    T = len(d)
    m1, m2 = d.mean()
    s1, s2 = d.std()
    rho = d.corr().iloc[0, 1]
    sr1, sr2 = m1 / s1, m2 / s2
    v = (2 - 2 * rho + 0.5 * (sr1 ** 2 + sr2 ** 2 - 2 * sr1 * sr2 * rho ** 2)) / T
    z = (sr1 - sr2) / np.sqrt(v)
    return sr1 - sr2, z, 2 * (1 - stats.norm.cdf(abs(z)))


def fama_macbeth(df, y, xs, lags=None):
    """Régressions cross-sectionnelles mensuelles, moyennes des gammas et t-stats Newey-West."""
    g = []
    for t, d in df.groupby("date"):
        d = d[[y] + xs].dropna()
        if len(d) < len(xs) + 10:
            continue
        X = np.column_stack([np.ones(len(d)), d[xs].to_numpy()])
        b = np.linalg.lstsq(X, d[y].to_numpy(), rcond=None)[0]
        r2 = 1 - np.sum((d[y].to_numpy() - X @ b) ** 2) / np.sum((d[y] - d[y].mean()) ** 2)
        g.append(dict(zip(["const"] + xs, b), date=t, r2=r2, n=len(d)))
    G = pd.DataFrame(g).set_index("date")
    out = {}
    for c in ["const"] + xs:
        r = nw_reg(G[c], None, lags)
        out[c] = (G[c].mean(), r["t_alpha"])
    return out, G["r2"].mean(), G["n"].mean(), len(G)


# =============================================================================== sorties
def save_table(df, name, caption="", floatfmt="{:.2f}", index=True):
    """CSV (pour Excel) + .tex (pour le rapport) dans output/tables/."""
    df.round(4).to_csv(TABLES / f"{name}.csv", index=index, encoding="utf-8-sig")

    def fmt(v):
        if isinstance(v, (float, np.floating)):
            return "" if np.isnan(v) else floatfmt.format(v)
        if isinstance(v, (bool, np.bool_)):
            return "Oui" if v else "Non"
        return str(v).replace("%", r"\%").replace("&", r"\&").replace("_", r"\_")

    cols = ([df.index.name or ""] if index else []) + [str(c) for c in df.columns]
    align = ("l" if index else "") + "r" * len(df.columns)
    lines = [r"\begin{table}[htbp]", r"\centering", r"\small", rf"\caption{{{caption}}}", rf"\label{{tab:{name}}}",
             rf"\begin{{tabular}}{{{align}}}", r"\toprule",
             " & ".join(fmt(c) for c in cols) + r" \\", r"\midrule"]
    for idx, row in df.iterrows():
        cells = ([fmt(idx)] if index else []) + [fmt(v) for v in row]
        lines.append(" & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    (TABLES / f"{name}.tex").write_text("\n".join(lines), encoding="utf-8")
    print(f"  tableau -> output/tables/{name}.csv / .tex")


def setup_mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.dpi": 150, "savefig.dpi": 300, "font.size": 9, "axes.titlesize": 10,
        "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#8a8984",
        "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.6, "axes.axisbelow": True,
        "lines.linewidth": 1.6, "legend.frameon": False, "legend.fontsize": 8,
        "xtick.color": "#52514e", "ytick.color": "#52514e", "axes.labelcolor": "#52514e",
    })
    return plt


def savefig(fig, name):
    fig.savefig(FIGS / f"{name}.png", bbox_inches="tight")
    fig.savefig(FIGS / f"{name}.pdf", bbox_inches="tight")
    print(f"  figure  -> output/figures/{name}.png / .pdf")
