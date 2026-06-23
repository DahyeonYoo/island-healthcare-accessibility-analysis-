# -*- coding: utf-8 -*-
import geopandas as gpd
import pandas as pd

from project_paths import RAW
shp = RAW / "AL_D158_00_20260114" / "AL_D158_00_20260114.shp"
csv = pd.read_csv(RAW / "전라남도 유인도정보_20241231.csv", encoding="utf-8-sig").rename(
    columns={"섬 코드": "섬코드", "섬 이름": "섬이름"}
)
csv["섬코드"] = csv["섬코드"].astype(int)

g = gpd.read_file(shp, encoding="cp949").to_crs(5179)
review = [467701011, 467701012, 467701018, 467701019, 467701020, 468201001,
          468201002, 468201003, 468201005, 468201006, 469101003, 469101012,
          469101013, 469101034, 469101035, 469101040, 469101041]

print("=== 전국 동명 폴리곤 존재여부 ===")
for nm in ["가거도", "중마도", "하마도", "상마도", "영산도", "대포작도", "황마도", "마산도", "오도", "취도"]:
    h = g[g["A3"].astype(str).str.strip() == nm]
    print(f"{nm}: n={len(h)} 시군구={h['A1'].unique().tolist()} 유무인={h['A5'].tolist()} 면적={[round(a) for a in h['A12'].tolist()]}")

print()
print("=== 거리제한 없는 최근접 (전국) ===")
sub = csv[csv["섬코드"].isin(review)].copy()
pts = gpd.GeoDataFrame(sub, geometry=gpd.points_from_xy(sub["경도"], sub["위도"], crs=4326)).to_crs(5179)
near = gpd.sjoin_nearest(pts[["섬코드", "섬이름", "geometry"]], g[["A1", "A3", "A5", "A12", "geometry"]], distance_col="d")
near = near.sort_values("d")
for _, r in near.iterrows():
    print(f"{r['섬코드']} {str(r['섬이름']):>6} -> {str(r['A3']):>8} ({r['A5']}, {r['A1']}) {r['d']:.0f}m")
