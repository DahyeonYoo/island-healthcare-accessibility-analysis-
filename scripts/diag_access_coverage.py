# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd

from project_paths import BASE
df = pd.read_csv(BASE / "03_master" / "island_analysis.csv", encoding="utf-8-sig")

conn_col = [c for c in df.columns if "육지" in c and "연결" in c][0]
ferry_run = [c for c in df.columns if "여객선" in c]
print("육지연결 컬럼:", conn_col)

# 접근성 유무 vs 육지연결
print("\n=== 접근성 유무 x 육지연결유무 ===")
print(pd.crosstab(df[conn_col], df["access_allnull"], margins=True))

print("\n=== 접근성 유무 x ferry_available ===")
print(pd.crosstab(df["ferry_available"], df["access_allnull"], margins=True))

# 접근성 있는 61개 섬의 육지연결 분포
have = df[df["access_allnull"] == 0]
print("\n접근성 보유 61섬의 육지연결:", have[conn_col].value_counts().to_dict())
print("접근성 보유 61섬 인구합:", int(have["2024년 총인구"].sum()))
print("접근성 무자료 216섬 인구합:", int(df[df["access_allnull"]==1]["2024년 총인구"].sum()))

# 큰 섬인데 무자료인 사례
big_null = df[(df["access_allnull"]==1) & (df["2024년 총인구"]>1000)]
print("\n인구1000+ 인데 접근성 무자료:", len(big_null))
print(big_null[["섬이름","시군구","2024년 총인구",conn_col,"ferry_available","최단소요_대표분"]].head(20).to_string(index=False))
