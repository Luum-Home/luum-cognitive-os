"""Record agent completion to learning pipeline."""
import sys, json, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

from lib.learning_pipeline import LearningPipeline

def main():
    data = json.loads(sys.stdin.read())
    output = str(data.get("tool_output", data.get("result", "")))

    success = not any(kw in output.upper() for kw in ["FAIL", "ERROR", "BLOCKED"])

    trust_score = 75
    match = re.search(r'SCORE=(\d+)', output)
    if match:
        trust_score = int(match.group(1))

    pipeline = LearningPipeline()
    result = pipeline.record_agent_completion(
        task_id=data.get("tool_call_id", "unknown"),
        success=success,
        trust_score=trust_score,
        skill_name=""
    )
    print(json.dumps({"action": str(result)}))

if __name__ == "__main__":
    main()
