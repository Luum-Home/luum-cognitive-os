# Task DAG — Dependency-Aware Agent Orchestration

## Purpose

Replaces manual dependency tracking in conversation with a formal Directed Acyclic Graph.
The orchestrator declares task dependencies and the system handles execution order,
parallelism detection, and state persistence across session crashes.

## When to Use a DAG

| Scenario | Use DAG? |
|----------|----------|
| Single independent task | No -- dispatch directly |
| 2-3 unrelated parallel tasks | No -- use WorkloadScheduler |
| Tasks with dependencies (A before B) | Yes |
| SDD pipeline (propose->spec->design->...) | Yes -- express as DAG |
| Complex feature with parallel + sequential work | Yes |
| Sprint with multiple interdependent tasks | Yes |

## Core API

```python
from lib.task_dag import TaskDAG

dag = TaskDAG(name="my-feature")
dag.add_task(id="research", description="...", prompt="...", model="sonnet")
dag.add_task(id="design", description="...", depends_on=["research"], model="opus")
dag.add_task(id="impl-a", description="...", depends_on=["design"])
dag.add_task(id="impl-b", description="...", depends_on=["design"])
dag.add_task(id="test", description="...", depends_on=["impl-a", "impl-b"])

# Get execution plan (waves of parallelizable tasks)
plan = dag.get_execution_plan()
# Wave 0: [research]
# Wave 1: [design]
# Wave 2: [impl-a, impl-b]  <- parallel
# Wave 3: [test]

# Get tasks ready to launch now
ready = dag.get_ready_tasks()

# Track state
dag.start_task("research", agent_id="agent-123")
dag.complete_task("research", result="findings...")
dag.fail_task("impl-a", error="build failed")
dag.retry_task("impl-a")  # moves back to READY

# Persist (survives crashes)
dag.save()
dag = TaskDAG.load("my-feature")
```

## Task State Machine

```
PENDING -> READY -> RUNNING -> COMPLETED
                          \-> FAILED -> READY (retry, max 3)
                                    \-> FAILED_FINAL (retries exhausted)
```

- PENDING: has unmet dependencies
- READY: all dependencies completed, launchable
- RUNNING: agent launched
- COMPLETED: agent finished successfully
- FAILED: agent failed, retryable
- FAILED_FINAL: retries exhausted, blocks all downstream tasks

## Orchestrator Protocol

### On task request with dependencies

1. Create a DAG: `dag = TaskDAG(name="feature-name")`
2. Add all tasks with their dependencies
3. Call `dag.get_ready_tasks()` to find initial tasks
4. Launch ready tasks as agents
5. Call `dag.save()` to persist

### On agent completion notification

1. Load the DAG: `dag = TaskDAG.load("feature-name")`
2. Call `dag.complete_task(task_id, result="...")`
3. Call `dag.get_ready_tasks()` to find newly unblocked tasks
4. Launch newly ready tasks
5. Call `dag.save()` to persist
6. If `dag.is_complete()`, report success to user
7. If `dag.is_blocked()`, report blockage to user

### On agent failure notification

1. Load the DAG
2. Call `dag.fail_task(task_id, error="...")`
3. If task has retries remaining, call `dag.retry_task(task_id)` then re-launch
4. If retries exhausted (FAILED_FINAL), report to user with diagnosis
5. Save DAG state

## Integration with Existing Systems

| System | Integration |
|--------|-------------|
| dispatch-gate.sh | DAG-launched tasks go through normal dispatch gate |
| queue_drainer.py | Tasks that can't launch (slots full) go into dispatch queue |
| WorkloadScheduler | DAG's get_ready_tasks() feeds into scheduler.plan() |
| crash recovery | DAG persists to .cognitive-os/tasks/dag-{name}.json |
| SDD pipeline | Can be expressed as a DAG via sdd_pipeline.py phases |
| active-tasks.json | DAG tasks should also be registered in active-tasks |

## Persistence

DAGs persist to `.cognitive-os/tasks/dag-{name}.json`. The file uses fcntl locking
for concurrent access safety. On session restart, load with `TaskDAG.load(name)`.

List all persisted DAGs: `TaskDAG.list_dags()`

## SDD as a DAG

The SDD pipeline is naturally a DAG:

```python
dag = TaskDAG(name=f"sdd-{change_name}")
dag.add_task(id="propose", model="opus", ...)
dag.add_task(id="spec", depends_on=["propose"], model="sonnet", ...)
dag.add_task(id="design", depends_on=["propose"], model="opus", ...)
dag.add_task(id="tasks", depends_on=["spec", "design"], model="sonnet", ...)
dag.add_task(id="apply", depends_on=["tasks"], model="sonnet", ...)
dag.add_task(id="verify", depends_on=["apply"], model="sonnet", ...)
dag.add_task(id="archive", depends_on=["verify"], model="haiku", ...)
```

Note: spec and design can run in parallel after propose.

## Contextual Trigger

This rule is loaded when: task DAG, dependency graph, execution waves, parallel tasks,
task dependencies, orchestration graph.
