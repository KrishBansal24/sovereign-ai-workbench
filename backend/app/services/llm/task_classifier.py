"""Local task-family classifier used before registered model routing.

High-confidence patterns select coding or reasoning roles; ambiguous input
falls back to the general role instead of calling a cloud classifier.
"""

import re
from dataclasses import dataclass

from app.schemas.models import TaskType


@dataclass(frozen=True)
class Classification:
    """Typed classifier result consumed by ModelRouter."""
    task_type: TaskType
    confidence: float
    source: str


class TaskClassifier:
    """Scores task intent patterns; ambiguous work deliberately defaults to general reasoning."""

    def classify(self, message: str) -> Classification:
        """Classify a user task using explainable deterministic signals.

        Args:
            message: Raw user request to assign to an approved task family.

        Returns:
            The selected task type, confidence estimate, and decision source.
        """
        normalized = message.lower().strip()
        code_block = "```" in normalized or bool(re.search(r"\bdef\s+\w+\(|\bclass\s+\w+", normalized))
        coding_signals = sum(bool(re.search(pattern, normalized)) for pattern in (
            r"\b(write|implement|generate|refactor)\b.*\b(function|class|api|endpoint|script|algorithm|code)\b",
            r"\bpython\b.*\b(function|code|script|fastapi)\b",
            r"\b(typeerror|traceback|bug|debug|exception)\b",
        )) + int(code_block)
        if re.search(r"\b(typeerror|traceback|debug|exception|bug)\b", normalized) and re.search(r"\b(api|endpoint|python|code|fastapi|function)\b", normalized):
            return Classification("debugging", 0.93, "deterministic_signals")
        if coding_signals >= 2:
            task: TaskType = "debugging" if re.search(r"\b(debug|error|exception|traceback|typeerror)\b", normalized) else "coding"
            return Classification(task, 0.92, "deterministic_signals")
        if re.search(r"\b(explain|walk through|what does)\b.*\b(code|function|class|script)\b", normalized):
            return Classification("code_explanation", 0.9, "deterministic_signals")
        if re.search(r"\b(summarize|summary)\b.*\b(document|report|file|inspection)\b", normalized):
            return Classification("summarization", 0.9, "deterministic_signals")
        if re.search(r"\b(analyze|review|summarize)\b.*\b(uploaded|document|report|inspection)\b", normalized):
            return Classification("document_analysis", 0.88, "deterministic_signals")
        if re.search(r"\b(explain|why|causes|effects|importance|compare|analyze)\b", normalized):
            return Classification("reasoning", 0.78, "deterministic_signals")
        # Layer 3: low-confidence or ambiguous tasks use the safe general capability.
        return Classification("general", 0.45, "general_fallback")


task_classifier = TaskClassifier()
