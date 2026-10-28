"""
01b_import_csv.py — QVMM : import des CSV téléchargés à la main sur le site WRDS (clé USB).

À utiliser À LA PLACE de 01_extract_wrds.py quand on n'a pas d'accès WRDS en Python.
Produit exactement les mêmes fichiers dans data/raw/ que 01_extract_wrds.py, donc la suite
(02 -> 11, ou main.py) ne change pas.

1) Copier les fichiers de la clé dans data/raw/csv/ en les nommant ainsi
   (.csv, .csv.gz ou .zip acceptés ; les majuscules/minuscules des colonnes n'importent pas) :
       data/raw/csv/crsp_monthly.csv          CRSP mensuel (CIZ OU ancien format msf)
       data/raw/csv/crsp_delist.csv           OPTIONNEL : délistings (ancien format seulement)
       data/raw/csv/crsp_daily/*.csv          CRSP journalier, un ou plusieurs fichiers (ex. par tranches d'années)
       data/raw/csv/compustat.csv             Compustat Fundamentals Annual
       data/raw/csv/ccm_link.csv              table de liens CRSP/Compustat
2) Lancer :  python code/01b_import_csv.py
   (ou une seule table : --only monthly | daily | compustat | ccm)

Les deux formats CRSP sont reconnus automatiquement :
    CIZ     : MthCalDt, MthRet, MthPrc, ShrOut, PrimaryExch, ShareType...  /  DlyCalDt, DlyRet
    ancien  : DATE, RET, PRC, SHROUT, SHRCD, EXCHCD (+ DLRET)               /  DATE, RET
"""
import argparse
import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
cfg_mod = importlib.import_module("00_config")
CFG, RAW = cfg_mod.CFG, cfg_mod.DATA_RAW
CSV = RAW / "csv"


# ------------------------------------------------------------------------------- utilitaires
def find(stem):
    for ext in (".csv", ".csv.gz", ".zip", ".txt"):
        f = CSV / f"{stem}{ext}"
        if f.exists():
            return f
    hits = sorted(CSV.glob(f"{stem}*"))
    return hits[0] if hits else None


def read(path, **kw):
    df = pd.read_csv(path, low_memory=False, **kw)
    df.columns = [c.strip().lower() for c in df.columns]
    return df


def parse_date(s):
    """Dates WRDS : 'AAAA-MM-JJ', 'JJ/MM/AAAA' ou entier AAAAMMJJ."""
    if pd.api.types.is_numeric_dtype(s):
        return pd.to_datetime(s.astype("Int64").astype(str), format="%Y%m%d", errors="coerce")
    s = s.astype(str).str.strip()
    if s.str.fullmatch(r"\d{8}").mean() > 0.9:
        return pd.to_datetime(s, format="%Y%m%d", errors="coerce")
    return pd.to_datetime(s, errors="coerce")


def pick(df, *cands):
    for c in cands:
        if c in df:
            return c
    return None


def num(s):
    return pd.to_numeric(s, errors="coerce")   # codes lettres de CRSP (B, C, ...) -> NaN


