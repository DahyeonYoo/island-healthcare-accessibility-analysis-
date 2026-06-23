# -*- coding: utf-8 -*-
"""
데이터센터 작업 공용 설정.
경로 / 연도 / 좌표계 / 인코딩만 현장에서 맞추면 prep01~05가 그대로 돈다.
"""
from pathlib import Path

import pandas as pd

# ── 폴더 ─────────────────────────────────────────────────────────────────────
BASE = Path(r"C:\Users\dyu18\OneDrive\문서\데이터활용대회")
INTERIM = BASE / "02_interim"          # 기존 격자/섬 크로스워크 자산
MASTER = BASE / "03_master"            # 기존 분석 결과
OUT = BASE / "04_center"               # 센터 산출물(새로 생성)
OUT.mkdir(exist_ok=True)

# ── 좌표계 ───────────────────────────────────────────────────────────────────
# 소지역 X/Y_COORD 좌표계. 통계청 SGIS 계열은 보통 EPSG:5179(UTM-K).
# prep01 sanity check 결과가 0이면 5181 / 5186 / 4326 으로 바꿔 재확인.
SMALLAREA_CRS = "EPSG:5179"
ISLAND_CRS = "EPSG:5179"               # 기존 island_boundaries_jeonnam.gpkg 좌표계

# ── 분석 대상 ────────────────────────────────────────────────────────────────
SIDO_JEONNAM = "46"                    # 전라남도 시도코드
YEARS = ["2020", "2021", "2022", "2023", "2024"]

# 현장 실제 파일명으로 교체할 자리(없으면 prep01에서 glob로 탐색)
FILE_GRID_POP = BASE / "<격자인구파일.csv>"
FILE_SMALLAREA = BASE / "<소지역파일.csv>"
FILE_CARD = BASE / "<카드매출파일.csv>"
FILE_SKT = BASE / "<SKT주거인구파일.csv>"


def smart_read_csv(path, **kw):
    """센터 export 인코딩이 cp949 / utf-8 섞여 있어 자동 폴백. 기본 dtype=str(코드 보존)."""
    kw.setdefault("dtype", str)
    last = None
    for enc in ("utf-8-sig", "cp949", "utf-8"):
        try:
            return pd.read_csv(path, encoding=enc, **kw)
        except (UnicodeDecodeError, UnicodeError) as e:
            last = e
            continue
    raise RuntimeError(f"인코딩 폴백 실패: {path} ({last})")
