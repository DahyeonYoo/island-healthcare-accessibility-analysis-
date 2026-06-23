# 전남 도서 의료취약성 분석 — 접근성 진단 · 정책 시뮬레이션

2026 국가데이터 활용대회 (데이터분석 보고서 부문) · 전라남도 277개 유인도 응급의료 도달시간 분석.

> 본 브랜치는 **분석 보강(접근성 격자) · 정책 시뮬레이션 · 공간자기상관(LISA) · 수요변수 통합(MDIS·KOSIS)** 코드와
> 산출물을 담습니다. 데이터 통합 마스터·종속변수(Y)·STEP1~3 원본 파이프라인은 **팀원 브랜치**에서 머지됩니다.

## 폴더 구조

```
island-medical-access/
├── code/
│   ├── 01_master_grid_access.py    # 접근성 격자(500m) → 섬 결합 (보강본)
│   ├── 02_policy_simulation.py     # STEP4 정책매트릭스 + 격차해소 시뮬레이션
│   ├── 03_lisa_spatial.py          # STEP5 Moran's I + LISA
│   └── 04_demand_integration.py    # STEP6 MDIS(지역사회건강조사) + KOSIS 고령화 결합
├── data/
│   ├── from_teammate/              # 팀원 파이프라인 산출물(공유 입력)
│   │   ├── island_analysis.csv         # 최종 분석 테이블(277섬, Y 통일본)
│   │   └── step3_map_table.csv         # 군집·병목·좌표 포함
│   ├── processed/                  # 본 브랜치 산출물(커밋 O)
│   │   ├── island_analysis_수요결합.csv  # +미충족의료·고령화 (191열)
│   │   ├── step6_시군구_수요지표.csv
│   │   ├── step4_scenario_summary.csv / step4_sensitivity.csv
│   │   ├── step4_island_simulation.csv / step4_policy_matrix_counts.csv
│   │   └── step5_lisa_result.csv
│   └── raw/                        # 원시데이터(.gitignore — data/raw/README.md 참조)
├── outputs/
│   ├── figures/                    # 보고서용 그림 4종
│   └── report/                     # 보고서(docx) + 통합마스터(xlsx)
├── docs/우승_로드맵.md
├── requirements.txt
└── .gitignore
```

## 실행

통합 리포지토리에서는 먼저 이 폴더로 이동한 뒤 실행합니다.

```bash
cd island-medical-access
pip install -r requirements.txt
python code/02_policy_simulation.py     # data/from_teammate 만 있으면 즉시 실행
python code/03_lisa_spatial.py          # 동일
python code/04_demand_integration.py    # data/raw 에 CHS·KOSIS 배치 필요(아래)
python code/01_master_grid_access.py    # data/raw 에 접근성 zip 배치 필요
```

01·04는 원시데이터가 필요합니다 → `data/raw/README.md`에 배치 목록.

## 핵심 결과 (재현값)

- **진단**: 평균 응급도달 62.3분, 골든타임(60분) 초과 124섬·36,965명. 최악 가거도 236분.
- **공간(LISA)**: Global Moran's I = 0.818 (p=0.001) → HH(취약집적) 31섬 전부 신안 외해.
- **정책 시뮬(S3 통합대책)**: 골든타임 초과 섬 124→60(▼51.6%), 인구 ▼65.8%, 평균 ▼26.3%.
- **수요 검증(MDIS)**: 도서 3개군 미충족의료율 신안 8.0%·진도 7.5%·완도 7.3% > 전남 평균 5.3%.

## 데이터 출처

행정안전부 유인도정보 · 국토교통부·통계청 국토통계 접근성격자 · 국토부 도서경계 · 해양수산부 여객선 ·
건강보험심사평가원 의료공급 · 응급의료포털 E-Gen · **MDIS 지역사회건강조사** · **KOSIS 주민등록인구**.

---

## 🔧 내 브랜치에 올리기 (VS Code / 터미널)

이 폴더(`island-medical-access`)를 이미 만든 리포지토리 안에 넣고, 본인 브랜치에서 커밋·푸시:

```bash
# (리포 클론이 이미 있다면) 이 폴더 내용을 리포 안으로 복사한 뒤:
git checkout 본인_브랜치이름        # 없으면: git checkout -b 본인_브랜치이름
git add island-medical-access        # 또는 리포 루트에 풀어 넣었으면 git add .
git commit -m "분석 보강·정책 시뮬레이션·LISA·수요변수(MDIS/KOSIS) 통합 추가"
git push origin 본인_브랜치이름
```

### 머지 시 주의 (충돌 예방)
- `data/from_teammate/island_analysis.csv`·`step3_map_table.csv`는 **팀원 산출물 사본**입니다.
  머지 시 **팀원 브랜치 버전을 정본**으로 두면 됩니다(내용 동일하면 충돌 없음).
- 본 브랜치 고유 산출물은 `data/processed/`, `outputs/`, `code/0X_*.py`이므로 팀원 코드와 **파일명이 겹치지 않습니다.**
- `data/raw/`는 `.gitignore`로 빠지니 원시데이터 충돌·대용량 push 걱정 없음.
