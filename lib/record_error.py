# SCOPE: both
"""Record error to learning pipeline."""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

from lib.learning_pipeline import LearningPipeline

def main():
    data = json.loads(sys.stdin.read())
    exit_code = data.get("exit_code", 0)
    if exit_code == 0:
        return

    command = data.get("tool_input", {}).get("command", "")
    stderr = str(data.get("tool_output", {}).get("stderr", ""))

    pipeline = LearningPipeline()
    pipeline.record_error(
        error_type="COMMAND_FAILURE",
        service="unknown",
        message=stderr[:500],
        context=command[:200]
    )

if __name__ == "__main__":
    main()
