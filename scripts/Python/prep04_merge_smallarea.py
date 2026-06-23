# -*- coding: utf-8 -*-
"""
소지역키 자료(카드매출 / SKT 주거인구) 범용 병합.
  prep02의 smallarea_island_lookup.csv 를 통해 어떤 키(BLOCK_CD/SMRY_AREA/ADONG_CD)든
  섬코드로 집계한다.

사용 예는 맨 아래 __main__ 참고. value_cols / key 만 현장에서 지정하면 됨.
"""
import pandas as pd

from prep00_config import FILE_CARD, FILE_SKT, OUT, smart_read_csv


def merge_to_island(data_path, key_col, value_cols, lookup_key="BLOCK_CD",
                    agg="sum", extra_groupers=None):
    """
    data_path   : 원자료 csv
    key_col     : 원자료의 결합키 컬럼명(BLOCK_CD/SMRY_AREA/ADONG_CD 등)
    value_cols  : 집계할 숫자 컬럼들
    lookup_key  : smallarea_island_lookup.csv 쪽 매칭키(보통 key_col과 동일 의미)
    extra_groupers: 월/성/연령 등 추가 그룹키(예: ["기준월","성별","연령대"])
    """
    df = smart_read_csv(data_path)
    for v in value_cols:
        df[v] = pd.to_numeric(df[v], errors="coerce")

    look = pd.read_csv(OUT / "smallarea_island_lookup.csv", dtype=str)
    key_map = look[[lookup_key, "섬코드"]].dropna().drop_duplicates()

    m = df.merge(key_map, left_on=key_col, right_on=lookup_key, how="inner")
    groupers = ["섬코드"] + (extra_groupers or [])
    out = m.groupby(groupers, as_index=False)[value_cols].agg(agg)
    out["섬코드"] = out["섬코드"].astype("Int64")
    print(f"{data_path.name}: 매칭 {m['섬코드'].nunique()}섬 | 결과행 {len(out)}")
    return out


if __name__ == "__main__":
    # ── SKT 성연령별 주거인구 → 섬별 실거주 인구(예시) ────────────────────────
    # skt = merge_to_island(
    #     FILE_SKT, key_col="BLOCK_CD",
    #     value_cols=["주거인구_총", "주거인구_65세이상"],   # 실제 컬럼명으로 교체
    #     extra_groupers=["기준연도"])
    # skt.to_csv(OUT / "island_skt_pop.csv", index=False, encoding="utf-8-sig")

    # ── 카드매출(통합카드) → 섬별 월 소비(예시) ──────────────────────────────
    # card = merge_to_island(
    #     FILE_CARD, key_col="BLOCK_CD",
    #     value_cols=["매출금액", "매출건수"],              # 실제 컬럼명으로 교체
    #     extra_groupers=["기준월", "업종"])
    # card.to_csv(OUT / "island_card.csv", index=False, encoding="utf-8-sig")
    print("value_cols/key를 지정한 뒤 위 블록의 주석을 해제해 실행하세요.")
