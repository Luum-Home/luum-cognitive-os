# Execution Backends -- Multi-Environment Support

> Inspired by Hermes Agent's 6-backend model. Allows services to run across
> different environments without changing application code.

## Overview

The platform currently runs exclusively via Docker Compose. This document
defines a 6-backend execution model that decouples service orchestration from the
runtime environment, enabling local development without Docker, remote deployment
via SSH, serverless dev environments, sandboxed code execution, and GPU compute.

## Backend Matrix

| Backend | Use Case | Entry Point | Status |
|---------|----------|-------------|--------|
| **Local** | Development without Docker | `go run ./apps/{service}/cmd/main.go` | Available now |
| **Docker** | Standard local dev | `docker compose up -d` | Available now |
| **SSH** | Deploy to remote VPS | SSH tunnel + deploy script | Design phase |
| **Daytona** | Serverless dev environments | Daytona workspace config | Design phase |
| **E2B** | Sandboxed code execution | E2B API (code-interpreter SDK) | Mock available |
| **Modal** | Serverless GPU compute | Modal SDK | Future |

## Current State

### What works today

1. **Docker backend**: Full stack via root `docker-compose.yml` (21+ containers).
   Includes MySQL, MongoDB, Redis, RabbitMQ, Keycloak, BigQuery emulator,
   TigerBeetle, and all application services.

2. **Local backend** (Go services only): Each Go service in `backend-go/apps/`
   can be run directly with `go run`. Requires infrastructure services (databases,
   message brokers) to be running separately (typically via Docker).

3. **E2B mock**: `scripts/e2b-sandbox-test.ts` demonstrates sandboxed Python/JS
   execution via the E2B code-interpreter SDK. Currently used for testing
   sandboxed agent code execution, not for running application services.

### Legacy services (not yet migrated to Go)

| Service | Framework | Run Command |
|---------|-----------|-------------|
| BFF Ninja | NestJS 10 | `yarn start:dev` |
| Users Core | Spring Boot 3.0.6 | `./gradlew bootRun` |
| Users Auth | Spring Boot 3.0.6 | `./gradlew bootRun` |
| Onboarding | NestJS 10 | `yarn start:dev` |
| Monolith | Express.js | `yarn dev` |

These run locally without Docker but are being replaced by Go equivalents in
`backend-go/apps/`.

---

## Backend 1: Local

### Description

Run Go services directly on the host machine. Fastest feedback loop for
development. Infrastructure dependencies (MySQL, MongoDB, Redis, etc.) still
need to run somewhere -- typically via Docker or a remote instance.

### Go services available

| Service | Entry Point | Default Port |
|---------|-------------|--------------|
| wallet | `backend-go/apps/wallet/cmd/wallet/main.go` | 4010 |
| transfers-p2p | `backend-go/apps/transfers-p2p/cmd/main.go` | 4011 |
| users-auth | `backend-go/apps/users-auth/cmd/main.go` | 4012 |
| onboarding | `backend-go/apps/onboarding/cmd/main.go` | 4013 |
| users-core | `backend-go/apps/users-core/cmd/main.go` | 4014 |

### Configuration

Each service reads configuration from environment variables. Copy `.env.example`
to `.env` in the service directory, or export variables directly.

### Quick start

```bash
# 1. Start infrastructure only
docker compose up -d   # Start all infrastructure containers

# 2. Run Go services locally
scripts/run-local.sh          # All services
scripts/run-local.sh wallet   # Single service
```

### When to use

- Rapid iteration on a single service
- Debugging with IDE breakpoints (Delve)
- Running tests that need a live server
- When Docker rebuild times are too slow

---

## Backend 2: Docker

### Description

Full stack via `docker-compose.yml` at the repository root. This is the standard
development environment and the most complete option.

### Quick start

```bash
docker compose up -d           # Full stack
docker compose up -d wallet    # Single service + deps
docker compose logs -f wallet  # Follow logs
```

### When to use

- First-time setup
- Integration testing across services
- Reproducing production-like behavior
- CI/CD pipelines

---

## Backend 3: SSH

### Description

Deploy built Go binaries to a remote Linux host via SSH. Useful for testing on
cloud VMs, staging environments, or shared development servers.

### Architecture

```
Developer machine                    Remote host (VPS)
  go build -o bin/                     ~/app/bin/wallet
  scp bin/* remote:~/app/bin/          ~/app/bin/transfers-p2p
  ssh remote "systemctl start ..."     ~/app/bin/users-auth
                                       systemd manages lifecycle
```

### Required setup

1. SSH key-based access to the remote host
2. Go-compatible target OS/arch (typically `linux/amd64`)
3. Infrastructure services accessible from the remote host
4. systemd unit files or supervisor config for process management

### Deploy script usage (planned)

```bash
# Build and deploy all services
scripts/deploy-ssh.sh --host user@remote-host

# Deploy single service
scripts/deploy-ssh.sh --host user@remote-host --service wallet

# Deploy with custom binary path
scripts/deploy-ssh.sh --host user@remote-host --deploy-dir /opt/cognitive-os
```

### SSH config example

```
Host staging-server
    HostName 10.0.1.x
    User deploy
    IdentityFile ~/.ssh/deploy-key
    ForwardAgent yes
```

### systemd unit template

