"""
07_performance.py — QVMM : performance, alphas, spanning, GRS (roadmap, section 8).

    T5   performance et risque de chaque portefeuille (+ UMD et marché)
    T6   alphas (% par mois), t-stats Newey-West et ratios d'information : CAPM, FF3, FF5, FF5+MOM, q
    T6b  expositions détaillées dans FF5+MOM
    T6c  test GRS (alphas de P1 à P5 conjointement nuls)
    T7   spanning de P5 et différences P5 - P1, P5 - P2 ; test de différence de Sharpe
Échantillon : rendements de janvier 1975 à décembre 2025.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (LABELS, MODELS, grs_test, in_sample, jkm_sharpe_test, load_factors, load_returns, nw_reg,
                 perf_stats, save_table)

MAIN = ["P1_VW", "P2_VW", "P3_VW", "P4_IV", "P5_IV", "P5B_IV"]
CONTROLS = ["P1_EW", "P2_EW", "P3_EW"]


def series(rets, fac):
    s = {k: v["LS"] for k, v in rets.items()}
    s["UMD"] = fac["MOM"]
    s["MKT_RF"] = fac["MKT_RF"]
    return pd.DataFrame(s)


def main():
    fac = load_factors()
    rets = load_returns()
    S = in_sample(series(rets, fac))
    ports = [p for p in MAIN + CONTROLS if p in S]

    # ------------------------------------------------------------------ T5
    t5 = pd.DataFrame({LABELS.get(k, k): perf_stats(S[k]) for k in ports + ["UMD", "MKT_RF"]}).T
    t5["Turnover mensuel (%)"] = [rets[k]["turnover"].mean() * 100 if k in rets else np.nan for k in ports + ["UMD", "MKT_RF"]]
    t5["Titres L/S"] = [f"{rets[k]['n_L'].mean():.0f}/{rets[k]['n_S'].mean():.0f}" if k in rets else ""
                        for k in ports + ["UMD", "MKT_RF"]]
    t5.index.name = "Portefeuille"
    save_table(t5, "T5_performance", "Performance et risque des portefeuilles long/short, 1975–2025")

    # ------------------------------------------------------------------ T6
    models = {m: f for m, f in MODELS.items() if all(c in fac for c in f)}
    if "q" not in models:
        print("  (facteurs q absents : modèle q ignoré — voir 00_config.py, qfactor_file)")
    rows, expo = {}, {}
    for k in ports + ["UMD"]:
        row = {}
        for m, f in models.items():
            if k == "UMD" and "MOM" in f:      # UMD régressé sur lui-même : sans objet
                continue
            r = nw_reg(S[k], fac[f])
            row[(m, "α (%)")] = r["alpha"] * 100
            row[(m, "t")] = r["t_alpha"]
            row[(m, "IR")] = r["ir"]
            if m == "FF5+MOM":
                e = {"α (%)": r["alpha"] * 100, "t(α)": r["t_alpha"]}
                for b in f:
                    e[b] = r["betas"][b]
                    e[f"t({b})"] = r["t_betas"][b]
                e["R²"] = r["r2"]
                expo[LABELS.get(k, k)] = e
        rows[LABELS.get(k, k)] = row
    t6 = pd.DataFrame(rows).T
    t6.columns = [f"{m} {s}" for m, s in t6.columns]
    t6.index.name = "Portefeuille"
    save_table(t6, "T6_alphas", "Alphas mensuels (%) avec t-stats Newey-West (6 lags) et ratios d'information annualisés")
    t6b = pd.DataFrame(expo).T
    t6b.index.name = "Portefeuille"
    save_table(t6b, "T6b_expositions_FF5MOM", "Expositions factorielles dans le modèle FF5 + Momentum")

    grs = {}
    main_avail = [p for p in MAIN if p in S and p != "P5B_IV"]
    for m, f in models.items():
        g, pv = grs_test(S[main_avail], fac[f])
        grs[m] = {"GRS": g, "p-value": pv, "N portefeuilles": len(main_avail)}
    t6c = pd.DataFrame(grs).T
    t6c.index.name = "Modèle"
    save_table(t6c, "T6c_GRS", "Test GRS : alphas de P1 à P5 conjointement nuls", floatfmt="{:.3f}")

    # ------------------------------------------------------------------ T7 spanning et différences
    F = fac[MODELS["FF5+MOM"]]
    t7 = {}
    for target, base in (("P5_IV", "P1_VW"), ("P5_IV", "P2_VW"), ("P4_IV", "P2_EW"), ("P3_EW", "P4_IV")):
        if target not in S or base not in S:
            continue
        X = F.join(S[base].rename(base))
        r = nw_reg(S[target], X)
        t7[f"{target} | FF5+MOM + {base}"] = {"α (%)": r["alpha"] * 100, "t(α)": r["t_alpha"], "IR": r["ir"],
                                               f"δ (bêta sur la base)": r["betas"][base], "t(δ)": r["t_betas"][base],
                                               "R²": r["r2"]}
        d = nw_reg(S[target] - S[base], F)
        dsr, z, pv = jkm_sharpe_test(S[target], S[base])
        t7[f"{target} − {base} sur FF5+MOM"] = {"α (%)": d["alpha"] * 100, "t(α)": d["t_alpha"], "IR": d["ir"],
                                                "Δ Sharpe annuel": dsr * np.sqrt(12), "z (JK-Memmel)": z, "p": pv}
    t7 = pd.DataFrame(t7).T
    t7.index.name = "Régression"
    save_table(t7, "T7_spanning", "Tests de spanning et différences de portefeuilles (FF5 + Momentum)")

    print("\nRésumé FF5+MOM :")
    print(t6[[c for c in t6.columns if c.startswith("FF5+MOM")]].round(2).to_string())


if __name__ == "__main__":
    main()
