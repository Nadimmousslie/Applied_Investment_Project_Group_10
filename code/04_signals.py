"""
04_signals.py — QVMM : signaux et panel final (une ligne par titre et par mois de formation t).

Entrées : data/clean/crsp_m.parquet (02), data/clean/op.parquet (03),
          data/raw/crsp_daily/*.parquet (01, optionnel), data/raw/french_ff3_daily.parquet
Sortie  : data/clean/panel.parquet

Timing (roadmap, section 4) : tout ce qui est dans une ligne datée t est connu à la fin de t,
sauf ret_next / retx_next, qui sont les rendements réalisés en t+1 (à n'utiliser que comme résultat).

Colonnes principales :
    mom, mom6   momentum 12-1 (t-12..t-2) et 6-1 (t-6..t-2)
    op          Operating Profitability winsorisée 1 %/99 % chaque mois (univers éligible)
    vol         volatilité annualisée : 126 jours de bourse jusqu'à t (repli : 36 mois)
    beta        bêta Dimson sur 126 jours (beta_0 + beta_-1), pour l'analyse des crashs
    me, log_me, log_bm, ret (rendement du mois t, reversal)
    nyse, eligible
"""
import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
cfg_mod = importlib.import_module("00_config")
CFG, RAW, CLEAN = cfg_mod.CFG, cfg_mod.DATA_RAW, cfg_mod.DATA_CLEAN
MONTH = pd.offsets.MonthEnd()


# ------------------------------------------------------------------------------- utilitaires
def to_wide(df, col, dates, permnos, dtype="float32"):
    """Matrice (mois x permno) d'une colonne ; mois manquants = NaN (aucun trou silencieux)."""
    w = df.pivot(index="date", columns="permno", values=col)
    return w.reindex(index=dates, columns=permnos).astype(dtype)


def lookup(wide, rows):
    """Valeurs de la matrice wide aux couples (date, permno) des lignes du panel."""
    i = wide.index.get_indexer(rows["date"])
    j = wide.columns.get_indexer(rows["permno"])
    out = np.full(len(rows), np.nan, dtype="float64")
    ok = (i >= 0) & (j >= 0)
    out[ok] = wide.to_numpy()[i[ok], j[ok]]
    return out


def momentum(logr, start, skip, min_obs):
    """Rendement cumulé de t-start à t-skip (ex. 12-1 : start=12, skip=2)."""
    window = start - skip + 1
    return np.expm1(logr.shift(skip).rolling(window, min_periods=min_obs).sum())


# ------------------------------------------------------------------------------- volatilité et bêta
def daily_vol_beta():
    """Vol 126 j et bêta Dimson à chaque fin de mois, année par année (mémoire limitée)."""
    files = sorted((RAW / "crsp_daily").glob("*.parquet"))
    if not files:
        return None
    ff = pd.read_parquet(RAW / "french_ff3_daily.parquet")
    mkt = (ff.set_index("date")["MKT_RF"] + ff.set_index("date")["RF"]).astype("float64")
    W, MINP = CFG["vol_window_days"], CFG["vol_min_obs_days"]
    buffer, out = None, []
    for fpath in files:
        d = pd.read_parquet(fpath)
        d["date"] = pd.to_datetime(d["date"])
        r = d.pivot_table(index="date", columns="permno", values="ret", aggfunc="last").astype("float64")
        if buffer is not None:
            r = pd.concat([buffer, r]).sort_index()
            r = r[~r.index.duplicated(keep="last")]
        m = mkt.reindex(r.index)
        m_lag = mkt.shift(1).reindex(r.index)

        def beta_vs(mser):
            mask = r.notna() & mser.notna().to_numpy()[:, None]
            rm = r.where(mask)
            mm = pd.DataFrame(np.broadcast_to(mser.to_numpy()[:, None], r.shape), index=r.index,
                              columns=r.columns).where(mask)
            roll = lambda x: x.rolling(W, min_periods=MINP).mean()
            cov = roll(rm * mm) - roll(rm) * roll(mm)
            var = roll(mm * mm) - roll(mm) ** 2
            return cov / var

        vol = r.rolling(W, min_periods=MINP).std() * np.sqrt(252)
        beta = beta_vs(m) + beta_vs(m_lag)      # Dimson : beta_0 + beta_-1 (approx. par bêtas simples)

        # dernier jour de bourse de chaque mois de l'année du fichier
        year = int(fpath.stem)
        idx = r.index[r.index.year == year]
        last_days = pd.Series(idx, index=idx).groupby(idx.to_period("M")).max().to_numpy()
        for name, w in (("vol", vol), ("beta", beta)):
            s = w.loc[last_days]
            s.index = pd.DatetimeIndex(s.index) + pd.offsets.MonthEnd(0)
            s = s.stack().rename(name)
            out.append(s)
        buffer = r.iloc[-(W + 5):]
        print(f"  vol/bêta {year} ok")
    vol = pd.concat([s for s in out if s.name == "vol"])
    beta = pd.concat([s for s in out if s.name == "beta"])
    res = pd.concat([vol, beta], axis=1).reset_index()
    res.columns = ["date", "permno", "vol", "beta"]
    return res


