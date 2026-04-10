# Cognitive OS -- 5 Minute Quickstart

## Install

```bash
# Clone the Cognitive OS source (one-time)
git clone https://github.com/luum-home/luum-agent-os.git ~/.cognitive-os-src

# cd into YOUR PROJECT, then run the installer
cd /path/to/your/project
bash ~/.cognitive-os-src/scripts/cos-init.sh
```

> The installer installs into the **current directory**. Always `cd` into your project first.

## That's it. Start coding.

The AI already knows about:
- **Quality gates** -- verifies its own work before claiming done
- **Error learning** -- captures mistakes, warns on repeat patterns
- **Safe operations** -- won't delete what it shouldn't

No Docker, Python, or Go required for core features.

## Want more?

```bash
bash ~/.cognitive-os-src/scripts/cos-init.sh --full  # or --minimal / --standard
```

## What works without Docker?

| Feature | Docker? | Python? | Go? |
|---------|---------|---------|-----|
| Core rules + hooks | No | No | No |
| SDD pipeline | No | No | No |
| Safety mesh | No | No | No |
| Error learning | No | No | No |
| cos-test TUI | No | No | Yes |
| Performance monitor | No | Yes | No |
| Cost dashboard | No | Yes | No |
| Testcontainers | Yes | Yes | No |
| Langfuse/Opik | Yes | No | No |
| Agent Bus (Valkey) | Yes | Yes | No |

## Upgrade

```bash
bash ~/.cognitive-os-src/scripts/upgrade.sh
```

## Uninstall

```bash
bash ~/.cognitive-os-src/scripts/uninstall.sh
```
