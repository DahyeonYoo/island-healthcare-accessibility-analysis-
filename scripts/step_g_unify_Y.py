# -*- coding: utf-8 -*-
"""
Y 단위 정합성 통일: island_analysis.csv를 정본(master_unified.csv)에 맞춤.
  - 문제: island_analysis.csv의 Y는 sea_leg(분)+land_leg(km) 혼합단위(버그, 평균48.5)
  - 정본: master_unified.csv의 Y는 전부 분 환산(40km/h) (평균62.3)
  - 조치: land_leg 컬럼명을 _km로 명확히, _min 추가, Y를 정본값으로 덮어씀.
"""
import pandas as pd
from project_paths import MASTER
import shutil

M = MASTER
ia_path = M / 'island_analysis.csv'

# 1) 백업
bak = M / 'island_analysis_OLD_buggyY.csv'
if not bak.exists():
    shutil.copy2(ia_path, bak)
    print('백업 생성:', bak.name)

ia = pd.read_csv(ia_path, encoding='utf-8-sig')
mu = pd.read_csv(M / 'master_unified.csv', encoding='utf-8-sig')

# 2) land_leg(km) 명확화
ia = ia.rename(columns={'land_leg_emergency': 'land_leg_emergency_km',
                        'land_leg_clinic': 'land_leg_clinic_km'})

# 3) 정본에서 분 환산 + 정정 Y 가져오기
pull = mu[['섬코드', 'land_leg_emergency_min', 'land_leg_clinic_min',
           'Y_time_emergency', 'Y_time_clinic']].copy()
ia = ia.drop(columns=[c for c in ['Y_time_emergency', 'Y_time_clinic'] if c in ia.columns])
ia = ia.merge(pull, on='섬코드', how='left')

# 4) 저장
ia.to_csv(ia_path, index=False, encoding='utf-8-sig')

# 5) 검증
print('정정 후 island_analysis.csv:')
print('  Y_time_emergency 평균 %.3f (정본 %.3f)' %
      (ia['Y_time_emergency'].mean(), mu['Y_time_emergency'].mean()))
print('  Y_time_clinic    평균 %.3f (정본 %.3f)' %
      (ia['Y_time_clinic'].mean(), mu['Y_time_clinic'].mean()))
diff = (ia.set_index('섬코드')['Y_time_emergency'] -
        mu.set_index('섬코드')['Y_time_emergency']).abs().max()
print('  정본과 최대 절대차: %.6f (0이면 완전 일치)' % diff)
print('  land_leg_emergency_km 평균 %.2f / _min 평균 %.2f' %
      (ia['land_leg_emergency_km'].mean(), ia['land_leg_emergency_min'].mean()))
