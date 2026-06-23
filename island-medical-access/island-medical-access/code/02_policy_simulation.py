# -*- coding: utf-8 -*-
"""
02_policy_simulation.py  (STEP 4)  — 정책매트릭스 + 격차해소율 시뮬레이션
실행: 리포지토리 루트에서  python code/02_policy_simulation.py
입력: data/from_teammate/step3_map_table.csv
출력: data/processed/step4_*.csv,  outputs/figures/step4_*.png
"""
import os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import koreanize_matplotlib  # noqa: F401
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

MAP_TABLE = "data/from_teammate/step3_map_table.csv"
PROC = "data/processed"
FIG = "outputs/figures"
GOLDEN, HELI_SPEED, HELI_OVH, LAND_CAP, SEA_RED = 60.0, 200.0, 15.0, 30.0, 0.40


def main():
    os.makedirs(PROC, exist_ok=True); os.makedirs(FIG, exist_ok=True)
    d = pd.read_csv(MAP_TABLE)
    d["pop"] = d["2024년 총인구"]
    base = d["Y_time_emergency"]
    sea, land, dist = d["sea_leg_min"], d["land_leg_emergency_min"], d["dist_main_km"]
    heli = dist / HELI_SPEED * 60 + HELI_OVH
    prC2, prC1 = d["cluster"] == 2, d["cluster"] == 1
    isL = d["bottleneck_type"].isin(["육지지배형", "혼합형"])

    def s1():
        y = base.copy(); y[prC2] = heli[prC2] + land[prC2]; return y

    def s2():
        y = base.copy(); m = (prC1 | prC2) & isL
        y[m] = sea[m] + np.minimum(land[m], LAND_CAP); return y

    def s3():
        y = base.copy(); y[prC2] = heli[prC2] + land[prC2]
        m = prC1 & isL; y[m] = sea[m] + np.minimum(land[m], LAND_CAP)
        s = prC1 & (d["bottleneck_type"] == "해상지배형"); y[s] = sea[s] * (1 - SEA_RED) + land[s]
        return y

    scen = {"현행": base, "S1 해상패키지": s1(), "S2 육지거점": s2(), "S3 통합대책": s3()}

    def stat(y, G=GOLDEN):
        v = y > G
        return int(v.sum()), int(d.loc[v, "pop"].sum()), round(y.mean(), 1)

    S = pd.DataFrame([[k, *stat(y)] for k, y in scen.items()],
                     columns=["시나리오", "골든타임초과_섬수", "초과_인구", "평균Y(분)"])
    bn, bp, bm = S.iloc[0, 1], S.iloc[0, 2], S.iloc[0, 3]
    S["섬_감소율%"] = ((bn - S["골든타임초과_섬수"]) / bn * 100).round(1)
    S["인구_감소율%"] = ((bp - S["초과_인구"]) / bp * 100).round(1)
    S["평균Y단축%"] = ((bm - S["평균Y(분)"]) / bm * 100).round(1)
    S.to_csv(f"{PROC}/step4_scenario_summary.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame([{"기준(분)": G, **{k.split(" ")[0]: int((y > G).sum()) for k, y in scen.items()}}
                  for G in [30, 45, 60]]).to_csv(f"{PROC}/step4_sensitivity.csv", index=False, encoding="utf-8-sig")

    d["Y_base"] = base.round(1); d["Y_S3"] = s3().round(1); d["Y단축_S3"] = (base - s3()).round(1)
    d[["섬코드", "섬이름", "시군구", "cluster", "bottleneck_type", "pop", "Y_base", "Y_S3", "Y단축_S3"]]\
        .sort_values("Y단축_S3", ascending=False)\
        .to_csv(f"{PROC}/step4_island_simulation.csv", index=False, encoding="utf-8-sig")
    pd.crosstab(d["cluster"], d["bottleneck_type"]).to_csv(f"{PROC}/step4_policy_matrix_counts.csv", encoding="utf-8-sig")

    _fig_scenario(S); _fig_matrix(d)
    print(S.to_string(index=False))


