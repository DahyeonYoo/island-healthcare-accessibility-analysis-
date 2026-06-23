# -*- coding: utf-8 -*-
"""
격자 인구(long: BASE_YEAR/GRID_CD/STAT_ITM/STAT_VAL)
  → 피벗(wide) → 숫자변환 → grid_island_lookup join → 섬코드·연도별 집계.

산출: 04_center/island_grid_pop.csv  (BASE_YEAR, 섬코드, 인구항목들)

전제: prep01 ②에서 GRID_CD ↔ gid 직접매칭률이 충분(>50%)할 때.
      매칭률이 0이면 USE_DIRECT_JOIN=False 로 두고, 센터에서 받은
      '격자 중심좌표'로 좌표기반 공간조인(폴백) 경로를 사용.
"""
import geopandas as gpd
import pandas as pd

from prep00_config import (BASE, INTERIM, OUT, ISLAND_CRS, SMALLAREA_CRS,
                           smart_read_csv)

USE_DIRECT_JOIN = True
GRID_GLOB = "<격자인구*.csv>"          # 연도별 파일 패턴(현장에서 교체)
DEDUP_SHARED_GRID = False             # True면 공유격자(여러 섬) 인구를 1/n 가중 분배

# 발견 단계(prep01 ①)에서 확인한 STAT_ITM 코드 → 친숙한 이름. 현장에서 채울 것.
ITEM_MAP = {
    # "<총인구코드>": "총인구",
    # "<청년인구코드>": "청년인구",
    # "<고령인구코드>": "고령인구",
    # "<학령인구코드>": "학령인구",
}


def load_grid_long():
    frames = []
    for path in sorted(BASE.glob(GRID_GLOB)):
        gp = smart_read_csv(path)
        gp["STAT_VAL"] = pd.to_numeric(gp["STAT_VAL"], errors="coerce")
        wide = gp.pivot_table(index=["BASE_YEAR", "GRID_CD"],
                              columns="STAT_ITM", values="STAT_VAL",
                              aggfunc="first").reset_index()
        frames.append(wide)
    grid = pd.concat(frames, ignore_index=True)
    grid.columns.name = None
    return grid.rename(columns=ITEM_MAP)


def attach_island_direct(grid):
    """GRID_CD == gid 직접조인."""
    look = pd.read_csv(INTERIM / "grid_island_lookup.csv", dtype=str)
    look["gid"] = look["gid"].astype(str)
    grid["GRID_CD"] = grid["GRID_CD"].astype(str)
    m = grid.merge(look[["gid", "섬코드"]], left_on="GRID_CD",
                   right_on="gid", how="inner")
    print(f"[직접조인] 매칭 행 {len(m)} | 매칭 섬 {m['섬코드'].nunique()}")
    return m


def attach_island_by_coord(grid, coord_csv):
    """폴백: 격자 중심좌표 파일(GRID_CD,X,Y)을 받아 공간조인.
    coord_csv 컬럼 예: GRID_CD, X_COORD, Y_COORD (센터에서 별도 export)."""
    co = smart_read_csv(coord_csv)
    grid = grid.merge(co[["GRID_CD", "X_COORD", "Y_COORD"]], on="GRID_CD", how="left")
    pts = gpd.GeoDataFrame(
        grid, geometry=gpd.points_from_xy(pd.to_numeric(grid["X_COORD"]),
                                          pd.to_numeric(grid["Y_COORD"])),
        crs=SMALLAREA_CRS).to_crs(ISLAND_CRS)
    isl = gpd.read_file(INTERIM / "island_boundaries_jeonnam.gpkg").to_crs(ISLAND_CRS)
    m = gpd.sjoin(pts, isl[["섬코드", "geometry"]], how="inner", predicate="within")
    print(f"[좌표조인] 매칭 행 {len(m)} | 매칭 섬 {m['섬코드'].nunique()}")
    return pd.DataFrame(m.drop(columns="geometry"))


def main():
    grid = load_grid_long()
    if USE_DIRECT_JOIN:
        m = attach_island_direct(grid)
    else:
        m = attach_island_by_coord(grid, BASE / "<격자중심좌표.csv>")

    val_cols = [c for c in m.columns if c in ITEM_MAP.values()]
    if not val_cols:
        raise SystemExit("ITEM_MAP을 채워야 집계할 인구 컬럼이 생깁니다(prep01 ① 참고).")

    if DEDUP_SHARED_GRID:
        # 공유격자 인구 과대합 방지: 격자가 속한 섬 수로 나눠 분배
        share = m.groupby("GRID_CD")["섬코드"].transform("nunique")
        for c in val_cols:
            m[c] = m[c] / share

    isl_pop = m.groupby(["BASE_YEAR", "섬코드"], as_index=False)[val_cols].sum()
    isl_pop["섬코드"] = isl_pop["섬코드"].astype("Int64")
    isl_pop.to_csv(OUT / "island_grid_pop.csv", index=False, encoding="utf-8-sig")
    print("저장:", OUT / "island_grid_pop.csv")
    print(isl_pop.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
