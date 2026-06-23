# -*- coding: utf-8 -*-
"""
STEP 3: 지역별 강도 공간 시각화
  ① 군집 3계층 지도
  ② 병목 유형 지도 (해상/육지/혼합/자립)
  ③ Y(응급의료 도달시간) 강도 단계구분도
  ④ C1(이중취약) 강조 — 인구 크기 + 위치
"""
import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False

from project_paths import BASE
INTERIM, MASTER = BASE / "02_interim", BASE / "03_master"

g = gpd.read_file(INTERIM / "island_boundaries_jeonnam.gpkg")
clu = pd.read_csv(MASTER / "step2_clusters.csv", encoding="utf-8-sig")
mu = pd.read_csv(MASTER / "master_unified.csv", encoding="utf-8-sig")
pop_col = "2024년 총인구"
clu = clu.merge(mu[["섬코드", pop_col]], on="섬코드", how="left")
g = g.merge(clu, on="섬코드", how="left", suffixes=("", "_c"))
g["pop"] = pd.to_numeric(g[pop_col], errors="coerce").fillna(0)

# 대표점(centroid) — 작은 섬도 보이도록 마커로 표시
g["cx"] = g.geometry.centroid.x
g["cy"] = g.geometry.centroid.y

CPAL = {0: "#2ecc71", 1: "#e67e22", 2: "#e74c3c"}
CLAB = {0: "C0 양호 (본토근접)", 1: "C1 중취약 (거리+인구과소)", 2: "C2 극취약 (해상고립)"}
BPAL = {"육지지배형": "#3498db", "해상지배형": "#e74c3c",
        "혼합형": "#9b59b6", "섬내자립형": "#2ecc71"}

def base_ax(ax, title):
    ax.set_title(title, fontsize=13)
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)

# ---- ① 군집 3계층 ----
fig, ax = plt.subplots(figsize=(9, 9))
g.plot(ax=ax, color="#f2f2f2", edgecolor="#cccccc", linewidth=0.3)
for c in sorted(g["cluster"].dropna().unique()):
    m = g["cluster"] == c
    ax.scatter(g.loc[m, "cx"], g.loc[m, "cy"], s=42, c=CPAL[int(c)],
               edgecolor="white", linewidth=0.4, label=CLAB[int(c)], zorder=3)
base_ax(ax, "STEP3-① 의료취약 군집 (K-means k=3)")
ax.legend(loc="lower left", fontsize=10, frameon=True)
plt.tight_layout(); plt.savefig(MASTER / "step3_map1_cluster.png", dpi=140, bbox_inches="tight"); plt.close()

# ---- ② 병목 유형 ----
fig, ax = plt.subplots(figsize=(9, 9))
g.plot(ax=ax, color="#f2f2f2", edgecolor="#cccccc", linewidth=0.3)
for t, col in BPAL.items():
    m = g["bottleneck_type"] == t
    if m.any():
        ax.scatter(g.loc[m, "cx"], g.loc[m, "cy"], s=42, c=col,
                   edgecolor="white", linewidth=0.4, label=f"{t} ({int(m.sum())})", zorder=3)
base_ax(ax, "STEP3-② 의료도달 병목 유형")
ax.legend(loc="lower left", fontsize=10, frameon=True)
plt.tight_layout(); plt.savefig(MASTER / "step3_map2_bottleneck.png", dpi=140, bbox_inches="tight"); plt.close()

# ---- ③ Y 강도 단계구분도 ----
fig, ax = plt.subplots(figsize=(9.5, 9))
g.plot(ax=ax, color="#f2f2f2", edgecolor="#cccccc", linewidth=0.3)
vmax = float(np.nanpercentile(g["Y_time_emergency"], 98))
sc = ax.scatter(g["cx"], g["cy"], c=g["Y_time_emergency"], cmap="YlOrRd",
                s=46, vmin=0, vmax=vmax, edgecolor="#555", linewidth=0.3, zorder=3)
# 가장 취약한 섬 라벨
top = g.sort_values("Y_time_emergency", ascending=False).head(8)
for _, r in top.iterrows():
    ax.annotate(f"{r['섬이름']}\n{r['Y_time_emergency']:.0f}분",
                (r["cx"], r["cy"]), fontsize=8, ha="center", va="bottom",
                xytext=(0, 6), textcoords="offset points", color="#7b241c")
cb = plt.colorbar(sc, ax=ax, shrink=0.6); cb.set_label("응급의료 도달시간 (분)")
base_ax(ax, "STEP3-③ 의료 도달시간(Y) 강도")
plt.tight_layout(); plt.savefig(MASTER / "step3_map3_Yintensity.png", dpi=140, bbox_inches="tight"); plt.close()

# ---- ④ C1 이중취약 강조 (마커=인구, 위치) ----
fig, ax = plt.subplots(figsize=(9.5, 9))
g.plot(ax=ax, color="#f7f7f7", edgecolor="#dddddd", linewidth=0.3)
# 배경: C0/C2 회색
other = g[g["cluster"] != 1]
ax.scatter(other["cx"], other["cy"], s=18, c="#cfcfcf", zorder=2, label="C0·C2")
# C1: 인구 크기로 마커 (작을수록 인구과소)
c1 = g[g["cluster"] == 1].copy()
sizes = 20 + (c1["pop"].clip(upper=2000) / 2000) * 280
ax.scatter(c1["cx"], c1["cy"], s=sizes, c="#e67e22", alpha=0.75,
           edgecolor="#7e3b09", linewidth=0.5, zorder=3, label="C1 (마커=인구)")
# 인구 최저 C1 섬 라벨 (이중취약 핵심)
lab = c1.sort_values("pop").head(10)
for _, r in lab.iterrows():
    ax.annotate(f"{r['섬이름']}({int(r['pop'])})", (r["cx"], r["cy"]),
                fontsize=7.5, ha="center", va="bottom",
                xytext=(0, 5), textcoords="offset points", color="#7e3b09")
base_ax(ax, "STEP3-④ C1 이중취약군 (거리+인구과소) — 마커=정주인구")
ax.legend(loc="lower left", fontsize=10, frameon=True)
plt.tight_layout(); plt.savefig(MASTER / "step3_map4_C1focus.png", dpi=140, bbox_inches="tight"); plt.close()

# 저장 (지도용 속성 테이블)
g.drop(columns="geometry").to_csv(MASTER / "step3_map_table.csv", index=False, encoding="utf-8-sig")
print("저장 완료: step3_map1~4 .png + step3_map_table.csv")
print("C1 인구과소 Top10:", ", ".join(f"{r['섬이름']}({int(r['pop'])})" for _, r in lab.iterrows()))
