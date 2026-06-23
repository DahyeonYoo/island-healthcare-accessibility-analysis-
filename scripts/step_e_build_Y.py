# -*- coding: utf-8 -*-
"""
Step E: 복합 '총 진료 도달시간' Y 생성 (옵션 A)

정의:
  Y = 섬에서 최근접 의료시설까지 최소 도달시간(분)
    = min( 섬내_도달시간(섬에 시설 있을 때) ,  sea_leg + land_leg )

  sea_leg(분):
    - 육지 연결섬           -> 0
    - 미연결 + ferry 실측    -> 최단소요_대표분 (ferry_island_access)
    - 미연결 + ferry 결측    -> 보정식 예측: f(육지 최근접거리)  [125섬 실측으로 학습]
  land_leg(분):
    - 최근접 '육지(비섬) 격자'의 도로 접근성 값 acc_{level}_2023
  섬내_도달시간(분):
    - 섬에 해당 level 시설 보유 시: 섬 자체 acc 값(있으면) 또는 nominal(중앙값)
    - 미보유 시: +inf (섬을 나가야 함)

level: emergency(응급), clinic(의원/1차) 두 가지 산출
산출물: 03_master/island_analysis.csv 갱신 (Y_* 컬럼 추가), 03_master/Y_build_report.txt
"""
import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path

BASE = Path(r"C:\Users\dyu18\OneDrive\문서\데이터활용대회")
INTERIM = BASE / "02_interim"
MASTER = BASE / "03_master"
CRS = "EPSG:5179"

# ---------- 로드 ----------
isl = gpd.read_file(INTERIM / "island_boundaries_jeonnam.gpkg").to_crs(CRS)
isl["섬코드"] = isl["섬코드"].astype(int)
isl["cx"] = isl.geometry.centroid.x
isl["cy"] = isl.geometry.centroid.y

grid = gpd.read_file(INTERIM / "grid_master_jeonnam.gpkg").to_crs(CRS)
lookup = pd.read_csv(INTERIM / "grid_island_lookup.csv", encoding="utf-8-sig")
island_gids = set(lookup["gid"].astype(str))

ana = pd.read_csv(MASTER / "island_analysis.csv", encoding="utf-8-sig")
conn = "육지b연결유무"

# ---------- 육지(비섬) 격자: acc 값 있고 섬 격자 아님 ----------
grid["gid"] = grid["gid"].astype(str)
grid_c = grid.copy()
grid_c["geometry"] = grid_c.geometry.centroid

LEVELS = {"emergency": "acc_emergency_2023", "clinic": "acc_clinic_2023"}

# 섬 대표점 GeoDataFrame
isl_pts = gpd.GeoDataFrame(
    isl[["섬코드", "cx", "cy"]].copy(),
    geometry=gpd.points_from_xy(isl["cx"], isl["cy"], crs=CRS),
)

report = []

# ---------- sea_leg 보정식 ----------
# 육지 최근접 거리: 모든 '육지 격자'(=섬격자 아님, 임의 level 값 유효) 중 최근접
mainland = grid_c[~grid_c["gid"].isin(island_gids)].copy()
mainland = mainland.dropna(subset=[LEVELS["emergency"]])  # 값 있는 육지격자
nn_main = gpd.sjoin_nearest(isl_pts, mainland[["gid", "geometry"]], distance_col="dist_main_m")
nn_main = nn_main.drop_duplicates(subset="섬코드")[["섬코드", "dist_main_m"]]
isl_d = isl[["섬코드"]].merge(nn_main, on="섬코드", how="left")

ferry = ana[["섬코드", "최단소요_대표분", "ferry_available", conn]].copy()
m = isl_d.merge(ferry, on="섬코드", how="left")
m["dist_main_km"] = m["dist_main_m"] / 1000.0

# 학습 표본: 미연결 + ferry 실측
train = m[(m[conn] == "미연결") & (m["ferry_available"] == 1) & m["최단소요_대표분"].notna()].copy()
coef = np.polyfit(train["dist_main_km"], train["최단소요_대표분"], 1)
pred = np.polyval(coef, train["dist_main_km"])
ss_res = ((train["최단소요_대표분"] - pred) ** 2).sum()
ss_tot = ((train["최단소요_대표분"] - train["최단소요_대표분"].mean()) ** 2).sum()
r2 = 1 - ss_res / ss_tot
report.append(f"[sea_leg 보정식] ferry_min = {coef[0]:.2f}*dist_km + {coef[1]:.2f} | R2={r2:.3f} | n={len(train)}")

def sea_leg(row):
    if row[conn] == "연결":
        return 0.0
    if pd.notna(row["최단소요_대표분"]):
        return float(row["최단소요_대표분"])
    # 결측 -> 예측 (음수 방지, 최소 10분)
    return max(10.0, float(np.polyval(coef, row["dist_main_km"])))

