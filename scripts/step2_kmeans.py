# -*- coding: utf-8 -*-
"""
STEP 2: K-means 클러스터링
목적: 의료취약 특성이 유사한 섬을 군집화 → 유형별 정책 묶음 도출.
피처: (A) 병목 구조(sea/land leg) + (B) 취약 프로파일(인구·고립 인프라)
"""
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False

from project_paths import BASE
MASTER = BASE / "03_master"
df = pd.read_csv(MASTER / "master_unified.csv", encoding="utf-8-sig")
bt = pd.read_csv(MASTER / "stepA_bottleneck.csv", encoding="utf-8-sig")
df = df.merge(bt[["섬코드", "bottleneck_type", "sea_share"]], on="섬코드", how="left")

FEATURES = [
    "sea_leg_min", "land_leg_emergency_min",      # 병목 구조
    "인구밀도(명/㎢)", "인구_log", "고령화_보조_세대당인구", "증감률_num(%)",  # 인구
    "소규모급수시설_b", "해수담수화시설_b", "디젤발전_b", "지하수(관정)_b",   # 고립 인프라
    "해안선길이(키로미터)",
]
rep = []
def log(*a):
    s = " ".join(str(x) for x in a); print(s); rep.append(s)

X = df[FEATURES].copy().apply(pd.to_numeric, errors="coerce")
X = X.fillna(X.median(numeric_only=True))
Z = StandardScaler().fit_transform(X)

log("=== STEP 2: K-means 클러스터링 (n=%d, 피처 %d개) ===" % (len(df), len(FEATURES)))
log("피처: " + ", ".join(FEATURES))

# ---- k 탐색 (elbow + silhouette) ----
log("\n[k 탐색]")
ks = range(2, 9)
inertias, sils = [], []
for k in ks:
    km = KMeans(n_clusters=k, n_init=20, random_state=42).fit(Z)
    inertias.append(km.inertia_)
    s = silhouette_score(Z, km.labels_)
    sils.append(s)
    log(f"  k={k}: inertia={km.inertia_:8.1f}  silhouette={s:.3f}")

best_k = list(ks)[int(np.argmax(sils))]
# 정책 해석을 위해 4개 내외 선호: silhouette 상위 중 3~5 범위 우선
pref = [k for k in ks if 3 <= k <= 5]
best_k = max(pref, key=lambda k: sils[list(ks).index(k)])
log(f"\n선택 k = {best_k} (정책 해석성 고려, k 3~5 중 silhouette 최대)")

km = KMeans(n_clusters=best_k, n_init=50, random_state=42).fit(Z)
df["cluster"] = km.labels_

# ---- 군집 프로파일 ----
log("\n[군집 프로파일]")
prof_cols = ["Y_time_emergency", "sea_leg_min", "land_leg_emergency_min",
             "인구밀도(명/㎢)", "고령화_보조_세대당인구",
             "소규모급수시설_b", "해수담수화시설_b"]
for c in sorted(df["cluster"].unique()):
    sub = df[df["cluster"] == c]
    bt_mode = sub["bottleneck_type"].mode()
    bt_mode = bt_mode.iloc[0] if len(bt_mode) else "-"
    log(f"\n  ◆ Cluster {c}  (n={len(sub)}, 주병목={bt_mode})")
    for pc in prof_cols:
        log(f"      {pc:>20}: {sub[pc].mean():8.2f}")
    # 병목 유형 구성
    comp = sub["bottleneck_type"].value_counts().to_dict()
    log(f"      병목구성: {comp}")
    log(f"      예시섬: {', '.join(sub.sort_values('Y_time_emergency',ascending=False)['섬이름'].head(5).astype(str))}")

# ---- 저장 ----
keep = ["섬코드", "섬이름", "cluster", "bottleneck_type",
        "Y_time_emergency", "sea_leg_min", "land_leg_emergency_min",
        "인구밀도(명/㎢)"]
keep = [c for c in keep if c in df.columns]
df[keep].to_csv(MASTER / "step2_clusters.csv", index=False, encoding="utf-8-sig")
(MASTER / "step2_report.txt").write_text("\n".join(rep), encoding="utf-8")

# ---- 시각화 ----
fig, ax = plt.subplots(1, 3, figsize=(17, 5))
ax[0].plot(list(ks), inertias, "o-"); ax[0].set_title("Elbow (inertia)")
ax[0].set_xlabel("k"); ax[0].axvline(best_k, ls="--", c="r")
ax[1].plot(list(ks), sils, "o-", c="green"); ax[1].set_title("Silhouette")
ax[1].set_xlabel("k"); ax[1].axvline(best_k, ls="--", c="r")

pca = PCA(n_components=2).fit(Z)
P = pca.transform(Z)
sc = ax[2].scatter(P[:, 0], P[:, 1], c=df["cluster"], cmap="tab10", s=22, alpha=0.8)
ax[2].set_title(f"PCA 2D (k={best_k}, 설명력 {pca.explained_variance_ratio_.sum():.0%})")
ax[2].set_xlabel("PC1"); ax[2].set_ylabel("PC2")
plt.colorbar(sc, ax=ax[2], label="cluster")
plt.tight_layout()
plt.savefig(MASTER / "step2_clusters.png", dpi=130, bbox_inches="tight")
plt.close()

# sea vs land, 색=cluster
fig2, ax2 = plt.subplots(figsize=(7, 6))
sc2 = ax2.scatter(df["land_leg_emergency_min"], df["sea_leg_min"],
                  c=df["cluster"], cmap="tab10", s=24, alpha=0.8)
lim = max(df["land_leg_emergency_min"].max(), df["sea_leg_min"].max())
ax2.plot([0, lim], [0, lim], "k--", lw=0.8)
ax2.set_xlabel("land_leg (분)"); ax2.set_ylabel("sea_leg (분)")
ax2.set_title("군집 × 병목 구조")
plt.colorbar(sc2, ax=ax2, label="cluster")
plt.tight_layout()
plt.savefig(MASTER / "step2_clusters_legmap.png", dpi=130, bbox_inches="tight")
plt.close()

log("\n저장: step2_clusters.csv / step2_report.txt / step2_clusters.png / step2_clusters_legmap.png")
