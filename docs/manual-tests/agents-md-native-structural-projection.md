# Manual test — AGENTS.md-native structural harness projection

## Purpose

Verify account-free structural projection for Gemini CLI, Warp, Amp, JetBrains Junie, Qoder CLI, and Factory Droid, while keeping Kiro lifecycle hooks as an investigation-only surface.

## Preconditions

- Run from the Cognitive OS repository root.
- No paid IDE/CLI account is required.
- Do not install or launch vendor CLIs unless you are explicitly running optional smoke tests.

## Structural projection steps

```bash
for harness in gemini-cli warp amp-code jetbrains-junie qoder factory-droid; do
  tmp="$(mktemp -d)"
  (cd "$tmp" && python3 <repo-root>/scripts/cos_init.py --default --harness "$harness")
  echo "== $harness =="
  find "$tmp" -maxdepth 3 \
    \( -name 'AGENTS.md' -o -name 'GEMINI.md' -o -name 'settings.json' -o -name 'mcp.json' -o -name '.mcp.json' -o -name 'SKILL.md' \) \
    -print | sort
  rm -rf "$tmp"
done
```

## Expected files

| Harness | Expected project-local files |
|---|---|
| Gemini CLI | `GEMINI.md`, `.gemini/settings.json` |
| Warp | `AGENTS.md`, `.warp/README.md` |
| Amp | `AGENTS.md`, `.amp/settings.json` |
| JetBrains Junie | `.junie/AGENTS.md`, `.junie/README.md` |
| Qoder CLI | `AGENTS.md`, `.mcp.json`, `.qoder/settings.json` |
| Factory Droid | `AGENTS.md`, `.factory/mcp.json`, `.factory/settings.json`, `.factory/skills/cognitive-os/SKILL.md` |

## Kiro lifecycle investigation check

```bash
python3 - <<'PY'
import yaml
projection = yaml.safe_load(open('manifests/harness-projection.yaml'))
landscape = yaml.safe_load(open('manifests/ai-agent-harness-landscape.yaml'))
kiro_projection = next(item for item in projection['harnesses'] if item['id'] == 'kiro')
kiro_landscape = next(item for item in landscape['candidates'] if item['id'] == 'kiro')
print(kiro_projection['status'], kiro_projection['proof_level'])
print(kiro_landscape['status'], kiro_landscape['proof_level'])
PY
```

Expected:

- `kiro` remains projection `planned` with `proof_level: none`.
- landscape status is `lifecycle-investigation`.

## Automated validation

```bash
python3 -m pytest tests/behavior/test_consumer_project_projection.py -q
python3 -m pytest tests/contracts/test_acc_pipeline_contract.py tests/contracts/test_harness_implementation_phases.py tests/contracts/test_ai_agent_harness_landscape.py -q
python3 scripts/acc_pipeline.py --project-dir . --refresh --fail-new
```

## Optional runtime smoke

Only run these if the corresponding CLI/IDE and account credentials are already available. Record the result in a dated report before promoting any proof level beyond `structural`.

- Gemini CLI: run `gemini` from a temp consumer project and confirm `GEMINI.md` is referenced.
- Warp: open Agent Mode from a temp consumer project and confirm root `AGENTS.md` appears as project rules/context.
- Amp: run `amp -x` or interactive Amp from the temp project and confirm `AGENTS.md` / workspace settings are loaded.
- Qoder: run `qodercli` from the temp project and confirm `AGENTS.md`, `.mcp.json`, and `.qoder/settings.json` are recognized.
- Factory Droid: run `droid exec` from the temp project and confirm AGENTS.md plus the COS skill shim are discovered.
- JetBrains Junie: open the temp project in a licensed JetBrains IDE and confirm `.junie/AGENTS.md` is used.

Do not mark any optional smoke as passed unless the account-backed command or IDE run was actually executed.
