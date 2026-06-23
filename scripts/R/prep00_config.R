# -*- coding: utf-8 -*-
# 데이터센터 작업 공용 설정 (R 버전). 다른 prep0x.R 들이 source() 로 불러 씀.
# 필요 패키지: sf, dplyr, tidyr, readr, stringr
suppressPackageStartupMessages({
  library(sf); library(dplyr); library(tidyr); library(readr); library(stringr)
})

# ── 폴더 ────────────────────────────────────────────────────────────────────
BASE    <- "C:/Users/dyu18/OneDrive/문서/데이터활용대회"
INTERIM <- file.path(BASE, "02_interim")   # 기존 격자/섬 크로스워크 자산
MASTER  <- file.path(BASE, "03_master")    # 기존 분석 결과
OUT     <- file.path(BASE, "04_center")    # 센터 산출물(새로 생성)
if (!dir.exists(OUT)) dir.create(OUT, recursive = TRUE)

# ── 좌표계 ──────────────────────────────────────────────────────────────────
# 소지역 X/Y_COORD 좌표계. 통계청 SGIS 계열은 보통 EPSG:5179(UTM-K).
# prep01 sanity check 결과가 0이면 5181 / 5186 / 4326 으로 바꿔 재확인.
SMALLAREA_CRS <- 5179
ISLAND_CRS    <- 5179   # 기존 island_boundaries_jeonnam.gpkg 좌표계

# ── 분석 대상 ───────────────────────────────────────────────────────────────
SIDO_JEONNAM <- "46"
YEARS <- c("2020", "2021", "2022", "2023", "2024")

# 현장 실제 파일명으로 교체(없으면 prep01에서 list.files 로 탐색)
FILE_GRID_POP  <- file.path(BASE, "<격자인구파일.csv>")
FILE_SMALLAREA <- file.path(BASE, "<소지역파일.csv>")
FILE_CARD      <- file.path(BASE, "<카드매출파일.csv>")
FILE_SKT       <- file.path(BASE, "<SKT주거인구파일.csv>")

# ── 인코딩 자동 폴백 CSV 리더 (모든 컬럼 character 로 읽어 코드 보존) ─────────
smart_read_csv <- function(path, n_max = Inf) {
  for (enc in c("UTF-8", "CP949", "EUC-KR")) {
    out <- tryCatch(
      suppressWarnings(readr::read_csv(
        path, n_max = n_max, col_types = cols(.default = col_character()),
        locale = locale(encoding = enc), show_col_types = FALSE)),
      error = function(e) NULL)
    # 한글 컬럼이 깨지지 않았으면 채택(간이 판정)
    if (!is.null(out) && ncol(out) > 0) return(out)
  }
  stop(sprintf("인코딩 폴백 실패: %s", path))
}

# 숫자 변환 헬퍼(마스킹/비공개 → NA)
as_num <- function(x) suppressWarnings(as.numeric(x))
