# -*- coding: utf-8 -*-
"""
STEP 1 - 모델링: 다중회귀(베이스라인) + Random Forest + SHAP
  Y = log1p(Y_time_emergency)
"""
import numpy as np
import pandas as pd
from pathlib import Path
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score, KFold
from sklearn.preprocessing import StandardScaler
import shap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False

from project_paths import BASE
MASTER = BASE / "03_master"
df = pd.read_csv(MASTER / "step1_X.csv", encoding="utf-8-sig")

YCOL, YLOG = "Y_time_emergency", "Y_log"
rep = []
def log(*a):
    s = " ".join(str(x) for x in a); print(s); rep.append(s)

Xcols = [c for c in df.columns if c not in ["섬코드", "섬이름", "시군구", YCOL, YLOG]]
# 결측 대치(중앙값)
X = df[Xcols].copy()
X = X.fillna(X.median(numeric_only=True))
y_log = df[YLOG].values
y_raw = df[YCOL].values

# ============ (A) 다중회귀: 공선성 정리 후 OLS ============
# 중복/대리 변수 정리 (인구 다중표현, 면적 다중표현)
drop_for_ols = ["2023년 총인구", "2024년 총인구", "2024년 남자인구", "2024년 여자인구",
                "해안선 데이터 기준 면적(제곱키로미터)", "지적도 기준 면적(제곱키로미터)",
                "어린이집 정원", "어린이집 유아", "유치원 정원", "유치원 유아", "유치원 학급",
                "초등학교 학생", "중학교 학생", "고등학교 학생",
                "초등학교 학급", "중학교 학급", "고등학교 학급",
                "초등학교 교직원", "중학교 교직원", "고등학교 교직원", "어린이집 교직원", "유치원 교직원"]
ols_cols = [c for c in Xcols if c not in drop_for_ols]
Xo = X[ols_cols].copy()

# VIF 반복 제거 (>10)
def reduce_vif(Xdf, thr=10.0):
    cols = list(Xdf.columns)
    while True:
        Z = StandardScaler().fit_transform(Xdf[cols])
        vifs = [variance_inflation_factor(Z, i) for i in range(len(cols))]
        mx = int(np.argmax(vifs))
        if vifs[mx] > thr and len(cols) > 2:
            cols.pop(mx)
        else:
            return cols, dict(zip(cols, [variance_inflation_factor(StandardScaler().fit_transform(Xdf[cols]), i) for i in range(len(cols))]))

ols_final, vifs = reduce_vif(Xo)
log("=== (A) 다중회귀 OLS ===")
log("VIF 정리 후 변수 %d개" % len(ols_final))

Zs = StandardScaler().fit_transform(Xo[ols_final])
Xsm = sm.add_constant(Zs)
model = sm.OLS(y_log, Xsm).fit()
log(f"R2={model.rsquared:.3f}  adjR2={model.rsquared_adj:.3f}  n={int(model.nobs)}")
coef = pd.DataFrame({"var": ["const"] + ols_final,
                     "beta_std": model.params,
                     "p": model.pvalues}).iloc[1:]
coef = coef.sort_values("p")
log("\n유의 변수 (p<0.05, 표준화계수):")
for _, r in coef[coef["p"] < 0.05].iterrows():
    sign = "+" if r["beta_std"] > 0 else "-"
    log(f"  {r['var']:>26}  beta={r['beta_std']:+.3f}  p={r['p']:.4f}  ({sign}=접근성 {'악화' if r['beta_std']>0 else '개선'})")

# ============ (B) Random Forest ============
log("\n=== (B) Random Forest ===")
rf = RandomForestRegressor(n_estimators=600, max_depth=None, min_samples_leaf=3,
                           random_state=42, n_jobs=-1, oob_score=True)
rf.fit(X, y_raw)
cv = cross_val_score(rf, X, y_raw, cv=KFold(5, shuffle=True, random_state=42), scoring="r2")
log(f"OOB R2={rf.oob_score_:.3f} | 5-fold CV R2={cv.mean():.3f}±{cv.std():.3f}")
imp = pd.Series(rf.feature_importances_, index=Xcols).sort_values(ascending=False)
log("\nRF 중요도 상위 12:")
for c, v in imp.head(12).items():
    log(f"  {c:>26}: {v:.4f}")

# ============ (C) SHAP ============
log("\n=== (C) SHAP ===")
expl = shap.TreeExplainer(rf)
sv = expl.shap_values(X)
mean_abs = pd.Series(np.abs(sv).mean(axis=0), index=Xcols).sort_values(ascending=False)
log("평균 |SHAP| 상위 10:")
for c, v in mean_abs.head(10).items():
    log(f"  {c:>26}: {v:.3f}")

top3 = mean_abs.head(3).index.tolist()
log("\n★ STEP1 핵심: 접근성에 가장 큰 영향 상위 3개 = %s" % top3)
# 방향성: 상위3의 Y와 상관
for c in top3:
    r = np.corrcoef(X[c], y_raw)[0, 1]
    log(f"   - {c}: Y와 상관 r={r:+.3f} ({'악화' if r>0 else '개선'} 방향)")

# SHAP summary plot
plt.figure()
shap.summary_plot(sv, X, max_display=12, show=False)
plt.tight_layout()
plt.savefig(MASTER / "step1_shap_summary.png", dpi=130, bbox_inches="tight")
plt.close()

(MASTER / "step1_model_report.txt").write_text("\n".join(rep), encoding="utf-8")
imp.to_csv(MASTER / "step1_rf_importance.csv", encoding="utf-8-sig")
mean_abs.to_csv(MASTER / "step1_shap_importance.csv", encoding="utf-8-sig")
log("\n저장: step1_model_report.txt, step1_shap_summary.png, step1_rf_importance.csv, step1_shap_importance.csv")