# ------------------------------------------------------------------------------- panel
def main():
    m = pd.read_parquet(CLEAN / "crsp_m.parquet")
    dates = pd.date_range(m["date"].min(), m["date"].max(), freq=MONTH)
    permnos = pd.Index(np.sort(m["permno"].unique()))
    print(f"CRSP : {len(m):,} lignes, {len(permnos):,} titres, {dates[0]:%Y-%m} -> {dates[-1]:%Y-%m}")

    # ------------------------------------------------ matrices mensuelles
    R = to_wide(m, "ret", dates, permnos)
    RX = to_wide(m, "retx", dates, permnos) if "retx" in m else R
    logR = np.log1p(R.clip(lower=-0.9999))
    s12, k12 = CFG["mom_window"]
    MOM = momentum(logR, s12, k12, CFG["mom_min_obs"])
    MOM6 = momentum(logR, 6, 2, 4)
    RNEXT, RXNEXT = R.shift(-1), RX.shift(-1)     # rendement réalisé en t+1 (RÉSULTAT, jamais signal)

    # ------------------------------------------------ panel aux dates de formation
    first_form = pd.Period(CFG["sample_start"], "M").to_timestamp(how="end").normalize() - MONTH
    last_form = pd.Period(CFG["sample_end"], "M").to_timestamp(how="end").normalize() - MONTH
    p = m[(m["date"] >= first_form) & (m["date"] <= last_form)].copy()
    p["mom"] = lookup(MOM, p)
    p["mom6"] = lookup(MOM6, p)
    p["ret_next"] = lookup(RNEXT, p)
    p["retx_next"] = lookup(RXNEXT, p)
    del R, RX, logR, MOM, MOM6, RNEXT, RXNEXT

    # ------------------------------------------------ OP (règle de juin)
    op = pd.read_parquet(CLEAN / "op.parquet")
    op["june"] = pd.to_datetime(op["june"])
    p["june"] = pd.to_datetime(np.where(p["date"].dt.month >= 6,
                                        p["date"].dt.year.astype(str) + "-06-30",
                                        (p["date"].dt.year - 1).astype(str) + "-06-30"))
    p = p.merge(op[["permno", "june", "be", "op"]], on=["permno", "june"], how="left")
    # BE/ME : BE de l'exercice y, ME (niveau permco) de décembre y
    me_dec = m[m["date"].dt.month == 12][["permno", "date", "me_permco"]].rename(columns={"me_permco": "me_dec"})
    me_dec["june"] = me_dec["date"] + pd.offsets.MonthEnd(6)
    p = p.merge(me_dec[["permno", "june", "me_dec"]], on=["permno", "june"], how="left")
    p["log_bm"] = np.log(p["be"].where(p["be"] > 0) / p["me_dec"])
    p["log_me"] = np.log(p["me"])

    # ------------------------------------------------ volatilité et bêta
    vb = daily_vol_beta()
    if vb is not None:
        p = p.merge(vb, on=["permno", "date"], how="left")
        print("Volatilité : 126 jours de rendements journaliers")
    else:
        Rm = to_wide(m, "ret", dates, permnos)
        V = Rm.rolling(CFG["vol_window_months"], min_periods=CFG["vol_min_obs_months"]).std() * np.sqrt(12)
        p["vol"] = lookup(V, p)
        p["beta"] = np.nan
        print("Volatilité : SOLUTION DE REPLI (36 mois de rendements mensuels) — pas de journalier trouvé")

    # ------------------------------------------------ univers éligible (section 3.2)
    elig = p["price_ok"] & p["size_ok"] & p["mom"].notna() & p["op"].notna() & (p["be"] > 0) & p["vol"].notna()
    if CFG["exclude_financials"]:
        elig &= ~p["is_fin"]
    p["eligible"] = elig

    # winsorisation mensuelle de l'OP sur l'univers éligible
    lo_q, hi_q = CFG["op_winsor"]
    q = p[p["eligible"]].groupby("date")["op"].quantile([lo_q, hi_q]).unstack()
    q.columns = ["op_lo", "op_hi"]
    p = p.merge(q, on="date", how="left")
    e_ = p["eligible"]
    p.loc[e_, "op"] = p.loc[e_, "op"].clip(p.loc[e_, "op_lo"], p.loc[e_, "op_hi"])

    cols = ["permno", "permco", "date", "ret", "ret_next", "retx_next", "me", "me_permco", "nyse",
            "siccd", "mom", "mom6", "op", "be", "log_me", "log_bm", "vol", "beta", "eligible", "bid", "ask", "volume"]
    cols = list(dict.fromkeys(c for c in cols if c in p))
    p = p[cols].sort_values(["date", "permno"]).reset_index(drop=True)
    p.to_parquet(CLEAN / "panel.parquet", index=False)

    # ------------------------------------------------ contrôles
    e = p[p["eligible"]]
    n = e.groupby("date")["permno"].size()
    print(f"\nPanel : {p['date'].min():%Y-%m} -> {p['date'].max():%Y-%m} (dates de formation)")
    print(f"Titres éligibles par mois : min {n.min()}, médiane {int(n.median())}, max {n.max()}")
    print("Moyenne par décennie :", n.groupby(n.index.year // 10 * 10).mean().round(0).to_dict())
    print(f"Part NYSE dans l'éligible : {e['nyse'].mean():.1%}")
    rc = e.groupby("date").apply(lambda g: g[["mom", "op", "vol"]].rank().corr().values[np.triu_indices(3, 1)])
    rc = np.nanmean(np.vstack(rc.to_numpy()), axis=0)
    print(f"Corrélations de rang moyennes : MOM-OP {rc[0]:.2f} | MOM-vol {rc[1]:.2f} | OP-vol {rc[2]:.2f}")
    print(f"ret_next manquant dans l'éligible : {e['ret_next'].isna().mean():.2%} (délistés sans rendement)")
    print(f"Écrit : {CLEAN / 'panel.parquet'}  ({len(p):,} lignes)")


if __name__ == "__main__":
    main()
