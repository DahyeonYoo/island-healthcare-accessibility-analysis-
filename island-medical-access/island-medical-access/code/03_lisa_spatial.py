# -*- coding: utf-8 -*-
"""
03_lisa_spatial.py  (STEP 5)  — 공간자기상관 (Global Moran's I + Local Moran/LISA)
실행: 리포지토리 루트에서  python code/03_lisa_spatial.py
입력: data/from_teammate/step3_map_table.csv  (cx, cy = EPSG:5179)
출력: data/processed/step5_lisa_result.csv,  outputs/figures/step5_lisa_map.png
방법: KNN(k=6) 행표준화 가중치, permutation=999, seed=42.
"""
import os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import koreanize_matplotlib  # noqa: F401
import matplotlib.pyplot as plt
from libpysal.weights import KNN
from esda.moran import Moran, Moran_Local

MAP_TABLE = "data/from_teammate/step3_map_table.csv"
PROC = "data/processed"; FIG = "outputs/figures"
SEED, K = 42, 6


def main():
    os.makedirs(PROC, exist_ok=True); os.makedirs(FIG, exist_ok=True)
    np.random.seed(SEED)
    d = pd.read_csv(MAP_TABLE)
    coords = np.c_[d["cx"].values, d["cy"].values]
    y = d["Y_time_emergency"].values
    w = KNN.from_array(coords, k=K); w.transform = "r"

    mi = Moran(y, w, permutations=999)
    print(f"Global Moran's I = {mi.I:.3f} | p(sim) = {mi.p_sim:.4f} | z = {mi.z_sim:.2f}")
    lm = Moran_Local(y, w, permutations=999, seed=SEED)
    labmap = {1: "HH(취약집적)", 2: "LH", 3: "LL(양호집적)", 4: "HL"}
    d["LISA_quadrant"] = [labmap[i] for i in lm.q]
    d["LISA_cluster"] = np.where(lm.p_sim < 0.05, d["LISA_quadrant"], "비유의")
    print(d["LISA_cluster"].value_counts().to_string())
    d[["섬코드", "섬이름", "시군구", "Y_time_emergency", "LISA_cluster"]].to_csv(
        f"{PROC}/step5_lisa_result.csv", index=False, encoding="utf-8-sig")

    colors = {"HH(취약집적)": "#C00000", "LL(양호집적)": "#2E75B6",
              "LH": "#F4B183", "HL": "#A6A6A6", "비유의": "#E8E8E8"}
    fig, ax = plt.subplots(figsize=(8, 8))
    for lab, c in colors.items():
        s = d[d["LISA_cluster"] == lab]
        ax.scatter(s["cx"], s["cy"], c=c, s=np.sqrt(s["2024년 총인구"].clip(1)) * 3 + 10,
                   label=f"{lab} ({len(s)})", edgecolors="white", linewidths=0.4, alpha=0.9)
    ax.set_title(f"LISA 공간자기상관 — 응급의료 도달시간\n"
                 f"Global Moran's I={mi.I:.3f} (p={mi.p_sim:.3f})", fontsize=13, fontweight="bold")
    ax.legend(loc="upper right", fontsize=9, title="군집(마커=인구)")
    ax.set_aspect("equal"); ax.axis("off")
    plt.tight_layout(); plt.savefig(f"{FIG}/step5_lisa_map.png", dpi=150, bbox_inches="tight"); plt.close()


if __name__ == "__main__":
    main()
