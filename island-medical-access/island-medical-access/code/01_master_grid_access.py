# -*- coding: utf-8 -*-
"""
01_master_grid_access.py  — 유인도 마스터 + 국토통계 접근성 격자(500m) 결합 (보강본)
실행: 리포지토리 루트에서  python code/01_master_grid_access.py
입력(raw, .gitignore): data/raw/전라남도 유인도정보_20241231.csv,
       data/raw/접근성/(보건/의원/응급) 접근성 500M_{year}.zip
출력: outputs/report/전남도서_의료취약성_통합마스터.xlsx

※ centroid 기준 보강본. 최종 분석은 팀의 '섬 경계 폴리곤' 기반 island_analysis.csv 사용(더 정밀).
"""
import os, zipfile, tempfile
import numpy as np, pandas as pd, geopandas as gpd

RAW = "data/raw"
ISLAND_CSV = f"{RAW}/전라남도 유인도정보_20241231.csv"
OUT_XLSX = "outputs/report/전남도서_의료취약성_통합마스터.xlsx"
# 접근성 zip 파일 경로 템플릿 (raw 폴더에 배치) — 실제 파일명에 맞게 조정
GRID = {
    "health": f"{RAW}/접근성/(B100)국토통계_국토정책지표-보건기관 접근성-500M_{{y}}.zip",
    "clinic": f"{RAW}/접근성/(B100)국토통계_국토정책지표-의원 접근성-500M_{{y}}.zip",
    "emerg":  f"{RAW}/접근성/(B100)국토통계_국토정책지표-응급의료시설 접근성-500M_{{y}}.zip",
}
YEARS = [2020, 2023]
KOR = {"health": "보건기관", "clinic": "의원", "emerg": "응급의료"}


def load_island_master():
    m = pd.read_csv(ISLAND_CSV, encoding="utf-8-sig")

    def pct(s):
        if pd.isna(s): return np.nan
        s = str(s).strip()
        return np.nan if s in ("", "-", "nan") else float(s.replace("▼", "-").replace("▲", "").replace("%", ""))

    m["증감률_num(%)"] = m["증감률"].map(pct)
    binmap = {"○": 1, "X": 0, "O": 1, "o": 1, "●": 1}
    for c in ["상수도", "지하수(관정)", "해수담수화시설", "소규모급수시설", "운반급수", "빗물 저장",
              "생수 배달", "생활용수 기타", "송전", "디젤발전", "태양광발전", "풍력발전", "전력공급 기타"]:
        if c in m: m[c + "_b"] = m[c].map(binmap).fillna(0).astype(int)
    m["육지연결_b"] = (m["육지b연결유무"].astype(str).str.contains("연결") & ~m["육지b연결유무"].astype(str).str.contains("미")).astype(int)
    m["여객선운항_b"] = (m["여객선 유도선 운항여부"].astype(str).str.contains("운항") & ~m["여객선 유도선 운항여부"].astype(str).str.contains("미")).astype(int)
    m["접안시설_b"] = (m["접안시설 보유"].astype(str) == "보유").astype(int)
    m["1차의료_시설합"] = m[["의원 시설 수", "보건지소 시설 수", "보건진료소 시설 수", "보건소 시설 수"]].sum(1)
    m["의료공백_flag"] = ((m["의원 시설 수"] == 0) & (m["보건지소 시설 수"] == 0) & (m["보건진료소 시설 수"] == 0)).astype(int)
    m["인구_log"] = np.log1p(m["2024년 총인구"])
    m["인구밀도(명/㎢)"] = (m["2024년 총인구"] / m["지적도 기준 면적(제곱키로미터)"].replace(0, np.nan)).round(1)
    return m


def grid_value(islands_5179, bbox, zip_path):
    td = tempfile.mkdtemp()
    with zipfile.ZipFile(zip_path) as zf:
        for n in zf.namelist():
            with zf.open(n) as s, open(os.path.join(td, "g." + n.split(".")[-1]), "wb") as d:
                d.write(s.read())
    g = gpd.read_file(os.path.join(td, "g.shp"), bbox=bbox)[["value", "geometry"]]
    j = gpd.sjoin(islands_5179[["섬 코드", "geometry"]], g, how="left", predicate="within")
    return j.groupby("섬 코드")["value"].first()


def main():
    os.makedirs(os.path.dirname(OUT_XLSX), exist_ok=True)
    m = load_island_master()
    isl = gpd.GeoDataFrame(m, geometry=gpd.points_from_xy(m["경도"], m["위도"]), crs=4326).to_crs(5179)
    minx, miny, maxx, maxy = isl.total_bounds
    bbox = (minx - 2000, miny - 2000, maxx + 2000, maxy + 2000)
    for key, tmpl in GRID.items():
        for y in YEARS:
            col = f"접근성_{KOR[key]}_km_{y}"
            vals = grid_value(isl, bbox, tmpl.format(y=y)).replace(-999, np.nan)
            m = m.merge(vals.rename(col), left_on="섬 코드", right_index=True, how="left")
        a, b = f"접근성_{KOR[key]}_km_{YEARS[0]}", f"접근성_{KOR[key]}_km_{YEARS[-1]}"
        m[f"접근성_{KOR[key]}_도로접근불가_{YEARS[-1]}"] = m[b].isna().astype(int)
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as xw:
        m.to_excel(xw, sheet_name="통합마스터(섬단위)", index=False)
    print(f"saved {OUT_XLSX}  shape={m.shape}  의료공백={int(m['의료공백_flag'].sum())}")


if __name__ == "__main__":
    main()
