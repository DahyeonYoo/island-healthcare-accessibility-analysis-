# -*- coding: utf-8 -*-
# 센터 산출물 → 기존 마스터 병합 + 수요가중 취약지수 (R 버전).
# 입력 : 03_master/island_analysis.csv, 04_center/island_grid_pop.csv (+ island_skt_pop.csv)
# 산출 : 04_center/island_analysis_plus.csv  → STEP1 재학습/STEP3 재시각화 입력
source("C:/Users/dyu18/OneDrive/문서/데이터활용대회/scripts/R/prep00_config.R")

isl <- readr::read_csv(file.path(MASTER, "island_analysis.csv"),
                       locale = locale(encoding = "UTF-8"), show_col_types = FALSE)
isl$섬코드 <- as.character(isl$섬코드)

# ── 격자 인구(2024 단면) 병합 ───────────────────────────────────────────────
pop <- smart_read_csv(file.path(OUT, "island_grid_pop.csv"))
pop$섬코드 <- as.character(pop$섬코드)
num_cols <- setdiff(names(pop), c("BASE_YEAR", "섬코드"))
pop[num_cols] <- lapply(pop[num_cols], as_num)
pop24 <- pop %>% filter(as.character(BASE_YEAR) == "2024") %>% select(-BASE_YEAR)
df <- left_join(isl, pop24, by = "섬코드")

# ── (선택) SKT 실거주 인구 병합 ─────────────────────────────────────────────
skt_path <- file.path(OUT, "island_skt_pop.csv")
if (file.exists(skt_path)) {
  skt <- smart_read_csv(skt_path); skt$섬코드 <- as.character(skt$섬코드)
  if ("기준연도" %in% names(skt)) skt <- skt %>% filter(as.character(기준연도) == "2024")
  df <- left_join(df, skt, by = "섬코드", suffix = c("", "_skt"))
}

# ── 수요가중 취약지수 ───────────────────────────────────────────────────────
tot <- if ("총인구" %in% names(df)) as_num(df$총인구) else as_num(df$`2024년 총인구`)
tot[tot == 0] <- NA
if ("고령인구" %in% names(df)) {
  df$고령비율      <- as_num(df$고령인구) / tot
  df$응급_고령부담 <- as_num(df$고령인구) * as_num(df$Y_time_emergency)  # 클수록 우선
  df$응급_고령부담_순위 <- rank(-df$응급_고령부담, na.last = "keep")
}
if ("학령인구" %in% names(df)) {
  df$학령비율        <- as_num(df$학령인구) / tot
  df$`1차의료_학령부담` <- as_num(df$학령인구) * as_num(df$Y_time_clinic)
}

write_excel_csv(df, file.path(OUT, "island_analysis_plus.csv"))
cat("저장:", file.path(OUT, "island_analysis_plus.csv"), "| 열 수:", ncol(df), "\n")

if ("응급_고령부담" %in% names(df)) {
  cat("\n[수요가중 취약 Top15] 고령인구 × 응급도달시간\n")
  top <- df %>% arrange(desc(응급_고령부담)) %>%
    select(섬이름, 고령인구, Y_time_emergency, 응급_고령부담) %>% head(15)
  print(as.data.frame(top))
}
