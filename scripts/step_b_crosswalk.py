# -*- coding: utf-8 -*-
"""
Step B: 유인도 CSV(섬코드) <-> 섬 경계 shp(AL_D158) crosswalk 생성

매칭 전략 (수정판):
  - shp의 이름(A3) 필드가 부실(무명섬 다수)하므로 이름 매칭은 보조로만 사용
  - CSV 대표 좌표(위도/경도)를 기준점으로 사용
  - 1순위: point-in-polygon (within)  -> 전남 유인+무인 전체 폴리곤 대상
  - 2순위: nearest (max 5km)           -> within 실패 시
  - 신뢰도(confidence):
        within            -> high
        nearest < 500m    -> medium
        nearest >= 500m   -> low (검토 필요)
        미매칭             -> none
"""
import re
from pathlib import Path

import geopandas as gpd
import pandas as pd

BASE = Path(r"C:\Users\dyu18\OneDrive\문서\데이터활용대회")
OUT = BASE / "02_interim"
OUT.mkdir(exist_ok=True)

CRS = "EPSG:5179"
PATH_ISLAND_CSV = BASE / "전라남도 유인도정보_20241231.csv"
PATH_ISLAND_SHP = BASE / "AL_D158_00_20260114" / "AL_D158_00_20260114.shp"

NEAREST_MAX_M = 5000
REVIEW_DIST_M = 500


def base_name(n: str) -> str:
    return re.sub(r"\(.*\)", "", str(n)).strip()


# --- 1) CSV 로드 + 대표점 ---
csv = pd.read_csv(PATH_ISLAND_CSV, encoding="utf-8-sig")
csv = csv.rename(columns={"섬 코드": "섬코드", "섬 이름": "섬이름"})
csv["섬코드"] = csv["섬코드"].astype(int)

pts = gpd.GeoDataFrame(
    csv[["섬코드", "섬이름", "시군구", "위도", "경도"]].copy(),
    geometry=gpd.points_from_xy(csv["경도"], csv["위도"], crs="EPSG:4326"),
).to_crs(CRS)

# --- 2) shp 로드 (전남 전체: 유인+무인) ---
shp = gpd.read_file(PATH_ISLAND_SHP, encoding="cp949").to_crs(CRS)
jn = shp[shp["A1"].astype(str).str.contains("전라남", na=False)].copy()
jn = jn.reset_index(drop=True)
jn["shp_id"] = jn.index
jn = jn.rename(columns={"A3": "shp_섬이름", "A5": "shp_유무인", "A12": "shp_면적_m2", "A0": "shp_시군구코드"})
jn_keep = jn[["shp_id", "shp_섬이름", "shp_유무인", "shp_면적_m2", "shp_시군구코드", "geometry"]]

# --- 3) within ---
within = gpd.sjoin(pts, jn_keep, how="left", predicate="within")
# 한 점이 여러 폴리곤에 들어가는 경우(중첩) 방지: 면적 가장 작은 폴리곤(가장 구체적) 선택
within = within.sort_values("shp_면적_m2").drop_duplicates(subset="섬코드", keep="first")
within = within.set_index("섬코드").reindex(csv["섬코드"]).reset_index()

within["match_method"] = pd.NA
within.loc[within["shp_id"].notna(), "match_method"] = "within"
within.loc[within["shp_id"].notna(), "match_dist_m"] = 0.0

# --- 4) nearest (within 실패분) ---
need = within[within["shp_id"].isna()]["섬코드"].tolist()
if need:
    rest_pts = pts[pts["섬코드"].isin(need)].copy()
    near = gpd.sjoin_nearest(
        rest_pts,
        jn_keep,
        how="left",
        max_distance=NEAREST_MAX_M,
        distance_col="match_dist_m",
    )
    near = near.sort_values("match_dist_m").drop_duplicates(subset="섬코드", keep="first")
    near = near.set_index("섬코드")
    for code in need:
        if code in near.index and pd.notna(near.loc[code, "shp_id"]):
            row = near.loc[code]
            mask = within["섬코드"] == code
            within.loc[mask, "shp_id"] = row["shp_id"]
            within.loc[mask, "shp_섬이름"] = row["shp_섬이름"]
            within.loc[mask, "shp_유무인"] = row["shp_유무인"]
            within.loc[mask, "shp_면적_m2"] = row["shp_면적_m2"]
            within.loc[mask, "shp_시군구코드"] = row["shp_시군구코드"]
            within.loc[mask, "match_method"] = "nearest"
            within.loc[mask, "match_dist_m"] = row["match_dist_m"]

# --- 5) 신뢰도 + 이름검증 ---
def confidence(r):
    if pd.isna(r["shp_id"]):
        return "none"
    if r["match_method"] == "within":
        return "high"
    if r["match_dist_m"] < REVIEW_DIST_M:
        return "medium"
    return "low"

within["confidence"] = within.apply(confidence, axis=1)
within["csv_base"] = within["섬이름"].map(base_name)
within["name_match"] = within["csv_base"] == within["shp_섬이름"].astype(str).str.strip()
within["needs_review"] = within["confidence"].isin(["low", "none"])

cols = [
    "섬코드", "섬이름", "시군구", "위도", "경도",
    "shp_id", "shp_섬이름", "shp_유무인", "shp_면적_m2", "shp_시군구코드",
    "match_method", "match_dist_m", "confidence", "name_match", "needs_review",
]
crosswalk = within[cols].copy()
crosswalk["shp_id"] = crosswalk["shp_id"].astype("Int64")

out_path = OUT / "island_crosswalk.csv"
crosswalk.to_csv(out_path, index=False, encoding="utf-8-sig")

# --- 6) 리포트 ---
print("=== Step B crosswalk 결과 ===")
print("총 CSV 섬:", len(crosswalk))
print("매칭:", crosswalk["shp_id"].notna().sum(), "| 미매칭:", crosswalk["shp_id"].isna().sum())
print("method:", crosswalk["match_method"].value_counts(dropna=False).to_dict())
print("confidence:", crosswalk["confidence"].value_counts().to_dict())
print("이름 일치:", int(crosswalk["name_match"].sum()), "/", crosswalk["shp_id"].notna().sum())
print()
print("=== 검토 필요 (low / none) ===")
rev = crosswalk[crosswalk["needs_review"]][
    ["섬코드", "섬이름", "시군구", "shp_섬이름", "shp_유무인", "match_method", "match_dist_m", "confidence"]
]
print(rev.to_string(index=False))
print()
print("저장:", out_path)
