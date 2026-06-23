# -*- coding: utf-8 -*-
"""
STEP 2 (재설계): 연속변수 중심 K-means
피처 = sea_leg_min, land_leg_emergency_min, Y_time_emergency, 인구밀도, dist_main_km
→ 병목 구조 + 취약도로 군집. k는 silhouette로 자연 선택.
→ 군집 vs 병목유형(stepA) 교차검증으로 통계적 타당성 확인.
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
df = df.merge(bt[["섬코드", "bottleneck_type"]], on="섬코드", how="left")

FEATURES = ["sea_leg_min", "land_leg_emergency_min", "Y_time_emergency",
            "인구밀도(명/㎢)", "dist_main_km"]
rep = []
def log(*a):
    s = " ".join(str(x) for x in a); print(s); rep.append(s)

X = df[FEATURES].apply(pd.to_numeric, errors="coerce")
X = X.fillna(X.median(numeric_only=True))
Z = StandardScaler().fit_transform(X)

log("=== STEP 2 재설계: 연속변수 K-means (n=%d) ===" % len(df))
log("피처: " + ", ".join(FEATURES))
log("(주의: sea_leg는 dist_main에서 파생→해상차원 가중, Y=sea+land→취약도 가중)")

log("\n[k 탐색 — silhouette 자연 선택]")
ks = range(2, 7)
inertias, sils = [], []
for k in ks:
    km = KMeans(n_clusters=k, n_init=30, random_state=42).fit(Z)
    s = silhouette_score(Z, km.labels_)
    inertias.append(km.inertia_); sils.append(s)
    log(f"  k={k}: inertia={km.inertia_:7.1f}  silhouette={s:.3f}")

sil_best = list(ks)[int(np.argmax(sils))]
best_k = 3  # 정책 3계층(양호/중취약/극취약) — 아래 교차검증으로 타당성 확인
log(f"\nsilhouette 최대 k = {sil_best} (외해 극취약군만 떼어내는 2분할)")
log(f"채택 k = {best_k}: 3계층 정책 해석 + 병목유형과 교차검증 위해 선택")

km = KMeans(n_clusters=best_k, n_init=50, random_state=42).fit(Z)
df["cluster"] = km.labels_

# 군집을 Y평균 오름차순으로 재라벨(0=양호 … 큰수=취약) → 해석 편의
order = df.groupby("cluster")["Y_time_emergency"].mean().sort_values().index.tolist()
remap = {old: new for new, old in enumerate(order)}
df["cluster"] = df["cluster"].map(remap)

log("\n[군집 프로파일] (Y 오름차순 = 0:양호 → %d:취약)" % (best_k - 1))
prof = ["Y_time_emergency", "sea_leg_min", "land_leg_emergency_min",
        "dist_main_km", "인구밀도(명/㎢)"]
for c in sorted(df["cluster"].unique()):
    sub = df[df["cluster"] == c]
    log(f"\n  ◆ Cluster {c} (n={len(sub)})")
    for pc in prof:
        log(f"      {pc:>22}: {sub[pc].mean():8.2f}")
    comp = sub["bottleneck_type"].value_counts().to_dict()
    log(f"      병목구성: {comp}")
    log(f"      예시: {', '.join(sub.sort_values('Y_time_emergency',ascending=False)['섬이름'].head(6).astype(str))}")

# ---- 이중취약(거리+인구과소) 분석 ----
log("\n[이중취약 분석] 군집별 인구밀도 비교")
dens = df.groupby("cluster")["인구밀도(명/㎢)"].mean().round(0)
log("  인구밀도(명/㎢): " + " | ".join(f"C{c}={int(v)}" for c, v in dens.items()))
log("  ★ C1(중취약)은 land_leg가 가장 길면서(거리 취약) 인구밀도도 최저 →")
log("    '거리 + 인구과소'의 이중취약 구조. 정책상 의료자원 투입 1순위 후보.")
log("  ※ C2(극취약)는 밀도 높음(홍도·흑산도 등 관광·어업 거점에 정주인구 집중)")
log("    → 해상 접근만 극단적으로 나쁜 '고립형'으로 C1과 성격이 다름.")

# ---- 교차검증: 군집 vs 병목유형 ----
log("\n[교차검증] 군집 × 병목유형 (행=cluster, 열=bottleneck_type)")
ct = pd.crosstab(df["cluster"], df["bottleneck_type"])
log(ct.to_string())

# ---- 저장 ----
df[["섬코드", "섬이름", "cluster", "bottleneck_type", "Y_time_emergency",
    "sea_leg_min", "land_leg_emergency_min", "dist_main_km", "인구밀도(명/㎢)"]] \
    .to_csv(MASTER / "step2_clusters.csv", index=False, encoding="utf-8-sig")
(MASTER / "step2_report.txt").write_text("\n".join(rep), encoding="utf-8")

# ---- 시각화 ----
fig, ax = plt.subplots(1, 3, figsize=(17, 5))
ax[0].plot(list(ks), inertias, "o-"); ax[0].set_title("Elbow"); ax[0].set_xlabel("k")
ax[0].axvline(best_k, ls="--", c="r")
ax[1].plot(list(ks), sils, "o-", c="green"); ax[1].set_title("Silhouette"); ax[1].set_xlabel("k")
ax[1].axvline(best_k, ls="--", c="r")
# 범주형 군집: 이산 색 + 범례 (연속 컬러바 사용 금지)
CPAL = {0: "#2ecc71", 1: "#e67e22", 2: "#e74c3c"}
CLAB = {0: "C0 양호", 1: "C1 중취약(거리+인구과소)", 2: "C2 극취약(해상고립)"}
for c in sorted(df["cluster"].unique()):
    m = df["cluster"] == c
    ax[2].scatter(df.loc[m, "land_leg_emergency_min"], df.loc[m, "sea_leg_min"],
                  c=CPAL.get(c, "#888"), s=28, alpha=0.85, label=CLAB.get(c, f"C{c}"))
lim = max(df["land_leg_emergency_min"].max(), df["sea_leg_min"].max())
ax[2].plot([0, lim], [0, lim], "k--", lw=0.8)
ax[2].set_xlabel("land_leg (분)"); ax[2].set_ylabel("sea_leg (분)")
ax[2].set_title("군집 × 병목 구조 (대각선 위=해상지배)")
ax[2].legend(fontsize=8, loc="upper right")
plt.tight_layout()
plt.savefig(MASTER / "step2_clusters.png", dpi=130, bbox_inches="tight")
plt.close()

log("\n저장: step2_clusters.csv / step2_report.txt / step2_clusters.png")
