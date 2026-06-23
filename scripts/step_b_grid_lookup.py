# -*- coding: utf-8 -*-
"""
Step B-3: 격자 <-> 섬 매핑 (grid_island_lookup.csv)
  방법:
    1) 격자 centroid가 섬 경계 내부(within) -> 해당 섬에 귀속 (중/대형 섬의 모든 격자 포착)
    2) 1)에서 격자가 0개인 섬(격자보다 작은 소형 섬) -> 섬 대표점을 포함하는 격자를 1개 강제 배정
  결과: 전남 격자 49,233개 각각에 (섬코드 or NaN), 그리고 모든 섬은 최소 1개 격자 보유
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd

BASE = Path(r"C:\Users\dyu18\OneDrive\문서\데이터활용대회")
OUT = BASE / "02_interim"
CRS = "EPSG:5179"

grid = gpd.read_file(OUT / "grid_master_jeonnam.gpkg").to_crs(CRS)
islands = gpd.read_file(OUT / "island_boundaries_jeonnam.gpkg").to_crs(CRS)

# --- 1) 격자 centroid within 섬 (long-format 멤버십) ---
gc = grid[["gid", "sgg_cd", "geometry"]].copy()
gc["geometry"] = gc.geometry.centroid
join = gpd.sjoin(
    gc, islands[["섬코드", "섬이름", "시군구", "geometry"]],
    how="inner", predicate="within",
)
members = join[["gid", "sgg_cd", "섬코드", "섬이름", "시군구"]].copy()
members["assign_method"] = "centroid_within"

islands_with_grid = set(members["섬코드"].unique())
missing = islands[~islands["섬코드"].isin(islands_with_grid)].copy()
print("centroid-within으로 격자 잡힌 섬:", len(islands_with_grid), "/", len(islands))
print("격자 0개라 보강 필요한 섬:", len(missing))

# --- 2) 격자 0개인 섬: 섬 대표점 포함 격자 1개 배정 (공유 격자 중복 허용) ---
if len(missing) > 0:
    miss_pts = missing.copy()
    miss_pts["geometry"] = miss_pts.geometry.centroid
    assign = gpd.sjoin(
        miss_pts[["섬코드", "섬이름", "시군구", "geometry"]],
        grid[["gid", "sgg_cd", "geometry"]],
        how="left", predicate="within",
    )
    no_grid = assign[assign["gid"].isna()]["섬코드"].tolist()
    if no_grid:
        nn = gpd.sjoin_nearest(
            miss_pts[miss_pts["섬코드"].isin(no_grid)][["섬코드", "섬이름", "시군구", "geometry"]],
            grid[["gid", "sgg_cd", "geometry"]],
            how="left",
        )
        assign = pd.concat([assign[~assign["섬코드"].isin(no_grid)], nn], ignore_index=True)
    assign = assign.dropna(subset=["gid"]).drop_duplicates(subset="섬코드")
    assign["assign_method"] = "rep_point"
    supp = assign[["gid", "sgg_cd", "섬코드", "섬이름", "시군구", "assign_method"]]
    members = pd.concat([members, supp], ignore_index=True)

members = members.drop_duplicates(subset=["gid", "섬코드"])
members["섬코드"] = members["섬코드"].astype("Int64")
members.to_csv(OUT / "grid_island_lookup.csv", index=False, encoding="utf-8-sig")

# --- 리포트 ---
n_isl = members["섬코드"].nunique()
print("=== grid_island_lookup.csv (long format: gid x 섬코드) ===")
print("총 멤버십 행:", len(members))
print("귀속 격자(고유 gid):", members["gid"].nunique())
print("격자 보유 섬:", n_isl, "/", len(islands))
still = set(islands["섬코드"]) - set(members["섬코드"])
print("여전히 격자 0개인 섬:", len(still), sorted(still))
per = members.groupby("섬코드").size()
print("섬당 격자 수 min/median/max:", per.min(), int(per.median()), per.max())
# 공유 격자(여러 섬이 같은 gid) 수
shared = members.groupby("gid").size()
print("2개 이상 섬이 공유하는 격자 수:", int((shared > 1).sum()))
print("저장:", OUT / "grid_island_lookup.csv")
