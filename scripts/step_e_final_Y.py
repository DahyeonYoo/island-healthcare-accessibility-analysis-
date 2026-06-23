# -*- coding: utf-8 -*-
"""
Step E-final: 거리기반 sea_leg로 복합 Y('총 진료 도달시간') 확정 (277섬 완전)

sea_leg(분) = 0 (육지연결) | 최근접 육지까지 해상거리(km) / FERRY_SPEED * 60 (미연결)
land_leg(분) = 최근접 '육지(비섬·도로접근성 유효) 격자'의 acc_{level}_2023
Y_time_{level} = min( 섬내_도달시간(시설 보유 시) , sea_leg + land_leg )

ferry 실측(최단소요_대표분)은 ferry_time_actual로 보존(검증용, Y에는 미사용).
"""
import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path

from project_paths import BASE
INTERIM = BASE / "02_interim"
MASTER = BASE / "03_master"
CRS = "EPSG:5179"
FERRY_SPEED_KMH = 30.0   # 여객선 평균속력 가정(파라미터)
NOMINAL_ONISLAND = 10.0  # 섬내 시설 있으나 도로접근성 무자료 시 가정 도달시간(분)
LEVELS = {"emergency": "acc_emergency_2023", "clinic": "acc_clinic_2023"}

# ---------- 로드 ----------
isl = gpd.read_file(INTERIM / "island_boundaries_jeonnam.gpkg").to_crs(CRS)
isl["섬코드"] = isl["섬코드"].astype(int)
isl_pts = isl.copy()
isl_pts["geometry"] = isl_pts.geometry.centroid

grid = gpd.read_file(INTERIM / "grid_master_jeonnam.gpkg").to_crs(CRS)
grid["gid"] = grid["gid"].astype(str)
grid_c = grid.copy()
grid_c["geometry"] = grid_c.geometry.centroid
lookup = pd.read_csv(INTERIM / "grid_island_lookup.csv", encoding="utf-8-sig")
island_gids = set(lookup["gid"].astype(str))

ana = pd.read_csv(MASTER / "island_analysis.csv", encoding="utf-8-sig")
conn = "육지b연결유무"

# ---------- 최근접 육지격자: 거리 + land_leg ----------
mainland = grid_c[~grid_c["gid"].isin(island_gids)].copy()
base_main = mainland.dropna(subset=[LEVELS["emergency"]])
nn = gpd.sjoin_nearest(isl_pts[["섬코드", "geometry"]], base_main[["gid", "geometry"]], distance_col="dist_main_m")
nn = nn.drop_duplicates("섬코드")[["섬코드", "dist_main_m"]]
df = isl[["섬코드"]].merge(nn, on="섬코드", how="left")
df["dist_main_km"] = df["dist_main_m"] / 1000.0

for lvl, col in LEVELS.items():
    ml = mainland.dropna(subset=[col])
    j = gpd.sjoin_nearest(isl_pts[["섬코드", "geometry"]], ml[["gid", col, "geometry"]], distance_col="d")
    j = j.drop_duplicates("섬코드")[["섬코드", col]].rename(columns={col: f"land_leg_{lvl}"})
    df = df.merge(j, on="섬코드", how="left")

df = df.merge(ana[["섬코드", conn]], on="섬코드", how="left")

# ---------- sea_leg ----------
df["sea_leg_min"] = np.where(
    df[conn] == "연결", 0.0,
    df["dist_main_km"] / FERRY_SPEED_KMH * 60.0,
)
df["sea_leg_source"] = np.where(df[conn] == "연결", "connected_0", "dist_based")

# ---------- 섬내 시설 보유 ----------
em_cols = [c for c in ana.columns if c in ["종합병원 시설 수", "병원 시설 수", "요양병원 시설 수"]]
cl_cols = [c for c in ana.columns if c in
           ["의원 시설 수", "보건소 시설 수", "보건의료원 시설 수", "보건지소 시설 수", "보건진료소 시설 수"]]
