# -*- coding: utf-8 -*-
"""
STEP 1 - EDA & 전처리
  Y = Y_time_emergency (분). X = 구조적/사회경제 변수 (Y 구성요소는 누수로 제외)
산출: 03_master/step1_X.csv (모델 입력), step1_eda_report.txt
"""
import re
import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path(r"C:\Users\dyu18\OneDrive\문서\데이터활용대회")
MASTER = BASE / "03_master"
df = pd.read_csv(MASTER / "master_unified.csv", encoding="utf-8-sig")

YCOL = "Y_time_emergency"
rep = []
def log(*a):
    s = " ".join(str(x) for x in a); print(s); rep.append(s)

# ---------- Y 분포 ----------
y = df[YCOL]
log("=== Y 분포 (Y_time_emergency, 분) ===")
log(f"n={y.notna().sum()} mean={y.mean():.1f} sd={y.std():.1f} median={y.median():.1f} min={y.min():.1f} max={y.max():.1f}")
log(f"왜도(skew)={y.skew():.2f}  -> 로그변환 권장" )
df["Y_log"] = np.log1p(y)
log(f"log1p(Y) 왜도={df['Y_log'].skew():.2f}")

# ---------- 지역지정 텍스트 -> 이진화 ----------
desig = ["개발대상섬", "성장촉진지역", "특수상황지역", "인구감소지역", "먼섬특별법"]
for c in desig:
    if c in df.columns:
        df[c + "_b"] = (df[c].astype(str).str.strip() == "해당").astype(int)

# ---------- X 후보: 누수 변수 제외 ----------
# 누수(=Y 구성요소/직접결정): 거리·페리·섬내의료·접근성·연결성
leak_patterns = [
    "Y_time", "Y_log", "Y_primary", "sea_leg", "land_leg", "dist_main",
    "acc_", "접근성", "ferry", "여객선", "최단소요", "총운항편수", "경유항로",
    "has_emergency", "has_clinic", "의료공백", "1차의료",
    "병원", "의원", "의료원", "보건", "약국", "치과", "한방", "한의", "정신병원", "조산",
    "의사", "병상", "시설 수",  # 의료 종별 컬럼
    "육지", "연결_b", "운항", "접안",  # 연결성(거리/sea_leg 결정)
    "access_allnull", "sea_route", "grid_count", "base",
]
def is_leak(c):
    return any(p in c for p in leak_patterns)

# 식별/원본텍스트 제외
id_cols = ["연번", "시도", "시군구", "섬 이름", "섬이름", "섬코드", "섬 코드",
           "위도", "경도", "증감률", "증감량", YCOL]
# 원본 ○/X, 해당/해당없음 텍스트(이진화본 _b 사용)
raw_text = desig + ["여객선 유도선 운항여부", "접안시설 보유",
                    "상수도", "지하수(관정)", "해수담수화시설", "소규모급수시설",
                    "운반급수", "빗물 저장", "생수 배달", "생활용수 기타",
                    "송전", "디젤발전", "태양광발전", "풍력발전", "전력공급 기타",
                    "대표항로", "sea_leg_source"]

cand = []
for c in df.columns:
    if c in id_cols or c in raw_text:
        continue
    if is_leak(c):
        continue
    if df[c].dtype == object:
        # 이진화 안 된 텍스트는 제외(이미 _b 있음)
        continue
    cand.append(c)

# 분산 0 / 전부결측 제외
cand = [c for c in cand if df[c].notna().sum() > 0 and df[c].nunique(dropna=True) > 1]

log("\n=== X 후보 변수 (%d개) ===" % len(cand))
log(", ".join(cand))

# ---------- 결측 ----------
miss = df[cand].isna().sum()
miss = miss[miss > 0].sort_values(ascending=False)
log("\n=== 결측 있는 X (%d개) ===" % len(miss))
for c, v in miss.items():
    log(f"  {c}: {v} ({100*v/len(df):.1f}%)")

# ---------- 상관(Y와 절대상관 상위) ----------
corr = df[cand + [YCOL]].corr()[YCOL].drop(YCOL).sort_values(key=lambda s: s.abs(), ascending=False)
log("\n=== Y와의 상관 상위 15 ===")
for c, v in corr.head(15).items():
    log(f"  {c:>28}: r={v:+.3f}")

# ---------- 저장 (모델 입력: 결측은 중앙값 대치 표시만, 실제 대치는 모델 단계) ----------
keep = ["섬코드", "섬이름", "시군구", YCOL, "Y_log"] + cand
df[keep].to_csv(MASTER / "step1_X.csv", index=False, encoding="utf-8-sig")
(MASTER / "step1_eda_report.txt").write_text("\n".join(rep), encoding="utf-8")
log("\n저장: step1_X.csv (%d변수) , step1_eda_report.txt" % len(cand))
