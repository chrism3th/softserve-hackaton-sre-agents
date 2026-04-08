---
name: data-scientist
description: Use for exploratory data analysis (EDA), statistical testing, feature engineering, model selection, and presenting findings from data. Works with pandas, polars, numpy, scikit-learn, and notebooks.
---

# Data Scientist Skill

Your job is to turn data into trustworthy decisions. Rigor beats cleverness.

## Workflow

1. **Understand the question.** What decision does this analysis inform? If you can't answer, stop and ask.
2. **Understand the data.** Row count, column types, missingness, duplicates, time range, source-of-truth.
3. **EDA before modeling.** Distributions, correlations, leaks, outliers.
4. **Baseline first.** Simple model (mean, logistic regression) as the floor to beat.
5. **Iterate with a metric.** Pick one primary metric up front.
6. **Validate honestly.** Train/val/test split respects time and groups. No leakage.
7. **Communicate uncertainty.** Confidence intervals, not point estimates.

## EDA Checklist

- [ ] Shape: `df.shape`, `df.dtypes`, `df.info()`
- [ ] Nulls: `df.isna().sum()` — and *why* they're null
- [ ] Duplicates: `df.duplicated().sum()`
- [ ] Categorical cardinality: `df.nunique()`
- [ ] Numeric summary: `df.describe()`
- [ ] Target distribution: is it imbalanced?
- [ ] Time coverage: min/max dates, gaps
- [ ] Correlation with target (but beware nonlinear relationships)
- [ ] Potential leaks: features that encode the target

## Feature Engineering Rules

- **Fit on train, transform on val/test.** Use `sklearn.Pipeline` or `ColumnTransformer` to enforce this.
- **Target encoding** must be done inside cross-validation folds, never globally.
- **Time-based features** (day of week, rolling means) must respect the past — no future leakage.
- **Scaling**: required for distance-based and regularized models, not for tree-based.

## Model Selection

- **Tabular data**: start with gradient boosted trees (LightGBM, XGBoost, CatBoost). They usually win.
- **Small data (< 10k rows)**: logistic / ridge / random forest.
- **Text**: sentence-transformers + logistic regression beats many fancy approaches.
- **Images**: pretrained CNN + fine-tune last layers.
- **Time series**: start with naive / seasonal naive / ETS before Prophet / neural.

## Validation

- **No shuffling** on time series. Use forward-chaining CV.
- **Stratify** on classification targets and groups.
- **Never** touch the test set until the very end. One look, one number.
- Report **CI via bootstrap** on the test metric.

## Metrics (pick one primary)

| Problem | Default metric |
|---|---|
| Binary classification (balanced) | ROC-AUC |
| Binary classification (imbalanced) | PR-AUC or F1 at chosen threshold |
| Multiclass | macro-F1 |
| Regression | RMSE (if errors symmetric) or MAE (if robust needed) |
| Ranking | NDCG@k, MAP@k |
| Forecasting | MAPE (if no zeros) or sMAPE |

## Reproducibility

- Set random seeds everywhere (`numpy`, `random`, `torch`).
- Pin package versions in `requirements.txt`.
- Save artifacts (model, feature names, scaler) together.
- Notebooks: clear output before commit; better, promote to `.py` modules once stable.
- Use DVC or a model registry (MLflow) for anything beyond a toy project.

## Communication

- Lead with the answer, not the methodology.
- One chart = one message. Label axes, title, units.
- Always show the baseline comparison.
- Acknowledge limitations explicitly: sample size, period, confounders.

## Anti-Patterns

- Reporting only the best run out of 20 (p-hacking).
- Training on the test set (happens via scaling/imputation leaks).
- "Accuracy 99%" on a 99/1 imbalanced dataset.
- Huge pipelines with no baseline.
- Unversioned CSVs passed by email.
- Not checking for duplicate rows before splitting.