# ------------------------------------------------------------------------------- CRSP mensuel
def import_monthly():
    f = find("crsp_monthly")
    if f is None:
        raise SystemExit(f"Fichier introuvable : {CSV}/crsp_monthly.csv")
    m = read(f)
    print(f"CRSP mensuel : {f.name}, {len(m):,} lignes, colonnes {list(m.columns)}")
    ciz = "mthret" in m or "mthcaldt" in m
    out = pd.DataFrame({"permno": num(m["permno"]).astype("Int64")})
    out["permco"] = num(m[pick(m, "permco")]) if pick(m, "permco") else out["permno"]

    if ciz:
        print("  format détecté : CIZ")
        out["date"] = parse_date(m[pick(m, "mthcaldt", "date")])
        out["ret"] = num(m["mthret"])
        out["retx"] = num(m[pick(m, "mthretx")]) if pick(m, "mthretx") else np.nan
        out["prc"] = num(m["mthprc"])
        out["shrout"] = num(m["shrout"])
        out["me"] = num(m[pick(m, "mthcap")]) if pick(m, "mthcap") else np.nan
        for std, cands in {"bid": ("mthbid", "mthprcbid", "bid"), "ask": ("mthask", "mthprcask", "ask"),
                           "vol": ("mthvol", "vol")}.items():
            c = pick(m, *cands)
            out[std] = num(m[c]) if c else np.nan
        for c in ("sharetype", "securitytype", "securitysubtype", "usincflg", "issuertype",
                  "primaryexch", "conditionaltype", "tradingstatusflg"):
            if c in m:
                out[c] = m[c].astype(str).str.strip()
        out["siccd"] = num(m[pick(m, "siccd", "sic")]) if pick(m, "siccd", "sic") else np.nan
        # mêmes filtres que l'extraction Python, appliqués seulement aux colonnes présentes
        keep = pd.Series(True, index=out.index)
        for col, vals in CFG["ciz_filters"].items():
            if col in out:
                keep &= out[col].isin(vals)
            else:
                print(f"  [info] colonne {col} absente : filtre non appliqué")
        out = out[keep]
    else:
        print("  format détecté : ancien CRSP (msf)")
        out["date"] = parse_date(m[pick(m, "date", "mthcaldt")])
        out["ret"] = num(m["ret"])
        out["retx"] = num(m[pick(m, "retx")]) if pick(m, "retx") else np.nan
        out["prc"] = num(m["prc"])
        out["shrout"] = num(m["shrout"])
        out["me"] = np.nan
        out["bid"] = num(m[pick(m, "bid")]) if pick(m, "bid") else np.nan
        out["ask"] = num(m[pick(m, "ask")]) if pick(m, "ask") else np.nan
        out["vol"] = num(m[pick(m, "vol")]) if pick(m, "vol") else np.nan
        out["siccd"] = num(m[pick(m, "siccd", "hsiccd")]) if pick(m, "siccd", "hsiccd") else np.nan
        shrcd = num(m[pick(m, "shrcd")]) if pick(m, "shrcd") else None
        exchcd = num(m[pick(m, "exchcd")]) if pick(m, "exchcd") else None
        if shrcd is None or exchcd is None:
            raise SystemExit("Ancien format : SHRCD et EXCHCD sont indispensables (actions ordinaires, bourse).")
        out["primaryexch"] = exchcd.map({1: "N", 2: "A", 3: "Q"})
        out = out[shrcd.isin([10, 11]) & exchcd.isin([1, 2, 3])]
        # rendement de délisting : colonne DLRET dans le fichier, ou fichier séparé
        dl = None
        if "dlret" in m:
            dl = pd.DataFrame({"permno": num(m["permno"]).astype("Int64"),
                               "date": parse_date(m[pick(m, "date")]), "dlret": num(m["dlret"])}).dropna()
        elif find("crsp_delist") is not None:
            d = read(find("crsp_delist"))
            dl = pd.DataFrame({"permno": num(d["permno"]).astype("Int64"), "date": parse_date(d["dlstdt"]),
                               "dlret": num(d["dlret"])}).dropna()
        if dl is not None:
            dl["date"] = dl["date"] + pd.offsets.MonthEnd(0)
            out["mdate"] = out["date"] + pd.offsets.MonthEnd(0)
            out = out.merge(dl.rename(columns={"date": "mdate"}), on=["permno", "mdate"], how="left")
            has = out["dlret"].notna()
            out.loc[has, "ret"] = (1 + out.loc[has, "ret"].fillna(0)) * (1 + out.loc[has, "dlret"]) - 1
            out = out.drop(columns=["mdate", "dlret"])
            print(f"  rendements de délisting intégrés : {int(has.sum()):,}")
        else:
            print("  [ATTENTION] aucun rendement de délisting trouvé (DLRET ou crsp_delist.csv) : biais de survie")

    out = out.dropna(subset=["permno", "date"])
    out["permno"] = out["permno"].astype("int64")
    out["permco"] = num(out["permco"]).fillna(out["permno"]).astype("int64")
    if out["me"].isna().all():
        out["me"] = out["prc"].abs() * out["shrout"]
    out.to_parquet(RAW / "crsp_monthly.parquet", index=False)
    print(f"  -> crsp_monthly.parquet : {len(out):,} lignes, {out['permno'].nunique():,} titres, "
          f"{out['date'].min():%Y-%m} -> {out['date'].max():%Y-%m}")


