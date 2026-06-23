# -*- coding: utf-8 -*-
"""
Step D: 섬 단위 분석 테이블 생성 (STEP1 회귀/RF 입력)
  결합:
    1) grid_access_table x grid_island_lookup -> 섬별 접근성 집계(mean/min/max)
    2) + 유인도 CSV (인구/면적/시설/연결/지역지정 등 전체)
    3) + ferry_island_access (소요시간/운항편수)
  산출물:
    03_master/island_analysis.csv (+ .parquet 가능 시)
"""
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(r"C:\Users\dyu18\OneDrive\문서\데이터활용대회")
INTERIM = BASE / "02_interim"
MASTER = BASE / "03_master"
MASTER.mkdir(exist_ok=True)

# --- 1) 격자 접근성 -> 섬 집계 ---
acc = pd.read_csv(INTERIM / "grid_access_table.csv", encoding="utf-8-sig")
lookup = pd.read_csv(INTERIM / "grid_island_lookup.csv", encoding="utf-8-sig")

acc_cols = [c for c in acc.columns if c.startswith("acc_")]
gi = lookup[["gid", "섬코드"]].merge(acc[["gid"] + acc_cols], on="gid", how="left")

agg_funcs = {}
for c in acc_cols:
    agg_funcs[c] = ["mean", "min", "max"]
island_acc = gi.groupby("섬코드").agg(agg_funcs)
island_acc.columns = [f"{c}_{stat}" for c, stat in island_acc.columns]
island_acc = island_acc.reset_index()

grid_cnt = gi.groupby("섬코드").size().rename("grid_count").reset_index()
island_acc = island_acc.merge(grid_cnt, on="섬코드", how="left")
island_acc["섬코드"] = island_acc["섬코드"].astype(int)
print("섬별 접근성 집계:", island_acc.shape)

# --- 2) 유인도 CSV (전체 속성) ---
csv = pd.read_csv(BASE / "전라남도 유인도정보_20241231.csv", encoding="utf-8-sig")
csv = csv.rename(columns={"섬 코드": "섬코드", "섬 이름": "섬이름"})
csv["섬코드"] = csv["섬코드"].astype(int)
print("유인도 CSV:", csv.shape)

# --- 3) ferry ---
ferry = pd.read_csv(
    BASE / "운항 소요시간-20260604T115924Z-3-001" / "운항 소요시간" / "ferry_island_access.csv",
    encoding="utf-8-sig",
)
ferry = ferry.rename(columns={"섬코드": "섬코드"})
ferry["섬코드"] = ferry["섬코드"].astype(int)
ferry_keep = ferry[["섬코드", "최단소요_대표분", "최단소요_min", "최단소요_max",
                    "총운항편수_편도", "경유항로수"]].copy()
ferry_keep["ferry_available"] = 1
print("ferry:", ferry_keep.shape)

# --- 결합 ---
df = csv.merge(island_acc, on="섬코드", how="left")
df = df.merge(ferry_keep, on="섬코드", how="left")
df["ferry_available"] = df["ferry_available"].fillna(0).astype(int)

# 접근성 무자료 섬 플래그 (모든 격자 -999였던 경우)
df["access_allnull"] = df["acc_health_2023_mean"].isna().astype(int)

# --- 저장 ---
out_csv = MASTER / "island_analysis.csv"
df.to_csv(out_csv, index=False, encoding="utf-8-sig")
saved = [str(out_csv)]
try:
    out_pq = MASTER / "island_analysis.parquet"
    df.to_parquet(out_pq, index=False)
    saved.append(str(out_pq))
except Exception as e:
    print("parquet 저장 생략:", e)

# --- 리포트 ---
print()
print("=== Step D 완료 ===")
print("최종 테이블:", df.shape, "(277섬 x 변수)")
print("ferry 보유 섬:", int(df["ferry_available"].sum()))
print("접근성 무자료 섬:", int(df["access_allnull"].sum()))
print()
key = ["acc_health_2023_mean", "acc_emergency_2023_mean", "acc_clinic_2023_mean",
       "최단소요_대표분", "2024년 총인구"]
key = [k for k in key if k in df.columns]
print(df[key].describe().T[["count", "mean", "min", "max"]].to_string())
print()
print("저장:", saved)
