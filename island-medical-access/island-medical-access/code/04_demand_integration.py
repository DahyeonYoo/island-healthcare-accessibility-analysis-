# -*- coding: utf-8 -*-
"""
04_demand_integration.py  (STEP 6)  — MDIS 지역사회건강조사(CHS) + KOSIS 고령화 결합
실행: 리포지토리 루트에서  python code/04_demand_integration.py
입력(raw, .gitignore): data/raw/chs{21,22,23}_m.sas7bdat, data/raw/chs{24,25}_jeonnam.sas7bdat,
                       data/raw/kosis_emd_pop.xlsx (행정구역 읍면동 5세별 주민등록인구, 전남)
입력(공유): data/from_teammate/island_analysis.csv
출력: data/processed/step6_시군구_수요지표.csv, data/processed/island_analysis_수요결합.csv,
      outputs/figures/step6_fig_unmet_medical.png

설계: CHS는 개인 마이크로데이터(시군구=signgu_code). 개인가중치(wt_p)로 시군구별 가중집계.
      섬↔시군구는 섬코드 앞 5자리(= signgu_code)로 결합. (시군구 단위 = 섬내 변이 없음, 한계 명시)
"""
import os, glob
import numpy as np, pandas as pd
import pyreadstat
import matplotlib
matplotlib.use("Agg")
import koreanize_matplotlib  # noqa: F401
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

RAW = "data/raw"; PROC = "data/processed"; FIG = "outputs/figures"
ISLAND = "data/from_teammate/island_analysis.csv"
KOSIS = f"{RAW}/kosis_emd_pop.xlsx"
CHS_FILES = ["chs21_m", "chs22_m", "chs23_m", "chs24_jeonnam", "chs25_jeonnam"]

SGG_NAME = {'46110': '목포시', '46130': '여수시', '46150': '순천시', '46170': '나주시', '46230': '광양시',
            '46710': '담양군', '46720': '곡성군', '46730': '구례군', '46770': '고흥군', '46780': '보성군',
            '46790': '화순군', '46800': '장흥군', '46810': '강진군', '46820': '해남군', '46830': '영암군',
            '46840': '무안군', '46860': '함평군', '46870': '영광군', '46880': '장성군', '46890': '완도군',
            '46900': '진도군', '46910': '신안군'}
NEED = ['signgu_code', 'CTPRVN_CODE', 'wt_p', 'age', 'sra_01z3', 'hya_04z1', 'dia_04z1', 'qoa_01z1']


def wrate(s, yes, valid, w):
    s = pd.to_numeric(s, errors='coerce'); m = s.isin(valid)
    ww = w[m]
    return np.average(s[m].isin(yes), weights=ww) * 100 if ww.sum() > 0 else np.nan


def load_chs():
    frames = []
    for name in CHS_FILES:
        hits = glob.glob(f"{RAW}/{name}.sas7bdat") + glob.glob(f"{RAW}/{name}/{name}.sas7bdat")
        if not hits:
            print(f"[skip] {name} 없음"); continue
        df, _ = pyreadstat.read_sas7bdat(hits[0])
        d = df[[c for c in NEED if c in df.columns]].copy()
        if 'CTPRVN_CODE' in d.columns:
            d = d[d['CTPRVN_CODE'].astype(str).str.zfill(2) == '46']  # 전남
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def chs_by_sigungu(chs):
    chs['w'] = pd.to_numeric(chs['wt_p'], errors='coerce').fillna(1.0)
    rows = []
    for code, g in chs.groupby(chs['signgu_code'].astype(str)):
        w = g['w']
        rows.append({'signgu_code': code, 'n': len(g),
                     '미충족의료율': round(wrate(g['sra_01z3'], (1,), (1, 2), w), 1),
                     '고혈압진단율': round(wrate(g['hya_04z1'], (1,), (1, 2), w), 1),
                     '당뇨진단율': round(wrate(g['dia_04z1'], (1,), (1, 2), w), 1),
                     '주관건강나쁨율': round(wrate(g['qoa_01z1'], (4, 5), (1, 2, 3, 4, 5), w), 1)})
    out = pd.DataFrame(rows); out['시군구'] = out['signgu_code'].map(SGG_NAME)
    return out


