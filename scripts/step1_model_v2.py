# -*- coding: utf-8 -*-
"""
STEP 1 재산출 (v2): '먼섬특별법' 제외 → 실질 원인 상위 3 확정
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

BASE = Path(r"C:\Users\dyu18\OneDrive\문서\데이터활용대회")
MASTER = BASE / "03_master"
df = pd.read_csv(MASTER / "step1_X.csv", encoding="utf-8-sig")

YCOL, YLOG = "Y_time_emergency", "Y_log"
EXCLUDE = ["먼섬특별법_b"]   # ★ 동어반복 변수 제외
rep = []
def log(*a):
    s = " ".join(str(x) for x in a); print(s); rep.append(s)

log("=== STEP1 재산출 (먼섬특별법 제외) ===")
Xcols = [c for c in df.columns if c not in ["섬코드", "섬이름", "시군구", YCOL, YLOG] + EXCLUDE]
X = df[Xcols].copy().fillna(df[Xcols].median(numeric_only=True))
y_log = df[YLOG].values
y_raw = df[YCOL].values

# ---------- (A) OLS ----------
drop_for_ols = ["2023년 총인구", "2024년 총인구", "2024년 남자인구", "2024년 여자인구",
                "해안선 데이터 기준 면적(제곱키로미터)", "지적도 기준 면적(제곱키로미터)",
                "어린이집 정원", "어린이집 유아", "유치원 정원", "유치원 유아", "유치원 학급",
                "초등학교 학생", "중학교 학생", "고등학교 학생",
                "초등학교 학급", "중학교 학급", "고등학교 학급",
                "초등학교 교직원", "중학교 교직원", "고등학교 교직원", "어린이집 교직원", "유치원 교직원"]
ols_cols = [c for c in Xcols if c not in drop_for_ols]
Xo = X[ols_cols].copy()

def reduce_vif(Xdf, thr=10.0):
    cols = list(Xdf.columns)
    while len(cols) > 2:
        Z = StandardScaler().fit_transform(Xdf[cols])
        vifs = [variance_inflation_factor(Z, i) for i in range(len(cols))]
        mx = int(np.argmax(vifs))
        if vifs[mx] > thr:
            cols.pop(mx)
        else:
            break
    return cols

ols_final = reduce_vif(Xo)
Zs = StandardScaler().fit_transform(Xo[ols_final])
model = sm.OLS(y_log, sm.add_constant(Zs)).fit()
log("\n(A) OLS  R2=%.3f adjR2=%.3f (변수 %d)" % (model.rsquared, model.rsquared_adj, len(ols_final)))
coef = pd.DataFrame({"var": ols_final, "beta": model.params[1:], "p": model.pvalues[1:]}).sort_values("p")
log("유의변수(p<0.05):")
for _, r in coef[coef["p"] < 0.05].iterrows():
    log(f"  {r['var']:>24} beta={r['beta']:+.3f} p={r['p']:.4f} ({'악화' if r['beta']>0 else '개선'})")

# ---------- (B) RF ----------
rf = RandomForestRegressor(n_estimators=600, min_samples_leaf=3, random_state=42,
                           n_jobs=-1, oob_score=True)
rf.fit(X, y_raw)
cv = cross_val_score(rf, X, y_raw, cv=KFold(5, shuffle=True, random_state=42), scoring="r2")
log("\n(B) RF  OOB R2=%.3f  CV R2=%.3f±%.3f" % (rf.oob_score_, cv.mean(), cv.std()))
imp = pd.Series(rf.feature_importances_, index=Xcols).sort_values(ascending=False)
log("RF 중요도 상위 10:")
for c, v in imp.head(10).items():
    log(f"  {c:>24}: {v:.4f}")

# ---------- (C) SHAP ----------
sv = shap.TreeExplainer(rf).shap_values(X)
mean_abs = pd.Series(np.abs(sv).mean(axis=0), index=Xcols).sort_values(ascending=False)
log("\n(C) 평균|SHAP| 상위 10:")
for c, v in mean_abs.head(10).items():
    r = np.corrcoef(X[c], y_raw)[0, 1]
    log(f"  {c:>24}: {v:.3f}  (r={r:+.3f}, {'악화' if r>0 else '개선'})")

top3 = mean_abs.head(3).index.tolist()
log("\n★ 실질 원인 상위 3 (먼섬특별법 제외) = %s" % top3)

plt.figure()
shap.summary_plot(sv, X, max_display=12, show=False)
plt.tight_layout()
plt.savefig(MASTER / "step1_shap_summary_v2.png", dpi=130, bbox_inches="tight")
plt.close()

imp.to_csv(MASTER / "step1_rf_importance_v2.csv", encoding="utf-8-sig")
mean_abs.to_csv(MASTER / "step1_shap_importance_v2.csv", encoding="utf-8-sig")
(MASTER / "step1_model_report_v2.txt").write_text("\n".join(rep), encoding="utf-8")
log("\n저장: *_v2 (report/png/csv)")