# ------------------------------------------------------------------------------- CRSP journalier
def import_daily():
    folder = CSV / "crsp_daily"
    files = sorted(p for p in folder.glob("*") if p.suffix in (".csv", ".gz", ".zip", ".txt")) if folder.exists() else []
    if not files:
        f = find("crsp_daily")
        files = [f] if f else []
    if not files:
        print("Pas de CSV journalier : la volatilité sera calculée sur 36 mois (solution de repli).")
        return
    tmp = RAW / "crsp_daily" / "_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    part = 0
    for f in files:
        print(f"Journalier : {f.name}")
        for chunk in pd.read_csv(f, chunksize=5_000_000, low_memory=False):
            chunk.columns = [c.strip().lower() for c in chunk.columns]
            d = pd.DataFrame({"permno": num(chunk["permno"]),
                              "date": parse_date(chunk[pick(chunk, "dlycaldt", "date")]),
                              "ret": num(chunk[pick(chunk, "dlyret", "ret")]).astype("float32")}).dropna(subset=["permno", "date"])
            d["permno"] = d["permno"].astype("int64")
            for y, g in d.groupby(d["date"].dt.year):
                g.to_parquet(tmp / f"{y}_{part:04d}.parquet", index=False)
            part += 1
            print(f"  bloc {part} : {len(d):,} lignes")
    years = sorted({p.name.split("_")[0] for p in tmp.glob("*.parquet")})
    for y in years:
        parts = sorted(tmp.glob(f"{y}_*.parquet"))
        g = pd.concat([pd.read_parquet(p) for p in parts]).drop_duplicates(["permno", "date"])
        g.to_parquet(RAW / "crsp_daily" / f"{y}.parquet", index=False)
        for p in parts:
            p.unlink()
    tmp.rmdir()
    print(f"  -> crsp_daily/ : {len(years)} années ({years[0]} -> {years[-1]})")


# ------------------------------------------------------------------------------- Compustat et CCM
def import_compustat():
    f = find("compustat")
    if f is None:
        raise SystemExit(f"Fichier introuvable : {CSV}/compustat.csv")
    c = read(f)
    for col, val in (("indfmt", "INDL"), ("datafmt", "STD"), ("popsrc", "D"), ("consol", "C")):
        if col in c:
            c = c[c[col].astype(str).str.strip() == val]
    c["datadate"] = parse_date(c["datadate"])
    need = ["gvkey", "datadate", "fyear", "revt", "cogs", "xsga", "xint", "seq", "ceq", "at", "lt", "txditc",
            "pstkrv", "pstkl", "pstk"]
    miss = [x for x in need if x not in c]
    if miss:
        raise SystemExit(f"Compustat : variables manquantes {miss}")
    c = c[need].copy()
    c["gvkey"] = c["gvkey"].astype(str).str.zfill(6)
    c.to_parquet(RAW / "compustat_funda.parquet", index=False)
    print(f"Compustat -> compustat_funda.parquet : {len(c):,} lignes, {c['gvkey'].nunique():,} firmes")


def import_ccm():
    f = find("ccm_link")
    if f is None:
        raise SystemExit(f"Fichier introuvable : {CSV}/ccm_link.csv")
    k = read(f)
    k = k.rename(columns={"lpermno": "permno"})
    k = k[k["linktype"].isin(["LU", "LC"]) & k["linkprim"].isin(["P", "C"]) & k["permno"].notna()]
    k["gvkey"] = k["gvkey"].astype(str).str.zfill(6)
    k["permno"] = num(k["permno"]).astype("int64")
    k["linkdt"] = parse_date(k["linkdt"])
    end = k["linkenddt"].astype(str).str.strip().replace({"E": None, "nan": None, "": None})
    k["linkenddt"] = parse_date(end).fillna(pd.Timestamp("2099-12-31"))
    k = k[["gvkey", "permno", "linktype", "linkprim", "linkdt", "linkenddt"]]
    k.to_parquet(RAW / "ccm_link.parquet", index=False)
    print(f"CCM -> ccm_link.parquet : {len(k):,} liens")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["monthly", "daily", "compustat", "ccm"])
    a = ap.parse_args()
    CSV.mkdir(parents=True, exist_ok=True)
    steps = {"monthly": import_monthly, "compustat": import_compustat, "ccm": import_ccm, "daily": import_daily}
    for k, fn in steps.items():
        if a.only in (None, k):
            fn()
    print("\nTerminé. Étape suivante : python code/main.py")


if __name__ == "__main__":
    main()
