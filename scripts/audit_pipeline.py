# -*- coding: utf-8 -*-
"""
전체 파이프라인 자가검증 (self-audit)
검사: 키정합성 / Y 일치 / 단위항등식 / Y구성식 / 결측 / 범위 / 누수 / 군집·병목 재현성
"""
import numpy as np
import pandas as pd
from project_paths import INTERIM, MASTER

M = MASTER
I = INTERIM
FERRY, ROAD = 30.0, 40.0
PASS, WARN, FAIL = [], [], []
def ok(m): PASS.append(m); print("  [OK]  " + m)
def warn(m): WARN.append(m); print("  [WARN]" + m)
def bad(m): FAIL.append(m); print("  [FAIL]" + m)

def load(p):
    return pd.read_csv(p, encoding='utf-8-sig')

ia = load(M / 'island_analysis.csv')
mu = load(M / 'master_unified.csv')
cl = load(M / 'step2_clusters.csv')
bt = load(M / 'stepA_bottleneck.csv')
mt = load(M / 'step3_map_table.csv')
xx = load(M / 'step1_X.csv')

print("\n##### 1. 행수 / 키(섬코드) 정합성 #####")
for nm, df in [('island_analysis', ia), ('master_unified', mu), ('step2_clusters', cl),
               ('stepA_bottleneck', bt), ('step3_map_table', mt), ('step1_X', xx)]:
    n = len(df); dup = df['섬코드'].duplicated().sum()
    (ok if (n == 277 and dup == 0) else bad)(f"{nm}: n={n}, 중복섬코드={dup}")
base = set(mu['섬코드'])
for nm, df in [('island_analysis', ia), ('step2_clusters', cl), ('stepA_bottleneck', bt),
               ('step3_map_table', mt), ('step1_X', xx)]:
    miss = base ^ set(df['섬코드'])
    (ok if not miss else bad)(f"{nm} 섬코드 집합 == master ({'일치' if not miss else f'차이 {len(miss)}'})")

print("\n##### 2. Y 4개 파일 일치 #####")
yref = mu.set_index('섬코드')['Y_time_emergency']
for nm, df in [('island_analysis', ia), ('step2_clusters', cl),
               ('stepA_bottleneck', bt), ('step3_map_table', mt)]:
    if 'Y_time_emergency' in df.columns:
        d = (df.set_index('섬코드')['Y_time_emergency'] - yref).abs().max()
        (ok if d < 1e-6 else bad)(f"{nm} Y == master (최대차 {d:.2e})")

print("\n##### 3. 단위 항등식 (master_unified) #####")
d = (mu['land_leg_emergency_min'] - mu['land_leg_emergency_km'] / ROAD * 60).abs().max()
(ok if d < 1e-6 else bad)(f"land_leg_emergency_min == km/{ROAD}*60 (최대차 {d:.2e})")
d = (mu['land_leg_clinic_min'] - mu['land_leg_clinic_km'] / ROAD * 60).abs().max()
(ok if d < 1e-6 else bad)(f"land_leg_clinic_min == km/{ROAD}*60 (최대차 {d:.2e})")
if 'dist_main_km' in mu.columns:
    exp = mu['dist_main_km'] / FERRY * 60
    # 연결섬(sea=0)은 제외하고 비교
    nz = mu['sea_leg_min'] > 0
    d = (mu.loc[nz, 'sea_leg_min'] - exp[nz]).abs().max()
    (ok if d < 1e-3 else warn)(f"sea_leg_min == dist/{FERRY}*60 (미연결섬, 최대차 {d:.2e})")
    conn = (~nz).sum()
    ok(f"sea_leg==0 (연결섬 추정) {conn}개")

print("\n##### 4. Y 구성식 재현 (master_unified) #####")
on = mu['has_emergency_onisland'].fillna(0).astype(int)
off = mu['sea_leg_min'] + mu['land_leg_emergency_min']
# 섬내시설 없는 섬: Y == off
no_on = on == 0
d = (mu.loc[no_on, 'Y_time_emergency'] - off[no_on]).abs().max()
(ok if d < 1e-6 else bad)(f"섬내시설無 Y == sea+land (n={no_on.sum()}, 최대차 {d:.2e})")
# 섬내시설 있는 섬: Y <= off (min 구조)
yes_on = on == 1
if yes_on.any():
    viol = (mu.loc[yes_on, 'Y_time_emergency'] > off[yes_on] + 1e-6).sum()
    (ok if viol == 0 else bad)(f"섬내시설有 Y <= sea+land (n={yes_on.sum()}, 위반 {viol})")

