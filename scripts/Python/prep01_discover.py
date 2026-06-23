# -*- coding: utf-8 -*-
"""
센터 도착 직후 '맨 먼저' 실행.
데이터를 미리 못 보고 왔으므로, 실물 구조와 매칭 가능성을 1차 점검한다.

확정해야 할 4가지:
  ① 격자인구 STAT_ITM(통계항목) 코드 목록      → prep03 ITEM_MAP 채움
  ② 신규 GRID_CD ↔ 기존 gid 직접매칭률          → prep03 병합방식(직접조인/좌표폴백) 결정
  ③ 소지역 X/Y_COORD 좌표계 타당성               → prep00 SMALLAREA_CRS 확정
  ④ 카드/SKT 결합키(BLOCK_CD/SMRY_AREA/ADONG_CD) → prep04 key 지정
"""
import geopandas as gpd
import pandas as pd

from prep00_config import (FILE_GRID_POP, FILE_SMALLAREA, FILE_CARD, FILE_SKT,
                           INTERIM, SIDO_JEONNAM, SMALLAREA_CRS, smart_read_csv)


def section(t):
    print("\n" + "=" * 70 + f"\n{t}\n" + "=" * 70)


# ── ① 격자 인구: 통계항목 코드 + 격자코드 형태 + 마스킹 ──────────────────────
section("① 격자 인구 구조")
gp = smart_read_csv(FILE_GRID_POP)
print("컬럼:", list(gp.columns))
print("\nSTAT_ITM(통계항목) 고유값 → 이 코드들을 prep03 ITEM_MAP에 넣을 것:")
print(gp["STAT_ITM"].value_counts())
print("\nGRID_CD 예시:", gp["GRID_CD"].head(5).tolist())
print("BASE_YEAR 고유값:", sorted(gp["BASE_YEAR"].unique()))
print("STAT_VAL 비숫자(마스킹/비공개) 비율:",
      f'{pd.to_numeric(gp["STAT_VAL"], errors="coerce").isna().mean():.2%}')

# ── ② 격자코드 ↔ 기존 gid 일치율 (★ 병합방식 결정의 핵심) ───────────────────
section("② 격자코드 ↔ 기존 gid 매칭률")
look = pd.read_csv(INTERIM / "grid_island_lookup.csv", dtype=str)
gid_set = set(look["gid"].astype(str))
gcd_set = set(gp["GRID_CD"].astype(str))
inter = gid_set & gcd_set
print(f"기존 gid {len(gid_set)} | 신규 GRID_CD {len(gcd_set)} | 교집합 {len(inter)}")
rate = len(inter) / max(len(gcd_set), 1)
print(f"신규 격자 중 직접매칭 비율: {rate:.1%}")
if rate > 0.5:
    print("→ [판정] 직접조인 사용 가능. prep03을 그대로 실행.")
else:
    print("→ [판정] 코드 체계/해상도 불일치 가능. 센터에서 '격자 중심좌표' export 여부 확인 →")
    print("         좌표 기반 공간조인(폴백)으로 prep03 전환 필요.")

# ── ③ 소지역 좌표계 sanity check ────────────────────────────────────────────
section("③ 소지역 좌표계 검증")
sa = smart_read_csv(FILE_SMALLAREA)
print("컬럼:", list(sa.columns))
sa46 = sa[sa["SIDO_CD"] == SIDO_JEONNAM].copy()
pts = gpd.GeoDataFrame(
    sa46,
    geometry=gpd.points_from_xy(pd.to_numeric(sa46["X_COORD"], errors="coerce"),
                                pd.to_numeric(sa46["Y_COORD"], errors="coerce")),
    crs=SMALLAREA_CRS)
isl = gpd.read_file(INTERIM / "island_boundaries_jeonnam.gpkg").to_crs(SMALLAREA_CRS)
hit = gpd.sjoin(pts, isl[["섬코드", "geometry"]], how="inner", predicate="within")
print(f"전남 블록 {len(sa46)} 중 섬 내부 점 {len(hit)}")
print("→ 0이면 SMALLAREA_CRS를 5181 / 5186 / 4326 으로 바꿔 재실행.")

# ── ④ 카드 / SKT 결합키 후보 식별 ───────────────────────────────────────────
section("④ 카드 / SKT 결합키 후보")
for label, path in [("카드", FILE_CARD), ("SKT", FILE_SKT)]:
    try:
        df = smart_read_csv(path, nrows=200)
        keys = [c for c in df.columns
                if c in ("BLOCK_CD", "SMRY_AREA", "ADONG_CD", "GRID_CD")]
        print(f"[{label}] 컬럼:", list(df.columns))
        print(f"[{label}] 결합키 후보:", keys or "없음(컬럼명 직접 확인 필요)")
    except Exception as e:
        print(f"[{label}] 로드 실패(파일명 확인): {e}")
