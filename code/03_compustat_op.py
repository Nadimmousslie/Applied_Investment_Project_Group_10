"""
03_compustat_op.py — QVMM : Operating Profitability (Fama-French 2015) avec la règle de juin.

Entrées : data/raw/compustat_funda.parquet, data/raw/ccm_link.parquet
Sortie  : data/clean/op.parquet   une ligne par (permno, june) :
          june = fin juin de l'année y+1, premier mois où les comptes de l'exercice
          clos pendant l'année civile y sont utilisables (jusqu'à fin mai y+2).

Définitions (roadmap, section 4.2) :
    BE = SH + TXDITC - PS
         SH = SEQ, sinon CEQ + PSTK, sinon AT - LT
         PS = PSTKRV, sinon PSTKL, sinon PSTK, sinon 0 ;  TXDITC manquant = 0
    OP = (REVT - COGS - XSGA - XINT) / BE
         REVT requis + au moins un des postes COGS, XSGA, XINT ; postes manquants = 0
         BE > 0 requis
    La firme doit figurer depuis au moins 2 ans dans Compustat (biais de backfill).
La winsorisation 1 %/99 % est faite chaque mois dans 04_signals.py, sur l'univers éligible.
"""
import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
cfg_mod = importlib.import_module("00_config")
CFG, RAW, CLEAN = cfg_mod.CFG, cfg_mod.DATA_RAW, cfg_mod.DATA_CLEAN


def first_valid(df, cols):
    """Première valeur non manquante parmi cols (dans l'ordre)."""
    out = pd.Series(np.nan, index=df.index)
    for c in cols:
        out = out.fillna(df[c])
    return out


def main():
    f = pd.read_parquet(RAW / "compustat_funda.parquet")
    f["datadate"] = pd.to_datetime(f["datadate"])
    num = ["revt", "cogs", "xsga", "xint", "seq", "ceq", "at", "lt", "txditc", "pstkrv", "pstkl", "pstk"]
    for c in num:
        f[c] = pd.to_numeric(f[c], errors="coerce")
    f = f.sort_values(["gvkey", "datadate"]).drop_duplicates(["gvkey", "datadate"], keep="last")
    print(f"Compustat : {len(f):,} firmes-années, {f['gvkey'].nunique():,} firmes")

    # ------------------------------------------------------------------ BE
    sh = f["seq"].copy()
    sh = sh.fillna(f["ceq"] + f["pstk"].fillna(0))
    sh = sh.fillna(f["at"] - f["lt"])
    ps = first_valid(f, ["pstkrv", "pstkl", "pstk"]).fillna(0)
    f["be"] = sh + f["txditc"].fillna(0) - ps

    # ------------------------------------------------------------------ OP
    has_cost = f[["cogs", "xsga", "xint"]].notna().any(axis=1)
    op_num = f["revt"] - f["cogs"].fillna(0) - f["xsga"].fillna(0) - f["xint"].fillna(0)
    f["op"] = np.where(f["revt"].notna() & has_cost & (f["be"] > 0), op_num / f["be"], np.nan)

    # ------------------------------------------------------------------ backfill : >= 2 ans dans Compustat
    f["n_years"] = f.groupby("gvkey").cumcount() + 1
    f = f[f["n_years"] >= CFG["min_years_compustat"]]

    # ------------------------------------------------------------------ règle de juin
    # Exercice clos pendant l'année civile y -> utilisable de fin juin y+1 à fin mai y+2.
    # Si deux exercices se terminent la même année civile (changement de date de clôture),
    # on garde le plus récent.
    f["y"] = f["datadate"].dt.year
    f = f.sort_values(["gvkey", "y", "datadate"]).drop_duplicates(["gvkey", "y"], keep="last")
    f["june"] = pd.to_datetime((f["y"] + 1).astype(str) + "-06-30")

    # ------------------------------------------------------------------ lien CCM (valide en juin y+1)
    link = pd.read_parquet(RAW / "ccm_link.parquet")
    link["linkdt"] = pd.to_datetime(link["linkdt"])
    link["linkenddt"] = pd.to_datetime(link["linkenddt"])
    x = f.merge(link, on="gvkey", how="inner")
    x = x[(x["linkdt"] <= x["june"]) & (x["june"] <= x["linkenddt"])]
    # Un gvkey -> plusieurs permno : lien principal 'P' prioritaire sur 'C'
    x["prio"] = x["linkprim"].map({"P": 0, "C": 1}).fillna(2)
    x = x.sort_values(["permno", "june", "prio", "datadate"])
    # Un permno -> une seule observation par juin (lien prioritaire, puis exercice le plus récent)
    x = x.drop_duplicates(["permno", "june"], keep="first")

    out = x[["permno", "gvkey", "datadate", "june", "be", "op"]].copy()
    out["permno"] = out["permno"].astype("int64")
    out = out.sort_values(["permno", "june"]).reset_index(drop=True)
    out.to_parquet(CLEAN / "op.parquet", index=False)

    # ------------------------------------------------------------------ contrôles
    lag_m = ((out["june"] - out["datadate"]).dt.days / 30.44)
    print(f"Lag datadate -> premier usage : min {lag_m.min():.1f} mois, médiane {lag_m.median():.1f}, max {lag_m.max():.1f}")
    assert lag_m.min() >= 5.9, "Look-ahead : un exercice serait utilisé moins de 6 mois après sa clôture"
    cov = out.groupby(out["june"].dt.year)["op"].apply(lambda s: s.notna().sum())
    print("Firmes avec OP valide par année d'usage :",
          cov.loc[[a for a in (1975, 1985, 2000, 2010, 2025) if a in cov.index]].to_dict())
    print("OP : percentiles 1/50/99 =", np.nanpercentile(out["op"], [1, 50, 99]).round(3))
    print(f"Écrit : {CLEAN / 'op.parquet'}  ({len(out):,} lignes)")


if __name__ == "__main__":
    main()
