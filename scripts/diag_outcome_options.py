# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd
import numpy as np

from project_paths import BASE
df = pd.read_csv(BASE / "03_master" / "island_analysis.csv", encoding="utf-8-sig")
conn = "육지b연결유무"
pop = "2024년 총인구"

# 섬내 의료시설 관련 컬럼(의사수 합산)
doc_cols = [c for c in df.columns if "의사 수" in c]
fac_presence = {
    "종합병원": "종합병원 시설 수",
    "병원": "병원 시설 수",
    "요양병원": "요양병원 시설 수",
    "의원": "의원 시설 수",
    "보건소": "보건소 시설 수",
    "보건지소": "보건지소 시설 수",
    "보건진료소": "보건진료소 시설 수",
    "약국": "약국",
}
fac_presence = {k: v for k, v in fac_presence.items() if v in df.columns}

df["총의사수_섬"] = df[doc_cols].sum(axis=1) if doc_cols else np.nan
df["1차의료시설수"] = df[[v for v in fac_presence.values()]].sum(axis=1)

print("=== 전체 277섬 ===")
print("총인구:", int(df[pop].sum()))
print("의사 1명 이상 있는 섬:", int((df["총의사수_섬"] > 0).sum()))
print("1차의료시설(의원/보건지소/진료소 등) 0개 섬:", int((df["1차의료시설수"] == 0).sum()))
print("의사 0명 섬 인구합:", int(df.loc[df["총의사수_섬"] == 0, pop].sum()))

print("\n=== 시설 종류별 보유 섬 수 (시설>=1) ===")
for k, v in fac_presence.items():
    n = int((df[v] > 0).sum())
    popn = int(df.loc[df[v] > 0, pop].sum())
    print(f"  {k:>6}: {n:3d}섬 | 거주인구 {popn}")

print("\n=== ferry 커버리지 ===")
print("ferry 소요시간 보유:", int(df["ferry_available"].sum()))
print("미연결인데 ferry 없음:", int(((df[conn]=='미연결') & (df['ferry_available']==0)).sum()))
print("연결섬 중 ferry 있음:", int(((df[conn]=='연결') & (df['ferry_available']==1)).sum()))

print("\n=== 도로 접근성 보유(참조) ===")
print("acc 값 있는 섬:", int((df["access_allnull"]==0).sum()))

# 각 옵션별 결측 현황
print("\n=== 옵션별 Y 결측(NaN) 섬 수 ===")
# 옵션C: ferry time, 연결섬=0 처리 가정
ferryY = df["최단소요_대표분"].copy()
ferryY[df[conn]=="연결"] = 0
print("옵션C ferry_time Y 결측:", int(ferryY.isna().sum()), "(미연결+ferry없음)")
# 옵션B: 의사수/인구
docY = df["총의사수_섬"] / df[pop].replace(0,np.nan)
print("옵션B 의사수/인구 Y 결측:", int(docY.isna().sum()))
# 옵션A 복합: ferry(미연결&무ferry만 결측) + 시설 + 도로
print("옵션A 복합: 결합 전 ferry결측", int(ferryY.isna().sum()), "→ 보강 필요")

# 미연결 & ferry 없는 섬들(가장 까다로운 그룹)
hard = df[(df[conn]=="미연결") & (df["ferry_available"]==0)]
print("\n=== 미연결 & ferry무 (가장 고립, n={}) ===".format(len(hard)))
print("인구합:", int(hard[pop].sum()), "| 의사0명 섬:", int((hard["총의사수_섬"]==0).sum()))
print(hard.sort_values(pop, ascending=False)[["섬이름","시군구",pop,"1차의료시설수","총의사수_섬"]].head(10).to_string(index=False))
