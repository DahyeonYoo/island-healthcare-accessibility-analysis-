# -*- coding: utf-8 -*-
# 격자 인구(long: BASE_YEAR/GRID_CD/STAT_ITM/STAT_VAL) → 피벗 → 섬코드 집계 (R 버전).
# 산출: 04_center/island_grid_pop.csv
# 전제: prep01 ②에서 GRID_CD↔gid 직접매칭률 충분(>50%). 0이면 좌표폴백 사용.
source("C:/Users/dyu18/OneDrive/문서/데이터활용대회/scripts/R/prep00_config.R")

USE_DIRECT_JOIN   <- TRUE
GRID_GLOB         <- "격자인구.*\\.csv$"   # 연도별 파일 정규식(현장 교체)
DEDUP_SHARED_GRID <- FALSE                  # TRUE면 공유격자 인구 1/n 분배

# prep01 ①에서 확인한 STAT_ITM 코드 → 친숙한 이름. 현장에서 채울 것.
ITEM_MAP <- c(
  # "<총인구코드>"   = "총인구",
  # "<청년인구코드>" = "청년인구",
  # "<고령인구코드>" = "고령인구",
  # "<학령인구코드>" = "학령인구"
)

load_grid_long <- function() {
  files <- list.files(BASE, pattern = GRID_GLOB, full.names = TRUE)
  stopifnot(length(files) > 0)
  dfs <- lapply(files, function(f) {
    gp <- smart_read_csv(f)
    gp$STAT_VAL <- as_num(gp$STAT_VAL)
    tidyr::pivot_wider(gp, id_cols = c(BASE_YEAR, GRID_CD),
                       names_from = STAT_ITM, values_from = STAT_VAL,
                       values_fn = dplyr::first)
  })
  grid <- dplyr::bind_rows(dfs)
  # ITEM_MAP 적용(이름 재명명)
  for (code in names(ITEM_MAP)) if (code %in% names(grid))
    names(grid)[names(grid) == code] <- ITEM_MAP[[code]]
  grid
}

attach_island_direct <- function(grid) {
  look <- smart_read_csv(file.path(INTERIM, "grid_island_lookup.csv")) %>%
    select(gid, 섬코드) %>% mutate(gid = as.character(gid))
  grid$GRID_CD <- as.character(grid$GRID_CD)
  m <- inner_join(grid, look, by = c("GRID_CD" = "gid"))
  cat(sprintf("[직접조인] 매칭 행 %d | 매칭 섬 %d\n",
              nrow(m), length(unique(m$섬코드))))
  m
}

attach_island_by_coord <- function(grid, coord_csv) {
  co <- smart_read_csv(coord_csv) %>%
    mutate(X_COORD = as_num(X_COORD), Y_COORD = as_num(Y_COORD))
  grid <- left_join(grid, co[, c("GRID_CD","X_COORD","Y_COORD")], by = "GRID_CD") %>%
    filter(!is.na(X_COORD), !is.na(Y_COORD))
  pts <- st_as_sf(grid, coords = c("X_COORD","Y_COORD"), crs = SMALLAREA_CRS) %>%
    st_transform(ISLAND_CRS)
  isl <- st_read(file.path(INTERIM, "island_boundaries_jeonnam.gpkg"), quiet = TRUE) %>%
    st_transform(ISLAND_CRS) %>% select(섬코드)
  m <- st_join(pts, isl, join = st_within, left = FALSE) %>% st_drop_geometry()
  cat(sprintf("[좌표조인] 매칭 행 %d | 매칭 섬 %d\n",
              nrow(m), length(unique(m$섬코드))))
  m
}

grid <- load_grid_long()
m <- if (USE_DIRECT_JOIN) attach_island_direct(grid) else
  attach_island_by_coord(grid, file.path(BASE, "<격자중심좌표.csv>"))

val_cols <- intersect(unname(ITEM_MAP), names(m))
if (length(val_cols) == 0)
  stop("ITEM_MAP을 채워야 집계할 인구 컬럼이 생깁니다(prep01 ① 참고).")

if (DEDUP_SHARED_GRID) {
  share <- m %>% group_by(GRID_CD) %>% mutate(n_isl = n_distinct(섬코드)) %>% ungroup()
  for (c in val_cols) m[[c]] <- share[[c]] / share$n_isl
}

isl_pop <- m %>% group_by(BASE_YEAR, 섬코드) %>%
  summarise(across(all_of(val_cols), ~ sum(.x, na.rm = TRUE)), .groups = "drop")
write_excel_csv(isl_pop, file.path(OUT, "island_grid_pop.csv"))
cat("저장:", file.path(OUT, "island_grid_pop.csv"), "\n")
print(utils::head(isl_pop, 10))
