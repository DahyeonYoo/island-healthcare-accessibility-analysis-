# -*- coding: utf-8 -*-
# 소지역키 자료(카드매출 / SKT 주거인구) 범용 병합 (R 버전).
# prep02의 smallarea_island_lookup.csv 로 어떤 키든 섬코드 집계.
source("C:/Users/dyu18/OneDrive/문서/데이터활용대회/scripts/R/prep00_config.R")

# data_path     : 원자료 csv
# key_col       : 원자료 결합키(BLOCK_CD/SMRY_AREA/ADONG_CD 등)
# value_cols    : 집계할 숫자 컬럼들
# lookup_key    : smallarea_island_lookup.csv 쪽 매칭키
# extra_groupers: 월/성/연령 등 추가 그룹키
merge_to_island <- function(data_path, key_col, value_cols,
                            lookup_key = "BLOCK_CD", agg = sum,
                            extra_groupers = NULL) {
  df <- smart_read_csv(data_path)
  for (v in value_cols) df[[v]] <- as_num(df[[v]])

  look <- smart_read_csv(file.path(OUT, "smallarea_island_lookup.csv")) %>%
    select(all_of(lookup_key), 섬코드) %>%
    filter(!is.na(섬코드)) %>% distinct()

  m <- inner_join(df, look, by = setNames(lookup_key, key_col))
  groupers <- c("섬코드", extra_groupers)
  out <- m %>% group_by(across(all_of(groupers))) %>%
    summarise(across(all_of(value_cols), ~ agg(.x, na.rm = TRUE)), .groups = "drop")
  cat(sprintf("%s: 매칭 %d섬 | 결과행 %d\n",
              basename(data_path), length(unique(m$섬코드)), nrow(out)))
  out
}

# ── 사용 예 (현장에서 컬럼명 채운 뒤 주석 해제) ──────────────────────────────
# SKT 성연령별 주거인구 → 섬별 실거주 인구
# skt <- merge_to_island(FILE_SKT, key_col = "BLOCK_CD",
#                        value_cols = c("주거인구_총","주거인구_65세이상"),
#                        extra_groupers = c("기준연도"))
# write_excel_csv(skt, file.path(OUT, "island_skt_pop.csv"))

# 카드매출(통합카드) → 섬별 월 소비
# card <- merge_to_island(FILE_CARD, key_col = "BLOCK_CD",
#                         value_cols = c("매출금액","매출건수"),
#                         extra_groupers = c("기준월","업종"))
# write_excel_csv(card, file.path(OUT, "island_card.csv"))

cat("value_cols/key 지정 후 위 예시 주석을 해제해 실행하세요.\n")
