# -*- coding: utf-8 -*-
"""Shared project paths for scripts.

All paths are resolved from this repository root so the pipeline can run on
different laptops after the required raw files are placed in the expected
folders.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE = REPO_ROOT

RAW = BASE / "data" / "raw"
INTERIM = BASE / "02_interim"
MASTER = BASE / "03_master"
CENTER = BASE / "04_center"

for path in (RAW, INTERIM, MASTER, CENTER):
    path.mkdir(parents=True, exist_ok=True)

TEAM_MASTER_XLSX = RAW / "가현이의 마스터파일.xlsx"
