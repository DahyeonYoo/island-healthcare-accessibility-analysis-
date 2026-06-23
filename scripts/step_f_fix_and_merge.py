# -*- coding: utf-8 -*-
"""
Step F: (1) Y 단위정합 재생성  (2) 팀원 X변수 병합  (3) 통합 마스터 저장

단위 확정: 국토통계 접근성 value = '도로 이동거리(km)' (뉴스/지표정의 확인)
  -> land_leg(km)를 시간(분)으로 환산해 Y를 '분'으로 통일

파라미터:
  FERRY_SPEED = 30 km/h  (사용자 지시: 그대로 유지)
  ROAD_SPEED  = 40 km/h  (도로구간 환산 가정, 민감도분석 대상)
  NOMINAL_ONISLAND = 10분 (섬내 시설 보유하나 도로접근성 무자료 시)

주 종속변수: Y_time_emergency  (확정)
"""
import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path(r"C:\Users\dyu18\OneDrive\문서\데이터활용대회")
MASTER = BASE / "03_master"
TEAM = Path(r"C:\Users\dyu18\Downloads\가현이의 마스터파일.xlsx")

FERRY_SPEED = 30.0
ROAD_SPEED = 40.0
NOMINAL_ONISLAND = 10.0
LEVELS = ["emergency", "clinic"]

ana = pd.read_csv(MASTER / "island_analysis.csv", encoding="utf-8-sig")

# ---------- (1) Y 단위정합 재생성 (분) ----------
# sea_leg_min: 이미 분(거리/30*60). 검증 재계산
ana["sea_leg_min"] = np.where(
    ana["육지b연결유무"] == "연결", 0.0,
    ana["dist_main_km"] / FERRY_SPEED * 60.0,
)

for lvl in LEVELS:
    # land_leg(km) -> 분
    ana[f"land_leg_{lvl}_km"] = ana[f"land_leg_{lvl}"]            # 원본(km) 보존
    ana[f"land_leg_{lvl}_min"] = ana[f"land_leg_{lvl}_km"] / ROAD_SPEED * 60.0

    # 섬내 도달시간(분): 섬 자체 접근성(km, 있으면) 환산, 없으면 nominal
    own_km = ana[f"acc_{lvl}_2023_mean"]                          # km
    on_min = np.where(own_km.notna(), own_km / ROAD_SPEED * 60.0, NOMINAL_ONISLAND)

    off_min = ana["sea_leg_min"] + ana[f"land_leg_{lvl}_min"]
    has = ana[f"has_{lvl}_onisland"] == 1
    ana[f"Y_time_{lvl}"] = np.where(has, np.minimum(on_min, off_min), off_min)

ana["Y_primary"] = ana["Y_time_emergency"]  # 주 종속변수 확정

# 더 이상 혼동되는 km/분 미표기 컬럼 제거
ana = ana.drop(columns=["land_leg_emergency", "land_leg_clinic"], errors="ignore")

# ---------- (2) 팀원 X변수 병합 ----------
team = pd.ExcelFile(TEAM).parse("01_통합마스터(섬단위)")
team = team.rename(columns={"섬 코드": "섬코드"})
team["섬코드"] = team["섬코드"].astype(int)
ana["섬코드"] = ana["섬코드"].astype(int)

mine_cols = set(ana.columns)
team_only = [c for c in team.columns
             if c not in mine_cols and c not in ("섬 이름",)]
# 팀원 파생 X변수 접두 표기(_t)로 출처 구분 — 단, 의미가 분명한 건 그대로
RENAME_PREFIX = {c: f"team_{c}" for c in team_only if c.startswith("접근성_") or c.startswith("여객선_")}
team_sel = team[["섬코드"] + team_only].rename(columns=RENAME_PREFIX)

merged = ana.merge(team_sel, on="섬코드", how="left")

# ---------- (3) 저장 ----------
out = MASTER / "master_unified.csv"
merged.to_csv(out, index=False, encoding="utf-8-sig")

# ---------- 리포트 ----------
print("=== Step F 완료 ===")
print(f"파라미터: FERRY={FERRY_SPEED} ROAD={ROAD_SPEED} NOMINAL={NOMINAL_ONISLAND}")
print("통합 마스터:", merged.shape, "(이전 분석테이블 +", len(team_only), "팀원컬럼)")
for lvl in LEVELS:
    s = merged[f"Y_time_{lvl}"]
    print(f"[Y_time_{lvl}] 결측={s.isna().sum()} mean={s.mean():.1f} median={s.median():.1f} min={s.min():.1f} max={s.max():.1f}")
print()
print("주 종속변수 Y_primary(=emergency) 악접근 상위 10:")
print(merged.sort_values("Y_primary", ascending=False)
      [["섬이름", "시군구", "2024년 총인구", "dist_main_km", "sea_leg_min", "land_leg_emergency_min", "Y_primary"]]
      .head(10).to_string(index=False))
print()
print("병합된 팀원 핵심 파생변수 결측 점검:")
for c in ["인구_log", "인구밀도(명/㎢)", "고령화_보조_세대당인구", "1차의료_시설합", "의료공백_flag", "증감률_num(%)"]:
    cc = c if c in merged.columns else None
    if cc:
        print(f"  {c}: 결측 {merged[cc].isna().sum()}")
print("저장:", out)
