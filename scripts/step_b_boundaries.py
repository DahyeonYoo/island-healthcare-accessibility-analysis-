# -*- coding: utf-8 -*-
"""
Step B-2: 277개 유인도 전체에 지오메트리 부여
  - confidence high/medium : shp(AL_D158) 매칭 폴리곤 사용
  - confidence low/none     : CSV 위/경도 + 면적 기반 '원형 버퍼' 대체 경계 (geom_source='buffer')
산출물: 02_interim/island_boundaries_jeonnam.gpkg  (섬코드별 1개 지오메트리)
"""
import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

BASE = Path(r"C:\Users\dyu18\OneDrive\문서\데이터활용대회")
OUT = BASE / "02_interim"
CRS = "EPSG:5179"

PATH_CW = OUT / "island_crosswalk.csv"
PATH_CSV = BASE / "전라남도 유인도정보_20241231.csv"
PATH_SHP = BASE / "AL_D158_00_20260114" / "AL_D158_00_20260114.shp"

DEFAULT_RADIUS_M = 150.0  # 면적 정보 없을 때 기본 반경

# --- 면적 컬럼 탐색 ---
csv = pd.read_csv(PATH_CSV, encoding="utf-8-sig").rename(
    columns={"섬 코드": "섬코드", "섬 이름": "섬이름"}
)
csv["섬코드"] = csv["섬코드"].astype(int)
area_cols = [c for c in csv.columns if "면적" in c and "제곱키로" in c]
# 지적도 우선, 없으면 해안선
area_col = next((c for c in area_cols if "지적도" in c), area_cols[0] if area_cols else None)
print("면적 컬럼:", area_col)

cw = pd.read_csv(PATH_CW, encoding="utf-8-sig")

# --- 1) high/medium: shp 폴리곤 ---
# 주의: crosswalk 스크립트와 동일하게 '전남 필터 -> reset_index -> shp_id' 순서여야 인덱스가 일치
shp = gpd.read_file(PATH_SHP, encoding="cp949").to_crs(CRS)
jn = shp[shp["A1"].astype(str).str.contains("전라남", na=False)].copy()
jn = jn.reset_index(drop=True)
jn["shp_id"] = jn.index

good = cw[cw["confidence"].isin(["high", "medium"])].copy()
good = good.merge(jn[["shp_id", "geometry"]], on="shp_id", how="left")
good = gpd.GeoDataFrame(good, geometry="geometry", crs=CRS)
good["geom_source"] = "shp"

# 면적 정합성 검사: shp 폴리곤 면적이 CSV 면적의 0.3~3.0배를 벗어나면 신뢰 불가 -> 버퍼로 강등
good = good.merge(csv[["섬코드", area_col]], on="섬코드", how="left")
good["geom_area_km2"] = good.geometry.area / 1e6
ratio = good["geom_area_km2"] / good[area_col]
area_bad = good[area_col].notna() & (good[area_col] > 0) & ((ratio < 0.3) | (ratio > 3.0))
print("면적 불일치로 버퍼 강등:", int(area_bad.sum()), "개 ->",
      good.loc[area_bad, "섬이름"].tolist())
demoted = good[area_bad].copy()
good = good[~area_bad].drop(columns=[area_col, "geom_area_km2"])

# --- 2) low/none + 면적불일치: CSV 좌표 + 면적 버퍼 ---
bad = cw[cw["confidence"].isin(["low", "none"])].copy()
# 강등된 섬코드 추가
bad = pd.concat([bad, cw[cw["섬코드"].isin(demoted["섬코드"])]], ignore_index=True).drop_duplicates(subset="섬코드")
bad = bad.merge(csv[["섬코드", area_col]], on="섬코드", how="left")

def radius_m(area_km2):
    if pd.isna(area_km2) or area_km2 <= 0:
        return DEFAULT_RADIUS_M
    return math.sqrt(area_km2 * 1e6 / math.pi)

bad_pts = gpd.GeoDataFrame(
    bad,
    geometry=gpd.points_from_xy(bad["경도"], bad["위도"], crs="EPSG:4326"),
).to_crs(CRS)
bad_pts["geometry"] = [
    geom.buffer(radius_m(a)) for geom, a in zip(bad_pts.geometry, bad_pts[area_col])
]
bad_pts["geom_source"] = "buffer"
bad_pts = bad_pts.drop(columns=[area_col])

# --- 3) 결합 ---
keep_cols = ["섬코드", "섬이름", "시군구", "confidence", "geom_source", "geometry"]
island_b = pd.concat(
    [good[keep_cols], bad_pts[keep_cols]], ignore_index=True
)
island_b = gpd.GeoDataFrame(island_b, geometry="geometry", crs=CRS)
island_b = island_b.dissolve(by="섬코드", aggfunc="first").reset_index()
island_b["area_km2"] = island_b.geometry.area / 1e6

out = OUT / "island_boundaries_jeonnam.gpkg"
island_b.to_file(out, driver="GPKG")

print("=== island_boundaries_jeonnam.gpkg ===")
print("총 섬:", len(island_b))
print("geom_source:", island_b["geom_source"].value_counts().to_dict())
print("confidence:", island_b["confidence"].value_counts().to_dict())
print("면적(km2) min/median/max:",
      round(island_b["area_km2"].min(), 3),
      round(island_b["area_km2"].median(), 3),
      round(island_b["area_km2"].max(), 1))
print("저장:", out)