def _fig_scenario(S):
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    lab = [c.replace(" ", "\n", 1) for c in S["시나리오"]]
    col = ["#9aa0a6", "#5B9BD5", "#ED7D31", "#C00000"]
    for a, key, title, unit in [(ax[0], "골든타임초과_섬수", "골든타임(60분) 초과 섬 수", "섬 수"),
                                (ax[1], "평균Y(분)", "평균 응급 도달시간", "분")]:
        a.bar(lab, S[key], color=col)
        for i, v in enumerate(S[key]): a.text(i, v, str(v), ha="center", va="bottom", fontweight="bold")
        a.set_title(title, fontweight="bold"); a.set_ylabel(unit)
    fig.suptitle("정책 시나리오별 의료격차 해소 효과 (전남 277개 유인도)", fontsize=13, fontweight="bold")
    plt.tight_layout(); plt.savefig(f"{FIG}/step4_fig1_scenario_effect.png", dpi=150, bbox_inches="tight"); plt.close()


def _fig_matrix(d):
    cnt = pd.crosstab(d["cluster"], d["bottleneck_type"])
    for c in ["해상지배형", "혼합형", "육지지배형", "섬내자립형"]:
        if c not in cnt: cnt[c] = 0
    cols = ["해상지배형", "혼합형", "육지지배형", "섬내자립형"]
    rlab = {2: "C2 극취약\n(외해 고립·14섬)", 1: "C1 중취약\n(거리+인구과소·117섬)", 0: "C0 양호\n(본토 근접·146섬)"}
    pol = {(2, "해상지배형"): "응급헬기 권역배치\n+ 병원선 정기운항", (2, "혼합형"): "헬기 + 거점 동시",
           (1, "해상지배형"): "병원선·항로 증편", (1, "혼합형"): "순회진료+응급이송\n+권역센터",
           (1, "육지지배형"): "도서인접 권역\n응급센터+이송체계", (1, "섬내자립형"): "기존 시설 유지",
           (0, "육지지배형"): "기존 육지망 유지\n·모니터링", (0, "해상지배형"): "현행 유지", (0, "혼합형"): "현행 유지"}
    sevface = {2: "#FCE4E4", 1: "#FFF2DD", 0: "#EAF3E3"}; sevcol = {2: "#C00000", 1: "#ED7D31", 0: "#70AD47"}
    fig, ax = plt.subplots(figsize=(12, 5.2)); ax.set_xlim(0, 4); ax.set_ylim(0, 3); ax.axis("off")
    for ri, cl in enumerate([2, 1, 0]):
        ax.text(-0.05, 2.5 - ri, rlab[cl], ha="right", va="center", fontweight="bold", color=sevcol[cl])
        for ci, c in enumerate(cols):
            n = int(cnt.loc[cl, c]) if c in cnt.columns else 0
            ax.add_patch(Rectangle((ci, 2 - ri), 0.96, 0.96,
                         facecolor=(sevface[cl] if n else "#F7F7F7"), edgecolor="white", lw=2))
            ax.text(ci + 0.48, 2 - ri + 0.62, f"{n}섬", ha="center", va="center", fontweight="bold", fontsize=11)
            ax.text(ci + 0.48, 2 - ri + 0.28, pol.get((cl, c), "—"), ha="center", va="center", fontsize=8)
    for ci, c in enumerate(cols):
        ax.text(ci + 0.48, 3.05, c, ha="center", va="bottom", fontweight="bold")
    ax.set_title("도서 의료취약 정책매트릭스: 심각도(군집) × 병목유형 → 맞춤 처방", fontsize=13, fontweight="bold", pad=18)
    plt.tight_layout(); plt.savefig(f"{FIG}/step4_fig2_policy_matrix.png", dpi=150, bbox_inches="tight"); plt.close()


if __name__ == "__main__":
    main()
