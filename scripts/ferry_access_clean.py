#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
여객선 항로별 소요시간표  ->  섬코드(9자리) 기준 여객선 접근성 테이블 정제
- 입력 1: 항로별_소요시간.xlsx   (53개 항로)
- 입력 2: 전라남도_유인도정보_20241231.csv  (277개 섬, PK=섬 코드)
- 출력  : ferry_island_access.csv  (섬코드별 최단 소요시간/운항편수)
          ferry_unmatched_ports.csv (섬이름 매칭 실패 기항지 = 본토항구/표기불일치 검수용)

설계 메모
- 소요시간은 '항로 전체(출발항~종점)' 기준이라, 중간 기항지에는 과대추정.
  -> 한 섬이 여러 항로에 나오면 '최단 소요시간 항로'를 그 섬의 대표 접근성으로 채택(주민은 가장 빠른 경로 사용).
  -> 구간별 정밀 시간은 나중에 PATIS 운항시간표로 보완(컬럼 비워둠).
- '총 0편' 항로는 현재 미운항 -> 운항편수 0으로 보존(사실상 접근 불가 신호).
"""
import pandas as pd
import re
from project_paths import RAW

FERRY_DIR = RAW / "운항 소요시간-20260604T115924Z-3-001" / "운항 소요시간"
FERRY_DIR.mkdir(parents=True, exist_ok=True)

ROUTE_XLSX = FERRY_DIR / "항로별_소요시간.xlsx"
ISLAND_CSV = RAW / "전라남도 유인도정보_20241231.csv"
OUT_ROUTES = FERRY_DIR / "ferry_routes_parsed.csv"
OUT_ACCESS = FERRY_DIR / "ferry_island_access.csv"
OUT_UNMATCH = FERRY_DIR / "ferry_manual_crosswalk.csv"

# 권역 -> 가능 시군구(매칭 모호성 해소 힌트). 목포발은 여러 군에 걸쳐 있어 넓게 둠.
REGION_HINT = {
    "완도": {"완도군"},
    "목포": {"신안군", "진도군", "목포시", "무안군", "영광군"},
    "고흥": {"고흥군", "완도군"},     # 녹동발 일부가 완도(금당권) 닿음
    "여수": {"여수시"},
}

# 본토/타지역 출발·도착항(섬코드 매칭 대상 아님 = 미매칭이 정상). 검수 부담을 줄이려 명시.
KNOWN_MAINLAND = {
    "목포", "여수", "여수신항(엑스포항)", "녹동", "땅끝", "화흥포", "노력", "이목",
    "신기", "돌산", "돌산대교", "오동도", "향화", "계마", "쉬미", "팽목", "남강",
    "봉리", "북강", "웅곡", "당두", "송공",            # 압해도(송공) 등 연륙항 포함
    "제주", "제주항", "성산포",                        # 타지역
}

# 명백한 표기차 별칭(여객선 기항지명 -> 유인도정보 섬명). 동명이도(혈도/모도 등)는 자동 제외, 수기로.
ALIAS = {
    "흑산": "대흑산도", "흑산도": "대흑산도",
    "안마": "안마도", "관매": "관매도", "거문": "거문도",
    "우이1구": "우이도", "우이2구": "우이도",
}

# ---------------------------------------------------------------- 1) 소요시간 -> 분
def minutes_cols(text):
    """ '약 2시간 27분'->147 / '약 30분 ~ 1시간 4분'->범위 / '약 90분'->90
        반환: (min분, max분, 대표분=중앙값)  """
    if pd.isna(text):
        return (None, None, None)
    parts = re.split(r"[~∼～]", str(text))
    vals = []
    for p in parts:
        h = re.search(r"(\d+)\s*시간", p)
        m = re.search(r"(\d+)\s*분", p)
        t = (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)
        if t > 0:
            vals.append(t)
    if not vals:
        return (None, None, None)
    if len(vals) == 1:
        return (vals[0], vals[0], vals[0])
    return (min(vals), max(vals), round(sum(vals) / len(vals)))

# ---------------------------------------------------------------- 2) 운항편수
def parse_trips(text):
    m = re.search(r"(\d+)", str(text))
    return int(m.group(1)) if m else None

# ---------------------------------------------------------------- 3) 기항지 분해 + 이름 후보 생성
def expand_port(token):
    """ 한 기항지 토큰 -> 매칭 시도용 이름 후보 리스트.
        - 괄호 별칭:  생일(서성) -> [생일, 서성]
        - 중점 합성:  상·중태도 -> [상태도, 중태도] / 동·서소우이 -> [동소우이, 서소우이]
    """
    token = token.strip()
    if not token:
        return []
    cands = set()

    # 괄호 별칭 분리
    paren = re.match(r"^(.*?)\(([^)]*)\)\s*$", token)
    base_tokens = []
    if paren:
        main, alias = paren.group(1).strip(), paren.group(2).strip()
        if main:  base_tokens.append(main)
        if alias: base_tokens.append(alias)
    else:
        base_tokens.append(token)

    for bt in base_tokens:
        if "·" in bt:
            seg = bt.split("·")
            common = seg[-1][1:]               # 마지막 조각 첫 글자 제거 = 공통 접미('태도','소우이')
            for s in seg[:-1]:
                cands.add(s + common)          # 상+태도=상태도, 동+소우이=동소우이
            cands.add(seg[-1])                 # 중태도, 서소우이
        else:
            cands.add(bt)
    return list(cands)

def split_ports(text):
    """ 기항지 목록 문자열 -> [(원본토큰, [이름후보...]), ...] """
    if pd.isna(text):
        return []
    s = re.sub(r"\([※*][^)]*\)", "", str(text))   # (※ ...) 주석 제거
    out = []
    for raw in s.split(","):
        raw = raw.strip()
        if raw:
            out.append((raw, expand_port(raw)))
    return out

# ---------------------------------------------------------------- 4) 섬이름 정규화(매칭용 키)
def norm(name):
    n = str(name).strip()
    n = re.sub(r"\s+", "", n)
    return n

def name_variants(name):
    """ 끝의 '도' 유무 양방향 변형 """
    n = norm(name)
    out = {n}
    if n.endswith("도"):
        out.add(n[:-1])
    else:
        out.add(n + "도")
    return out

# ================================================================ MAIN
routes  = pd.read_excel(ROUTE_XLSX)
islands = pd.read_csv(ISLAND_CSV, encoding="utf-8-sig")

# 섬 룩업: 정규화이름 -> [(섬코드, 섬이름, 시군구), ...]
lookup = {}
for _, r in islands.iterrows():
    code, nm, sgg = r["섬 코드"], r["섬 이름"], r["시군구"]
    for v in name_variants(nm):
        lookup.setdefault(v, []).append((code, nm, sgg))

# 소요시간/편수 파생
mn = routes["소요 시간"].apply(minutes_cols)
routes["소요_min"] = [x[0] for x in mn]
routes["소요_max"] = [x[1] for x in mn]
routes["소요_대표분"] = [x[2] for x in mn]
routes["운항편수_편도"] = routes["1일 운항 횟수 (편도 기준)"].apply(parse_trips)

# 항로 x 기항지 펼치기 -> 섬 매칭
all_names = list({norm(n): n for n in islands["섬 이름"].astype(str)}.items())  # (정규화, 원본)
records, unmatched = [], []
for _, r in routes.iterrows():
    region = r["권역"]
    hint   = REGION_HINT.get(region, set())
    for raw, cands in split_ports(r["기항지 목록"]):
        # 별칭 보정 후보 추가
        cands = list(cands)
        if raw in ALIAS:
            cands.append(ALIAS[raw])
        for c in list(cands):
            if c in ALIAS:
                cands.append(ALIAS[c])

        # 후보 이름들로 섬 룩업
        hits = []
        for c in cands:
            for v in name_variants(c):
                if v in lookup:
                    hits.extend(lookup[v])
        hits = list({h[0]: h for h in hits}.values())  # 섬코드 기준 dedup

        if not hits:
            # 미매칭 분류 + 부분일치 후보 자동제시(수기 검수 보조)
            base = raw.split("(")[0].strip()
            kind = "본토/타지역항(제외)" if raw in KNOWN_MAINLAND or base in KNOWN_MAINLAND else "검수필요(섬추정)"
            cand_isl = [orig for nm, orig in all_names
                        if base and len(base) >= 2 and (base in nm or nm in base)][:5]
            unmatched.append({
                "권역": region, "항로명": r["항로명"], "기항지원본": raw,
                "분류": kind, "후보섬(부분일치)": " / ".join(cand_isl), "섬코드(수기입력)": "",
            })
            continue

        # 모호성 해소: 권역 시군구 힌트로 좁히기
        narrowed = [h for h in hits if h[2] in hint] if hint else hits
        chosen = narrowed if narrowed else hits
        ambiguous = len(chosen) > 1

        for code, nm, sgg in chosen:
            records.append({
                "섬코드": code, "섬이름": nm, "시군구": sgg,
                "권역": region, "항로명": r["항로명"], "기항지원본": raw,
                "소요_대표분": r["소요_대표분"], "소요_min": r["소요_min"], "소요_max": r["소요_max"],
                "운항편수_편도": r["운항편수_편도"],
                "모호매칭": ambiguous,
            })

ferry = pd.DataFrame(records)

# 섬코드별 집계: 최단 소요시간(대표) 항로 채택 + 운항편수는 닿는 모든 항로 합
def agg_island(g):
    g_oper = g[g["운항편수_편도"].fillna(0) > 0]          # 실제 운항 항로
    base = g_oper if len(g_oper) else g                  # 전부 0편이면 원본 유지
    best = base.loc[base["소요_대표분"].idxmin()] if base["소요_대표분"].notna().any() else g.iloc[0]
    return pd.Series({
        "섬이름": best["섬이름"],
        "시군구": best["시군구"],
        "최단소요_대표분": best["소요_대표분"],
        "최단소요_min": best["소요_min"],
        "최단소요_max": best["소요_max"],
        "대표항로": best["항로명"],
        "총운항편수_편도": int(g_oper["운항편수_편도"].sum()) if len(g_oper) else 0,
        "경유항로수": g["항로명"].nunique(),
        "미운항항로포함": bool((g["운항편수_편도"].fillna(0) == 0).any()),
        "모호매칭포함": bool(g["모호매칭"].any()),
    })

island_access = (ferry.groupby("섬코드", as_index=False)
                       .apply(agg_island, include_groups=False)
                       .reset_index(drop=True)) if len(ferry) else pd.DataFrame()

unmatched_df = pd.DataFrame(unmatched).drop_duplicates().sort_values(["분류", "권역", "항로명"])

# 저장
routes_out = routes[["권역", "항로명", "소요 시간", "소요_대표분", "소요_min", "소요_max",
                     "운항편수_편도", "기항지 목록"]]
routes_out.to_csv(OUT_ROUTES, index=False, encoding="utf-8-sig")
island_access.to_csv(OUT_ACCESS, index=False, encoding="utf-8-sig")
unmatched_df.to_csv(OUT_UNMATCH, index=False, encoding="utf-8-sig")

# ---- 리포트 ----
print("=" * 60)
print("[1] 항로 소요시간 파싱: 53개 항로 전부 분(min) 변환 완료")
print("[2] 자동 매칭된 고유 섬 :", ferry["섬코드"].nunique() if len(ferry) else 0, "개")
nm_check = unmatched_df["분류"].value_counts().to_dict()
print("[3] 미매칭 기항지       :", len(unmatched_df), "건", nm_check)
print("    -> '본토/타지역항'은 매칭 대상 아님(정상). '검수필요'만 수기 확인.")
print("[4] 모호매칭(동명이도) 포함 섬 :",
      int(island_access["모호매칭포함"].sum()) if len(island_access) else 0, "개 (권역으로 못 좁힘 -> 검수)")
print("=" * 60)
print("\n[검수필요(섬추정) — 후보까지 자동 제시한 수기 워크시트 일부]")
need = unmatched_df[unmatched_df["분류"] == "검수필요(섬추정)"]
print(need[["권역", "항로명", "기항지원본", "후보섬(부분일치)"]].head(20).to_string(index=False))
print("\n[섬 접근성 결과 — 접근성 좋은 섬 상위]")
print(island_access.sort_values("최단소요_대표분").head(8).to_string(index=False))
print("\n[섬 접근성 결과 — 접근성 나쁜 섬 상위(취약 후보)]")
print(island_access.sort_values("최단소요_대표분", ascending=False).head(8).to_string(index=False))
