# -*- coding: utf-8 -*-
"""
Step C: 접근성 shp value -> 격자 마스터 wide merge
  대상: 보건기관 / 응급의료 / 의원  x  2020~2023  (총 12개 레이어)
  키:   gid (대문자 GID도 자동 정규화)
  결측: value == -999 -> NaN (별도 *_raw 보존 안 함, 정책지표상 -999는 무자료)
산출물:
  02_interim/grid_master_jeonnam.gpkg   (geometry + 12개 접근성 컬럼)
  02_interim/grid_access_table.csv      (geometry 제외, gid 기준 분석용)
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd

from project_paths import BASE
OUT = BASE / "02_interim"
CRS = "EPSG:5179"
MISSING = -999

# 지표 종류: (폴더 키워드, 출력 접두)
TYPES = {
    "보건기관": "health",
    "응급의료시설": "emergency",
    "의원": "clinic",
}
YEARS = [2020, 2021, 2022, 2023]


def find_shp(folder: Path) -> Path:
    shps = list(folder.glob("*.shp"))
    if not shps:
        raise FileNotFoundError(f"shp 없음: {folder}")
    return shps[0]


# --- 격자 마스터 로드 (geometry 유지) ---
grid = gpd.read_file(OUT / "grid_master_jeonnam.gpkg").to_crs(CRS)
# 기존 임시 컬럼 정리 (Step A에서 넣은 2023 보건 값은 재생성)
drop_old = [c for c in grid.columns if c.startswith("access_")]
grid = grid.drop(columns=drop_old)
print("격자 마스터:", len(grid), "행 | 기존 임시컬럼 제거:", drop_old)

merged = grid[["gid", "sgg_cd", "sgg_nm_k", "geometry"]].copy()
jeonnam_gids = set(merged["gid"].astype(str))

report = []
for kw, prefix in TYPES.items():
    for yr in YEARS:
        folder = BASE / f"(B100)국토통계_국토정책지표-{kw} 접근성-500M_{yr}"
        if not folder.exists():
            print("폴더 없음(건너뜀):", folder.name)
            continue
        shp = find_shp(folder)
        # geometry 무시하고 속성만 빠르게 로드
        df = gpd.read_file(shp, ignore_geometry=True)
        df.columns = [c.lower() for c in df.columns]
        if "gid" not in df.columns or "value" not in df.columns:
            print("컬럼 이상(건너뜀):", shp.name, list(df.columns))
            continue
        col = f"acc_{prefix}_{yr}"
        sub = df[["gid", "value"]].copy()
        sub["gid"] = sub["gid"].astype(str)
        sub = sub[sub["gid"].isin(jeonnam_gids)]
        sub = sub.rename(columns={"value": col})
        sub.loc[sub[col] == MISSING, col] = pd.NA
        sub = sub.drop_duplicates(subset="gid")
        merged = merged.merge(sub, on="gid", how="left")
        valid = merged[col].notna().sum()
        report.append((col, len(sub), valid))
        print(f"{col}: 매칭 {len(sub)} | 유효(non-null) {valid}")

# --- 저장 ---
merged = gpd.GeoDataFrame(merged, geometry="geometry", crs=CRS)
merged.to_file(OUT / "grid_master_jeonnam.gpkg", driver="GPKG")

tbl = merged.drop(columns="geometry")
tbl.to_csv(OUT / "grid_access_table.csv", index=False, encoding="utf-8-sig")

print()
print("=== Step C 완료 ===")
acc_cols = [c for c in merged.columns if c.startswith("acc_")]
print("추가된 접근성 컬럼:", len(acc_cols))
print(merged[acc_cols].describe().T[["count", "mean", "min", "max"]].to_string())
print("저장:", OUT / "grid_master_jeonnam.gpkg", "/", OUT / "grid_access_table.csv")
