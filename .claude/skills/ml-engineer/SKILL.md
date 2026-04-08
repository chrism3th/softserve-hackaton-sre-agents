---
name: ml-engineer
description: Use when productionizing ML models — training pipelines, model serving, feature stores, model monitoring, MLOps infrastructure, and turning a data scientist's notebook into a reliable service.
---

# ML Engineer Skill

Bridge between data science and production. Your output is a system that runs every day without you.

## The ML System Has Four Surfaces

1. **Training**: data → features → model → artifact.
2. **Serving**: request → features → prediction → response.
3. **Monitoring**: predictions + ground truth → metrics → alerts.
4. **Feedback loop**: new data → retrain → redeploy.

All four must exist before you call it production.

## Training Pipeline

- Deterministic: same input, same output. Seed everything.
- Parameterized: no hardcoded paths. Use a config file (Hydra, pydantic-settings).
- Versioned: data version + code version + config version → model version.
- Reproducible in Docker. "Runs on my laptop" is not acceptable.
- Idempotent: re-running does not corrupt state.

## Model Artifact

Store alongside the weights:
- Feature schema (names, dtypes, allowed ranges)
- Preprocessing pipeline (scaler, encoder)
- Training data hash / version
- Metrics on validation and test
- Training timestamp and git SHA
- Model card: intended use, limitations, ethical considerations

Use MLflow, Weights & Biases, or at minimum a structured folder convention.

## Serving

- **Batch** for non-urgent predictions (nightly scores). Simple, cheap.
- **Online** for low-latency (<200ms) via REST or gRPC. More complex.
- **Streaming** for continuous data (Kafka → model → sink).

Serving checklist:
- [ ] Input validation matches training schema
- [ ] Feature transformations match training exactly (use the same pipeline object)
- [ ] Fallback when model fails (default response, previous model, error)
- [ ] Latency budget measured and enforced
- [ ] Warm-up on startup (avoid first-request slowness)
- [ ] Health and readiness endpoints

## Feature Engineering for Production

- **Offline/online parity**: the function that computes features in training must be the exact same function at serving time. Put it in a shared library, not two notebooks.
- **Feature store** (Feast, Tecton) if you have > 1 model sharing features.
- **Time-travel**: historical features must reflect what was known at that time, not today's values.

## Monitoring

Track these, not just latency:
- **Input drift**: distribution of each feature vs. training.
- **Prediction drift**: distribution of model outputs over time.
- **Concept drift**: accuracy decay when ground truth arrives.
- **Data quality**: null rates, out-of-range values, schema violations.
- **Business metric**: the thing you actually optimize for.

Alert thresholds based on rolling baselines, not fixed numbers.

## Deployment Strategies

- **Shadow mode**: new model runs in parallel, predictions logged but not served. Compare offline.
- **Canary**: 1% → 10% → 50% → 100% with auto-rollback.
- **A/B**: for business metric comparison.
- **Champion/challenger**: ongoing comparison.

Never big-bang swap a model in production.

## Retraining

- Triggered by: schedule, drift alarms, or performance decay.
- Always validate against the previous model before promoting.
- Keep the last N models deployable for instant rollback.

## Anti-Patterns

- Training in a notebook, pickling the model, copying it to prod.
- Feature code duplicated between training and serving (drift guaranteed).
- No versioning — "which model is live right now?"
- Logging inputs without predictions (or vice versa).
- Manual retraining every quarter with no triggers.
- Model serving behind a synchronous API when batch would do.
- One giant "ml" repo with 50 models — use per-model repos or a monorepo with clear boundaries.
