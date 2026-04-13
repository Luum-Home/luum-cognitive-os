# scope: both
"""Process user messages: feedback detection + user model + prompt classification.
Called by user-prompt-capture.sh via: python3 lib/process_user_message.py"""
import sys, json, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

from lib.feedback_detector import FeedbackDetector
from lib.user_model import UserModel
from lib.prompt_classifier import classify_prompt

def process(message):
    results = {}

    # 1. Detect feedback
    try:
        detector = FeedbackDetector()
        signal = detector.detect(message)
        results["feedback_type"] = signal.type.value
        results["feedback_confidence"] = signal.confidence
    except Exception:
        results["feedback_type"] = "error"

    # 2. Infer user preferences
    try:
        model = UserModel()
        model.infer_from_message(message)
        results["inferred_prefs"] = len(model.preferences)
    except Exception:
        pass

    # 3. Classify prompt
    try:
        classification = classify_prompt(message)
        results["should_capture"] = classification.should_capture
        results["category"] = str(classification.category.value) if hasattr(classification.category, 'value') else str(classification.category)
    except Exception:
        results["should_capture"] = False

    return results

if __name__ == "__main__":
    msg = sys.stdin.read().strip()
    if msg:
        result = process(msg)
        print(json.dumps(result))