def kosis_aging():
    k = pd.read_excel(KOSIS, header=1)
    k.columns = ['지역', '항목', '계', '65_69', '70_74', '75_79', '80_84', '85_89', '90_94', '95_99', '100p']
    k['지역'] = k['지역'].ffill().astype(str).str.replace(r'[\s　]', '', regex=True)
    tot = k[k['항목'].astype(str).str.contains('총인구')].copy()
    for c in ['계', '65_69', '70_74', '75_79', '80_84', '85_89', '90_94', '95_99', '100p']:
        tot[c] = pd.to_numeric(tot[c], errors='coerce')
    eld = ['65_69', '70_74', '75_79', '80_84', '85_89', '90_94', '95_99', '100p']
    tot['고령화율_65(%)'] = (tot[eld].sum(1) / tot['계'] * 100).round(1)
    tot['후기고령_75(%)'] = (tot[eld[2:]].sum(1) / tot['계'] * 100).round(1)
    return tot[tot['지역'].isin(set(SGG_NAME.values()))][['지역', '고령화율_65(%)', '후기고령_75(%)']]\
        .rename(columns={'지역': '시군구'})


def main():
    os.makedirs(PROC, exist_ok=True); os.makedirs(FIG, exist_ok=True)
    dem = chs_by_sigungu(load_chs()).merge(kosis_aging(), on='시군구', how='left')
    dem = dem[['signgu_code', '시군구', 'n', '미충족의료율', '고령화율_65(%)', '후기고령_75(%)',
               '고혈압진단율', '당뇨진단율', '주관건강나쁨율']]
    dem.to_csv(f"{PROC}/step6_시군구_수요지표.csv", index=False, encoding="utf-8-sig")
    print(dem.sort_values('미충족의료율', ascending=False).to_string(index=False))

    island = pd.read_csv(ISLAND)
    island['signgu_code'] = (island['섬코드'] // 10000).astype(str)
    enr = island.merge(dem.drop(columns=['n', '시군구']), on='signgu_code', how='left')
    enr.to_csv(f"{PROC}/island_analysis_수요결합.csv", index=False, encoding="utf-8-sig")
    print("\n섬 결합:", enr.shape, "| 미충족 결측:", int(enr['미충족의료율'].isna().sum()))

    _fig(dem)


def _fig(dem):
    isl3 = {'신안군', '진도군', '완도군'}
    isl_all = {'신안군', '진도군', '완도군', '고흥군', '여수시', '목포시', '해남군', '영광군'}
    d = dem.sort_values('미충족의료율')
    colors = ['#C00000' if s in isl3 else ('#ED7D31' if s in isl_all else '#BFBFBF') for s in d['시군구']]
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.barh(d['시군구'], d['미충족의료율'], color=colors)
    avg = dem['미충족의료율'].mean()
    ax.axvline(avg, color='#1F4E78', ls='--', lw=1.5)
    ax.text(avg + 0.05, 0.3, f'전남 평균 {avg:.1f}%', color='#1F4E78', fontweight='bold')
    for i, v in enumerate(d['미충족의료율']): ax.text(v + 0.05, i, f'{v}', va='center', fontsize=8)
    ax.set_xlabel('연간 미충족의료율 (%)')
    ax.set_title('전남 시군구별 미충족의료율 (지역사회건강조사, MDIS)\n도서 집중 3개군(빨강)이 전남 평균 상회', fontweight='bold')
    ax.legend(handles=[Patch(color='#C00000', label='도서집중(신안·진도·완도)'),
                       Patch(color='#ED7D31', label='기타 도서보유'), Patch(color='#BFBFBF', label='비도서')],
              loc='lower right', fontsize=9)
    plt.tight_layout(); plt.savefig(f"{FIG}/step6_fig_unmet_medical.png", dpi=150, bbox_inches='tight'); plt.close()


if __name__ == "__main__":
    main()
