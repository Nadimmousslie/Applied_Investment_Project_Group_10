"""
01_extract_wrds.py — QVMM : extraction des données brutes (à lancer au CDIF ou avec un accès WRDS).

Produit dans data/raw/ :
    crsp_monthly.parquet       CRSP CIZ mensuel (rendement, prix, shrout, ME, bid, ask, volume, flags, SIC)
    crsp_daily/YYYY.parquet    CRSP CIZ journalier (permno, date, ret), un fichier par année
    compustat_funda.parquet    Compustat annuel (postes de l'OP et du BE)
    ccm_link.parquet           table de liens CRSP-Compustat
    french_ff5.parquet, french_mom.parquet, french_ff3_daily.parquet  (facteurs, en décimal)

Lancement :
    pip install wrds pandas pyarrow requests
    python 01_extract_wrds.py              # tout
    python 01_extract_wrds.py --skip-daily # sans le journalier (long)
    python 01_extract_wrds.py --only french

Le script vérifie les colonnes réellement présentes dans les tables CIZ et s'arrête avec un
message clair s'il en manque une. Les noms CIZ varient selon les versions : en cas d'erreur,
corrigez seulement le dictionnaire MSF_COLS ci-dessous (alignez-le sur le code du prof).
"""
import argparse
import importlib
import io
import os
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
cfg_mod = importlib.import_module("00_config")
CFG, RAW = cfg_mod.CFG, cfg_mod.DATA_RAW

# ------------------------------------------------------------------------------------------
# Colonnes CIZ : nom standard dans notre code -> noms candidats dans crsp.msf_v2 (premier trouvé)
MSF_COLS = {
    "permno": ["permno"],
    "permco": ["permco"],
    "date": ["mthcaldt", "date"],
    "ret": ["mthret"],                    # rendement total, delisting inclus en CIZ (à vérifier)
    "retx": ["mthretx"],                  # rendement de prix (pour la dérive des poids)
    "prc": ["mthprc"],
    "shrout": ["shrout"],
    "me": ["mthcap"],
    "bid": ["mthbid", "mthprcbid", "bid"],
    "ask": ["mthask", "mthprcask", "ask"],
    "vol": ["mthvol", "vol"],
    "sharetype": ["sharetype"],
    "securitytype": ["securitytype"],
    "securitysubtype": ["securitysubtype"],
    "usincflg": ["usincflg"],
    "issuertype": ["issuertype"],
    "primaryexch": ["primaryexch"],
    "conditionaltype": ["conditionaltype"],
    "tradingstatusflg": ["tradingstatusflg"],
    "siccd": ["siccd", "sic"],
}
OPTIONAL = {"bid", "ask", "vol", "retx", "me"}   # utiles mais pas bloquants
DSF_COLS = {"permno": ["permno"], "date": ["dlycaldt", "date"], "ret": ["dlyret", "ret"]}


def connect():
    import wrds
    user = os.environ.get(CFG["wrds_username_env"])
    return wrds.Connection(wrds_username=user) if user else wrds.Connection()


def resolve(db, library, table, wanted):
    """Associe nos noms aux colonnes présentes dans la table ; erreur claire si une colonne manque."""
    present = set(db.describe_table(library=library, table=table)["name"].str.lower())
    mapping, missing = {}, []
    for std, cands in wanted.items():
        hit = next((c for c in cands if c in present), None)
        if hit:
            mapping[std] = hit
        elif std not in OPTIONAL:
            missing.append(f"{std} (essayé : {cands})")
        else:
            print(f"  [info] colonne optionnelle absente : {std}")
    if missing:
        raise SystemExit(f"\nColonnes introuvables dans {library}.{table} :\n  - " + "\n  - ".join(missing)
                         + f"\nColonnes disponibles : {sorted(present)}\n"
                         "-> corrigez MSF_COLS / DSF_COLS en haut du script.")
    return mapping


def select_clause(mapping):
    return ", ".join(f"{src} AS {std}" for std, src in mapping.items())


# ------------------------------------------------------------------------------------------
def extract_crsp_monthly(db):
    print("CRSP mensuel (crsp.msf_v2)...")
    m = resolve(db, "crsp", "msf_v2", MSF_COLS)
    f = CFG["ciz_filters"]

    def inlist(col):
        return "(" + ", ".join(f"'{v}'" for v in f[col]) + ")"

    # On filtre les titres côté serveur (actions ordinaires US cotées). Le prix, la taille et
    # le SIC sont filtrés plus tard (02), car ils dépendent de la date t.
    where = " AND ".join(f"{m[c]} IN {inlist(c)}" for c in f if c in m)
    sql = f"""
        SELECT {select_clause(m)}
        FROM crsp.msf_v2
        WHERE {m['date']} BETWEEN '{CFG['crsp_start']}' AND '{CFG['crsp_end']}'
          AND {where}
    """
    df = db.raw_sql(sql, date_cols=["date"])
    df["permno"] = df["permno"].astype("int64")
    if "me" not in df:   # capitalisation si mthcap absent : |prix| x shrout
        df["me"] = df["prc"].abs() * df["shrout"]
    df.to_parquet(RAW / "crsp_monthly.parquet", index=False)
    print(f"  {len(df):,} lignes, {df['permno'].nunique():,} titres, "
          f"{df['date'].min():%Y-%m} -> {df['date'].max():%Y-%m}")
    return df