print("\n##### 5. 결측 / 음수 / 범위 #####")
for c in ['Y_time_emergency', 'sea_leg_min', 'land_leg_emergency_min', 'dist_main_km']:
    if c in mu.columns:
        na = mu[c].isna().sum(); neg = (mu[c] < 0).sum()
        (ok if (na == 0 and neg == 0) else bad)(f"{c}: 결측 {na}, 음수 {neg}")
ok(f"Y 범위: {mu['Y_time_emergency'].min():.1f} ~ {mu['Y_time_emergency'].max():.1f}분 "
   f"(평균 {mu['Y_time_emergency'].mean():.1f})")
# Y == sea+land 이므로 자동 양수지만 상한 점검
if mu['Y_time_emergency'].max() > 600:
    warn("Y 최댓값 600분 초과 — 이상치 점검 필요")
else:
    ok("Y 최댓값 600분 이하 (현실적 범위)")

print("\n##### 6. STEP1 X 누수 점검 #####")
leak_kw = ['Y_time', 'sea_leg', 'land_leg', 'dist_main', 'acc_', 'ferry', 'sea_route',
           'has_emergency', 'has_clinic', 'on_min', 'off_leg', 'bottleneck', 'cluster']
hit = [c for c in xx.columns if any(k.lower() in c.lower() for k in leak_kw)]
(ok if not hit else bad)(f"step1_X 누수 의심 컬럼: {hit if hit else '없음'}")
ok(f"step1_X 변수 수: {xx.shape[1]} (섬코드/이름 포함)")

print("\n##### 7. 병목유형 재현 (stepA) #####")
m2 = mu.merge(bt[['섬코드', 'bottleneck_type', 'sea_share']], on='섬코드')
off2 = m2['sea_leg_min'] + m2['land_leg_emergency_min']
share = np.where(off2 > 0, m2['sea_leg_min'] / off2, 0.0)
d = np.abs(share - m2['sea_share']).max()
(ok if d < 1e-6 else bad)(f"sea_share 재현 (최대차 {d:.2e})")
def reclass(i):
    onb = (m2['has_emergency_onisland'].fillna(0).astype(int).iloc[i] == 1) and \
          (m2['Y_time_emergency'].iloc[i] < off2.iloc[i] - 1e-6)
    if onb: return '섬내자립형'
    s = share[i]
    return '해상지배형' if s >= 0.6 else ('육지지배형' if s <= 0.4 else '혼합형')
rec = [reclass(i) for i in range(len(m2))]
mismatch = (pd.Series(rec) != m2['bottleneck_type'].reset_index(drop=True)).sum()
(ok if mismatch == 0 else bad)(f"bottleneck_type 재현 불일치 {mismatch}개")
print("    분포:", m2['bottleneck_type'].value_counts().to_dict())

print("\n##### 8. 군집 정합성 (step2 vs step3_map) #####")
mc = cl.set_index('섬코드')['cluster']
mm = mt.set_index('섬코드')['cluster']
common = mc.index.intersection(mm.index)
dd = (mc.loc[common] != mm.loc[common]).sum()
(ok if dd == 0 else bad)(f"cluster (step2 vs map_table) 불일치 {dd}개")
print("    군집 분포:", cl['cluster'].value_counts().sort_index().to_dict())

print("\n##### 9. 경계 데이터(GPKG) 정합성 #####")
try:
    import geopandas as gpd
    g = gpd.read_file(I / 'island_boundaries_jeonnam.gpkg')
    miss = base ^ set(g['섬코드'])
    (ok if not miss else bad)(f"boundaries 섬코드 == master ({'일치' if not miss else len(miss)})")
    inv = (~g.geometry.is_valid).sum(); emp = g.geometry.is_empty.sum()
    (ok if (inv == 0 and emp == 0) else warn)(f"geometry 무효 {inv}, 빈 {emp}")
except Exception as e:
    warn("GPKG 검사 스킵: " + str(e))

print("\n" + "=" * 50)
print(f"결과: PASS {len(PASS)} / WARN {len(WARN)} / FAIL {len(FAIL)}")
if FAIL: print("FAIL 항목:\n  - " + "\n  - ".join(FAIL))
if WARN: print("WARN 항목:\n  - " + "\n  - ".join(WARN))
report = ["전체 파이프라인 자가검증 결과", "=" * 40,
          f"PASS {len(PASS)} / WARN {len(WARN)} / FAIL {len(FAIL)}", "",
          "[PASS]"] + PASS + ["", "[WARN]"] + WARN + ["", "[FAIL]"] + FAIL
(M / 'AUDIT_report.txt').write_text("\n".join(report), encoding='utf-8')
print("저장: AUDIT_report.txt")
