"""
02_crsp_clean.py — QVMM : nettoyage de CRSP mensuel et drapeaux d'univers.

Entrée  : data/raw/crsp_monthly.parquet          (01_extract_wrds.py)
Sortie  : data/clean/crsp_m.parquet

Une ligne par (permno, mois). On GARDE toutes les lignes, y compris les titres qui ne passent
pas les filtres, car leur historique sert au momentum. Les filtres de la roadmap (section 3.2)
sont stockés sous forme de colonnes booléennes, appliquées dans 04_signals.py :
    price_ok  : |prix| >= 5 $ à la fin du mois t
    size_ok   : capitalisation (niveau permco) >= 20e percentile NYSE du mois t
    is_fin    : SIC 6000-6999
    nyse      : titre coté au NYSE (pour les points de coupure)
Les filtres sur le type de titre (actions ordinaires US) ont déjà été appliqués à l'extraction.
"""
import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
cfg_mod = importlib.import_module("00_config")
CFG, RAW, CLEAN = cfg_mod.CFG, cfg_mod.DATA_RAW, cfg_mod.DATA_CLEAN


def main():
    m = pd.read_parquet(RAW / "crsp_monthly.parquet")
    print(f"Lu : {len(m):,} lignes")

    # ------------------------------------------------------------------ dates et types
    m["date"] = pd.to_datetime(m["date"]) + pd.offsets.MonthEnd(0)   # fin de mois calendaire
    m["permno"] = m["permno"].astype("int64")
    m["permco"] = m["permco"].astype("int64")
    # « vol » de CRSP = volume échangé ; renommé pour ne pas le confondre avec la volatilité
    m = m.rename(columns={"vol": "volume"})
    for c in ("ret", "retx", "prc", "shrout", "me", "bid", "ask", "volume"):
        if c in m:
            m[c] = pd.to_numeric(m[c], errors="coerce")

    # Doublons éventuels (permno, mois) : on garde la dernière observation du mois
    m = m.sort_values(["permno", "date"]).drop_duplicates(["permno", "date"], keep="last")

    # bid/ask mensuels vides : on reprend ceux du dernier jour coté du mois (journalier, 01b_import_csv.py)
    ba_file = RAW / "crsp_bidask_monthly.parquet"
    if ba_file.exists() and ("bid" not in m or m["bid"].isna().mean() > 0.5):
        ba = pd.read_parquet(ba_file)
        ba["date"] = pd.to_datetime(ba["date"]) + pd.offsets.MonthEnd(0)
        m = m.drop(columns=[c for c in ("bid", "ask") if c in m]).merge(ba, on=["permno", "date"], how="left")
        print(f"Bid/ask repris du journalier : {m['bid'].notna().mean():.1%} des lignes couvertes")

    # ------------------------------------------------------------------ capitalisation
    m["prc"] = m["prc"].abs()                     # prix négatif CRSP = moyenne bid/ask
    me_calc = m["prc"] * m["shrout"]
    m["me"] = m["me"].where(m["me"] > 0, me_calc) if "me" in m else me_calc
    m.loc[~(m["me"] > 0), "me"] = np.nan
    # Taille au niveau de l'entreprise (permco) pour le filtre de taille (plusieurs classes d'actions)
    m["me_permco"] = m.groupby(["date", "permco"])["me"].transform("sum", min_count=1)

    # ------------------------------------------------------------------ drapeaux
    m["nyse"] = m["primaryexch"].eq("N") if "primaryexch" in m else False
    sic = pd.to_numeric(m["siccd"], errors="coerce") if "siccd" in m else pd.Series(np.nan, index=m.index)
    if CFG["exclude_financials"]:
        if sic.isna().all():
            raise SystemExit("SIC (siccd) absent ou vide : impossible d'exclure les financières. "
                             "Retélécharger CRSP mensuel avec la colonne SICCD.")
        if sic.isna().mean() > 0.05:
            print(f"  [ATTENTION] SIC manquant pour {sic.isna().mean():.1%} des lignes : ces titres ne sont pas exclus")
    lo, hi = CFG["sic_fin"]
    m["is_fin"] = sic.between(lo, hi)
    m["price_ok"] = m["prc"] >= CFG["min_price"]

    # 20e percentile NYSE de la capitalisation, mois par mois (seuls les titres NYSE comptent)
    bp = (m[m["nyse"] & m["me_permco"].notna()]
          .groupby("date")["me_permco"].quantile(CFG["size_nyse_pct"]).rename("me_nyse_p20"))
    m = m.merge(bp, on="date", how="left")
    m["size_ok"] = m["me_permco"] >= m["me_nyse_p20"]

    keep = ["permno", "permco", "date", "ret", "retx", "prc", "shrout", "me", "me_permco",
            "nyse", "siccd", "is_fin", "price_ok", "size_ok", "bid", "ask", "volume"]
    m = m[[c for c in keep if c in m]].sort_values(["permno", "date"]).reset_index(drop=True)
    m.to_parquet(CLEAN / "crsp_m.parquet", index=False)

    # ------------------------------------------------------------------ contrôles
    y = m["date"].dt.year
    tab = pd.DataFrame({
        "titres": m.groupby(y)["permno"].nunique(),
        "nyse": m[m["nyse"]].groupby(y)["permno"].nunique(),
        "prix>=5 & taille>=p20": m[m["price_ok"] & m["size_ok"]].groupby(y)["permno"].nunique(),
        "hors financières": m[m["price_ok"] & m["size_ok"] & ~m["is_fin"]].groupby(y)["permno"].nunique(),
    })
    print("\nTitres distincts par an (sélection d'années) :")
    print(tab.loc[[a for a in (1975, 1985, 1995, 2000, 2010, 2020, 2025) if a in tab.index]].to_string())
    print(f"\nRendements manquants : {m['ret'].isna().mean():.2%}  |  ME manquante : {m['me'].isna().mean():.2%}")
    print(f"Écrit : {CLEAN / 'crsp_m.parquet'}  ({len(m):,} lignes)")


if __name__ == "__main__":
    main()
