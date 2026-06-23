# -*- coding: utf-8 -*-
"""
소지역 중심좌표(X_COORD/Y_COORD) → 섬코드 매핑.
  핵심: 소지역 테이블에 좌표가 있으므로 별도 집계구 경계 shp가 필요 없다.
  점(블록 중심) → 기존 island_boundaries 폴리곤에 point-in-polygon 공간조인.

산출:
  04_center/smallarea_island_lookup.csv  (BLOCK_CD/집계구/행정동 ↔ 섬코드)  ★카드·SKT 병합키
  04_center/adong_island_map.csv         (행정동 → 섬코드 리스트, 다대다·안분/맥락용)
"""
import geopandas as gpd
import pandas as pd

from prep00_config import (FILE_SMALLAREA, INTERIM, OUT, ISLAND_CRS,
                           SIDO_JEONNAM, SMALLAREA_CRS, smart_read_csv)

NEAREST_FALLBACK_M = 0   # >0 으로 두면 섬 경계 밖 블록을 그 거리 내 최근접 섬에 보강매칭

sa = smart_read_csv(FILE_SMALLAREA)
sa = sa[sa["SIDO_CD"] == SIDO_JEONNAM].copy()
for c in ["X_COORD", "Y_COORD", "AREA", "LENGTH"]:
    if c in sa.columns:
        sa[c] = pd.to_numeric(sa[c], errors="coerce")

pts = gpd.GeoDataFrame(
    sa, geometry=gpd.points_from_xy(sa["X_COORD"], sa["Y_COORD"]),
    crs=SMALLAREA_CRS).to_crs(ISLAND_CRS)
isl = gpd.read_file(INTERIM / "island_boundaries_jeonnam.gpkg").to_crs(ISLAND_CRS)

joined = gpd.sjoin(pts, isl[["섬코드", "섬이름", "geometry"]],
                   how="left", predicate="within").drop(columns="index_right")

# (옵션) 섬 경계 밖 블록을 최근접 섬에 보강 — 부두/방파제 등 경계 살짝 밖 블록 구제
if NEAREST_FALLBACK_M > 0:
    miss = joined[joined["섬코드"].isna()].copy()
    if len(miss):
        near = gpd.sjoin_nearest(
            miss.drop(columns=["섬코드", "섬이름"]),
            isl[["섬코드", "섬이름", "geometry"]],
            how="left", max_distance=NEAREST_FALLBACK_M, distance_col="_d")
        joined.loc[near.index, "섬코드"] = near["섬코드"]
        joined.loc[near.index, "섬이름"] = near["섬이름"]

keep = [c for c in ["BLOCK_CD", "SMRY_AREA", "ADONG_CD", "ADONG_NM",
                    "LDONG_CD", "SGNG_CD", "SGNG_NM", "AREA", "섬코드", "섬이름"]
        if c in joined.columns]
lookup = joined[keep].copy()
lookup.to_csv(OUT / "smallarea_island_lookup.csv", index=False, encoding="utf-8-sig")

print("=== 소지역 → 섬 크로스워크 ===")
print(f"전남 블록 {len(lookup)} | 섬 매칭 {lookup['섬코드'].notna().sum()} "
      f"| 커버 섬 {lookup['섬코드'].nunique()}")

# 행정동 → 섬(다대다). 한 면이 여러 섬을 포함하므로 안분/맥락용으로 별도 보관.
adong = (lookup.dropna(subset=["섬코드"])
         .groupby("ADONG_CD")["섬코드"]
         .agg(lambda s: ",".join(sorted(set(s.astype(str))))).reset_index())
adong.to_csv(OUT / "adong_island_map.csv", index=False, encoding="utf-8-sig")
print("행정동→섬 매핑 저장:", len(adong), "개 행정동")
print("저장:", OUT / "smallarea_island_lookup.csv")
