# data/raw — 원시 데이터 (Git 추적 제외)

이 폴더의 실제 데이터 파일은 **용량·라이선스·민감성** 때문에 Git에 커밋하지 않습니다(`.gitignore`).
코드를 돌리려면 아래 파일을 각자 로컬에 내려받아 이 폴더에 배치하세요.

## 배치 목록

| 파일 | 위치 | 출처 |
|---|---|---|
| `전라남도 유인도정보_20241231.csv` | `data/raw/` | 행정안전부 도서통계 |
| `접근성/...보건기관/의원/응급의료 접근성-500M_{2020~2023}.zip` | `data/raw/접근성/` | 국토교통부·통계청 국토통계 |
| `chs21_m.sas7bdat` ~ `chs23_m.sas7bdat` (전국) | `data/raw/` | MDIS 지역사회건강조사 |
| `chs24_jeonnam.sas7bdat`, `chs25_jeonnam.sas7bdat` | `data/raw/` | MDIS 지역사회건강조사(전남) |
| `kosis_emd_pop.xlsx` (읍면동 5세별 주민등록인구, 전남) | `data/raw/` | KOSIS 주민등록인구 |

## 주의
- **MDIS 마이크로데이터(.sas7bdat)와 SDC 자료는 GitHub 등에 재배포 금지.** 집계 산출물만 `data/processed/`에 커밋합니다.
- 국토통계 격자 zip은 파일당 16MB 내외라 GitHub 100MB 제한과 무관하나, 리포 비대화 방지를 위해 추적 제외합니다.