def extract_crsp_daily(db, permnos):
    print("CRSP journalier (crsp.dsf_v2), par année...")
    m = resolve(db, "crsp", "dsf_v2", DSF_COLS)
    y0, y1 = int(CFG["crsp_start"][:4]), int(CFG["crsp_end"][:4])
    perm_sql = ", ".join(str(p) for p in sorted(permnos))
    for y in range(y0, y1 + 1):
        out = RAW / "crsp_daily" / f"{y}.parquet"
        if out.exists():
            print(f"  {y} déjà téléchargé")
            continue
        sql = f"""
            SELECT {select_clause(m)}
            FROM crsp.dsf_v2
            WHERE {m['date']} BETWEEN '{y}-01-01' AND '{y}-12-31'
              AND permno IN ({perm_sql})
        """
        d = db.raw_sql(sql, date_cols=["date"])
        d["permno"] = d["permno"].astype("int64")
        d["ret"] = d["ret"].astype("float32")
        d.to_parquet(out, index=False)
        print(f"  {y} : {len(d):,} lignes")


def extract_compustat(db):
    print("Compustat annuel (comp.funda)...")
    sql = f"""
        SELECT gvkey, datadate, fyear,
               revt, cogs, xsga, xint, seq, ceq, at, lt, txditc, pstkrv, pstkl, pstk
        FROM comp.funda
        WHERE indfmt = 'INDL' AND datafmt = 'STD' AND popsrc = 'D' AND consol = 'C'
          AND datadate BETWEEN '{CFG['comp_start']}' AND '{CFG['crsp_end']}'
    """
    df = db.raw_sql(sql, date_cols=["datadate"])
    df.to_parquet(RAW / "compustat_funda.parquet", index=False)
    print(f"  {len(df):,} lignes, {df['gvkey'].nunique():,} firmes")


def extract_ccm(db):
    print("Liens CRSP-Compustat (crsp.ccmxpf_linktable)...")
    sql = """
        SELECT gvkey, lpermno AS permno, linktype, linkprim, linkdt, linkenddt
        FROM crsp.ccmxpf_linktable
        WHERE linktype IN ('LU', 'LC') AND linkprim IN ('P', 'C') AND lpermno IS NOT NULL
    """
    df = db.raw_sql(sql, date_cols=["linkdt", "linkenddt"])
    df["permno"] = df["permno"].astype("int64")
    df["linkenddt"] = df["linkenddt"].fillna(pd.Timestamp("2099-12-31"))  # lien encore actif
    df.to_parquet(RAW / "ccm_link.parquet", index=False)
    print(f"  {len(df):,} liens")


# ------------------------------------------------------------------------------------------
def read_french_zip(fname):
    """Télécharge un fichier Kenneth French et renvoie le PREMIER tableau (mensuel ou journalier) en décimal."""
    import requests
    r = requests.get(CFG["french_url"] + fname, timeout=60)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        text = z.read(z.namelist()[0]).decode("latin-1")
    rows, header, started = [], None, False
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if not started:
            if len(parts) > 1 and parts[0] == "" and any(parts[1:]):
                header = ["date"] + parts[1:]
                started = True
            continue
        if not parts[0].isdigit():      # fin du premier tableau (les annuels suivent)
            break
        rows.append(parts)
    df = pd.DataFrame(rows, columns=header)
    fmt = "%Y%m%d" if len(df["date"].iloc[0]) == 8 else "%Y%m"
    df["date"] = pd.to_datetime(df["date"], format=fmt)
    if fmt == "%Y%m":
        df["date"] = df["date"] + pd.offsets.MonthEnd(0)
    for c in df.columns[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce") / 100.0
    df.columns = ["date"] + [c.replace("-", "_").replace(" ", "_").upper() for c in df.columns[1:]]
    return df


def extract_french():
    print("Facteurs Kenneth French...")
    for key, fname in CFG["french_files"].items():
        df = read_french_zip(fname)
        df.to_parquet(RAW / f"french_{key}.parquet", index=False)
        print(f"  {key} : {df['date'].min():%Y-%m} -> {df['date'].max():%Y-%m}, colonnes {list(df.columns[1:])}")
    q = RAW / CFG["qfactor_file"]
    print("  q-factors : " + ("trouvé" if q.exists() else
          f"À TÉLÉCHARGER à la main sur global-q.org et placer dans {q}"))


# ------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["monthly", "daily", "compustat", "ccm", "french"])
    ap.add_argument("--skip-daily", action="store_true")
    a = ap.parse_args()

    if a.only == "french":
        extract_french()
        return

    db = connect()
    try:
        steps = [a.only] if a.only else ["monthly", "compustat", "ccm", "daily", "french"]
        monthly = None
        for s in steps:
            if s == "monthly":
                monthly = extract_crsp_monthly(db)
            elif s == "compustat":
                extract_compustat(db)
            elif s == "ccm":
                extract_ccm(db)
            elif s == "daily" and not a.skip_daily:
                if monthly is None:
                    monthly = pd.read_parquet(RAW / "crsp_monthly.parquet", columns=["permno"])
                extract_crsp_daily(db, monthly["permno"].unique())
            elif s == "french":
                extract_french()
    finally:
        db.close()

    # ------------------------------------------------------------------ contrôles rapides
    print("\nContrôles :")
    if (RAW / "crsp_monthly.parquet").exists():
        m = pd.read_parquet(RAW / "crsp_monthly.parquet")
        n = m.groupby(m["date"].dt.year)["permno"].nunique()
        print("  titres par an (extraits) :", n.loc[[y for y in (1975, 1990, 2000, 2010, 2025) if y in n.index]].to_dict())
        print("  part de rendements manquants :", round(m["ret"].isna().mean(), 4))
        for c in ("bid", "ask", "vol"):
            if c in m:
                print(f"  couverture {c} :", round(m[c].notna().mean(), 3))
    print("Terminé. Étape suivante : 02_crsp_clean.py")


if __name__ == "__main__":
    main()

