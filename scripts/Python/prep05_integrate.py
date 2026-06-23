# -*- coding: utf-8 -*-
"""
센터 산출물(섬 단위 인구/소비)을 기존 마스터에 병합하고,
'수요(고령·학령) × 공급(도달시간)' 미스매치 기반 취약지수를 생성.

입력 : 03_master/island_analysis.csv  (기존 277섬 분석표, Y_time_* 포함)
       04_center/island_grid_pop.csv  (prep03)
       04_center/island_skt_pop.csv   (선택, prep04)
산출 : 04_center/island_analysis_plus.csv  → STEP1 재학습 / STEP3 재시각화 입력
"""
import pandas as pd

from prep00_config import MASTER, OUT

isl = pd.read_csv(MASTER / "island_analysis.csv")
isl["섬코드"] = isl["섬코드"].astype("Int64")

# ── 격자 인구(2024 단면) 병합 ───────────────────────────────────────────────
pop = pd.read_csv(OUT / "island_grid_pop.csv")
pop["섬코드"] = pop["섬코드"].astype("Int64")
pop24 = pop[pop["BASE_YEAR"].astype(str) == "2024"].drop(columns=["BASE_YEAR"])
df = isl.merge(pop24, on="섬코드", how="left")

# ── (선택) SKT 실거주 인구 병합 ─────────────────────────────────────────────
skt_path = OUT / "island_skt_pop.csv"
if skt_path.exists():
    skt = pd.read_csv(skt_path)
    skt["섬코드"] = skt["섬코드"].astype("Int64")
    skt24 = skt[skt.get("기준연도", "2024").astype(str) == "2024"] if "기준연도" in skt else skt
    df = df.merge(skt24, on="섬코드", how="left", suffixes=("", "_skt"))

# ── 수요가중 취약지수 ───────────────────────────────────────────────────────
tot = df.get("총인구", df["2024년 총인구"]).replace(0, pd.NA)
if "고령인구" in df:
    df["고령비율"] = df["고령인구"] / tot
    # 응급 도달시간 × 고령인구 = '고령 person-minute' (클수록 우선 개입)
    df["응급_고령부담"] = df["고령인구"] * df["Y_time_emergency"]
    df["응급_고령부담_순위"] = df["응급_고령부담"].rank(ascending=False)
if "학령인구" in df:
    df["학령비율"] = df["학령인구"] / tot
    df["1차의료_학령부담"] = df["학령인구"] * df["Y_time_clinic"]

df.to_csv(OUT / "island_analysis_plus.csv", index=False, encoding="utf-8-sig")
print("저장:", OUT / "island_analysis_plus.csv", "| 열 수:", df.shape[1])

if "응급_고령부담" in df:
    print("\n[수요가중 취약 Top15] 고령인구 × 응급도달시간")
    cols = ["섬이름", "고령인구", "Y_time_emergency", "응급_고령부담"]
    print(df.nlargest(15, "응급_고령부담")[cols].to_string(index=False))
