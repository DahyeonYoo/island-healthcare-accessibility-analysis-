# -*- coding: utf-8 -*-
# 센터 도착 직후 '맨 먼저' 실행 (R 버전).
# 확정할 4가지: ①STAT_ITM 코드 ②GRID_CD↔gid 매칭률 ③소지역 좌표계 ④카드/SKT 키
config_path <- file.path("scripts", "R", "prep00_config.R")`r`nif (!file.exists(config_path)) config_path <- file.path(dirname(normalizePath(sys.frame(1)$ofile)), "prep00_config.R")`r`nsource(config_path)

sec <- function(t) cat("\n", strrep("=", 70), "\n", t, "\n", strrep("=", 70), "\n", sep = "")

# ── ① 격자 인구 구조 ────────────────────────────────────────────────────────
sec("① 격자 인구 구조")
gp <- smart_read_csv(FILE_GRID_POP)
cat("컬럼:", paste(names(gp), collapse = ", "), "\n")
cat("\nSTAT_ITM(통계항목) 고유값 → prep03 ITEM_MAP 에 반영:\n")
print(table(gp$STAT_ITM))
cat("\nGRID_CD 예시:", paste(head(gp$GRID_CD, 5), collapse = ", "), "\n")
cat("BASE_YEAR 고유값:", paste(sort(unique(gp$BASE_YEAR)), collapse = ", "), "\n")
cat("STAT_VAL 비숫자(마스킹) 비율:",
    sprintf("%.2f%%", mean(is.na(as_num(gp$STAT_VAL))) * 100), "\n")

# ── ② 격자코드 ↔ 기존 gid 매칭률 (★ 병합방식 결정) ──────────────────────────
sec("② 격자코드 ↔ 기존 gid 매칭률")
look <- smart_read_csv(file.path(INTERIM, "grid_island_lookup.csv"))
gid_set <- unique(as.character(look$gid))
gcd_set <- unique(as.character(gp$GRID_CD))
inter <- intersect(gid_set, gcd_set)
rate <- length(inter) / max(length(gcd_set), 1)
cat(sprintf("기존 gid %d | 신규 GRID_CD %d | 교집합 %d\n",
            length(gid_set), length(gcd_set), length(inter)))
cat(sprintf("신규 격자 직접매칭 비율: %.1f%%\n", rate * 100))
if (rate > 0.5) cat("→ [판정] 직접조인 사용. prep03 그대로 실행.\n") else
  cat("→ [판정] 코드/해상도 불일치 가능. 격자 중심좌표 export 확인 → 좌표조인 폴백.\n")

# ── ③ 소지역 좌표계 검증 ────────────────────────────────────────────────────
sec("③ 소지역 좌표계 검증")
sa <- smart_read_csv(FILE_SMALLAREA)
cat("컬럼:", paste(names(sa), collapse = ", "), "\n")
sa46 <- sa %>% filter(SIDO_CD == SIDO_JEONNAM) %>%
  mutate(X_COORD = as_num(X_COORD), Y_COORD = as_num(Y_COORD)) %>%
  filter(!is.na(X_COORD), !is.na(Y_COORD))
pts <- st_as_sf(sa46, coords = c("X_COORD", "Y_COORD"), crs = SMALLAREA_CRS)
isl <- st_read(file.path(INTERIM, "island_boundaries_jeonnam.gpkg"), quiet = TRUE) %>%
  st_transform(SMALLAREA_CRS)
hit <- st_join(pts, isl["섬코드"], join = st_within, left = FALSE)
cat(sprintf("전남 블록 %d 중 섬 내부 점 %d\n", nrow(sa46), nrow(hit)))
cat("→ 0이면 SMALLAREA_CRS를 5181/5186/4326 으로 바꿔 재실행.\n")

# ── ④ 카드/SKT 결합키 후보 ──────────────────────────────────────────────────
sec("④ 카드 / SKT 결합키 후보")
for (lp in list(c("카드", FILE_CARD), c("SKT", FILE_SKT))) {
  df <- tryCatch(smart_read_csv(lp[2], n_max = 200), error = function(e) NULL)
  if (is.null(df)) { cat(sprintf("[%s] 로드 실패(파일명 확인)\n", lp[1])); next }
  keys <- intersect(names(df), c("BLOCK_CD", "SMRY_AREA", "ADONG_CD", "GRID_CD"))
  cat(sprintf("[%s] 컬럼: %s\n", lp[1], paste(names(df), collapse = ", ")))
  cat(sprintf("[%s] 결합키 후보: %s\n", lp[1],
              ifelse(length(keys) > 0, paste(keys, collapse = ", "), "없음")))
}