ana["has_emergency_onisland"] = (ana[em_cols].sum(axis=1) > 0).astype(int)
ana["has_clinic_onisland"] = (ana[cl_cols].sum(axis=1) > 0).astype(int)

df = df.merge(ana[["섬코드", "has_emergency_onisland", "has_clinic_onisland",
                   "acc_emergency_2023_mean", "acc_clinic_2023_mean"]], on="섬코드", how="left")

# ---------- Y ----------
for lvl in LEVELS:
    def by(r):
        off = r["sea_leg_min"] + r[f"land_leg_{lvl}"]
        if r[f"has_{lvl}_onisland"] == 1:
            own = r.get(f"acc_{lvl}_2023_mean")
            on = float(own) if pd.notna(own) else NOMINAL_ONISLAND
            return min(on, off) if pd.notna(off) else on
        return off
    df[f"Y_time_{lvl}"] = df.apply(by, axis=1)

# ---------- 분석테이블 갱신 ----------
ana = ana.rename(columns={"최단소요_대표분": "ferry_time_actual"}) if "최단소요_대표분" in ana.columns else ana
# 기존 Y/leg 컬럼 제거 후 새로 결합
drop = [c for c in ana.columns if c in
        ["dist_main_km", "sea_leg_min", "sea_leg_source", "land_leg_emergency", "land_leg_clinic",
         "Y_time_emergency", "Y_time_clinic"]]
ana = ana.drop(columns=drop, errors="ignore")
addc = ["섬코드", "dist_main_km", "sea_leg_min", "sea_leg_source",
        "land_leg_emergency", "land_leg_clinic", "Y_time_emergency", "Y_time_clinic"]
ana = ana.merge(df[addc], on="섬코드", how="left")
ana.to_csv(MASTER / "island_analysis.csv", index=False, encoding="utf-8-sig")

# ---------- 검증 + 리포트 ----------
rep = []
rep.append(f"FERRY_SPEED={FERRY_SPEED_KMH}km/h, NOMINAL_ONISLAND={NOMINAL_ONISLAND}min")
rep.append(f"sea_leg_source: {ana['sea_leg_source'].value_counts().to_dict()}")
for lvl in LEVELS:
    s = ana[f"Y_time_{lvl}"]
    rep.append(f"[Y_time_{lvl}] n={s.notna().sum()} 결측={s.isna().sum()} mean={s.mean():.1f} median={s.median():.1f} min={s.min():.1f} max={s.max():.1f}")
# 검증: ferry 실측 있는 섬에서 거리기반 sea_leg vs 실측 상관
if "ferry_time_actual" in ana.columns:
    v = ana[ana["ferry_time_actual"].notna() & (ana[conn] == "미연결")]
    sl = v["dist_main_km"] / FERRY_SPEED_KMH * 60.0
    if len(v) > 3:
        corr = np.corrcoef(sl, v["ferry_time_actual"])[0, 1]
        rep.append(f"[검증] 거리기반 sea_leg vs ferry실측 상관 r={corr:.3f} (n={len(v)})")
rep.append(f"섬내 emergency 보유:{int(ana['has_emergency_onisland'].sum())} clinic 보유:{int(ana['has_clinic_onisland'].sum())}")
txt = "\n".join(rep)
(MASTER / "Y_build_report.txt").write_text(txt, encoding="utf-8")
print("=== Step E-final 완료 ===")
print(txt)
print("\n악접근 상위 12 (Y_time_emergency):")
print(ana.sort_values("Y_time_emergency", ascending=False)
      [["섬이름", "시군구", "2024년 총인구", "dist_main_km", "sea_leg_min", "land_leg_emergency", "Y_time_emergency"]]
      .head(12).to_string(index=False))
print("\n양접근 하위 8:")
print(ana.sort_values("Y_time_emergency")
      [["섬이름", "시군구", "2024년 총인구", "Y_time_emergency", "has_emergency_onisland"]]
      .head(8).to_string(index=False))
