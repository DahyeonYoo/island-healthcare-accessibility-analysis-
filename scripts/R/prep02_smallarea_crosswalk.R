# -*- coding: utf-8 -*-
# 소지역 중심좌표(X_COORD/Y_COORD) → 섬코드 매핑 (R 버전).
#   소지역 테이블에 좌표가 있으므로 별도 집계구 경계 shp 불필요.
#   점(블록 중심) → island_boundaries 폴리곤 point-in-polygon 공간조인.
# 산출: 04_center/smallarea_island_lookup.csv  (카드·SKT 병합키)
#       04_center/adong_island_map.csv         (행정동→섬, 다대다)
source("C:/Users/dyu18/OneDrive/문서/데이터활용대회/scripts/R/prep00_config.R")

NEAREST_FALLBACK_M <- 0   # >0 이면 섬 경계 밖 블록을 그 거리 내 최근접 섬에 보강

sa <- smart_read_csv(FILE_SMALLAREA) %>%
  filter(SIDO_CD == SIDO_JEONNAM) %>%
  mutate(X_COORD = as_num(X_COORD), Y_COORD = as_num(Y_COORD),
         AREA = as_num(AREA)) %>%
  filter(!is.na(X_COORD), !is.na(Y_COORD))

pts <- st_as_sf(sa, coords = c("X_COORD", "Y_COORD"), crs = SMALLAREA_CRS) %>%
  st_transform(ISLAND_CRS)
isl <- st_read(file.path(INTERIM, "island_boundaries_jeonnam.gpkg"), quiet = TRUE) %>%
  st_transform(ISLAND_CRS) %>% select(섬코드, 섬이름)

joined <- st_join(pts, isl, join = st_within, left = TRUE)

# (옵션) 섬 경계 밖 블록 보강
if (NEAREST_FALLBACK_M > 0) {
  miss <- joined %>% filter(is.na(섬코드))
  if (nrow(miss) > 0) {
    nidx <- st_nearest_feature(miss, isl)
    d <- as.numeric(st_distance(miss, isl[nidx, ], by_element = TRUE))
    ok <- d <= NEAREST_FALLBACK_M
    joined$섬코드[is.na(joined$섬코드)][ok] <- isl$섬코드[nidx][ok]
    joined$섬이름[is.na(joined$섬이름)][ok] <- isl$섬이름[nidx][ok]
  }
}

lookup <- joined %>% st_drop_geometry()
keep <- intersect(c("BLOCK_CD","SMRY_AREA","ADONG_CD","ADONG_NM",
                    "LDONG_CD","SGNG_CD","SGNG_NM","AREA","섬코드","섬이름"),
                  names(lookup))
lookup <- lookup[, keep]
write_excel_csv(lookup, file.path(OUT, "smallarea_island_lookup.csv"))

cat("=== 소지역 → 섬 크로스워크 ===\n")
cat(sprintf("전남 블록 %d | 섬 매칭 %d | 커버 섬 %d\n",
            nrow(lookup), sum(!is.na(lookup$섬코드)),
            length(unique(na.omit(lookup$섬코드)))))

# 행정동 → 섬 (다대다)
adong <- lookup %>% filter(!is.na(섬코드)) %>%
  group_by(ADONG_CD) %>%
  summarise(섬코드들 = paste(sort(unique(as.character(섬코드))), collapse = ","),
            .groups = "drop")
write_excel_csv(adong, file.path(OUT, "adong_island_map.csv"))
cat("행정동→섬 매핑 저장:", nrow(adong), "개\n저장:",
    file.path(OUT, "smallarea_island_lookup.csv"), "\n")
