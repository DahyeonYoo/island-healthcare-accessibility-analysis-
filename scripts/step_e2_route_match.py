# -*- coding: utf-8 -*-
"""
Step E-2: 항로 기항지 -> 섬 매칭으로 sea_leg 재구성
  - 54개 항로의 기항지 토큰을 277개 섬에 매칭 (부분일치 + 별칭사전)
  - 섬별 sea_leg_route = 매칭된 항로들의 min(소요_대표분)
  - 최종 sea_leg = 0(연결) / min(ferry_actual, route_min)(미연결)
"""
import re
import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path(r"C:\Users\dyu18\OneDrive\문서\데이터활용대회")
FERRY = BASE / "운항 소요시간-20260604T115924Z-3-001" / "운항 소요시간"
MASTER = BASE / "03_master"

routes = pd.read_csv(FERRY / "ferry_routes_parsed.csv", encoding="utf-8-sig")
ana = pd.read_csv(MASTER / "island_analysis.csv", encoding="utf-8-sig")
conn = "육지b연결유무"

# 본토/타지역 항구 토큰(섬 아님) - 매칭 제외
MAINLAND_PORTS = {
    "목포", "여수", "완도", "녹동", "향화", "계마", "땅끝", "이목", "화흥포", "노력",
    "남강", "북강", "송공", "쉬미", "봉리", "팽목", "율목", "당두", "웅곡", "신기",
    "백야", "돌산대교", "여수신항(엑스포항)", "제주", "제주항", "성산포", "오동도",
    "당목", "일정", "신월", "증도", "도초", "송도", "가산",
}

# 별칭: 기항지토큰 -> 섬 base 이름
ALIAS = {
    "청산": "청산도", "소안": "소안도", "비금": "비금도", "흑산": "흑산도",
    "거문": "거문도", "고도(거문)": "거문도", "손죽": "손죽도", "동천": "노화도",
    "산양": "노화도", "넙도": "넙도", "관매": "관매도", "창유": "조도",  # 창유항=하조도
    "역포(연도)": "연도", "고이": "고이도", "안좌": "안좌도",
}

def norm(tok):
    t = re.sub(r"\(.*?\)", "", str(tok)).strip()
    return t

# 섬 base 이름
ana["base"] = ana["섬이름"].map(lambda n: re.sub(r"\(.*?\)", "", str(n)).strip())

# 섬별 후보 항로시간 수집
sea_route = {code: [] for code in ana["섬코드"]}
name2codes = {}
for _, r in ana.iterrows():
    name2codes.setdefault(r["base"], []).append(r["섬코드"])

for _, rt in routes.iterrows():
    t = rt["소요_대표분"]
    stops = [norm(s) for s in str(rt["기항지 목록"]).replace("·", ",").split(",")]
    for s in stops:
        if not s or s in MAINLAND_PORTS:
            continue
        cand = ALIAS.get(s, s)
        # 1) 정확/별칭 일치
        matched_codes = []
        if cand in name2codes:
            matched_codes = name2codes[cand]
        else:
            # 2) 부분일치: 섬 base가 토큰으로 시작하거나 토큰이 base 포함 (len>=2)
            for base, codes in name2codes.items():
                if len(s) >= 2 and (base.startswith(s) or s.startswith(base) or s in base):
                    matched_codes += codes
        for c in set(matched_codes):
            sea_route[c].append(t)

route_min = {c: (min(v) if v else np.nan) for c, v in sea_route.items()}
ana["sea_route_min"] = ana["섬코드"].map(route_min)

# 최종 sea_leg 재구성
def final_sea(row):
    if row[conn] == "연결":
        return 0.0, "connected_0"
    cands = []
    if pd.notna(row.get("최단소요_대표분")):
        cands.append(row["최단소요_대표분"])
    if pd.notna(row["sea_route_min"]):
        cands.append(row["sea_route_min"])
    if cands:
        src = "ferry_actual" if pd.notna(row.get("최단소요_대표분")) else "route_match"
        if len(cands) == 2 and row["sea_route_min"] < row["최단소요_대표분"]:
            src = "route_match_min"
        return float(min(cands)), src
    return np.nan, "unknown"

res = ana.apply(lambda r: final_sea(r), axis=1)
ana["sea_leg_min"] = [x[0] for x in res]
ana["sea_leg_source"] = [x[1] for x in res]

# Y 재계산 (land_leg, 섬내시설은 기존 컬럼 사용)
NOMINAL = 10.0
for lvl in ["emergency", "clinic"]:
    def by(row):
        off = row["sea_leg_min"] + row[f"land_leg_{lvl}"]
        if row[f"has_{lvl}_onisland"] == 1:
            own = row.get(f"acc_{lvl}_2023_mean")
            on = float(own) if pd.notna(own) else NOMINAL
            return min(on, off) if pd.notna(off) else on
        return off
    ana[f"Y_time_{lvl}"] = ana.apply(by, axis=1)

ana.to_csv(MASTER / "island_analysis.csv", index=False, encoding="utf-8-sig")

print("=== sea_leg_source 분포 ===")
print(ana["sea_leg_source"].value_counts().to_dict())
print("sea_leg 결측(unknown):", int((ana["sea_leg_source"]=="unknown").sum()))
print("Y_time_emergency 결측:", int(ana["Y_time_emergency"].isna().sum()))
print()
print("미연결인데 여전히 unknown인 섬:")
unk = ana[(ana[conn]=="미연결") & (ana["sea_leg_source"]=="unknown")]
print(unk[["섬이름","시군구","2024년 총인구"]].to_string(index=False))
print()
for lvl in ["emergency","clinic"]:
    s = ana[f"Y_time_{lvl}"]
    print(f"[Y_time_{lvl}] n={s.notna().sum()} mean={s.mean():.1f} median={s.median():.1f} max={s.max():.1f}")