```ini
[Unit]
Description=Cognitive OS %i Service
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/cognitive-os
ExecStart=/opt/cognitive-os/bin/%i
EnvironmentFile=/opt/cognitive-os/env/%i.env
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### When to use

- Staging environment on a VPS
- Performance testing on production-like hardware
- Sharing a dev environment with team members
- Testing networking between services on a real network

---

## Backend 4: Daytona

### Description

Cloud-based development environments with full IDE support. Each developer gets
an isolated, pre-configured workspace that mirrors the local setup.

### Configuration

See `.daytona/config.yaml` for the workspace definition.

### Setup

```bash
# Install Daytona CLI
curl -sfL https://get.daytona.io | sh

# Create workspace from config
daytona create --config .daytona/config.yaml

# Open in IDE
daytona code my-platform
```

### What Daytona provides

- Pre-built Docker images with all dependencies
- Port forwarding for all services
- Git integration (branch per workspace)
- Shared workspaces for pair programming
- Prebuilds for faster startup

### When to use

- Onboarding new developers (zero local setup)
- Temporary feature environments
- Code review with a live environment
- When local machine resources are insufficient

---

## Backend 5: E2B (Sandboxed Execution)

### Description

E2B provides sandboxed Firecracker microVMs for executing untrusted code safely.
Currently used for agent code execution (running generated scripts in isolation),
not for running application services.

### Current integration

- `scripts/e2b-sandbox-test.ts` -- SDK integration test
- `scripts/package.json` -- E2B dependency (`@e2b/code-interpreter`)
- Mock mode available for development without API key

### Use cases

| Use Case | Description |
|----------|-------------|
| Agent code execution | Run AI-generated code safely |
| Data migration scripts | Execute one-off migration scripts in sandbox |
| User-submitted code | Future: run user plugins or extensions |
| Test isolation | Run integration tests without affecting host |

### Configuration

```bash
# Cloud mode (requires API key)
export E2B_API_KEY="e2b_..."
npx tsx scripts/e2b-sandbox-test.ts

# Self-hosted (future)
# See https://github.com/e2b-dev/infra for AWS/GCP deployment
```

### When to use

- Running untrusted or generated code
- Isolating destructive operations (DB migrations, cleanup scripts)
- Multi-tenant code execution (future)

---

## Backend 6: Modal (Future)

### Description

Serverless GPU compute platform. Pay-per-use, scales to zero, supports Python
and custom Docker images. Relevant for compute-intensive fintech workloads.

### Potential use cases

| Use Case | Why Modal |
|----------|-----------|
| ML-based fraud detection | GPU inference for transaction scoring |
| Batch financial calculations | Parallel processing of large datasets |
| Risk model training | GPU training without managing infrastructure |
| Document OCR/processing | Image processing for KYC documents |

### Integration pattern

```python
import modal

app = modal.App("cognitive-os-compute")

@app.function(gpu="T4", image=modal.Image.debian_slim().pip_install("torch"))
def score_transaction(tx_data: dict) -> float:
    """Run fraud scoring model on GPU."""
    model = load_model()
    return model.predict(tx_data)
```

### When to pursue

- After Go migration is complete (Sprint 4+)
- When ML models are ready for production inference
- When batch processing exceeds single-machine capacity

---

## Implementation Plan

### Phase 1: Document and Script (now)

- [x] Document all 6 backends (this file)
- [x] Create `scripts/run-local.sh` for local Go service execution
- [x] Create `.daytona/config.yaml` workspace definition

### Phase 2: SSH Backend (Sprint 3)

- [ ] Create `scripts/deploy-ssh.sh`
- [ ] Create systemd unit templates in `deploy/systemd/`
- [ ] Document required server provisioning
- [ ] Test with a single service (wallet) on a VPS

### Phase 3: Daytona Integration (Sprint 4)

- [ ] Set up Daytona server (self-hosted or cloud)
- [ ] Create prebuild configuration
- [ ] Test with full stack
- [ ] Document onboarding flow

### Phase 4: E2B Production (Sprint 5)

- [ ] Deploy self-hosted E2B on AWS (if cost-effective)
- [ ] Or configure cloud E2B with budget caps
- [ ] Integrate with agent code execution pipeline
- [ ] Add monitoring and usage tracking

### Phase 5: Modal Evaluation (Sprint 6+)

- [ ] Evaluate Modal vs AWS Lambda for batch workloads
- [ ] Prototype fraud scoring model deployment
- [ ] Cost analysis and comparison

---

## Backend Selection Guide

```
Need to run untrusted code?
  └─ Yes → E2B
  └─ No ↓

Need GPU compute?
  └─ Yes → Modal
  └─ No ↓

Deploying to remote server?
  └─ Yes → SSH
  └─ No ↓

Need isolated reproducible environment?
  └─ Yes → Daytona
  └─ No ↓

Working on a single service?
  └─ Yes → Local (go run)
  └─ No → Docker (full stack)
```

## Configuration Abstraction (Future)

To support backend switching, a unified configuration layer will be needed:

```yaml
# backends.yaml (future)
default: docker

backends:
  local:
    services: [wallet, transfers-p2p, users-auth, onboarding, users-core]
    infra: docker  # infrastructure still runs in Docker

  docker:
    compose_file: docker-compose.yml

  ssh:
    host: staging-server
    deploy_dir: /opt/cognitive-os
    services: [wallet, transfers-p2p]

  daytona:
    config: .daytona/config.yaml

  e2b:
    api_key_env: E2B_API_KEY
    mode: cloud  # or self-hosted

  modal:
    app_name: cognitive-os-compute
    functions: [score_transaction, batch_calculate]
```

This abstraction is not yet implemented. Each backend currently has its own
configuration and scripts.
