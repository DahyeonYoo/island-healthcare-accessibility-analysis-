# Merge notes

통합 브랜치: `merge-contest-analysis`

병합 대상:

- `origin/dh_code`: 원천 데이터 전처리, 접근성/Y 구축, STEP1~3 모델링/군집/지도 코드
- `origin/khyitty`: STEP4 정책 시뮬레이션, STEP5 LISA, STEP6 MDIS/KOSIS 수요결합, 보고서용 산출물

## 통합 배치 원칙

1. `scripts/`는 원천 파이프라인과 STEP1~3 분석의 정본으로 둔다.
2. `island-medical-access/`는 STEP4~6 보강 분석과 보고서 산출물의 정본으로 둔다.
3. 중첩 복제본 `island-medical-access/island-medical-access/`는 제거했다.
4. 압축해제 폴더에 있던 `ferry_access_clean.py`는 `scripts/ferry_access_clean.py`로 옮겼다.
5. 원시데이터는 계속 git에서 제외하고, 공유 가능한 처리 산출물과 보고서용 결과만 추적한다.

## 보고서상 추천 서사

1. 문제: 전남 277개 유인도는 의료시설 유무만으로는 응급의료 접근성을 설명하기 어렵다.
2. 진단: 섬내 접근, 해상 이동, 육지 접근을 결합해 `Y_time_emergency`를 만든다.
3. 원인: SHAP과 병목 분해로 취약성이 교통/육지/혼합/섬내자립 중 어디서 생기는지 분리한다.
4. 유형: K-means로 C0/C1/C2 심각도 군집을 만들고 공간지도로 검증한다.
5. 처방: `군집 심각도 × 병목 유형` 정책매트릭스와 S1~S3 시나리오로 실현 가능한 대책을 제시한다.
6. 수요 보정: MDIS 미충족의료율과 KOSIS 고령화율로 실제 의료수요가 큰 지역을 우선순위에 반영한다.
