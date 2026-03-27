# Cost Prediction Protocol

## When to Predict

Before starting medium+ complexity tasks, run cost prediction to set expectations:

| Complexity | Prediction Required? |
|------------|---------------------|
| Trivial | No |
| Small | Optional |
| Medium | Yes -- show prediction before proceeding |
| Large | Yes -- show prediction and get user confirmation |
| Critical | Yes -- show prediction and get explicit approval |

## How It Works

1. The `CostPredictor` (`lib/cost_predictor.py`) finds similar historical tasks using Jaccard similarity
2. It applies calibration factors from `estimation_calibrator` to adjust for known biases
3. It returns a prediction with confidence level and per-phase breakdown
4. After task completion, `task-recorder.sh` (Stop hook) records actual costs for future predictions

## Rules

- **Prices are ALWAYS based on real API responses when available.** The predictor calculates measured prices from `cost-events.jsonl`. It falls back to published defaults only when no historical data exists.
- **Never report estimated costs as actual costs.** Predictions are labeled with confidence levels. Only `cost-events.jsonl` entries represent real costs.
- **Show prediction before proceeding on medium+ tasks.** Include the confidence level so the user can decide whether to proceed.
- **Record actual costs after every significant task.** The `task-recorder.sh` Stop hook handles this automatically for sessions with cost > $0.01.
- **Calibration improves over time.** More recorded tasks means higher confidence predictions. The system is self-correcting.

## Integration

- **Hook**: `hooks/task-recorder.sh` (Stop) -- records completed task costs
- **Lib**: `lib/cost_predictor.py` -- prediction engine
- **Data**: `.cognitive-os/metrics/task-history.jsonl` -- historical task records
- **Data**: `.cognitive-os/metrics/cost-events.jsonl` -- raw API cost events

## Contextual Trigger

This rule is loaded when: cost prediction, estimate cost, budget, how much will this cost.
