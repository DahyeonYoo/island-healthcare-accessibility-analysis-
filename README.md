# 전라남도 277개 유인도 응급의료 접근성 분석

2026 국가데이터 활용대회 분석 프로젝트입니다. 주제는 **전라남도 277개 유인도 응급의료 도달시간 진단과 유형별 정책 처방**입니다.

이 통합본은 두 작업 브랜치를 합쳐, 데이터 구축부터 정책 시뮬레이션과 보고서 산출까지 이어지는 분석 흐름을 한 리포지토리 안에 정리합니다.

## 분석 흐름

1. **데이터 전처리와 분석 테이블 구축**
   - 위치: `scripts/`
   - 섬 경계, 500m 접근성 격자, ferry/운항 자료, 의료공급 자료를 결합합니다.
   - 최종적으로 277개 섬 단위의 `island_analysis.csv`, `master_unified.csv`, `step3_map_table.csv` 계열 산출물을 만듭니다.

2. **응급의료 도달시간 진단**
   - 위치: `scripts/step_e_final_Y.py`, `scripts/step_f_fix_and_merge.py`
   - `Y_time_emergency = min(섬내 의료접근, 해상 이동시간 + 육지 접근시간)`으로 277개 섬의 응급의료 도달시간을 산정합니다.

3. **원인 분석과 유형화**
   - 위치: `scripts/step1_*.py`, `scripts/step2*.py`, `scripts/step3_maps.py`
   - EDA, OLS/RF/SHAP, 병목 분해, K-means 군집, 지도 시각화를 수행합니다.
   - 정책적으로는 `C0 양호`, `C1 중취약`, `C2 극취약`의 3계층과 해상/육지/혼합 병목 유형을 함께 봅니다.

4. **정책 시뮬레이션, LISA, 수요 결합**
   - 위치: `island-medical-access/`
   - STEP4 정책 시나리오, STEP5 공간자기상관(LISA), STEP6 MDIS/KOSIS 수요지표 결합을 수행합니다.
   - 보고서용 그림과 중간 산출물은 `island-medical-access/outputs/`, `island-medical-access/data/processed/`에 있습니다.

## 폴더 구조

```text
.
├── scripts/                       # 원천 전처리, Y 구축, STEP1~3 분석
│   ├── step_b_*.py                # 섬 경계/격자 crosswalk
│   ├── step_c_*.py                # 접근성 격자 병합
│   ├── step_d_*.py                # 섬 단위 분석 테이블
│   ├── step_e*.py, step_f*.py     # 응급/1차의료 도달시간 Y 구축
│   ├── step1_*.py                 # EDA, OLS/RF/SHAP
│   ├── step2*.py                  # 병목 분해, K-means
│   ├── step3_maps.py              # 지도 시각화
│   └── Python/, R/                # SDC/소지역/격자인구 통합 보조 코드
├── island-medical-access/          # STEP4~6 보강 분석과 보고서 산출물
│   ├── code/
│   ├── data/
│   ├── outputs/
│   └── docs/
└── README.md
```

## 실행 순서

친구 브랜치의 원천 파이프라인은 로컬 절대경로를 쓰는 스크립트가 일부 있습니다. 실행 전 각 파일 상단의 `BASE` 경로를 현재 데이터 폴더에 맞게 수정해야 합니다.

```bash
# 1. 전처리와 마스터 구축
python scripts/step_b_crosswalk.py
python scripts/step_b_boundaries.py
python scripts/step_b_grid_lookup.py
python scripts/step_c_merge_access.py
python scripts/step_d_island_table.py
python scripts/step_e_final_Y.py
python scripts/step_f_fix_and_merge.py

# 2. 원인 분석, 군집, 지도
python scripts/step1_eda.py
python scripts/step1_model_v2.py
python scripts/step2a_bottleneck.py
python scripts/step2b_kmeans.py
python scripts/step3_maps.py

# 3. 정책 시뮬레이션, LISA, 수요 결합
cd island-medical-access
pip install -r requirements.txt
python code/02_policy_simulation.py
python code/03_lisa_spatial.py
python code/04_demand_integration.py
```

## 대회 보고서 핵심 메시지

- 전남 277개 유인도 중 응급의료 도달시간 60분을 초과하는 섬과 인구를 정량화합니다.
- 취약 원인을 해상 이동 병목, 육지 접근 병목, 혼합형, 섬내 자립형으로 나누어 설명합니다.
- `군집 심각도 × 병목 유형` 정책매트릭스로 섬마다 다른 처방을 제안합니다.
- S3 통합대책 같은 정책 시나리오로 골든타임 초과 섬 수와 노출 인구 감소 효과를 수치로 제시합니다.

## 데이터 관리 원칙

- `data/raw/`와 `island-medical-access/data/raw/`의 원시데이터는 git에 올리지 않습니다.
- 팀 간 공유가 필요한 처리 산출물과 보고서용 그림은 필요 범위 안에서 추적합니다.
- 동명이섬이 있으므로 모든 병합은 섬이름이 아니라 `섬코드`를 기준으로 합니다.
