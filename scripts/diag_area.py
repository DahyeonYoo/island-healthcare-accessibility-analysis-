# -*- coding: utf-8 -*-
from pathlib import Path
import geopandas as gpd
import pandas as pd

BASE = Path(r"C:\Users\dyu18\OneDrive\문서\데이터활용대회")
OUT = BASE / "02_interim"

csv = pd.read_csv(BASE / "전라남도 유인도정보_20241231.csv", encoding="utf-8-sig").rename(
    columns={"섬 코드": "섬코드", "섬 이름": "섬이름"})
csv["섬코드"] = csv["섬코드"].astype(int)
acol = "지적도 기준 면적(제곱키로미터)"

ib = gpd.read_file(OUT / "island_boundaries_jeonnam.gpkg")
ib["area_km2_geom"] = ib.geometry.area / 1e6
m = ib.merge(csv[["섬코드", acol]], on="섬코드", how="left")
m["ratio"] = m["area_km2_geom"] / m[acol]

# 큰 섬인데 geom 면적이 작은 경우 = 파편 매칭 의심
big = m[m[acol] >= 1.0].copy()
bad = big[(big["ratio"] < 0.5) | (big["ratio"] > 2.0)].sort_values(acol, ascending=False)
print("CSV면적>=1km2 섬:", len(big), "| 면적 불일치(0.5~2배 벗어남):", len(bad))
print(bad[["섬코드", "섬이름", acol, "area_km2_geom", "ratio", "geom_source", "confidence"]].head(30).to_string(index=False))

print()
print("=== 큰 섬 샘플 비교 (CSV면적 상위 15) ===")
top = m.sort_values(acol, ascending=False).head(15)
print(top[["섬코드", "섬이름", acol, "area_km2_geom", "ratio", "geom_source"]].to_string(index=False))
