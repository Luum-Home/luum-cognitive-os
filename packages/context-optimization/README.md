# @luum/context-optimization

Context window optimization — metrics calibration, rotation, and contextual rule loading

## Install

```bash
cos install @luum/context-optimization
```

## Components

- `hooks/metrics-calibrator-trigger.sh` (hook) -- Triggers metrics calibration based on accumulated data
- `hooks/metrics-rotation.sh` (hook) -- Rotates and archives old metrics files on session start
- `hooks/contextual-rule-loader.sh` (hook) -- Loads relevant rules based on file context at session start

## License

Apache-2.0
