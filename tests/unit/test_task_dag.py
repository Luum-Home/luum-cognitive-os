"""Tests for lib/task_dag.py — Task DAG runner."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from lib.task_dag import TaskDAG, TaskNode, TaskStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_dag_dir(tmp_path):
    """Provide a temporary directory for DAG persistence."""
    dag_dir = str(tmp_path / "tasks")
    os.makedirs(dag_dir, exist_ok=True)
    return dag_dir


def _make_linear_dag(dag_dir: str) -> TaskDAG:
    """A -> B -> C linear chain."""
    dag = TaskDAG(name="linear", dag_dir=dag_dir)
    dag.add_task(id="a", description="Task A", prompt="do A")
    dag.add_task(id="b", description="Task B", prompt="do B", depends_on=["a"])
    dag.add_task(id="c", description="Task C", prompt="do C", depends_on=["b"])
    return dag


def _make_diamond_dag(dag_dir: str) -> TaskDAG:
    """A -> B, A -> C, B+C -> D diamond."""
    dag = TaskDAG(name="diamond", dag_dir=dag_dir)
    dag.add_task(id="a", description="Task A", prompt="do A")
    dag.add_task(id="b", description="Task B", prompt="do B", depends_on=["a"])
    dag.add_task(id="c", description="Task C", prompt="do C", depends_on=["a"])
    dag.add_task(id="d", description="Task D", prompt="do D", depends_on=["b", "c"])
    return dag


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAddTasksAndGetPlan:
    """test_add_tasks_and_get_plan — waves computed correctly."""

    def test_basic_waves(self, tmp_dag_dir):
        dag = _make_diamond_dag(tmp_dag_dir)
        plan = dag.get_execution_plan()
        assert len(plan) == 3
        assert plan[0] == ["a"]
        assert set(plan[1]) == {"b", "c"}
        assert plan[2] == ["d"]


class TestParallelTasksInSameWave:
    """test_parallel_tasks_in_same_wave — independent tasks grouped."""

    def test_independent_tasks(self, tmp_dag_dir):
        dag = TaskDAG(name="parallel", dag_dir=tmp_dag_dir)
        dag.add_task(id="x", description="X")
        dag.add_task(id="y", description="Y")
        dag.add_task(id="z", description="Z")
        plan = dag.get_execution_plan()
        assert len(plan) == 1
        assert set(plan[0]) == {"x", "y", "z"}


class TestSequentialDependencies:
    """test_sequential_dependencies — A->B->C in 3 waves."""

    def test_linear_chain(self, tmp_dag_dir):
        dag = _make_linear_dag(tmp_dag_dir)
        plan = dag.get_execution_plan()
        assert len(plan) == 3
        assert plan[0] == ["a"]
        assert plan[1] == ["b"]
        assert plan[2] == ["c"]


class TestDiamondDependency:
    """test_diamond_dependency — A->B,C->D works correctly."""

    def test_diamond(self, tmp_dag_dir):
        dag = _make_diamond_dag(tmp_dag_dir)
        plan = dag.get_execution_plan()
        assert plan[0] == ["a"]
        assert set(plan[1]) == {"b", "c"}
        assert plan[2] == ["d"]


class TestCycleDetection:
    """test_cycle_detection — A->B->A raises ValueError."""

    def test_direct_cycle(self, tmp_dag_dir):
        dag = TaskDAG(name="cycle", dag_dir=tmp_dag_dir)
        dag.add_task(id="a", description="A")
        dag.add_task(id="b", description="B", depends_on=["a"])
        # Manually create a cycle by modifying internals
        dag._tasks["a"].depends_on = ["b"]
        with pytest.raises(ValueError, match="Cycle detected"):
            dag.validate()

    def test_cycle_on_add(self, tmp_dag_dir):
        """Adding a task that creates a cycle should raise immediately."""
        dag = TaskDAG(name="cycle2", dag_dir=tmp_dag_dir)
        dag.add_task(id="a", description="A")
        dag.add_task(id="b", description="B", depends_on=["a"])
        # Now try to make a depend on b (cycle)
        dag._tasks["a"].depends_on = ["b"]
        with pytest.raises(ValueError, match="Cycle detected"):
            dag._detect_cycles()

    def test_self_cycle(self, tmp_dag_dir):
        """A task depending on itself should be detected."""
        dag = TaskDAG(name="self-cycle", dag_dir=tmp_dag_dir)
        dag.add_task(id="a", description="A")
        dag._tasks["a"].depends_on = ["a"]
        with pytest.raises(ValueError, match="Cycle detected"):
            dag.validate()


class TestGetReadyTasksWithCompletedDeps:
    """test_get_ready_tasks_with_completed_deps — only returns tasks whose deps are done."""

    def test_ready_after_completion(self, tmp_dag_dir):
        dag = _make_linear_dag(tmp_dag_dir)

        # Initially only 'a' is ready (no deps)
        ready = dag.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "a"

        # Complete 'a' -> 'b' becomes ready
        dag.start_task("a")
        dag.complete_task("a", result="done")
        ready = dag.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "b"

        # Complete 'b' -> 'c' becomes ready
        dag.start_task("b")
        dag.complete_task("b")
        ready = dag.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "c"


class TestGetReadyTasksWithIncompleteDeps:
    """test_get_ready_tasks_with_incomplete_deps — blocks correctly."""

    def test_blocks_when_deps_incomplete(self, tmp_dag_dir):
        dag = _make_diamond_dag(tmp_dag_dir)

        # Complete 'a', start 'b' but not 'c'
        dag.start_task("a")
        dag.complete_task("a")
        ready = dag.get_ready_tasks()
        assert set(t.id for t in ready) == {"b", "c"}

        # Start and complete 'b', 'c' still pending -> 'd' not ready
        dag.start_task("b")
        dag.complete_task("b")
        ready = dag.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "c"  # c is ready but d is not (c not done)


class TestCompleteTaskUpdatesStatus:
    """test_complete_task_updates_status."""

    def test_status_transitions(self, tmp_dag_dir):
        dag = TaskDAG(name="status", dag_dir=tmp_dag_dir)
        dag.add_task(id="t1", description="Task 1")

        assert dag.get_task("t1").status == TaskStatus.READY

        dag.start_task("t1")
        assert dag.get_task("t1").status == TaskStatus.RUNNING
        assert dag.get_task("t1").started_at is not None

        dag.complete_task("t1", result="success")
        assert dag.get_task("t1").status == TaskStatus.COMPLETED
        assert dag.get_task("t1").result == "success"
        assert dag.get_task("t1").completed_at is not None

    def test_cannot_complete_non_running(self, tmp_dag_dir):
        dag = TaskDAG(name="bad-complete", dag_dir=tmp_dag_dir)
        dag.add_task(id="t1", description="Task 1")
        with pytest.raises(ValueError, match="expected 'running'"):
            dag.complete_task("t1")


class TestFailTaskBlocksDownstream:
    """test_fail_task_blocks_downstream."""

    def test_failed_final_blocks_children(self, tmp_dag_dir):
        dag = _make_linear_dag(tmp_dag_dir)

        dag.start_task("a")
        # Fail a with max_retries=1 so it immediately goes FAILED_FINAL
        dag._tasks["a"].max_retries = 1
        dag.fail_task("a", error="boom")
        assert dag.get_task("a").status == TaskStatus.FAILED_FINAL

        # b and c should remain PENDING (blocked)
        ready = dag.get_ready_tasks()
        assert len(ready) == 0
        assert dag.is_blocked()


class TestRetryOnFailure:
    """test_retry_on_failure — retries up to max, then FAILED_FINAL."""

    def test_retry_cycle(self, tmp_dag_dir):
        dag = TaskDAG(name="retry", dag_dir=tmp_dag_dir)
        dag.add_task(id="t1", description="Task 1", max_retries=3)

        # Attempt 1
        dag.start_task("t1")
        dag.fail_task("t1", error="err1")
        assert dag.get_task("t1").status == TaskStatus.FAILED
        assert dag.get_task("t1").retries == 1

        # Retry -> back to READY
        dag.retry_task("t1")
        assert dag.get_task("t1").status == TaskStatus.READY

        # Attempt 2
        dag.start_task("t1")
        dag.fail_task("t1", error="err2")
        assert dag.get_task("t1").retries == 2
        dag.retry_task("t1")

        # Attempt 3 - should go FAILED_FINAL
        dag.start_task("t1")
        dag.fail_task("t1", error="err3")
        assert dag.get_task("t1").status == TaskStatus.FAILED_FINAL
        assert dag.get_task("t1").retries == 3

        # Cannot retry FAILED_FINAL
        with pytest.raises(ValueError, match="expected 'failed'"):
            dag.retry_task("t1")


class TestSaveAndLoadRoundtrip:
    """test_save_and_load_roundtrip — persistence works."""

    def test_roundtrip(self, tmp_dag_dir):
        dag = _make_diamond_dag(tmp_dag_dir)

        # Complete some tasks
        dag.start_task("a")
        dag.complete_task("a", result="research done")

        # Save
        path = dag.save()
        assert os.path.isfile(path)

        # Load
        loaded = TaskDAG.load("diamond", dag_dir=tmp_dag_dir)
        assert loaded.name == "diamond"
        assert loaded.task_count == 4
        assert loaded.get_task("a").status == TaskStatus.COMPLETED
        assert loaded.get_task("a").result == "research done"
        assert loaded.get_task("b").status == TaskStatus.READY
        assert loaded.get_task("d").status == TaskStatus.PENDING

    def test_load_nonexistent(self, tmp_dag_dir):
        with pytest.raises(FileNotFoundError):
            TaskDAG.load("nonexistent", dag_dir=tmp_dag_dir)


class TestFormatStatus:
    """test_format_status — readable output."""

    def test_format_includes_key_info(self, tmp_dag_dir):
        dag = _make_linear_dag(tmp_dag_dir)
        dag.start_task("a")
        dag.complete_task("a")

        status = dag.format_status()
        assert "linear:" in status
        assert "1/3 completed" in status
        assert "completed" in status
        assert "a" in status
        assert "b" in status
        assert "c" in status

    def test_format_blocked(self, tmp_dag_dir):
        dag = _make_linear_dag(tmp_dag_dir)
        dag._tasks["a"].max_retries = 1
        dag.start_task("a")
        dag.fail_task("a", error="boom")
        status = dag.format_status()
        assert "BLOCKED" in status


class TestEmptyDag:
    """test_empty_dag — edge case."""

    def test_empty(self, tmp_dag_dir):
        dag = TaskDAG(name="empty", dag_dir=tmp_dag_dir)
        assert dag.task_count == 0
        assert dag.get_ready_tasks() == []
        assert dag.get_execution_plan() == []
        assert dag.is_complete() is True  # vacuously true
        assert dag.is_blocked() is False


class TestSingleTaskNoDeps:
    """test_single_task_no_deps — trivial DAG."""

    def test_single(self, tmp_dag_dir):
        dag = TaskDAG(name="single", dag_dir=tmp_dag_dir)
        dag.add_task(id="only", description="The only task")

        plan = dag.get_execution_plan()
        assert plan == [["only"]]

        ready = dag.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "only"
        assert ready[0].status == TaskStatus.READY

        dag.start_task("only")
        dag.complete_task("only")
        assert dag.is_complete()


class TestComplexDag6Tasks:
    """test_complex_dag_6_tasks — the full example from the API design."""

    def test_full_example(self, tmp_dag_dir):
        dag = TaskDAG(name="implement-auth", dag_dir=tmp_dag_dir)

        dag.add_task(
            id="research-auth",
            description="Research auth patterns",
            prompt="research prompt",
            model="sonnet",
        )
        dag.add_task(
            id="research-db",
            description="Research DB schema",
            prompt="db prompt",
            model="sonnet",
        )
        dag.add_task(
            id="design-arch",
            description="Design architecture",
            prompt="design prompt",
            model="opus",
            depends_on=["research-auth", "research-db"],
        )
        dag.add_task(
            id="impl-auth",
            description="Implement auth",
            prompt="impl auth prompt",
            depends_on=["design-arch"],
        )
        dag.add_task(
            id="impl-db",
            description="Implement DB",
            prompt="impl db prompt",
            depends_on=["design-arch"],
        )
        dag.add_task(
            id="integration-test",
            description="Integration testing",
            prompt="test prompt",
            depends_on=["impl-auth", "impl-db"],
        )

        # Verify execution plan
        plan = dag.get_execution_plan()
        assert len(plan) == 4
        assert set(plan[0]) == {"research-auth", "research-db"}
        assert plan[1] == ["design-arch"]
        assert set(plan[2]) == {"impl-auth", "impl-db"}
        assert plan[3] == ["integration-test"]

        # Wave 0: launch parallel research
        ready = dag.get_ready_tasks()
        assert set(t.id for t in ready) == {"research-auth", "research-db"}

        # Complete research
        dag.start_task("research-auth")
        dag.start_task("research-db")
        dag.complete_task("research-auth", result="auth patterns found")
        dag.complete_task("research-db", result="schema designed")

        # Wave 1: design becomes ready
        ready = dag.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "design-arch"

        dag.start_task("design-arch")
        dag.complete_task("design-arch")

        # Wave 2: parallel implementation
        ready = dag.get_ready_tasks()
        assert set(t.id for t in ready) == {"impl-auth", "impl-db"}

        dag.start_task("impl-auth")
        dag.start_task("impl-db")
        dag.complete_task("impl-auth")
        dag.complete_task("impl-db")

        # Wave 3: integration test
        ready = dag.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "integration-test"

        dag.start_task("integration-test")
        dag.complete_task("integration-test")

        assert dag.is_complete()
        assert dag.completed_count() == 6
        assert dag.failed_count() == 0

        # Persistence roundtrip
        dag.save()
        loaded = TaskDAG.load("implement-auth", dag_dir=tmp_dag_dir)
        assert loaded.is_complete()
        assert loaded.completed_count() == 6


class TestDuplicateTaskId:
    """Adding a task with a duplicate ID raises ValueError."""

    def test_duplicate(self, tmp_dag_dir):
        dag = TaskDAG(name="dup", dag_dir=tmp_dag_dir)
        dag.add_task(id="a", description="A")
        with pytest.raises(ValueError, match="already exists"):
            dag.add_task(id="a", description="A again")


class TestMissingDependency:
    """Adding a task with a nonexistent dependency raises ValueError."""

    def test_missing_dep(self, tmp_dag_dir):
        dag = TaskDAG(name="missing", dag_dir=tmp_dag_dir)
        with pytest.raises(ValueError, match="not found"):
            dag.add_task(id="b", description="B", depends_on=["nonexistent"])


class TestListAndDeleteDags:
    """Test list_dags and delete methods."""

    def test_list_and_delete(self, tmp_dag_dir):
        dag1 = TaskDAG(name="alpha", dag_dir=tmp_dag_dir)
        dag1.add_task(id="t1", description="T1")
        dag1.save()

        dag2 = TaskDAG(name="beta", dag_dir=tmp_dag_dir)
        dag2.add_task(id="t2", description="T2")
        dag2.save()

        names = TaskDAG.list_dags(dag_dir=tmp_dag_dir)
        assert "alpha" in names
        assert "beta" in names

        dag1.delete()
        names = TaskDAG.list_dags(dag_dir=tmp_dag_dir)
        assert "alpha" not in names
        assert "beta" in names


class TestRemoveTask:
    """Removing a task cleans up dependencies."""

    def test_remove(self, tmp_dag_dir):
        dag = _make_linear_dag(tmp_dag_dir)
        dag.remove_task("b")
        # c no longer depends on b
        assert dag.get_task("c").depends_on == []
        plan = dag.get_execution_plan()
        # a and c should be in the same wave (independent)
        assert len(plan) == 1
        assert set(plan[0]) == {"a", "c"}


class TestFormatExecutionPlan:
    """Test the execution plan formatter."""

    def test_format(self, tmp_dag_dir):
        dag = _make_diamond_dag(tmp_dag_dir)
        output = dag.format_execution_plan()
        assert "Wave 0" in output
        assert "Wave 1" in output
        assert "Wave 2" in output
        assert "[parallel]" in output

    def test_empty_format(self, tmp_dag_dir):
        dag = TaskDAG(name="empty", dag_dir=tmp_dag_dir)
        output = dag.format_execution_plan()
        assert "empty DAG" in output


class TestRepr:
    """Test __repr__."""

    def test_repr(self, tmp_dag_dir):
        dag = _make_linear_dag(tmp_dag_dir)
        r = repr(dag)
        assert "linear" in r
        assert "tasks=3" in r
