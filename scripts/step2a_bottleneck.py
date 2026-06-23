# -*- coding: utf-8 -*-
"""
STEP (A) Y 병목 분해 + 섬별 병목유형 분류
Y_time_emergency = min( 섬내도달시간(보유시), sea_leg_min + land_leg_emergency_min )
→ 각 섬의 '의료 도달시간이 어디서 발생하는가'를 분해해 개입 레버를 식별.
"""
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False

BASE = Path(r"C:\Users\dyu18\OneDrive\문서\데이터활용대회")
MASTER = BASE / "03_master"
df = pd.read_csv(MASTER / "master_unified.csv", encoding="utf-8-sig")

sea = df["sea_leg_min"].astype(float)
land = df["land_leg_emergency_min"].astype(float)
off = sea + land
Y = df["Y_time_emergency"].astype(float)
has_on = df.get("has_emergency_onisland", pd.Series(0, index=df.index)).fillna(0).astype(int)

# 섬내 시설이 실제로 Y를 결정(=off보다 빠름)하는지
on_binds = (has_on == 1) & (Y < off - 1e-6)

# off-leg 내 해상 비중
sea_share = np.where(off > 0, sea / off, 0.0)

def classify(i):
    if on_binds.iloc[i]:
        return "섬내자립형"
    s = sea_share[i]
    if s >= 0.60:
        return "해상지배형"
    if s <= 0.40:
        return "육지지배형"
    return "혼합형"

df["off_leg_min"] = off
df["sea_share"] = sea_share
df["bottleneck_type"] = [classify(i) for i in range(len(df))]

# ---- 요약 ----
rep = []
def log(*a):
    s = " ".join(str(x) for x in a); print(s); rep.append(s)

log("=== STEP A: Y 병목 분해 (응급의료 도달시간 기준, n=%d) ===" % len(df))
log("Y 평균 %.1f분 | sea_leg 평균 %.1f분 | land_leg 평균 %.1f분" %
    (Y.mean(), sea.mean(), land.mean()))
log("\n[병목 유형별 분포]")
g = df.groupby("bottleneck_type").agg(
    n=("섬코드", "size"),
    Y평균=("Y_time_emergency", "mean"),
    sea평균=("sea_leg_min", "mean"),
    land평균=("land_leg_emergency_min", "mean"),
).round(1).sort_values("n", ascending=False)
for t, r in g.iterrows():
    log(f"  {t:>7}: {int(r['n']):>3}개  | Y {r['Y평균']:>6.1f}분  "
        f"(sea {r['sea평균']:.1f} / land {r['land평균']:.1f})")

log("\n[유형별 정책 레버]")
log("  해상지배형 → 항로 증편·연륙(연도)교·응급헬기/병원선 (해상이동 단축)")
log("  육지지배형 → 도서 인접 권역응급의료센터 배치·강화 (육지측 거점)")
log("  혼합형     → 해상+육지 동시 개선 필요")
log("  섬내자립형 → 기존 시설 유지·보강 (이미 섬내 해결)")

# 가장 취약한 상위 15개 섬 (Y 큰 순)
log("\n[가장 취약한 섬 Top 15 (Y_time_emergency 큰 순)]")
top = df.sort_values("Y_time_emergency", ascending=False).head(15)
for _, r in top.iterrows():
    log(f"  {str(r.get('섬이름','?')):>8} | Y {r['Y_time_emergency']:>6.1f}분 "
        f"| sea {r['sea_leg_min']:>6.1f} land {r['land_leg_emergency_min']:>5.1f} "
        f"| {r['bottleneck_type']}")

# ---- 저장 ----
out_cols = ["섬코드", "섬이름"]
if "시군구" in df.columns:
    out_cols.append("시군구")
out_cols += ["Y_time_emergency", "sea_leg_min", "land_leg_emergency_min",
             "off_leg_min", "sea_share", "bottleneck_type"]
out = df[out_cols].copy()
out.to_csv(MASTER / "stepA_bottleneck.csv", index=False, encoding="utf-8-sig")
(MASTER / "stepA_bottleneck_report.txt").write_text("\n".join(rep), encoding="utf-8")

# ---- 시각화: 유형별 개수 + sea vs land 산점도 ----
fig, ax = plt.subplots(1, 2, figsize=(13, 5))
g["n"].plot(kind="bar", ax=ax[0], color="#4C72B0")
ax[0].set_title("병목 유형별 섬 수"); ax[0].set_ylabel("섬 수")
ax[0].tick_params(axis="x", rotation=0)

colors = {"해상지배형": "#1f77b4", "육지지배형": "#d62728",
          "혼합형": "#9467bd", "섬내자립형": "#2ca02c"}
for t, c in colors.items():
    m = df["bottleneck_type"] == t
    ax[1].scatter(df.loc[m, "land_leg_emergency_min"], df.loc[m, "sea_leg_min"],
                  s=18, alpha=0.7, c=c, label=t)
lim = max(df["land_leg_emergency_min"].max(), df["sea_leg_min"].max())
ax[1].plot([0, lim], [0, lim], "k--", lw=0.8)
ax[1].set_xlabel("land_leg (육지측, 분)"); ax[1].set_ylabel("sea_leg (해상, 분)")
ax[1].set_title("섬별 병목 위치 (대각선 위=해상지배)"); ax[1].legend(fontsize=8)
plt.tight_layout()
plt.savefig(MASTER / "stepA_bottleneck.png", dpi=130, bbox_inches="tight")
plt.close()

log("\n저장: stepA_bottleneck.csv / _report.txt / _bottleneck.png")
