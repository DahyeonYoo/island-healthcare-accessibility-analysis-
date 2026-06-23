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

from project_paths import INTERIM, RAW
OUT = INTERIM
CRS = "EPSG:5179"
MISSING = -999

# 지표 종류: (폴더 키워드, 출력 접두)
TYPES = {
    "보건기관": "health",
    "응급의료시설": "emergency",
    "의원": "clinic",
}
YEARS = [2020, 2021, 2022, 2023]


def find_access_source(keyword: str, year: int) -> Path:
    stem = f"(B100)국토통계_국토정책지표-{keyword} 접근성-500M_{year}"
    folder = RAW / "접근성" / stem
    if folder.exists():
        shps = list(folder.glob("*.shp"))
        if shps:
            return shps[0]

    zip_path = RAW / "접근성" / f"{stem}.zip"
    if zip_path.exists():
        return zip_path

    raise FileNotFoundError(stem)


def read_access_source(path: Path):
    if path.suffix.lower() == ".zip":
        return gpd.read_file(f"zip://{path}", ignore_geometry=True)
    return gpd.read_file(path, ignore_geometry=True)


def read_access_geometry(path: Path):
    if path.suffix.lower() == ".zip":
        return gpd.read_file(f"zip://{path}")
    return gpd.read_file(path)


def ensure_grid_master() -> None:
    out = OUT / "grid_master_jeonnam.gpkg"
    if out.exists():
        return

    source = find_access_source("보건기관", 2023)
    g = read_access_geometry(source)
    g.columns = [c.lower() for c in g.columns]
    if "sido_cd" not in g.columns:
        raise KeyError(f"sido_cd 컬럼 없음: {source}")
    g = g[g["sido_cd"].astype(str).str.zfill(2) == "46"].copy()
    keep = [c for c in ["gid", "sgg_cd", "sgg_nm_k", "geometry"] if c in g.columns]
    g = g[keep].to_crs(CRS)
    g.to_file(out, driver="GPKG")
    print("초기 격자 마스터 생성:", out, "| rows:", len(g))


# --- 격자 마스터 로드 (geometry 유지) ---
ensure_grid_master()
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
        try:
            source = find_access_source(kw, yr)
        except FileNotFoundError as e:
            print("접근성 파일 없음(건너뜀):", e)
            continue
        # geometry 무시하고 속성만 빠르게 로드
        df = read_access_source(source)
        df.columns = [c.lower() for c in df.columns]
        if "gid" not in df.columns or "value" not in df.columns:
            print("컬럼 이상(건너뜀):", source.name, list(df.columns))
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