m["sea_leg_min"] = m.apply(sea_leg, axis=1)
m["sea_leg_source"] = np.where(
    m[conn] == "연결", "connected_0",
    np.where(m["최단소요_대표분"].notna(), "ferry_actual", "predicted"),
)

# ---------- land_leg: 최근접 육지격자 acc 값 (level별) ----------
for lvl, col in LEVELS.items():
    ml = grid_c[~grid_c["gid"].isin(island_gids)].dropna(subset=[col]).copy()
    nn = gpd.sjoin_nearest(isl_pts, ml[["gid", col, "geometry"]], distance_col="d")
    nn = nn.drop_duplicates(subset="섬코드")[["섬코드", col]].rename(columns={col: f"land_leg_{lvl}"})
    m = m.merge(nn, on="섬코드", how="left")

# ---------- 섬내 시설 보유 여부 (level별) ----------
# emergency 수준: 병원/종합병원/응급 (섬에 입원·응급 가능 시설)
em_cols = [c for c in ana.columns if ("종합병원 시설 수" == c or "병원 시설 수" == c or "요양병원 시설 수" == c)]
# clinic 수준: 의원/보건지소/보건진료소/보건소/보건의료원
cl_cols = [c for c in ana.columns if c in
           ["의원 시설 수", "보건소 시설 수", "보건의료원 시설 수", "보건지소 시설 수", "보건진료소 시설 수"]]
ana["has_emergency_onisland"] = (ana[em_cols].sum(axis=1) > 0).astype(int) if em_cols else 0
ana["has_clinic_onisland"] = (ana[cl_cols].sum(axis=1) > 0).astype(int) if cl_cols else 0

# 섬 자체 도로접근성(있으면) - 61섬만; 없으면 nominal=섬내시설 보유섬 중앙값 대용 10분
onisland_acc = ana[["섬코드", "acc_emergency_2023_mean", "acc_clinic_2023_mean"]].copy()
m = m.merge(onisland_acc, on="섬코드", how="left")
m = m.merge(ana[["섬코드", "has_emergency_onisland", "has_clinic_onisland"]], on="섬코드", how="left")

NOMINAL_ONISLAND = 10.0  # 섬내 시설 있으나 acc 무자료 시 가정 도달시간(분)

def build_Y(row, lvl):
    has = row[f"has_{lvl}_onisland"]
    off = row["sea_leg_min"] + row[f"land_leg_{lvl}"]
    if has == 1:
        own = row[f"acc_{lvl}_2023_mean"]
        on = float(own) if pd.notna(own) else NOMINAL_ONISLAND
        return min(on, off)
    return off

for lvl in LEVELS:
    m[f"Y_time_{lvl}"] = m.apply(lambda r: build_Y(r, lvl), axis=1)

# ---------- 분석 테이블에 병합 ----------
ycols = ["섬코드", "dist_main_km", "sea_leg_min", "sea_leg_source",
         "land_leg_emergency", "land_leg_clinic",
         "has_emergency_onisland", "has_clinic_onisland",
         "Y_time_emergency", "Y_time_clinic"]
ana2 = ana.merge(m[ycols].drop_duplicates("섬코드"), on="섬코드", how="left",
                 suffixes=("", "_dup"))
ana2 = ana2.loc[:, ~ana2.columns.str.endswith("_dup")]
ana2.to_csv(MASTER / "island_analysis.csv", index=False, encoding="utf-8-sig")

# ---------- 리포트 ----------
report.append(f"sea_leg_source: {m['sea_leg_source'].value_counts().to_dict()}")
report.append(f"Y_time_emergency 결측: {ana2['Y_time_emergency'].isna().sum()} / {len(ana2)}")
report.append(f"Y_time_clinic 결측: {ana2['Y_time_clinic'].isna().sum()} / {len(ana2)}")
for lvl in LEVELS:
    s = ana2[f"Y_time_{lvl}"]
    report.append(f"[Y_time_{lvl}] mean={s.mean():.1f} min={s.min():.1f} median={s.median():.1f} max={s.max():.1f}")
report.append(f"섬내 emergency 보유: {int(ana2['has_emergency_onisland'].sum())} | clinic 보유: {int(ana2['has_clinic_onisland'].sum())}")

txt = "\n".join(report)
(MASTER / "Y_build_report.txt").write_text(txt, encoding="utf-8")
print("=== Step E 완료 ===")
print(txt)
print()
print("악접근(Y_time_emergency 상위 12섬):")
top = ana2.sort_values("Y_time_emergency", ascending=False)
print(top[["섬이름", "시군구", "2024년 총인구", "sea_leg_min", "land_leg_emergency", "Y_time_emergency", "sea_leg_source"]].head(12).to_string(index=False))
