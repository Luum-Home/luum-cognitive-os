## Benchmark Report -- {date}
### System: Cognitive OS v{version}
### Model: {model}
### Run ID: {run_id}

| Task | Time | Tokens | Files | Tests | Compiles | Architecture | Score |
|------|------|--------|-------|-------|----------|-------------|-------|
| create-go-service | Xs | N | N | N | pass/FAIL | N/10 | N/10 |
| fix-bug | Xs | N | N | N | pass/FAIL | -- | N/10 |
| add-endpoint | Xs | N | N | N | pass/FAIL | N/10 | N/10 |
| refactor-code | Xs | N | N | N | pass/FAIL | N/10 | N/10 |
| cross-service-feature | Xs | N | N | N | pass/FAIL | -- | N/10 |

### Overall Score: X/50
### Cost: $X.XX
### Total Time: Xm Xs
### Total Tokens: N

---

### Per-Task Details

#### 1. Create Go Service (create-go-service)

- **Prompt**: Create a new Go microservice called 'preferences' with CRUD endpoints...
- **Duration**: X seconds
- **Token usage**: N input + N output
- **Files created**: N (list key files)
- **Tests created**: N
- **Compilation**: pass/FAIL
- **Architecture score**: N/10
- **Notes**: (any observations)

#### 2. Fix Bug (fix-bug)

- **Prompt**: The transfers-p2p service crashes when amount is negative...
- **Duration**: X seconds
- **Bug fixed**: yes/no
- **Test added**: yes/no
- **Regression introduced**: yes/no
- **Notes**: (any observations)

#### 3. Add Endpoint (add-endpoint)

- **Prompt**: Add a GET /api/v1/user/:id/preferences endpoint...
- **Duration**: X seconds
- **Endpoint works**: yes/no
- **Follows patterns**: N/10
- **Test added**: yes/no
- **Notes**: (any observations)

#### 4. Refactor Code (refactor-code)

- **Prompt**: The admin service has business logic in controllers...
- **Duration**: X seconds
- **Logic moved**: yes/no
- **Tests pass**: yes/no
- **Architecture improved**: N/10
- **Notes**: (any observations)

#### 5. Cross-Service Feature (cross-service-feature)

- **Prompt**: When a user changes their email, notify via push notification...
- **Duration**: X seconds
- **Services touched**: N
- **Kafka event added**: yes/no
- **All services compile**: yes/no
- **Integration test added**: yes/no
- **Notes**: (any observations)

---

### Environment

- **Machine**: (hardware description)
- **OS**: (operating system version)
- **Claude CLI version**: (version)
- **Date**: {date}
- **Network conditions**: (notes on latency)

### Comparison Summary (fill after running both systems)

| Dimension | Cognitive OS | BMAD v6 | Delta |
|-----------|----------|---------|-------|
| Total time | | | |
| Total tokens | | | |
| Overall score | | | |
| Estimated cost | | | |
| Best at | | | |
| Weakest at | | | |
